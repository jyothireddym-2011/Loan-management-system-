# syntax=docker/dockerfile:1
# Production image for the lending-platform backend.
# Build:  docker build -t lending-platform-backend .
# Run:    docker run --env-file .env -p 5000:5000 lending-platform-backend

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps: libmagic (optional MIME sniffing) + build tools for
# cryptography/psycopg2 wheels that don't ship prebuilt manylinux wheels
# for the target platform.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user; never run the app (or gunicorn) as root.
RUN useradd --create-home --uid 1000 appuser

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runtime-writable dirs (SQLite file + uploaded documents) when not using
# external volumes / Postgres.
RUN mkdir -p /app/data /app/documents/storage \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

# gunicorn, not the Flask dev server, per README "Running in production".
# Workers/threads are conservative defaults; tune via GUNICORN_* env vars
# or override the CMD in docker-compose/orchestrator config.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "--threads", "2", \
     "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", \
     "app:create_app()"]
