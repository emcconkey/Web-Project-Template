"""Application factory.

A trimmed-down version of the architecture described in PROJECT_SETUP.md: a
Flask JSON API exposed under /api. This sample omits the database, auth, and
migrations layers — it exists only to serve the example get_message() endpoint
and demonstrate the app-factory + blueprint wiring.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent


def create_app():
    load_dotenv(BASE_DIR / ".env")

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "change-me"),
        # Shown in the auto-generated OpenAPI docs (api/docs.py).
        API_TITLE="Web Project Template API",
        API_VERSION="1.0.0",
    )

    # Register the JSON API blueprint (/api/*).
    import api
    api.init_app(app)

    # Credentialed CORS scoped to /api/*, origins from CORS_ORIGINS.
    cors_origins = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "").split(",")
        if o.strip()
    ]
    if cors_origins:
        CORS(app, resources={r"/api/*": {"origins": cors_origins}},
             supports_credentials=True)

    return app


# gunicorn serves this module-level app (see docker/Dockerfile: `app:app`).
app = create_app()


if __name__ == "__main__":
    app.run(port=5000, debug=True)
