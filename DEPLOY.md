# Despliegue — Mi Canasta D1 (Coolify)

Sitio estático (HTML/CSS/JS, sin backend). Se construye con el `Dockerfile`
(nginx) y se despliega en **Coolify**, que maneja el dominio y el HTTPS.

Dominio: **https://canastad1.mainics.com**

---

## 1. Subir el proyecto a Git

Coolify despliega desde un repositorio (GitHub / GitLab / Gitea):

```bash
git init
git add .
git commit -m "Mi Canasta D1 — listo para desplegar"
git branch -M main
git remote add origin git@github.com:TU_USUARIO/canastad1.git
git push -u origin main
```

## 2. DNS

Crea un registro **A** apuntando a la IP de tu servidor Coolify:

```
canastad1.mainics.com   A   <IP_DEL_SERVIDOR_COOLIFY>
```

## 3. Crear la aplicación en Coolify

1. **+ New** → **Application** → conecta tu fuente de Git y elige el repo/rama (`main`).
2. **Build Pack:** `Dockerfile`  *(Coolify detecta el `Dockerfile` en la raíz).*
3. **Port / Ports Exposes:** `80`  *(nginx escucha en el 80).*
4. **Domains:** `https://canastad1.mainics.com`
   - Coolify provisiona el certificado SSL (Let's Encrypt) automáticamente.
   - No publiques puertos al host: el proxy de Coolify enruta el dominio → contenedor:80.
5. **Deploy.**

Cada `git push` a `main` puede redeplegar automáticamente (si activas el webhook/auto-deploy).

---

## Notas

- **Caché:** el `nginx.conf` sirve HTML/JS/CSS con `Cache-Control: no-cache`
  (revalidan con ETag), así nunca queda una versión vieja pegada tras un deploy.
- **Imagen OG / WhatsApp:** queda en `https://canastad1.mainics.com/og-image.png`
  (incluida en la imagen). Valídala tras el deploy en https://www.opengraph.xyz/.
- **Healthcheck:** el `Dockerfile` ya trae uno (`wget` a `/`).

## Probar local antes (opcional, requiere Docker Desktop abierto)

```bash
docker build -t mi-canasta-d1 .
docker run -d --name mi-canasta -p 8080:80 mi-canasta-d1   # http://localhost:8080
docker rm -f mi-canasta
```

## Regenerar datos / assets (opcional)

```bash
python scripts/scrape_d1.py        # refresca precios reales desde D1
python scripts/build_app_data.py   # regenera app-data.js
python scripts/make_assets.py      # regenera favicon, iconos y og-image
```
