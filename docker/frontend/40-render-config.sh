#!/bin/sh
# Render the SPA's runtime config (/config.js) from container environment
# variables. Runs once at container startup, before nginx launches. This is what
# lets a single built image target any environment — dev or prod — purely by
# changing the running environment (no rebuild).
set -eu

cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL:-}",
};
EOF

echo "render-config: wrote /config.js (API_BASE_URL='${API_BASE_URL:-}')"
