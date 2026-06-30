# Mi Canasta D1 — sitio estático servido con nginx.
# No hay paso de build: el frontend ya está generado (app-data.js).
FROM nginx:1.27-alpine

# Configuración de nginx (gzip + cabeceras de caché).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Solo los archivos que el navegador necesita (no scripts ni data de build).
WORKDIR /usr/share/nginx/html
RUN rm -rf ./*
COPY index.html app.js app-data.js styles.css ./
COPY favicon.svg apple-touch-icon.png icon-192.png icon-512.png og-image.png ./
COPY site.webmanifest robots.txt ./

EXPOSE 80

# Healthcheck robusto: usa 127.0.0.1 (IPv4 — nginx escucha ahí seguro) en vez de
# localhost (que puede resolver a IPv6 ::1 y fallar). nginx:alpine trae wget.
HEALTHCHECK --interval=5s --timeout=3s --start-period=3s --retries=5 \
  CMD wget -qO- http://127.0.0.1:80/ >/dev/null 2>&1 || exit 1
