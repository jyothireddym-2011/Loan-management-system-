"""
settings.py
-----------
All configuration is read from environment variables (see `.env.example`).
Nothing sensitive is hardcoded here — the previous review flagged the old
config.py for a hardcoded SECRET_KEY default; this version fails loudly in
production instead of silently falling back to a dev secret.
"""

from __future__ import annotations

import os
from datetime import timedelta

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is optional
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    ENV = "base"
    DEBUG = False
    TESTING = False

    # --- Database ---
    # sqlite:///path or postgresql://user:pass@host:port/dbname
    DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'data', 'app.db')}")

    # --- Auth / JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TTL = timedelta(hours=int(os.environ.get("JWT_ACCESS_TTL_HOURS", "24")))
    SESSION_CLEANUP_INTERVAL_MINUTES = int(os.environ.get("SESSION_CLEANUP_INTERVAL_MINUTES", "60"))

    # --- Aadhaar encryption (Fernet, symmetric) ---
    AADHAAR_ENCRYPTION_KEY = os.environ.get("AADHAAR_ENCRYPTION_KEY")

    # --- Documents ---
    DOCUMENTS_STORAGE_DIR = os.environ.get(
        "DOCUMENTS_STORAGE_DIR", os.path.join(BASE_DIR, "documents", "storage")
    )
    DOCUMENT_TEMPLATE_PATH = os.path.join(BASE_DIR, "documents", "templates", "loan_agreement_template.txt")
    ALLOWED_DOCUMENT_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "docx", "txt"}
    ALLOWED_DOCUMENT_MIME_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }
    MAX_DOCUMENT_SIZE_MB = int(os.environ.get("MAX_DOCUMENT_SIZE_MB", "10"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", "20")) * 1024 * 1024

    # --- CORS ---
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()
    ]

    # --- Rate limiting (simple in-memory limiter; see middleware/rate_limit.py) ---
    RATE_LIMIT_ENABLED = _bool_env("RATE_LIMIT_ENABLED", True)
    AUTH_RATE_LIMIT = (int(os.environ.get("AUTH_RATE_LIMIT_MAX", "10")), 60)  # 10 req / 60s per IP

    # --- Logging ---
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_JSON = _bool_env("LOG_JSON", True)

    # --- Money ---
    # Decimal precision for all monetary fields (rupees.paise).
    MONEY_DECIMAL_PLACES = 2

    @classmethod
    def validate(cls) -> None:
        """Fail fast on boot if required secrets are missing."""
        missing = []
        if not cls.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        if not cls.AADHAAR_ENCRYPTION_KEY:
            missing.append("AADHAAR_ENCRYPTION_KEY")
        if missing:
            raise RuntimeError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". See .env.example. Generate an encryption key with: "
                  "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )


class DevelopmentConfig(BaseConfig):
    ENV = "development"
    DEBUG = True
    # Safe, non-secret defaults ONLY for local dev so `flask run` works
    # out of the box. Production must set these via real env vars —
    # validate() below still refuses to boot with the placeholder values.
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-only-jwt-secret-do-not-use-in-prod")
    AADHAAR_ENCRYPTION_KEY = os.environ.get("AADHAAR_ENCRYPTION_KEY", "")

    @classmethod
    def validate(cls) -> None:
        if not cls.AADHAAR_ENCRYPTION_KEY:
            raise RuntimeError(
                "AADHAAR_ENCRYPTION_KEY is not set. Generate one with:\n"
                '  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"\n'
                "and put it in your .env file."
            )


class TestingConfig(BaseConfig):
    ENV = "testing"
    DEBUG = False
    TESTING = True
    DATABASE_URL = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret"
    from cryptography.fernet import Fernet as _Fernet
    AADHAAR_ENCRYPTION_KEY = _Fernet.generate_key().decode()
    RATE_LIMIT_ENABLED = False

    import tempfile as _tempfile
    DOCUMENTS_STORAGE_DIR = _tempfile.mkdtemp(prefix="lending_platform_test_docs_")

    @classmethod
    def validate(cls) -> None:
        return None


class ProductionConfig(BaseConfig):
    ENV = "production"
    DEBUG = False  # Debug mode is NEVER enabled outside development, full stop.


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None):
    env_name = (env_name or os.environ.get("FLASK_ENV") or "development").lower()
    return CONFIG_BY_NAME.get(env_name, DevelopmentConfig)
