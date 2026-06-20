"""Example resource module: a single get_message() endpoint.

Follows the API pattern from PROJECT_SETUP.md — plain function views registered
via bp.add_url_rule in register(bp). The view's docstring first line is its
OpenAPI summary, so keep it short.
"""

from datetime import datetime, timezone

from flask import jsonify


def register(bp):
    bp.add_url_rule("/message", view_func=get_message, methods=["GET"])


def get_message():
    """Return a greeting with the current server date and time."""
    now = datetime.now(timezone.utc)
    return jsonify({
        "message": "Hello World",
        "datetime": now.isoformat(),
    })
