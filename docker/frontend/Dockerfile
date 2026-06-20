# --- Build stage: produce the static SPA bundle -------------------------------
FROM node:22-alpine AS build
WORKDIR /app/frontend

# Build context is the repo root (see compose), hence the frontend/ prefix.
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./

# NOTHING environment-specific is baked in here. The API base URL is injected at
# RUNTIME via /config.js (see the startup script below), so this image is byte
# identical across dev and prod — only the running environment differs.
RUN npm run build

# --- Serve stage: static files via nginx --------------------------------------
FROM nginx:alpine
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

# Renders /config.js from container env at startup. nginx:alpine's entrypoint
# runs every executable script in /docker-entrypoint.d/ before launching nginx.
COPY docker/frontend/40-render-config.sh /docker-entrypoint.d/40-render-config.sh
RUN chmod +x /docker-entrypoint.d/40-render-config.sh

EXPOSE 3000
# nginx:alpine's default entrypoint runs /docker-entrypoint.d/* then nginx -g 'daemon off;'.
