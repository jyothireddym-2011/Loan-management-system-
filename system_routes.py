"""
Health checks + admin-only operational endpoints (demonstrates RBAC via
require_role, review recommendation: "Role-based access control").

Two flavours of health check, matching the Kubernetes/orchestrator
liveness-vs-readiness distinction so a load balancer or scheduler can
tell "process is up" apart from "process can actually serve traffic":

- /health         liveness  — process is running and can respond at all.
                    Deliberately does NOT touch the database: a slow/
                    unreachable DB should not cause an orchestrator to
                    kill and restart otherwise-healthy pods.
- /health/ready    readiness — process is running AND its dependencies
                    (database) are reachable. Used to gate traffic
                    (e.g. remove the pod from a Service's endpoints)
                    without restarting it.
"""
import logging

from flask import Blueprint, jsonify

from middleware.auth import require_auth, require_role
from repositories.database import get_db
from services.auth_service import AuthService

logger = logging.getLogger("app.health")

system_bp = Blueprint("system", __name__)


@system_bp.route("/", methods=["GET"])
@system_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "service": "lending-platform-backend"})


@system_bp.route("/health/live", methods=["GET"])
def liveness_check():
    return jsonify({"status": "ok", "check": "liveness"})


@system_bp.route("/health/ready", methods=["GET"])
def readiness_check():
    db = get_db()
    try:
        with db.connection() as conn:
            conn.cursor().execute("SELECT 1")
    except Exception:  # pragma: no cover - defensive; DB is up in tests
        logger.exception("readiness_check_failed")
        return jsonify({
            "status": "unavailable",
            "check": "readiness",
            "database": "unreachable",
        }), 503

    return jsonify({"status": "ok", "check": "readiness", "database": "reachable"})


@system_bp.route("/admin/sessions/cleanup", methods=["POST"])
@require_auth
@require_role("admin")
def trigger_session_cleanup(current_user):
    removed = AuthService().cleanup_expired_sessions()
    return jsonify({"success": True, "removed_sessions": removed})
