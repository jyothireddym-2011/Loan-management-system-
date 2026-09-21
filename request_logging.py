"""
Structured request logging + CORS + request-id correlation.
(review recommendations: "Add structured logging", "Request/response
logging" from the FastAPI section applied here too.)
"""
from __future__ import annotations

import logging
import time
import uuid

from flask import g, request

logger = logging.getLogger("app.requests")

_SENSITIVE_KEYS = {"password", "confirm_password", "aadhaar_number", "token", "authorization"}


def register_request_logging(app) -> None:
    @app.before_request
    def _start_timer():
        g.request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        g._start_time = time.monotonic()

    @app.after_request
    def _log_and_tag(response):
        duration_ms = round((time.monotonic() - g.get("_start_time", time.monotonic())) * 1000, 2)
        user = g.get("current_user")
        logger.info(
            "request_completed",
            extra={
                "request_id": g.get("request_id"),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user["id"] if user else None,
                "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
            },
        )
        response.headers["X-Request-ID"] = g.get("request_id", "")

        origins = app.config.get("CORS_ALLOWED_ORIGINS") or []
        origin = request.headers.get("Origin")
        if origin and (origin in origins or "*" in origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Vary"] = "Origin"

        return response
