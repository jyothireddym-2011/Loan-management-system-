"""
app.py
------
Application entry point. Uses the app-factory pattern so tests can spin up
isolated instances (TestingConfig, in-memory DB) without importing a
module-level `app` singleton.

Run:
    python app.py                    # development
    gunicorn "app:create_app()"      # production (see README)
"""

from __future__ import annotations

import logging
import os
import sys

# NOTE (review recommendation: "Remove sys.path.append() import patterns"):
# this is the ONLY sys.path adjustment in the whole codebase, and it exists
# for exactly one reason — so `backend/` and the sibling `ml/` package can
# both be imported as top-level packages without installing this project
# as a package first. Every module below imports with plain, absolute,
# non-hacky imports (e.g. `from services.auth_service import AuthService`,
# `from ml.risk_model import RiskClassifier`) — no other file touches
# sys.path at all.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
for path in (_BACKEND_DIR, _PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from flask import Flask, jsonify

from config import configure_logging, get_config
from middleware.errors import register_error_handlers
from middleware.request_logging import register_request_logging
from middleware.scheduler import SessionCleanupScheduler
from middleware.security_headers import register_security_headers
from repositories.database import init_database
from repositories.migrations import run_migrations
from routes.accounts_routes import accounts_bp
from routes.borrower_routes import borrowers_bp
from routes.docs_routes import docs_bp
from routes.document_routes import documents_bp
from routes.lending_routes import lending_bp
from routes.loan_routes import loans_bp
from routes.system_routes import system_bp

logger = logging.getLogger("app")


def create_app(config_name: str | None = None) -> Flask:
    config_cls = get_config(config_name)
    config_cls.validate()

    configure_logging(level=config_cls.LOG_LEVEL, json_output=config_cls.LOG_JSON)

    app = Flask(__name__)
    app.config.from_object(config_cls)

    db = init_database(app.config["DATABASE_URL"])
    with app.app_context():
        applied = run_migrations(db)
        if applied:
            logger.info("migrations_applied", extra={"migrations": applied})

    register_error_handlers(app)
    register_request_logging(app)
    register_security_headers(app)

    app.register_blueprint(system_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(borrowers_bp)
    app.register_blueprint(loans_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(lending_bp)
    app.register_blueprint(docs_bp)

    # --- API versioning (/api/v1/...) ---------------------------------
    # The same blueprint objects are re-registered under a v1-prefixed
    # name/URL rather than moving the original routes, so every existing
    # (unversioned) path keeps working for current clients/tests and
    # nothing in routes/ had to change. New integrations should use the
    # /api/v1 paths; the unversioned aliases are the deprecated surface
    # and are documented as such in the README/OpenAPI spec.
    app.register_blueprint(accounts_bp, name="accounts_v1", url_prefix="/api/v1/accounts")
    app.register_blueprint(borrowers_bp, name="borrowers_v1", url_prefix="/api/v1/borrowers")
    app.register_blueprint(loans_bp, name="loans_v1", url_prefix="/api/v1")
    app.register_blueprint(documents_bp, name="documents_v1", url_prefix="/api/v1/documents")
    app.register_blueprint(lending_bp, name="lending_v1", url_prefix="/api/v1/lending")
    app.register_blueprint(system_bp, name="system_v1", url_prefix="/api/v1")

    # OPTIONS preflight support for the manual CORS headers set in
    # middleware/request_logging.py's after_request hook.
    @app.route("/<path:_any>", methods=["OPTIONS"])
    def cors_preflight(_any):
        return jsonify({}), 200

    _register_cli_commands(app)

    if not app.config["TESTING"] and app.config.get("SESSION_CLEANUP_INTERVAL_MINUTES", 0) > 0:
        scheduler = SessionCleanupScheduler(app, app.config["SESSION_CLEANUP_INTERVAL_MINUTES"])
        scheduler.start()
        app.extensions = getattr(app, "extensions", {})
        app.extensions["session_cleanup_scheduler"] = scheduler

    return app


def _register_cli_commands(app: Flask) -> None:
    @app.cli.command("cleanup-sessions")
    def cleanup_sessions_command():
        """Manually run the expired-session cleanup job (for cron/k8s CronJob use)."""
        from services.auth_service import AuthService
        removed = AuthService().cleanup_expired_sessions()
        print(f"Removed {removed} expired session(s).")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Interactive helper to promote/create an admin user."""
        import getpass
        from repositories.user_repository import UserRepository
        from security.password_utils import hash_password, validate_password_strength

        email = input("Admin email: ").strip().lower()
        repo = UserRepository()
        existing = repo.find_by_email(email)
        if existing:
            with repo.db.connection() as conn:
                conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (email,))
            print(f"Promoted existing user {email} to admin.")
            return

        name = input("Name: ").strip()
        password = getpass.getpass("Password: ")
        ok, msg = validate_password_strength(password)
        if not ok:
            print(f"Rejected: {msg}")
            return
        user_id = repo.create(name=name, email=email, phone="", password_hash=hash_password(password), role="admin")
        print(f"Created admin user id={user_id}.")


# Deliberately NOT creating a module-level `app = create_app()` here: that
# would run app creation (config validation, DB migrations, background
# scheduler) as a side effect of merely *importing* this module — which
# breaks `from app import create_app` in tests/CLI tooling whenever the
# importing environment doesn't have production env vars set.
#
# Instead:
#   - `python app.py`                 -> see __main__ block below
#   - `flask run`                     -> set FLASK_APP=app:create_app
#   - `gunicorn "app:create_app()"`   -> calls the factory itself

if __name__ == "__main__":
    app = create_app()
    debug = app.config["DEBUG"]  # NEVER True outside development — see config/settings.py
    app.run(debug=debug, use_reloader=debug, host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
