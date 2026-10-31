import logging
import os
import secrets
from datetime import timedelta

from flask import Flask, jsonify, redirect
from flask_cors import CORS
from sqlalchemy import text

from .routes.cases import cases_api
from .routes.auth import auth_api
from .routes.bin_conversion import bin_conversion_api
from .routes.autopsy_import import autopsy_import_api
from .routes.evidence import evidence_api
from .routes.evidence_integrity import evidence_integrity_api
from .routes.telemetry import telemetry_api
from .routes.image_samples_step72 import image_samples_api
from .routes.bookmarks_step75 import bookmarks_api
from .routes.chain_of_custody_step76 import custody_api
from .routes.forensic_reports_step77 import reports_api
from .services.database import SessionLocal, initialize_database


def create_app() -> Flask:
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=1024 * 1024 * 1024 + 1024 * 1024,
    )

    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://127.0.0.1:5173",
                    "http://localhost:5173",
                ]
            }
        },
    )

    # Initialize MySQL tables.
    initialize_database()

    # Existing APIs.
    app.register_blueprint(cases_api, url_prefix="/api")
    app.register_blueprint(auth_api, url_prefix="/api")
    app.register_blueprint(bin_conversion_api, url_prefix="/api")

    # Autopsy evidence import API.
    app.register_blueprint(autopsy_import_api, url_prefix="/api")

    # Read-only Evidence Explorer API.
    app.register_blueprint(evidence_api, url_prefix="/api")

    # On-demand SHA-256 integrity verification API.
    app.register_blueprint(evidence_integrity_api, url_prefix="/api")

    # Read-only, hash-verified drone telemetry API.
    app.register_blueprint(telemetry_api, url_prefix="/api")

    # Investigator-supplied external sample gallery; separate from Autopsy evidence.
    app.register_blueprint(image_samples_api, url_prefix="/api")

    # Append-only investigator findings (Step 75A).
    app.register_blueprint(bookmarks_api, url_prefix="/api")

    # Step 76A: append-only investigator-declared chain of custody.
    app.register_blueprint(custody_api, url_prefix="/api")

    # Step 77: PDF/DOCX forensic report preview and generation.
    app.register_blueprint(reports_api, url_prefix="/api")

    @app.get("/")
    def open_frontend():
        return redirect("http://127.0.0.1:5173/", code=302)

    @app.get("/api/health")
    def health():
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))

            return jsonify({
                "status": "healthy",
                "database": "mysql",
            })

        except Exception:
            app.logger.exception("MySQL health check failed")

            return jsonify({
                "status": "unhealthy",
                "database": "mysql",
            }), 503

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({
            "error": "API route not found."
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(
            "Unhandled API error: %s",
            error,
        )

        return jsonify({
            "error": "An unexpected server error occurred."
        }), 500

    return app


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Starting MySQL case API at http://127.0.0.1:5001")

    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False,
    )
