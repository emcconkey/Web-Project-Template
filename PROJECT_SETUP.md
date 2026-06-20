# Project Setup

A full guide to how this project is built, so you can stand up a **new** project with the same architecture: a **Vue 3 SPA** talking to a **Flask JSON API** (session-cookie auth, RBAC, auto-generated OpenAPI docs), each deployed as its own container on its own domain.

This single document replaces the earlier split guides. It has three main sections — **[Frontend](#frontend)**, **[Backend](#backend)**, and **[Docker](#docker)** — preceded by a shared overview and followed by a setup checklist.

> **What this repo actually contains.** This is a trimmed, runnable **sample** of the architecture described below: a Flask JSON API (app factory + `/api` blueprint + auto-generated OpenAPI docs) and a Vue 3 SPA (router + runtime config + `useApi`), wired end to end and Dockerized. The **database, auth/RBAC, email, migrations, and `pages/` layers are documented but not yet implemented** — passages covering them are marked ***Full template*** and act as the blueprint for extending the sample. What exists today: `app.py`, `api/{__init__,message,docs}.py`, `frontend/`, `docker/`, `start.sh`, and `dev_start.sh`.

---

## Architecture at a glance

```
Browser
  │
  ├──────────────► app.example.com       (SPA — nginx serving the Vite build)
  │                                       static files only; no app server
  │
  └── XHR (fetch) ► api.example.com       (API — gunicorn + Flask)
         credentials:'include'            JSON under /api/*, session-cookie auth
```

- **Two separate services, two separate domains.** The SPA is static files on nginx; the API is Flask behind gunicorn. They do **not** share an origin in production.
- **Auth is a Flask-Login session cookie** — no JWT. Because the call is cross-origin, the cookie is set `SameSite=None; Secure`, and the API sends credentialed CORS headers for the SPA's origin.
- **The SPA reads its API base URL at runtime** from `window.__APP_CONFIG__` (injected by `/config.js`), so a single built image runs in any environment — the value is set from the container's `API_BASE_URL` env var at startup. In local dev, the default config leaves it empty and the Vite dev proxy forwards `/api` to Flask instead (same-origin, no CORS).

| Piece | Dev (no Docker) | Docker service | Published port | Inside container |
| ----- | --------------- | -------------- | -------------- | ---------------- |
| API (Flask + gunicorn) | `localhost:5000` | `backend`  | `8002` | `5000` |
| SPA (Vite → nginx)     | `localhost:5173` | `frontend` | `8001` | `3000` |

### Technology choices

| Concern        | Choice                                                            |
| -------------- | ----------------------------------------------------------------- |
| Web framework  | [Flask](https://flask.palletsprojects.com) `>=3.1` (app factory)  |
| WSGI server    | [Gunicorn](https://gunicorn.org) `>=23` (4 workers)               |
| ORM            | [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com) `>=3.1` |
| Migrations     | [Flask-Migrate](https://flask-migrate.readthedocs.io) (Alembic)   |
| Auth / session | [Flask-Login](https://flask-login.readthedocs.io) `>=0.6`         |
| CORS           | [Flask-Cors](https://flask-cors.readthedocs.io) (credentialed)    |
| API docs       | Hand-rolled OpenAPI 3 (from the Flask `url_map`) + Swagger UI (CDN) |
| Database       | MariaDB/MySQL via PyMySQL (prod); SQLite (tests / `USE_SQLITE`)    |
| Config         | `python-dotenv` reading `.env`                                    |
| SPA framework  | [Vue 3](https://vuejs.org) (`^3.5`) — Composition API, `<script setup>` |
| Build / dev    | [Vite 5](https://vitejs.dev) (`@vitejs/plugin-vue`)               |
| Routing        | [vue-router 4](https://router.vuejs.org) (`createWebHistory`)     |
| Styling        | Plain CSS — tokens + reset + layered component/page sheets        |
| State / auth   | Composables (e.g. `useAuth`) — no Pinia/Vuex                      |

---

## Repository layout

***Target layout*** for the full architecture — see the sample-contents note at the top for what exists in this repo today (`pages/`, `lib/`, `migrations/`, `templates/`, `static/`, `tests/`, `scripts/`, and most `api/` modules are not present yet).

```
.
├── app.py                  # Application factory (create_app) — wires everything
├── requirements.txt
├── start.sh                # Build + run the Docker stack, prod-style (see Docker → Running it)
├── dev_start.sh            # Run the stack locally without Docker (see Running locally)
│                           #   Config is injected at runtime — no committed .env (see Environment variables)
│
├── api/                    # ◄── JSON API consumed by the SPA. Build new work here.
│   ├── __init__.py         #     init_app(): creates the /api blueprint, registers modules,
│   │                       #     installs JSON (not HTML) error handlers
│   ├── utils.py            #     shared helpers: json_error, api_login_required,
│   │                       #     require_api_permission, serialize_user
│   ├── serializers.py      #     model → dict converters (one per resource)
│   ├── docs.py             #     auto-generated OpenAPI spec + Swagger UI
│   ├── auth.py             #     /api/auth/* (login, logout, me, password reset)
│   ├── customers.py        #     one module per resource: register() + view functions
│   ├── workorders.py
│   ├── locations.py
│   └── … (users, dashboard, intake, lab_tests, reports, profile, portal, form_options)
│
├── pages/                  # Legacy server-rendered HTML (Flask-Classful + Jinja). Reference only.
│
├── lib/                    # Framework-agnostic app code shared by api/ and pages/
│   ├── extensions.py       #     the singletons: db, migrate, login_manager
│   ├── rbac.py             #     ROLE_PERMISSIONS map + has_permission / require_permission
│   ├── models/__init__.py  #     SQLAlchemy models (User, Customer, Location, Workorder, …)
│   ├── email.py            #     SendGrid email helper
│   └── … (audit, pdf, storage, uploads, ocr, workorder_lifecycle)
│
├── migrations/             # Flask-Migrate / Alembic (versions/ holds each migration)
├── templates/              # Jinja templates (used by pages/ + error pages)
├── static/                 # Static assets + runtime uploads (avatars)
├── uploads/                # Runtime file uploads (mounted volume, not in image)
├── tests/                  # pytest suite (see CLAUDE.md for the full test guide)
│
├── docker/
│   ├── Dockerfile          # Backend image (python:3.12-slim → gunicorn)
│   ├── docker-compose.yml  # backend + frontend services, one repo-root build context
│   └── frontend/
│       ├── Dockerfile             # Multi-stage: Node build → nginx serve
│       ├── nginx.conf             # SPA history fallback + asset caching
│       └── 40-render-config.sh    # Renders /config.js from env at container startup
│
├── scripts/
│   ├── deploy.sh           # rsync code to server, then run.sh over SSH
│   ├── run.sh              # build + up --wait on the server, Cloudflare purge
│   └── migrate_mounts.sh   # one-time: relocate runtime data outside the code tree
│
└── frontend/               # The Vue SPA (see Frontend section)
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
```

The **build context for both Docker images is the repo root**, so one tree builds both services.

> **Note on two backend patterns.** `pages/` holds the older server-rendered HTML controllers (Flask-Classful, Jinja templates). `api/` holds the JSON API the SPA consumes. New work belongs in the **`api/` + SPA** pattern; `pages/` is the legacy surface being superseded. This guide documents the `api/` pattern.

---

# Environment variables

**No `.env` file is required to run this project.** Every variable has a working default or is supplied by the launch script, and all configuration is injected at **runtime** — nothing is baked into a Docker image — so one build runs unchanged in every environment. There are intentionally **no `.env.example` files**; this section is the single source of truth for what exists and where to set it.

### Where to declare variables

| Environment | Declare in | Reaches the app via |
| ----------- | ---------- | ------------------- |
| **Local dev (Docker stack)** | `export` lines at the top of [`start.sh`](start.sh) | compose `environment:` → container |
| **Local dev (frontend alone, `npm run dev`)** | shell env, or just rely on defaults | `vite.config.js` (all have defaults) |
| **Production** | a `.env` mounted at `MOUNTS_DIR` (outside the code tree) and/or your orchestrator's env | compose `env_file:` (`required: false`) and `environment:` |

The production `.env` lives at `MOUNTS_DIR` so deploys never overwrite it (see [Runtime data & secrets](#runtime-data--secrets--mounts_dir)); it is never committed and never shipped in an image.

### Variables this project actually reads

**Backend** — read at runtime in [`app.py`](app.py) via `os.environ`:

| Variable | Required? | Default | Purpose |
| -------- | --------- | ------- | ------- |
| `SECRET_KEY` | Recommended in prod | `change-me` | Flask session signing. Harmless default for this sample (no sessions/auth yet); set a real value once you add login. |
| `CORS_ORIGINS` | Only when the SPA is a different origin than the API | `""` (CORS disabled) | Comma-separated allowed SPA origins. Not needed for local same-origin dev (the Vite proxy makes it same-origin). |

**Frontend (runtime)** — injected into `/config.js` at container startup (see [Runtime config](#runtime-config-frontend)):

| Variable | Required? | Default | Purpose |
| -------- | --------- | ------- | ------- |
| `API_BASE_URL` | No | `""` | Base URL the SPA calls. Empty → relative paths (same-origin / dev proxy). |

**Frontend dev server** — affect `npm run dev` only; never part of the built image. All optional (defaults in `vite.config.js`):

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `VITE_BACKEND_PROXY_TARGET` | `http://localhost:5000` | Where the dev server proxies `/api` + `/health`. |
| `VITE_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hosts the dev server accepts. |
| `FRONTEND_PORT` | `5173` | Vite dev-server bind port. |

**Compose / host orchestration** — set by [`start.sh`](start.sh) for the Docker stack:

| Variable | `start.sh` value | Purpose |
| -------- | ---------------- | ------- |
| `BACKEND_PORT` | `8002` | Host port → backend container. |
| `FRONTEND_PORT` | `8001` | Host port → frontend container. (Distinct from the Vite dev-server use above.) |
| `CORS_ORIGINS` | `http://minime:8001` | Passed to the backend. |
| `API_BASE_URL` | `http://minime:8002` | Passed to the frontend, rendered into `/config.js`. |
| `MOUNTS_DIR` | unset → `..` (repo root) | Where prod mounts `.env` + `logs/`. |

> **Precedence:** compose `environment:` overrides `env_file:`. The backend's `CORS_ORIGINS` is wired through `environment: - CORS_ORIGINS=${CORS_ORIGINS}`, so set it via the shell/`start.sh` (or a prod orchestrator) — a value placed only in `MOUNTS_DIR/.env` would be overridden by the empty shell default. `SECRET_KEY` is **not** wired through `environment:`, so it comes from `MOUNTS_DIR/.env` (prod) or the `change-me` default (dev).

### Extending the template

The fuller architecture this guide describes (database, auth sessions, SendGrid email, Cloudflare cache purge, live-site tests) adds more **backend** variables. Declare them the same way — `start.sh` for dev, `MOUNTS_DIR/.env` for prod — and add any that must reach the container to the backend's compose `env_file`/`environment`:

```sh
# --- Core ---
MAX_CONTENT_LENGTH=5242880                # max upload size in bytes (default 5 MiB)

# --- Database (DATABASE_URL wins; else assembled from DB_* ; else sqlite when USE_SQLITE=true) ---
DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname
DB_DRIVER=mysql+pymysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=myapp
DB_USER=myapp
DB_PASS=change-me
USE_SQLITE=false                          # true → sqlite:///app.db (tests / local)

# --- Session cookie (cross-origin SPA needs None+Secure; Lax+false for local http) ---
SESSION_COOKIE_SAMESITE=None
SESSION_COOKIE_SECURE=true

# --- Email (SendGrid) ---
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=
SENDGRID_FROM_NAME=
EMAIL_OVERRIDE_DESTINATION=               # route all mail here in non-prod

# --- Deploy: Cloudflare cache purge (optional) ---
CLOUDFLARE_ZONE_ID=
CLOUDFLARE_API_TOKEN=

# --- Tests (live-site smoke) ---
TEST_ADMIN_USER=
TEST_ADMIN_PASS=
TEST_STAFF_USER=
TEST_STAFF_PASS=
```

---

# Running locally

The fastest way to run the whole stack **without Docker** is [`dev_start.sh`](dev_start.sh). It sets up the Python virtualenv, installs both dependency sets, and runs the Flask and Vite dev servers together in one terminal:

```sh
./dev_start.sh
#   backend  → http://localhost:5001   (Flask, --debug auto-reload)
#   frontend → http://localhost:5173   (Vite; proxies /api + /health → backend)
```

What it does, in order:

- Creates `venv/` if missing and installs `requirements.txt` (idempotent — safe to re-run).
- Runs `npm install` in `frontend/`.
- Starts both servers, prints their URLs, and **waits**. Ctrl+C — or either server exiting — tears the whole process group down cleanly (`trap … kill 0`).

No env file is required: the frontend reaches the backend through Vite's proxy, so it's same-origin (no CORS, no `API_BASE_URL`). Override ports by exporting first:

```sh
BACKEND_PORT=8000 FRONTEND_PORT=3000 ./dev_start.sh
```

> **Why 5001 and not 5000?** On macOS the AirPlay Receiver (ControlCenter) listens on `:5000` and answers with `403`, silently shadowing Flask. The script defaults the backend to `5001` and points Vite's proxy (`VITE_BACKEND_PROXY_TARGET`) at it using the `127.0.0.1` literal — which also sidesteps `localhost`→IPv6 resolving away from Flask's IPv4 bind. Use a non-5000 port if you run the servers by hand on macOS too.

To run a single service on its own, see [Local development (frontend)](#local-development-frontend) and [Local development (backend)](#local-development-backend). For the production-style containerized stack, see [Docker → Running it](#running-it) (driven by [`start.sh`](start.sh)).

---

# Frontend

A Vue 3 SPA: Composition API with `<script setup>`, Vite dev server with a backend proxy, file-based route + view organization, and a layered plain-CSS design system. Containerization is covered in the [Docker](#docker) section.

## Folder structure

```
frontend/
├── index.html                  # Vite entry; mounts <div id="app"> and loads /src/main.js
├── package.json                # type:module, scripts: dev / build / preview
├── vite.config.js              # vue plugin + dev proxy + allowedHosts
├── public/
│   └── config.js               # runtime config default (window.__APP_CONFIG__); overwritten in Docker
└── src/
    ├── main.js                 # createApp(App).use(router).mount('#app'); imports master CSS
    ├── App.vue                 # root shell
    ├── router/
    │   └── index.js            # routes + global navigation guard (meta: requiresAuth/guestOnly/permission)
    ├── views/                  # one .vue per route (DashboardView.vue, LoginView.vue, …)
    ├── components/             # reusable components (layouts, form primitives, …)
    ├── composables/            # shared reactive logic (useApi.js, useAuth.js, useToast.js, …)
    └── assets/
        └── styles/
            ├── index.css       # master sheet — imported once from main.js
            ├── tokens.css      # CSS custom properties (colors, spacing, …)
            ├── reset.css       # box-sizing, body/#app base
            ├── base.css        # typography, links, focus ring, scrollbar
            ├── layout.css      # app shell, top-nav, sidebar, content region
            ├── components/     # shared UI primitives (buttons, forms, cards, tables, modals, …)
            └── pages/          # page-specific sheets, imported from each view's <script setup>
```

## Conventions

- **Views vs components** — every route maps to a `*View.vue` in `views/`; anything reused lives in `components/`.
- **CSS loading order matters.** `index.css` imports tokens → reset → base → layout → shared components, in that order. It's imported once from `main.js`. Page-specific styles are imported locally inside the view that needs them (`import '../assets/styles/pages/dashboard.css'`) — keeping per-page CSS out of the global bundle path.
- **Auth via composable + route meta.** Routes declare `meta: { requiresAuth: true }` / `{ guestOnly: true }` / `{ permission: 'x' }`; a global `router.beforeEach` guard reads `useAuth()` to redirect.
- **No CSS framework, no global store library** — plain CSS + composables unless a real need appears.

## The API client

The SPA talks to the API through a composable:

- **`composables/useApi.js`** (this sample) — a thin `fetch` wrapper. Base URL is read at runtime from `window.__APP_CONFIG__?.API_BASE_URL` (or empty → relative paths through the dev proxy). **Every request sends `credentials: 'include'`** so a session cookie would travel cross-origin. It exposes `get` / `post` and throws on a non-2xx response.

> ***Full template:*** add **`composables/useAuth.js`** (shared reactive auth state — `login` / `logout` / `fetchCurrentUser` plus a `can(permission)` check), a global `onUnauthorized` handler registered in `main.js` that bounces to `/login` on a 401, and a `router.beforeEach` guard (`router/index.js`) enforcing `requiresAuth` / `guestOnly` / `permission` per route. Client checks are UX only — the server stays authoritative.

## Runtime config (frontend)

The API base URL is **not** a build-time `VITE_*` value — it is read at runtime from a global the app loads before its bundle:

```js
// frontend/public/config.js — default for local dev; OVERWRITTEN in Docker.
window.__APP_CONFIG__ = { API_BASE_URL: "" }
```

- **`frontend/public/config.js`** is the default (empty → dev proxy). Vite copies `public/` into the build, so the file also ships inside the image.
- **In Docker**, `docker/frontend/40-render-config.sh` regenerates `/config.js` from the container's `API_BASE_URL` env var at startup, so the *same image* targets any environment with no rebuild.
- **`index.html`** loads `<script src="/config.js">` before the module bundle; since the bundle is a deferred `type="module"` script, `window.__APP_CONFIG__` is always set first.

## Dev-server config (`vite.config.js`)

The Vite dev server reads a few **optional** variables (`VITE_BACKEND_PROXY_TARGET`, `VITE_ALLOWED_HOSTS`, `FRONTEND_PORT`) from the shell — see [Environment variables](#environment-variables) for the full list and defaults. No `.env` file is needed; every one has a built-in default. These affect `npm run dev` only and are never part of the built image (the API base URL is handled by [runtime config](#runtime-config-frontend) instead).

`vite.config.js` reads them to wire the proxy and `allowedHosts`:

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendTarget = process.env.VITE_BACKEND_PROXY_TARGET || 'http://localhost:5000'
const port = Number(process.env.FRONTEND_PORT) || 5173
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS || 'localhost,127.0.0.1')
  .split(',').map((h) => h.trim()).filter(Boolean)

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port,
    allowedHosts,
    proxy: { '/health': backendTarget, '/api': backendTarget },
  },
})
```

> **Build-time vs runtime:** Vite **inlines** `VITE_*` values into the bundle at build time — they are not read at runtime, which is why the dev-server vars above only affect `npm run dev`. The API base URL is deliberately kept *out* of the bundle and supplied at runtime via `/config.js` (see [Runtime config](#runtime-config-frontend) and [Docker → frontend image](#frontend-image--dockerfrontenddockerfile)).

## Local development (frontend)

> To run the frontend **and** backend together with one command, use [`dev_start.sh`](#running-locally). The steps below run just the frontend.

```sh
cd frontend
npm install
npm run dev               # Vite on :5173, proxying /api + /health → http://localhost:5000
```

No env file needed — the dev server runs on defaults, and the runtime API base is empty so `/api` proxies to the backend. Override any [dev-server variable](#environment-variables) via the shell if you need to. If your backend isn't on the default `:5000` (e.g. `:5001` on macOS — see the [port note](#running-locally)), point the proxy at it: `VITE_BACKEND_PROXY_TARGET=http://127.0.0.1:5001 npm run dev`.

`npm run build` outputs static assets to `dist/`; `npm run preview` serves the build locally.

## Scaffolding a new SPA from scratch

```sh
npm create vite@latest my-app -- --template vue
cd my-app
npm install vue-router@4
```

Then recreate the layout above: add `src/router/index.js` with a `beforeEach` guard, split `views/` and `components/`, set up the layered `assets/styles/` sheets, copy `useApi.js` / `useAuth.js`, and add the proxy block to `vite.config.js`.

---

# Backend

A Flask JSON API. Everything is wired in an application factory; endpoints live under `/api` and speak JSON; auth is a Flask-Login session cookie.

## The application factory (`app.py`)

**In this sample**, `create_app()` does a trimmed subset: `load_dotenv()`, set `SECRET_KEY` + the OpenAPI doc title/version, register the `/api` blueprint, and enable credentialed CORS (only when `CORS_ORIGINS` is set).

***Full template*** — `create_app()` wires everything, in order:

1. **`load_dotenv(BASE_DIR / ".env")`** — config comes from environment variables.
2. **`app.config.update(...)`** — `SECRET_KEY`, DB URI, `MAX_CONTENT_LENGTH`, upload folders. `SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True}` keeps pooled MySQL connections from going stale.
3. **Cross-site cookie config** — `SESSION_COOKIE_SAMESITE`/`SECURE` and the matching `REMEMBER_COOKIE_*`, driven by env so local http dev can drop to `Lax`/insecure.
4. **`db.init_app(app)` / `migrate.init_app(app, db)`** — bind the shared extension singletons.
5. **`login_manager`** — set `login_view`, register, and define the `user_loader`.
6. **Register blueprints** — `pages.init_app(app)` then `api.init_app(app)`.
7. **`CORS(...)`** — scoped to `/api/*`, `supports_credentials=True`, origins from `CORS_ORIGINS`.
8. **Error handlers** — HTML error pages for the page blueprint; the API blueprint installs its own JSON handlers (below).

The singleton extensions live in **`lib/extensions.py`** and are imported wherever needed — this avoids circular imports between the factory, models, and blueprints:

```python
# lib/extensions.py
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
```

## Environment variables (backend)

Config is read from the process environment via `python-dotenv` (`load_dotenv()` is a no-op when no file is present). This sample reads only `SECRET_KEY` and `CORS_ORIGINS`; the fuller template adds database, session-cookie, email, and deploy variables. See the consolidated [Environment variables](#environment-variables) section for the complete list and where to declare each one for dev vs prod.

When you add the database layer, `_database_uri()` resolves: `DATABASE_URL` if present → else `sqlite:///app.db` when `USE_SQLITE=true` → else a `mysql+pymysql://…` URL assembled from the `DB_*` parts.

## The API pattern (build new endpoints here)

### Blueprint assembly (`api/__init__.py`)

`init_app(app)` creates a single blueprint at `url_prefix="/api"`, imports every resource module, calls each module's `register(api_bp)`, installs JSON error handlers, and registers the blueprint. **To add a resource: create the module, then add it to the imports and the `register()` calls.**

```python
def init_app(app):
    api_bp = Blueprint("api", __name__, url_prefix="/api")
    from . import auth, customers, workorders, docs  # …
    docs.register(api_bp)
    auth.register(api_bp)
    customers.register(api_bp)
    # … one register() per module …

    @api_bp.errorhandler(HTTPException)
    def handle_api_http_exception(error):
        return jsonify({"message": error.description or error.name}), error.code or 500
    # + a catch-all Exception handler → {"message": "Internal server error"}, 500

    app.register_blueprint(api_bp)
```

### One module per resource

Endpoints are **plain functions**, registered via `bp.add_url_rule`. Each module exposes a `register(bp)` that maps URLs/methods to views. (This differs from the class-based Flask-Classful style in `pages/`; the API deliberately uses simple function views.)

```python
# api/customers.py  (abridged)
def register(bp):
    bp.add_url_rule("/customers", view_func=list_customers, methods=["GET"])
    bp.add_url_rule("/customers/<int:customer_id>", view_func=get_customer, methods=["GET"])
    bp.add_url_rule("/customers", view_func=create_customer, methods=["POST"])
    bp.add_url_rule("/customers/<int:customer_id>", view_func=update_customer, methods=["PUT"])

@require_api_permission("manage_customers")
def list_customers():
    rows = _scope_query(Customer.query.order_by(Customer.company_name.asc()))
    return jsonify({"customers": [serialize_customer(c) for c in rows.all()]})
```

**Conventions that hold across the API:**

- **The view's docstring's first line becomes its OpenAPI summary** — keep it short and descriptive.
- **Serialization is centralized** in `api/serializers.py` (and `serialize_user` in `utils.py`): models never get jsonified directly.
- **Validation returns `400` with a field map**: `json_error("Validation failed", 400, errors)` where `errors` is `{field: message}`. The SPA renders these inline.
- **Input is read defensively**: `request.get_json(silent=True) or {}`.
- **Location scoping**: non-admin users are filtered to their own `location_id`; out-of-scope rows return `404` (don't reveal existence).

### Auth & RBAC helpers (`api/utils.py`)

Because the API returns JSON, it must **not** redirect to an HTML login page on 401. Use these instead of Flask-Login's `@login_required`:

```python
@api_login_required                       # 401 JSON if no session
def me(): ...

@require_api_permission("manage_users")   # 401 if anonymous, 403 if lacking the permission
def list_users(): ...
```

- `json_error(message, status, errors=None)` → the standard `{"message", "errors"?}` shape.
- Permissions come from **`lib/rbac.py`**: a `ROLE_PERMISSIONS` dict maps each role (`admin`, `manager`, `lab_supervisor`, `team_lead`, `technician`, `staff`) to a set of permission strings. `has_permission(user, perm)` is the single source of truth — used by the API decorator, the page decorator, and the Jinja `can()` context processor.
- On login, the API returns the user **with their permission list** (`serialize_user(user, include_permissions=True)`), so the SPA can mirror the same checks client-side, while the server stays authoritative.

### Auth endpoints (`api/auth.py`)

`POST /api/auth/login` (sets the session cookie, returns the user + permissions), `POST /api/auth/logout`, `GET /api/auth/me` (current user or 401), `POST /api/auth/forgot-password`, and `GET|POST /api/auth/reset-password/<token>`. Password reset issues a hashed, single-use, TTL'd token and emails the link.

### Error responses

| Status | When                                   | Body                                  |
| ------ | -------------------------------------- | ------------------------------------- |
| 400    | Validation / bad input                 | `{"message", "errors": {field: msg}}` |
| 401    | No / expired session                   | `{"message": "Not authenticated"}`    |
| 403    | Authenticated but lacks permission     | `{"message": "…"}`                    |
| 404    | Missing or out-of-scope resource       | `{"message": "… not found."}`         |
| 409    | Uniqueness conflict                    | `{"message": "…"}`                    |
| 500    | Unhandled                              | `{"message": "Internal server error"}`|

## Auto-generated API docs (`api/docs.py`)

Swagger UI and the OpenAPI 3 spec are generated **from the live Flask `url_map` on every request** — there is no hand-maintained spec to drift. Any route you add to `api/*.py` appears automatically.

- `GET /api/docs` → Swagger UI (HTML).
- `GET /api/openapi.json` → the generated OpenAPI 3 document.
- Each operation's **summary** is the view's docstring first line (the rest becomes its description); operations are **tagged** by the first path segment (`/api/message` → tag `message`); multiple methods on the same path (e.g. GET + POST) merge into one path item.
- This sample serves the docs **open** — it has no auth layer. The fuller template gates both routes behind `@api_login_required` and adds a `sessionCookie` security scheme so Swagger UI's "Try it out" sends the session cookie (`withCredentials: true`).
- Swagger UI assets load from a CDN (browser-side only); the page is same-origin with the API.

How it works: `_build_spec()` iterates `app.url_map.iter_rules()`, keeps `/api` endpoints (minus the doc routes), and converts Flask converters (`<int:id>` → `{id}` + a typed path param). Set `API_TITLE` / `API_VERSION` in `app.config` to control the spec's `info` block.

> To enrich the spec (request/response schemas, descriptions), extend `_build_spec` — e.g. attach `apispec` schema components per operation. The current spec documents paths, params, and tags, with a generic `200` response.

## Database & migrations

- Models live in **`lib/models/`** and inherit from `db.Model`; `User` mixes in `UserMixin`. Passwords use `werkzeug.security` hashing (`set_password` / `check_password`).
- Migrations are **Flask-Migrate (Alembic)** in `migrations/`. The backend container runs `flask db upgrade` on startup, so deploys apply pending migrations automatically.

```sh
export FLASK_APP=app:create_app
flask db migrate -m "add foo table"   # autogenerate from model changes
flask db upgrade                       # apply
```

## Frontend↔backend contract

The contract between the two halves:

- **Every request sends `credentials: 'include'`** so the session cookie travels cross-origin.
- **Base URL** = `window.__APP_CONFIG__?.API_BASE_URL` (set at runtime via `/config.js`) or empty (relative → dev proxy).
- **A global 401 handler** (registered in `main.js`) resets auth and bounces to `/login` when a session expires mid-use — except for `/api/auth/*`, where a 401 just means "logged out".
- **Route guards mirror RBAC**: routes declare `meta: { permission: 'x' }`; the guard checks `useAuth().can(...)` against the permission list the login response returned. The server still enforces every permission — the client checks are UX, not security.

## Local development (backend)

> To run the backend **and** frontend together with one command, use [`dev_start.sh`](#running-locally). The steps below run just the backend.

```sh
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
export FLASK_APP=app:create_app
./venv/bin/flask run --debug -p 5001  # API on :5001 (avoid :5000 on macOS — see the port note)
```

No env file is needed to run this sample (`SECRET_KEY` falls back to `change-me`, and local dev is same-origin so `CORS_ORIGINS` is unused). Once you add the database/auth layers, set the relevant [variables](#environment-variables) in your shell — e.g. `USE_SQLITE=true`, `SESSION_COOKIE_SECURE=false`, `SESSION_COOKIE_SAMESITE=Lax` for local http — and run `flask db upgrade` before `flask run`.

Tests (pytest, SQLite-backed — full guide in `CLAUDE.md`):

```sh
./venv/bin/python -m pytest -q
```

Swagger UI: open `http://localhost:5001/api/docs` (or `http://localhost:5173/api/docs` through the Vite proxy). The raw spec is at `/api/openapi.json`. No login required in this sample.

---

# Docker

Two images, two containers, two domains in production. Both images build from the **repo root** (`context: ..`), so one source tree builds both services.

## The big picture

```
                    docker-compose.yml
                  build context = repo root  (..)
        ┌───────────────────────┴───────────────────────┐
        ▼                                                 ▼
  docker/Dockerfile                          docker/frontend/Dockerfile
  python:3.12-slim                           node:22-alpine (build)
  pip install -r requirements.txt              └─ npm install && npm run build → dist/
  COPY . .                                    nginx:alpine (serve)
  gunicorn :5000                                └─ COPY dist/ + nginx.conf + render-config
        │                                                 │
        ▼                                                 ▼
  service: backend  →  8002:5000              service: frontend  →  8001:3000
  (api.example.com)                           (app.example.com)
```

A shared [`.dockerignore`](#dockerignore) keeps host-built artifacts (`venv`, `node_modules`, `dist`, `__pycache__`, logs) out of both contexts.

## Backend image — `docker/Dockerfile`

A single-stage Python image: install dependencies, copy the source, run gunicorn.

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 5000

# gunicorn serves the app factory's module-level `app` (app.py: app = create_app()).
# The full template runs `flask db upgrade &&` first; this sample has no database
# or migrations, so it's omitted.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers 4 \
     --access-logfile logs/access.log --error-logfile logs/error.log app:app"]
```

- **`requirements.txt` is copied before the source** so the `pip install` layer is cached unless dependencies change.
- **`gunicorn app:app`** serves the module-level `app = create_app()` from `app.py`. `FLASK_APP=app:create_app` (set in compose) is what Flask CLI commands use.
- **`mkdir -p logs`** seeds the log dir that the compose `logs` volume mounts over at runtime (see [runtime mounts](#runtime-data--secrets--mounts_dir)).

> ***Full template:*** once you add the database, install the MySQL client build deps (`gcc`, `default-libmysqlclient-dev`, `pkg-config`) before `pip install`, prepend `flask db upgrade &&` to the `CMD` so deploys apply Alembic migrations on startup, and extend the `mkdir` to seed `uploads static/uploads/avatars`.

## Frontend image — `docker/frontend/Dockerfile`

A **multi-stage** build: Node compiles the SPA to static files, then a tiny nginx image serves them. No Node runtime ships to production.

```dockerfile
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
```

### Why the API base URL is injected at runtime (not a build arg)

The goal is **one image for every environment** — what you QA is byte-for-byte what ships to prod; only the running environment changes. Vite **inlines** `import.meta.env.VITE_*` at build time, which would freeze the API domain into the bundle and force a separate build per environment. Instead:

- The app reads `window.__APP_CONFIG__.API_BASE_URL`, populated by `/config.js`.
- `docker/frontend/40-render-config.sh` (run by nginx's `/docker-entrypoint.d/` hook at startup) regenerates `/config.js` from the container's `API_BASE_URL` env var.
- Compose supplies that env var per environment (`environment: - API_BASE_URL=...`); no rebuild, no build args.
- nginx serves `/config.js` with `Cache-Control: no-cache` so an env change takes effect on the next page load.

In **local dev** the default `frontend/public/config.js` leaves the base URL empty, and the Vite dev proxy forwards `/api` to the backend (same-origin, no CORS).

### nginx — `docker/frontend/nginx.conf`

```nginx
server {
    listen 3000;
    root /usr/share/nginx/html;
    index index.html;

    # Vite assets are content-hashed (index-AbC123.js) — safe to cache forever.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files $uri =404;
    }

    # Never cache the entry HTML, so a new deploy is picked up immediately.
    location = /index.html {
        add_header Cache-Control "no-cache";
    }

    # Runtime config, regenerated per environment at startup — never cache it,
    # so an env change takes effect on the next page load.
    location = /config.js {
        add_header Cache-Control "no-cache";
    }

    # SPA history fallback (vue-router createWebHistory): unknown paths → index.html.
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

The history fallback is what lets `app.example.com/workorders/42` load directly instead of 404ing — every non-file path serves `index.html` and the router takes over.

## Compose — `docker/docker-compose.yml`

```yaml
services:
  backend:
    container_name: helloworld-backend
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "${BACKEND_PORT}:5000"
    # MOUNTS_DIR holds runtime data + secrets OUTSIDE the code tree. Defaults to
    # .. (repo) for local dev; the server sets an absolute path. The .env is
    # marked optional so the stack still starts without one (this sample needs
    # no secrets to serve the example endpoint).
    env_file:
      - path: ${MOUNTS_DIR:-..}/.env
        required: false
    environment:
      - FLASK_APP=app:create_app
      # The SPA calls this API cross-origin, so allow its origin. Value is
      # defined in start.sh (CORS_ORIGINS).
      - CORS_ORIGINS=${CORS_ORIGINS}
    volumes:
      - ${MOUNTS_DIR:-..}/logs:/app/logs
    restart: unless-stopped

  frontend:
    container_name: helloworld-frontend
    build:
      context: ..
      dockerfile: docker/frontend/Dockerfile
    depends_on:
      - backend
    ports:
      - "${FRONTEND_PORT}:3000"
    # Injected into /config.js at container STARTUP (not baked into the image),
    # so the same image runs in every environment. Value defined in start.sh.
    environment:
      - API_BASE_URL=${API_BASE_URL}
    restart: unless-stopped
    healthcheck:
      # nginx serves the SPA on 3000. Use 127.0.0.1 (not localhost/::1).
      test: ["CMD-SHELL", "wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
```

- **`env_file` and `volumes` are anchored to `${MOUNTS_DIR:-..}`** — see below. The `.env` is `required: false`, so the stack starts even without one.
- **Ports and URLs come from the environment** (`BACKEND_PORT`, `FRONTEND_PORT`, `CORS_ORIGINS`, `API_BASE_URL`) — the compose file sets no defaults, so `start.sh` exports them.
- **`API_BASE_URL` is a runtime `environment` value**, not a build `arg` — it's injected into `/config.js` at container startup, so one image serves every environment.
- **The healthcheck** lets `docker compose up --wait` block until the SPA is actually serving.

> ***Full template:*** add the persistent-data volumes the app writes to — `${MOUNTS_DIR:-..}/uploads:/app/uploads` and `${MOUNTS_DIR:-..}/static_uploads:/app/static/uploads` — alongside the `logs` mount.

### Runtime data & secrets — `MOUNTS_DIR`

Secrets (`.env`) and user data (`uploads/`, `logs/`) must **not** live inside the code tree, because the deploy clean-syncs the source with `rsync --delete` (anything not in the repo gets wiped). So they're mounted from `MOUNTS_DIR`:

- **Local dev:** `MOUNTS_DIR` is unset → defaults to `..` (the repo root). Your local `.env`, `uploads/`, and `logs/` are used directly. Nothing extra to set up.
- **Server:** the deploy exports an absolute `MOUNTS_DIR` (e.g. `/app/data/myapp`) holding the real `.env` and persistent data. The `rsync --delete` of the code tree can never touch it.

The container paths (`/app/uploads`, `/app/static/uploads`, `/app/logs`) are seeded by the backend Dockerfile's `mkdir`, then mounted over by these volumes so data survives rebuilds.

## `.dockerignore`

Shared by both build contexts (repo root). Keeps the context small and prevents host-built artifacts from leaking into images (they're rebuilt inside the image instead):

```
.git
.idea
.pytest_cache
**/__pycache__
*.py[cod]
venv
**/node_modules
frontend/dist
*.log
.DS_Store
**/.DS_Store
```

## Running it

This project's Docker daemon runs on a **separate host**, so confirm `DOCKER_HOST` points at the right daemon before building or testing:

```sh
echo "$DOCKER_HOST"   # must target the intended Docker host
```

### Local (whole stack in containers)

```sh
./start.sh                 # exports ports/URLs, then builds + starts the compose stack
# backend → http://localhost:8002   frontend → http://localhost:8001
```

The compose file reads `BACKEND_PORT` / `FRONTEND_PORT` / `CORS_ORIGINS` / `API_BASE_URL` from the environment and sets no defaults, so use `start.sh` (which exports them) rather than a bare `docker compose up`. With `MOUNTS_DIR` unset, an optional `.env` at the repo root is loaded if present.

> For day-to-day work, use [`dev_start.sh`](#running-locally) (Flask + Vite, no Docker). Docker is for parity testing and deploys.

### Common commands

```sh
COMPOSE="docker compose -f docker/docker-compose.yml"
$COMPOSE build backend frontend     # rebuild images
$COMPOSE up -d --wait               # start, block on healthchecks
$COMPOSE ps                         # status
$COMPOSE logs -f backend            # tail API logs
$COMPOSE down                       # stop & remove containers
```

## Deploy — `scripts/deploy.sh` → `scripts/run.sh`

***Full template*** (the `scripts/` directory is not in this sample yet). Deploys are two scripts. **`deploy.sh`** (run from your machine) ships the code; **`run.sh`** (runs on the server) rebuilds and swaps containers with no downtime.

```
deploy.sh                                   run.sh (on server)
─────────                                   ──────────────────
rsync -az --delete code → server      ┌──►  source $MOUNTS_DIR/.env
  excludes: venv, .git, node_modules, │     build backend + frontend   (old containers keep serving)
  dist, __pycache__,                  │     up -d --wait                (swap only after healthchecks pass)
  AND the runtime mounts (.env,       │     docker compose ps
  uploads, static/uploads, logs)      │     purge Cloudflare cache      (if CLOUDFLARE_* set)
ssh server, export MOUNTS_DIR ────────┘
```

Why it's safe and zero-downtime:

- **`rsync --delete` makes the server match the repo** — files removed from the repo stop getting baked into images. The runtime mounts and `.env` are **excluded**, so `--delete` never touches secrets or user data, and a local `.env` is never shipped over the server's.
- **`run.sh` builds the new images while the current containers keep serving**, then `up -d --wait` recreates them only after the build finishes and the healthchecks pass. There's no `down` step, so no full-build outage.
- **Cloudflare cache is purged** after the swap if `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ZONE_ID` are set (otherwise skipped). Combined with nginx's no-cache on `index.html`, a deploy is picked up immediately.

---

## Starting a fresh project from this template

**Backend**

1. **Scaffold the factory.** Copy `app.py`'s `create_app()`, `lib/extensions.py`, and `lib/rbac.py`. Trim `ROLE_PERMISSIONS` to your roles.
2. **Stand up the API blueprint.** Copy `api/__init__.py`, `api/utils.py`, `api/serializers.py`, `api/docs.py`, and `api/auth.py` — these give you JSON errors, the auth decorators, serialization, auto-docs, and login/session out of the box.
3. **Add resource modules.** For each resource, create `api/<resource>.py` with a `register(bp)` + function views, a `serialize_<resource>` in `serializers.py`, and wire it into `api/__init__.py`.
4. **Models + migrations.** Define models in `lib/models/`, `flask db init` (once), then `migrate` / `upgrade`.

**Frontend**

5. **Scaffold the SPA** (`npm create vite@latest … --template vue`, add `vue-router@4`), recreate `views/` + `components/` + layered `assets/styles/`, and copy `useApi.js` / `useAuth.js` + the router-guard pattern so the client contract matches.

**Docker & config**

6. **Copy `docker/` and `start.sh`.** Set `container_name`s, the `API_BASE_URL` value in `start.sh`, published ports, and (full template) `deploy.sh`'s `REMOTE_HOST` / `REMOTE_PATH`. Keep the gunicorn `--bind`, `EXPOSE`, and compose `ports`/healthcheck in sync if you change the backend port.
7. **Set up `MOUNTS_DIR`** on the server with the real `.env` and empty `uploads/`, `static_uploads/`, `logs/`.
8. **Provide config at `MOUNTS_DIR`, not in the repo.** There are no committed `.env` / `.env.example` files (see [Environment variables](#environment-variables)). Generate a real `SECRET_KEY` and set `CORS_ORIGINS` in the server's `MOUNTS_DIR/.env`; set `API_BASE_URL` via `start.sh` / compose.
```
