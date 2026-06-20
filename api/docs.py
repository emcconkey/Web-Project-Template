"""Auto-generated OpenAPI spec + Swagger UI.

The OpenAPI 3 document is built **from the live Flask `url_map` on every
request** — there is no hand-maintained spec to drift. Any route added to
`api/*.py` shows up automatically:

  - GET /api/docs          → Swagger UI (HTML).
  - GET /api/openapi.json  → the generated OpenAPI 3 document.

Each operation's **summary** is the view function's first docstring line; the
rest of the docstring becomes its description. Operations are **tagged** by the
first path segment (`/api/message` → tag `message`), and methods on the same
path (e.g. GET + POST) merge into one path item.

This sample has no auth layer, so the docs are open. The fuller template gates
both routes behind `@api_login_required` and adds a `sessionCookie` security
scheme so Swagger UI's "Try it out" sends the session cookie.
"""

import re

from flask import current_app, jsonify

OPENAPI_VERSION = "3.0.3"

# Flask rule param → OpenAPI path template: /items/<int:id> → /items/{id}
_RULE_PARAM = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")

# Swagger UI is loaded from a CDN (browser-side only — no Python dependency and
# nothing to vendor). The page is same-origin with the API, so the spec URL and
# "Try it out" calls resolve against this backend.
_SWAGGER_UI_HTML = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({{
        url: "{spec_url}",
        dom_id: "#swagger-ui",
      }});
    </script>
  </body>
</html>
"""


def register(bp):
    bp.add_url_rule("/openapi.json", view_func=openapi_spec, methods=["GET"])
    bp.add_url_rule("/docs", view_func=swagger_ui, methods=["GET"])


def swagger_ui():
    """Interactive API documentation (Swagger UI)."""
    title = current_app.config.get("API_TITLE", "API documentation")
    return _SWAGGER_UI_HTML.format(title=title, spec_url="/api/openapi.json")


def openapi_spec():
    """OpenAPI 3 specification for the JSON API."""
    return jsonify(_build_spec())


def _build_spec():
    app = current_app
    paths = {}

    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static" or not rule.rule.startswith("/api"):
            continue
        # Don't document the docs plumbing itself.
        if rule.rule in ("/api/openapi.json", "/api/docs"):
            continue

        openapi_path = _RULE_PARAM.sub(r"{\1}", rule.rule)
        summary, description = _doc_parts(app.view_functions.get(rule.endpoint))
        parameters = _path_parameters(rule)
        tag = _tag_for(openapi_path)

        path_item = paths.setdefault(openapi_path, {})
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            operation = {
                "summary": summary,
                "tags": [tag],
                "responses": {"200": {"description": "Successful response"}},
            }
            if description:
                operation["description"] = description
            if parameters:
                operation["parameters"] = parameters
            path_item[method.lower()] = operation

    return {
        "openapi": OPENAPI_VERSION,
        "info": {
            "title": app.config.get("API_TITLE", "API"),
            "version": app.config.get("API_VERSION", "1.0.0"),
        },
        "paths": paths,
    }


def _doc_parts(view):
    """Split a view's docstring into (summary, description)."""
    if not view or not view.__doc__:
        return "", ""
    lines = [line.strip() for line in view.__doc__.strip().splitlines()]
    summary = lines[0] if lines else ""
    description = " ".join(line for line in lines[1:] if line).strip()
    return summary, description


def _tag_for(openapi_path):
    """Tag = first non-parameter path segment after /api (e.g. /api/message → message)."""
    segments = [p for p in openapi_path.split("/") if p and not p.startswith("{")]
    return segments[1] if len(segments) > 1 else "api"


def _path_parameters(rule):
    """Typed OpenAPI path params from the rule's converters (best effort)."""
    converters = getattr(rule, "_converters", {})
    params = []
    for arg in sorted(rule.arguments):
        is_int = type(converters.get(arg)).__name__ == "IntegerConverter"
        params.append({
            "name": arg,
            "in": "path",
            "required": True,
            "schema": {"type": "integer" if is_int else "string"},
        })
    return params
