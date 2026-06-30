#!/usr/bin/env python3
"""
Scraper del catálogo de mercado de Tiendas D1 (domicilios.tiendasd1.com).

La tienda corre sobre Instaleap (Next.js + Apollo GraphQL). Este script habla
directo con el API GraphQL headless de Instaleap, descubierto por ingeniería
inversa del bundle del sitio:

  - Endpoint : https://nextgentheadless.instaleap.io/api/v3
  - Header   : Apikey: <dplApiKey embebido en la página>
  - clientId : "D1"   storeReference: "12109"

Operaciones usadas:
  GetCategoryTree(getCategoryInput)        -> árbol de categorías
  GetProductsByCategory(...Input)          -> productos paginados por categoría
        input: { clientId, storeReference, categoryReference, currentPage, pageSize }

Salida: data/d1_catalog.json  (lista de productos deduplicada por SKU)

Uso:
    python scripts/scrape_d1.py
"""
import json
import time
import os
import sys
import urllib.request

ENDPOINT = "https://nextgentheadless.instaleap.io/api/v3"
APIKEY = "cbc45b69-89da-4f99-b846-cd9928610b8e"
CLIENT_ID = "D1"
STORE_REFERENCE = "12109"
ORIGIN = "https://domicilios.tiendasd1.com"

# Top-level categories que cuentan como "mercado" (excluye aseo, cuidado
# personal, bebé, mascotas). Se filtra por el `reference` de nivel raíz.
MARKET_TOPLEVEL = {
    "LO NUEVO",
    "EXTRAORDINARIOS",
    "CONGELADOS",
    "ALIMENTOS Y DESPENSA",
    "LACTEOS", "LÁCTEOS",
    "BEBIDAS",
    "OTROS",
}

PAGE_SIZE = 100
REQUEST_DELAY = 0.25  # segundos entre requests (cortesía)

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Campos escalares de CatalogProductModel que nos interesan.
PRODUCT_FIELDS = (
    "name price priceBeforeTaxes previousPrice photosUrl unit subUnit subQty "
    "sku ean brand slug stock isAvailable isActive maxQty minQty location nutritionalDetails"
)

CATEGORY_FIELDS = "reference name level hasChildren isAssociatedToCatalog categoryNamesPath"


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Apikey", APIKEY)
    req.add_header("Origin", ORIGIN)
    req.add_header("User-Agent", "Mozilla/5.0")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
            if "errors" in data:
                raise RuntimeError(data["errors"][0].get("message", "GraphQL error"))
            return data["data"]
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    return None


def get_category_tree():
    cf = CATEGORY_FIELDS
    sub = "subCategories{%s subCategories{%s subCategories{%s}}}" % (cf, cf, cf)
    q = "query GetCategoryTree($i: GetCategoryInput!){getCategory(getCategoryInput:$i){%s %s}}" % (cf, sub)
    data = gql(q, {"i": {"clientId": CLIENT_ID, "storeReference": STORE_REFERENCE}})
    return data["getCategory"]


def iter_nodes(node, path=()):
    """Recorre un nodo y sus descendientes; yields (node, path_de_nombres)."""
    here = path + (node["name"],)
    yield node, here
    for child in (node.get("subCategories") or []):
        yield from iter_nodes(child, here)


def fetch_category_products(reference):
    """Pagina una categoría completa y devuelve la lista de productos."""
    q = ("query GetProductsByCategory($i: GetProductsByCategoryInput!){"
         "getProductsByCategory(getProductsByCategoryInput:$i){"
         "category{products{%s}} pagination{page pages total{value}}}}" % PRODUCT_FIELDS)
    out = []
    page = 1
    while True:
        variables = {"i": {
            "clientId": CLIENT_ID,
            "storeReference": STORE_REFERENCE,
            "categoryReference": reference,
            "currentPage": page,
            "pageSize": PAGE_SIZE,
        }}
        data = gql(q, variables)
        block = data["getProductsByCategory"]
        out.extend(block["category"]["products"])
        pages = block["pagination"]["pages"] or 1
        if page >= pages:
            break
        page += 1
        time.sleep(REQUEST_DELAY)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Descargando árbol de categorías…")
    tops = get_category_tree()
    market_tops = [t for t in tops if t["reference"].strip().upper() in MARKET_TOPLEVEL]
    print("Categorías raíz de mercado:", ", ".join(t["name"] for t in market_tops))

    # Recolecta TODOS los nodos (padres + hojas) de las raíces de mercado.
    # Consultar cada nodo y deduplicar por SKU garantiza cobertura completa
    # sin depender de la semántica hoja/padre del catálogo.
    nodes = []
    seen_ref = set()
    for top in market_tops:
        for node, path in iter_nodes(top):
            ref = node["reference"]
            if ref in seen_ref:
                continue
            seen_ref.add(ref)
            nodes.append((node, path))

    print(f"Nodos de categoría a consultar: {len(nodes)}")

    products = {}  # sku -> producto
    for idx, (node, path) in enumerate(nodes, 1):
        ref = node["reference"]
        try:
            items = fetch_category_products(ref)
        except Exception as e:  # noqa: BLE001
            print(f"  [{idx}/{len(nodes)}] ⚠ {ref}: {e}")
            continue
        new = 0
        for p in items:
            sku = p.get("sku")
            if not sku:
                continue
            if sku not in products:
                p["categoryPath"] = " > ".join(path[1:])  # sin el top-level repetido
                p["topCategory"] = path[0]
                products[sku] = p
                new += 1
        print(f"  [{idx}/{len(nodes)}] {node['name'][:34]:34} {len(items):4d} items (+{new} nuevos) | total {len(products)}")
        time.sleep(REQUEST_DELAY)

    catalog = sorted(products.values(), key=lambda p: (p.get("topCategory", ""), p.get("name", "")))
    out_path = os.path.join(OUT_DIR, "d1_catalog.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    print(f"\nOK: {len(catalog)} productos unicos -> {out_path}")
    # resumen por categoría raíz
    by_top = {}
    for p in catalog:
        by_top[p.get("topCategory", "?")] = by_top.get(p.get("topCategory", "?"), 0) + 1
    for k in sorted(by_top):
        print(f"    {k:24} {by_top[k]}")


if __name__ == "__main__":
    sys.exit(main())
