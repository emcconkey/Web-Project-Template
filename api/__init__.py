"""API blueprint assembly.

init_app(app) creates a single blueprint at url_prefix="/api", imports every
resource module, calls each module's register(api_bp), installs JSON (not HTML)
error handlers, and registers the blueprint.

To add a resource: create the module, import it below, and add its register() call.
"""

from flask import Blueprint, jsonify
from werkzeug.exceptions import HTTPException


def init_app(app):
    api_bp = Blueprint("api", __name__, url_prefix="/api")

    from . import message
    message.register(api_bp)
    # … one register() per module …

    # Auto-generated OpenAPI spec + Swagger UI (/api/docs, /api/openapi.json).
    from . import docs
    docs.register(api_bp)

    @api_bp.errorhandler(HTTPException)
    def handle_api_http_exception(error):
        return jsonify({"message": error.description or error.name}), error.code or 500

    @api_bp.errorhandler(Exception)
    def handle_api_exception(error):
        return jsonify({"message": "Internal server error"}), 500

    app.register_blueprint(api_bp)
