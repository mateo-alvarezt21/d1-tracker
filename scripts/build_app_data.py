#!/usr/bin/env python3
"""
Genera app-data.js a partir del catálogo real de D1 (data/d1_catalog.json).

La data de la app parte de productos REALES de D1; las recetas se construyen
referenciando esos productos por SKU, y la lista de compras (shopBase) se deriva
de los productos seleccionados. Así nombres, precios y la canasta salen del
catálogo oficial.

Realismo de presupuesto: cada receta tiene un `tier` (economica | estandar).
El plan de comidas en la app escoge platos económicos (arroz con huevo, arroz
con lenteja, spaghetti sencillo...) cuando el presupuesto por persona/día es
bajo, tal como resolvería un hogar colombiano.

Nota: el huevo NO está en el catálogo online de domicilios (solo dulces), pero
es la base del plato económico colombiano por excelencia. Se agrega como staple
de TIENDA FÍSICA con precio realista de D1 (marcado `tienda: true`).

Salida: app-data.js -> window.D1_DATA = { dietList, dayNames, products,
recipes, mealPools, shopBase }

Uso:  python scripts/build_app_data.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, "data", "d1_catalog.json")
OUT = os.path.join(ROOT, "app-data.js")

# --- Productos del catálogo real ---------------------------------------------
# sku -> (nombre corto UI, categoría lista, qty base 7 días/4 personas)
PICK = {
    # Granos y cereales
    "12005770": ("Arroz Albar 2500g",            "Granos y cereales", 2),
    "12000066": ("Spaghetti Capríssima 250g",    "Granos y cereales", 2),
    "12000067": ("Concha Capríssima 250g",       "Granos y cereales", 1),
    "12000040": ("Fríjol cargamanto El Estío",   "Granos y cereales", 1),
    "12000042": ("Lenteja El Estío 500g",        "Granos y cereales", 1),
    "12000044": ("Garbanzo El Estío 500g",       "Granos y cereales", 1),
    "12000043": ("Maíz pira El Estío 500g",      "Granos y cereales", 1),
    "12001209": ("Harina de maíz Quicksy 1kg",   "Granos y cereales", 1),
    "12000645": ("Pasta lasaña Deliziare 450g",  "Granos y cereales", 1),
    "12003213": ("Avena Latti 900ml",            "Granos y cereales", 1),
    # Proteínas y enlatados
    "12004370": ("Atún en agua Carlo Forte",     "Proteínas y enlatados", 2),
    "12000389": ("Atún rallado El Navío",        "Proteínas y enlatados", 2),
    "12000077": ("Jamón de cerdo Viandí 400g",   "Proteínas y enlatados", 1),
    "12000360": ("Jamón de pollo Brakel 250g",   "Proteínas y enlatados", 1),
    "12000591": ("Salchichón de pollo Viandí",   "Proteínas y enlatados", 1),
    "12000575": ("Hamburguesa de res Viandí",    "Proteínas y enlatados", 1),
    "12000289": ("Chile con carne Crachos 300g", "Proteínas y enlatados", 1),
    # Lácteos
    "12000052": ("Leche entera Latti 1L",        "Lácteos", 4),
    "12003513": ("Leche en polvo Latti 350g",    "Lácteos", 1),
    "12002431": ("Yogurt Latti vaso 150g",       "Lácteos", 4),
    "12005836": ("Yogur con granola Vita Latti", "Lácteos", 2),
    "12000076": ("Dulce de leche Latti 250g",    "Lácteos", 1),
    # Panadería y arepas
    "12000024": ("Arepa de chócolo Masmaí",      "Panadería y arepas", 2),
    "12000025": ("Arepa de queso Masmaí",        "Panadería y arepas", 2),
    "12000069": ("Pan leche Horneaditos x10",    "Panadería y arepas", 1),
    "12000239": ("Pandequeso Horneaditos x4",    "Panadería y arepas", 1),
    # Verduras
    "12007453": ("Papa criolla 1kg",             "Verduras", 1),
    "12002258": ("Zanahoria 1kg",                "Verduras", 1),
    # Condimentos y salsas
    "12000775": ("Aceite girasol Don Olio 2L",   "Condimentos y salsas", 1),
    "12002874": ("Sal Refisal 1kg",              "Condimentos y salsas", 1),
    "12000249": ("Azúcar blanca Riopaila 1kg",   "Condimentos y salsas", 1),
    "12000121": ("Panela El Refugio 1kg",        "Condimentos y salsas", 1),
    "12000266": ("Salsa de tomate ZEV 500g",     "Condimentos y salsas", 1),
    "12000264": ("Pasta de tomate ZEV 200g",     "Condimentos y salsas", 1),
    "12002266": ("Base salsa boloñesa Rico",     "Condimentos y salsas", 1),
    "12003293": ("Ajo granulado Speciaria",      "Condimentos y salsas", 1),
    "12003282": ("Canela molida Speciaria",      "Condimentos y salsas", 1),
    # Bebidas
    "12000333": ("Café granulado Viejo Molino",  "Bebidas", 1),
}

# Staples que NO están en el catálogo online pero sí en tienda física D1.
# Precio realista de referencia (COP). Se marcan `tienda: true`.
EXTRA = {
    "T-huevo": dict(name="Huevos rojos AA x30", brand="D1", price=13900,
                    subQty=30, subUnit="und", cat="Proteínas y enlatados", qty=1),
}

CAT_ORDER = [
    "Proteínas y enlatados", "Lácteos", "Granos y cereales",
    "Panadería y arepas", "Verduras", "Condimentos y salsas", "Bebidas",
]

# --- Recetas: ingredientes referencian SKUs; cada una con tier ----------------
# ing = (sku, "porción visible", fracción del paquete consumida)
RECIPES = {
    # ====== ECONÓMICAS (presupuesto apretado) ======
    "be1": dict(name="Agua de panela con pan", type="Desayuno", tier="economica",
                time="8 min", cal=300, nut=("8 g", "58 g", "4 g"),
                ing=[("12000121", "Panela", 0.1), ("12000069", "Pan leche", 0.3)],
                steps=["Disuelve la panela en agua caliente.",
                       "Sirve el agua de panela bien caliente.",
                       "Acompaña con pan."]),
    "be2": dict(name="Avena con panela", type="Desayuno", tier="economica",
                time="8 min", cal=320, nut=("9 g", "54 g", "6 g"),
                ing=[("12003213", "Avena Latti", 0.5), ("12000121", "Panela", 0.05),
                     ("12003282", "Canela", 0.1)],
                steps=["Calienta la avena con un trozo de panela.",
                       "Agrega una pizca de canela y revuelve.",
                       "Sirve caliente."]),
    "be3": dict(name="Arepa de chócolo con café", type="Desayuno", tier="economica",
                time="10 min", cal=340, nut=("9 g", "50 g", "9 g"),
                ing=[("12000024", "Arepa de chócolo", 0.4), ("12000333", "Café", 0.04),
                     ("12000249", "Azúcar", 0.03)],
                steps=["Asa la arepa de chócolo por ambos lados.",
                       "Prepara el café con agua caliente y azúcar.",
                       "Sirve la arepa con el café."]),
    "le1": dict(name="Arroz con huevo", type="Almuerzo", tier="economica",
                time="15 min", cal=480, nut=("16 g", "62 g", "16 g"),
                ing=[("12005770", "Arroz Albar", 0.25), ("T-huevo", "2 huevos", 2/30),
                     ("12000775", "Aceite", 0.015), ("12002874", "Sal", 0.01)],
                steps=["Prepara el arroz blanco con sal.",
                       "Fríe los huevos en un poco de aceite.",
                       "Sirve el arroz con los huevos encima."]),
    "le2": dict(name="Arroz con lenteja", type="Almuerzo", tier="economica",
                time="30 min", cal=520, nut=("20 g", "84 g", "8 g"),
                ing=[("12005770", "Arroz Albar", 0.25), ("12000042", "Lenteja", 0.4),
                     ("12003293", "Ajo granulado", 0.08), ("12000775", "Aceite", 0.015)],
                steps=["Cocina la lenteja con ajo y sal hasta ablandar.",
                       "Prepara el arroz blanco aparte.",
                       "Sirve la lenteja sobre el arroz."]),
    "le3": dict(name="Spaghetti sencillo con salsa", type="Almuerzo", tier="economica",
                time="20 min", cal=460, nut=("13 g", "82 g", "9 g"),
                ing=[("12000066", "Spaghetti Capríssima", 1.0),
                     ("12000266", "Salsa de tomate ZEV", 0.3),
                     ("12000775", "Aceite", 0.01)],
                steps=["Cocina el spaghetti en agua con sal.",
                       "Calienta la salsa de tomate con un toque de aceite.",
                       "Mezcla la pasta con la salsa y sirve."]),
    "de1": dict(name="Huevo con arepa", type="Cena", tier="economica",
                time="12 min", cal=380, nut=("16 g", "40 g", "16 g"),
                ing=[("T-huevo", "2 huevos", 2/30), ("12000024", "Arepa de chócolo", 0.4),
                     ("12000775", "Aceite", 0.015), ("12002874", "Sal", 0.01)],
                steps=["Asa la arepa de chócolo.",
                       "Fríe los huevos con un poco de aceite y sal.",
                       "Sirve los huevos sobre la arepa."]),
    "de2": dict(name="Sopa de concha con verduras", type="Cena", tier="economica",
                time="25 min", cal=360, nut=("11 g", "66 g", "6 g"),
                ing=[("12000067", "Concha Capríssima", 1.0), ("12002258", "Zanahoria", 0.2),
                     ("12007453", "Papa criolla", 0.2), ("12003293", "Ajo granulado", 0.08)],
                steps=["Pica la zanahoria y la papa criolla.",
                       "Cocínalas en agua con ajo y sal.",
                       "Agrega la pasta concha y cocina hasta ablandar.",
                       "Sirve la sopa caliente."]),
    "de3": dict(name="Calentado de fríjol", type="Cena", tier="economica",
                time="15 min", cal=440, nut=("18 g", "60 g", "11 g"),
                ing=[("12000040", "Fríjol cargamanto", 0.3), ("12005770", "Arroz Albar", 0.15),
                     ("12000024", "Arepa de chócolo", 0.4), ("12000775", "Aceite", 0.01)],
                steps=["Calienta el fríjol y el arroz juntos con un toque de aceite.",
                       "Revuelve a fuego medio unos 5 minutos.",
                       "Asa la arepa y sirve el calentado al lado."]),
    # ====== ESTÁNDAR (presupuesto holgado) ======
    "b1": dict(name="Arepa de queso con café", type="Desayuno", tier="estandar",
               time="10 min", cal=380, nut=("14 g", "44 g", "15 g"),
               ing=[("12000025", "2 arepas de queso", 0.4), ("12000333", "Café", 0.05),
                    ("12000052", "Leche entera", 0.2)],
               steps=["Asa las arepas de queso por ambos lados hasta dorar.",
                      "Prepara el café con leche al gusto.",
                      "Sirve las arepas calientes con el café con leche."]),
    "b2": dict(name="Avena con dulce de leche", type="Desayuno", tier="estandar",
               time="8 min", cal=340, nut=("9 g", "52 g", "8 g"),
               ing=[("12003213", "Avena Latti", 0.5), ("12000076", "Dulce de leche", 0.2),
                    ("12000121", "Panela", 0.05)],
               steps=["Calienta la avena con un trozo de panela.",
                      "Sirve y decora con un hilo de dulce de leche."]),
    "b4": dict(name="Yogur con granola", type="Desayuno", tier="estandar",
               time="3 min", cal=240, nut=("8 g", "38 g", "6 g"),
               ing=[("12005836", "Yogur con granola Vita Latti", 1.0),
                    ("12000121", "Panela en polvo", 0.03)],
               steps=["Sirve el yogur con granola en un tazón.",
                      "Espolvorea un toque de panela por encima."]),
    "l1": dict(name="Arroz con atún y zanahoria", type="Almuerzo", tier="estandar",
               time="30 min", cal=560, nut=("28 g", "70 g", "14 g"),
               ing=[("12005770", "Arroz Albar", 0.3), ("12004370", "Atún Carlo Forte", 1.0),
                    ("12002258", "Zanahoria", 0.2), ("12003293", "Ajo granulado", 0.1),
                    ("12000775", "Aceite", 0.02)],
               steps=["Sofríe la zanahoria rallada con ajo y aceite.",
                      "Agrega el arroz cocido y el atún escurrido.",
                      "Revuelve a fuego medio 5 minutos y sirve."]),
    "l2": dict(name="Fríjoles con arroz y hamburguesa", type="Almuerzo", tier="estandar",
               time="40 min", cal=720, nut=("34 g", "78 g", "24 g"),
               ing=[("12000040", "Fríjol cargamanto", 0.5), ("12005770", "Arroz Albar", 0.3),
                    ("12000575", "Hamburguesa de res Viandí", 0.5), ("12000775", "Aceite", 0.02)],
               steps=["Cocina el fríjol con sal hasta que espese.",
                      "Prepara el arroz blanco aparte.",
                      "Asa la carne de hamburguesa a la plancha.",
                      "Sirve fríjol, arroz y la carne juntos."]),
    "l4": dict(name="Lasaña boloñesa rápida", type="Almuerzo", tier="estandar",
               time="45 min", cal=640, nut=("30 g", "68 g", "22 g"),
               ing=[("12000645", "Pasta para lasaña Deliziare", 0.6),
                    ("12002266", "Base salsa boloñesa Rico", 1.0),
                    ("12000266", "Salsa de tomate ZEV", 0.4),
                    ("12000575", "Hamburguesa de res Viandí", 0.5)],
               steps=["Prepara la base de salsa boloñesa con la carne desmenuzada.",
                      "Mezcla con la salsa de tomate ZEV.",
                      "Arma capas de pasta y salsa en un molde.",
                      "Hornea hasta gratinar y sirve."]),
    "d1": dict(name="Garbanzos guisados con arroz", type="Cena", tier="estandar",
               time="30 min", cal=520, nut=("22 g", "76 g", "12 g"),
               ing=[("12000044", "Garbanzo El Estío", 0.5), ("12005770", "Arroz Albar", 0.25),
                    ("12000266", "Salsa de tomate ZEV", 0.3), ("12003293", "Ajo granulado", 0.1)],
               steps=["Guisa el garbanzo con salsa de tomate y ajo.",
                      "Cocina a fuego bajo 15 minutos.",
                      "Sirve acompañado de arroz blanco."]),
    "d2": dict(name="Sándwich de jamón y queso", type="Cena", tier="estandar",
               time="12 min", cal=430, nut=("22 g", "42 g", "16 g"),
               ing=[("12000069", "Pan leche Horneaditos", 0.4), ("12000077", "Jamón de cerdo Viandí", 0.3),
                    ("12000239", "Pandequeso Horneaditos", 0.5)],
               steps=["Arma el sándwich con pan, jamón y pandequeso.",
                      "Calienta en sartén hasta dorar el pan.",
                      "Sirve caliente."]),
    "d3": dict(name="Crema de papa criolla", type="Cena", tier="estandar",
               time="25 min", cal=360, nut=("10 g", "54 g", "11 g"),
               ing=[("12007453", "Papa criolla", 0.4), ("12002258", "Zanahoria", 0.2),
                    ("12000052", "Leche entera", 0.3), ("12002874", "Sal", 0.01)],
               steps=["Cocina la papa criolla y la zanahoria hasta ablandar.",
                      "Licúalas con leche y sal hasta obtener una crema.",
                      "Calienta de nuevo y sirve."]),
}

DIET_LIST = ["Sin gluten", "Vegetariano", "Alto en proteína", "Bajo en grasa", "Sin lácteos"]
DAY_NAMES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MEAL_TYPES = ["Desayuno", "Almuerzo", "Cena"]


def price_of(cat, sku):
    if sku in EXTRA:
        return EXTRA[sku]["price"]
    return cat[sku]["price"]


def main():
    cat = {p["sku"]: p for p in json.load(open(CATALOG, encoding="utf-8"))}

    # productos (catálogo + extras de tienda)
    products = {}
    for sku, (short, catname, _q) in PICK.items():
        p = cat[sku]
        products[sku] = {"name": short, "full": p["name"], "brand": p["brand"],
                         "price": p["price"], "subQty": p["subQty"], "subUnit": p["subUnit"],
                         "cat": catname, "tienda": False}
    for sku, e in EXTRA.items():
        products[sku] = {"name": e["name"], "full": e["name"], "brand": e["brand"],
                         "price": e["price"], "subQty": e["subQty"], "subUnit": e["subUnit"],
                         "cat": e["cat"], "tienda": True}

    # recetas: costo desde precios reales
    recipes = {}
    for rid, r in RECIPES.items():
        cost = 0.0
        ingredients = []
        for sku, label, frac in r["ing"]:
            cost += price_of(cat, sku) * frac
            ingredients.append(f"{label} — {products[sku]['name']}")
        # Nota: las recetas (combinaciones, calorías y nutrición) son autoría
        # propia basada en cocina casera colombiana; los pasos de preparación se
        # omiten a propósito (la app solo muestra ingredientes). Precios reales.
        recipes[rid] = {"name": r["name"], "type": r["type"], "tier": r["tier"],
                        "time": r["time"], "cal": r["cal"],
                        "cost": int(round(cost / 50.0) * 50),
                        "ingredients": ingredients,
                        "ing": [{"sku": s, "frac": f} for s, _l, f in r["ing"]],
                        "nut": {"protein": r["nut"][0], "carbs": r["nut"][1], "fat": r["nut"][2]}}

    # mealPools[tier][type] = [ids]  (ordenados por costo para rotación estable)
    meal_pools = {"economica": {t: [] for t in MEAL_TYPES},
                  "estandar": {t: [] for t in MEAL_TYPES}}
    for rid, r in sorted(recipes.items(), key=lambda kv: kv[1]["cost"]):
        meal_pools[r["tier"]][r["type"]].append(rid)
    # respaldo: si un tier/tipo quedara vacío, usa el del otro tier
    for t in MEAL_TYPES:
        if not meal_pools["economica"][t]:
            meal_pools["economica"][t] = list(meal_pools["estandar"][t])
        if not meal_pools["estandar"][t]:
            meal_pools["estandar"][t] = list(meal_pools["economica"][t])

    # La lista de compras se calcula en la app a partir del plan (ingredientes
    # reales × días × personas). Solo emitimos el orden de las categorías.
    data = {"dietList": DIET_LIST, "dayNames": DAY_NAMES, "mealTypes": MEAL_TYPES,
            "catOrder": CAT_ORDER,
            "products": products, "recipes": recipes, "mealPools": meal_pools,
            "generatedFrom": "data/d1_catalog.json (precios reales D1)"}

    js = ("// AUTO-GENERADO por scripts/build_app_data.py — NO editar a mano.\n"
          "// Productos y precios reales de Tiendas D1 (domicilios.tiendasd1.com).\n"
          "window.D1_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(js)

    print(f"OK -> {OUT}")
    print(f"  productos: {len(products)} | recetas: {len(recipes)}")
    for tier in ("economica", "estandar"):
        for t in MEAL_TYPES:
            ids = meal_pools[tier][t]
            print(f"  {tier:9} {t:9}: {', '.join(ids)}")


if __name__ == "__main__":
    main()
