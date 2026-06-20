#!/usr/bin/env bash
#
# Build and start the full stack with a forced image rebuild.
#
set -euo pipefail

# --- Configuration ------------------------------------------------------------
# Host ports and the URLs the services use. The compose file reads these from
# the environment (no defaults set there), so define them here.
export BACKEND_PORT=8002                          # host port -> backend
export FRONTEND_PORT=8001                         # host port -> frontend
export CORS_ORIGINS=http://minime:8001         # SPA origin(s) the API allows
export API_BASE_URL=http://minime:8002         # API base URL injected into the SPA at runtime

# Resolve paths relative to this script so it works from any directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker/docker-compose.yml"

# --build forces a rebuild; --no-cache (via build step) guarantees fresh layers.
docker compose -f "${COMPOSE_FILE}" build --no-cache
docker compose -f "${COMPOSE_FILE}" up -d --build "$@"
