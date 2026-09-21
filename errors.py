"""
Central error types + handlers. Every route raises AppError (or a subclass)
instead of hand-rolling jsonify(...) tuples, so the response shape is
consistent everywhere and gets logged in one place.
"""
from __future__ import annotations

import logging

from flask import jsonify, g

logger = logging.getLogger("app.errors")


class AppError(Exception):
    status_code = 400

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload or {}


class ValidationError(AppError):
    status_code = 400


class AuthError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


def register_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        response = {"success": False, "error": err.message}
        response.update(err.payload)
        logger.info("app_error", extra={
            "request_id": getattr(g, "request_id", None),
            "status_code": err.status_code,
            "error": err.message,
        })
        return jsonify(response), err.status_code

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"success": False, "error": "Resource not found."}), 404

    @app.errorhandler(405)
    def handle_405(err):
        return jsonify({"success": False, "error": "Method not allowed."}), 405

    @app.errorhandler(413)
    def handle_413(err):
        return jsonify({"success": False, "error": "Request payload too large."}), 413

    @app.errorhandler(Exception)
    def handle_unexpected(err: Exception):
        logger.exception("unhandled_exception", extra={"request_id": getattr(g, "request_id", None)})
        # Never leak internals (stack traces, DB errors) to the client.
        return jsonify({"success": False, "error": "An unexpected error occurred."}), 500
