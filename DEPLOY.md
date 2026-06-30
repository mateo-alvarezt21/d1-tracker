# Despliegue — Mi Canasta D1

Sitio estático (HTML/CSS/JS, sin backend). Se sirve con nginx vía Docker.

## 1. Antes de desplegar: poner tu dominio

El preview de WhatsApp/redes necesita URLs **absolutas**. Reemplaza el
placeholder `https://TU-DOMINIO.com` por tu dominio real en:

- `index.html` → etiquetas `canonical`, `og:url`, `og:image`, `twitter:image`

```bash
# ejemplo (bash): reemplazar en index.html
sed -i 's#https://TU-DOMINIO.com#https://midominio.com#g' index.html
```

## 2. Build & run con Docker

> Requiere Docker Desktop **abierto** (el engine corriendo).

```bash
docker build -t mi-canasta-d1 .
docker run -d --name mi-canasta -p 8080:80 mi-canasta-d1
# abrir http://localhost:8080
```

Parar / borrar:

```bash
docker rm -f mi-canasta
```

## 3. Desplegar en un servidor

Cualquier host con Docker (VPS, Fly.io, Render, Railway, Cloud Run, etc.):

```bash
docker build -t mi-canasta-d1 .
docker tag mi-canasta-d1 TU_REGISTRO/mi-canasta-d1:latest
docker push TU_REGISTRO/mi-canasta-d1:latest
```

Como es estático, también puedes subir directo a Netlify, Vercel, GitHub
Pages o Cloudflare Pages: solo necesitan estos archivos (sin `Dockerfile`):

```
index.html app.js app-data.js styles.css
favicon.svg apple-touch-icon.png icon-192.png icon-512.png og-image.png
site.webmanifest robots.txt
```

## 4. Regenerar datos / assets (opcional)

```bash
python scripts/scrape_d1.py          # refresca precios reales desde D1
python scripts/build_app_data.py     # regenera app-data.js
python scripts/make_assets.py        # regenera favicon, iconos y og-image
```

## Verificar el preview de WhatsApp

Tras desplegar con el dominio real, valida en:
- https://www.opengraph.xyz/  (pega tu URL)
- o comparte el link en un chat de WhatsApp contigo mismo.
