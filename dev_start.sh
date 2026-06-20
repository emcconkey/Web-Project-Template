#!/usr/bin/env bash
#
# Local development (no Docker): set up deps and run both servers together.
#   - backend:  Python venv + Flask dev server (auto-reload) on :5000
#   - frontend: npm install + Vite dev server on :5173, proxying /api → :5000
#
# Ctrl+C stops both. The frontend talks to the backend through Vite's proxy, so
# it's same-origin and needs no CORS or API_BASE_URL config (see PROJECT_SETUP.md
# → Environment variables).
#
set -euo pipefail

# --- Configuration ------------------------------------------------------------
# Override by exporting before running, e.g. BACKEND_PORT=8000 ./dev_start.sh
# Default backend port is 5001, not 5000: on macOS the AirPlay Receiver
# (ControlCenter) listens on :5000 and answers with 403, which would shadow Flask.
BACKEND_PORT="${BACKEND_PORT:-5001}"   # Flask dev server (Vite proxies here)
FRONTEND_PORT="${FRONTEND_PORT:-5173}" # Vite dev server

# Point Vite's dev proxy at our backend (IPv4 literal avoids localhost→::1, which
# Flask's 127.0.0.1 bind would refuse). vite.config.js reads this from the env.
export VITE_BACKEND_PROXY_TARGET="http://127.0.0.1:${BACKEND_PORT}"

# Resolve paths relative to this script so it works from any directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

PYTHON="python3.13"

# --- Prerequisites ------------------------------------------------------------
command -v ${PYTHON} >/dev/null 2>&1 || { echo "error: ${PYTHON} not found" >&2; exit 1; }
command -v npm     >/dev/null 2>&1 || { echo "error: npm not found" >&2; exit 1; }

# --- Backend: virtualenv + dependencies ---------------------------------------
if [ ! -d venv ]; then
  echo "==> Creating Python virtualenv (venv/)"
  ${PYTHON} -m venv venv
fi
source venv/bin/activate
echo "==> Installing backend dependencies"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# --- Frontend: npm dependencies -----------------------------------------------
echo "==> Installing frontend dependencies"
( cd frontend && npm install )

# --- Run both servers; stop both on exit --------------------------------------
# The script is its own process group leader, so `kill 0` cleans up every child
# (Flask + its reloader, npm + Vite) without touching the parent shell.
cleanup() {
  trap - INT TERM EXIT          # disable traps so cleanup runs once
  echo
  echo "==> Shutting down dev stack"
  kill 0
}
trap cleanup INT TERM EXIT

echo "==> Starting backend on http://localhost:${BACKEND_PORT}"
FLASK_APP=app:create_app flask run --debug -p "${BACKEND_PORT}" &

echo "==> Starting frontend on http://localhost:${FRONTEND_PORT}"
( cd frontend && FRONTEND_PORT="${FRONTEND_PORT}" npm run dev ) &

echo
echo "Dev stack running — press Ctrl+C to stop both:"
echo "    backend  → http://localhost:${BACKEND_PORT}"
echo "    frontend → http://localhost:${FRONTEND_PORT}"
echo

# Wait for either server to exit; if one dies, cleanup() tears down the other.
wait
