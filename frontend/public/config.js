// Runtime config consumed by the SPA. Default values for local Vite dev
// (npm run dev). Empty API_BASE_URL → API calls use relative paths through the
// Vite dev proxy (see vite.config.js).
//
// In Docker this file is OVERWRITTEN at container startup from environment
// variables (see docker/frontend/40-render-config.sh), so the same built image
// can target any environment without a rebuild.
window.__APP_CONFIG__ = {
  API_BASE_URL: "",
};
