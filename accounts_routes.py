"""
Accounts routes.
POST /accounts/register
POST /accounts/login
POST /accounts/logout
GET  /accounts/me
---
openapi: /accounts/register
tags: [Accounts]
summary: Register a new user
---
"""
from flask import Blueprint, g, jsonify, request

from middleware.auth import require_auth
from middleware.rate_limit import rate_limited
from services.auth_service import AuthService

accounts_bp = Blueprint("accounts", __name__, url_prefix="/accounts")


@accounts_bp.route("/register", methods=["POST"])
@rate_limited("register", max_requests=10, window_seconds=60)
def register():
    data = request.get_json(force=True, silent=True) or {}
    user = AuthService().register(data)
    return jsonify({"success": True, "user": user}), 201


@accounts_bp.route("/login", methods=["POST"])
@rate_limited("login", max_requests=10, window_seconds=60)
def login():
    data = request.get_json(force=True, silent=True) or {}
    result = AuthService().login(data)
    return jsonify({"success": True, **result})


@accounts_bp.route("/logout", methods=["POST"])
@require_auth
def logout(current_user):
    AuthService().logout(g.current_jti, user_id=current_user["id"])
    return jsonify({"success": True, "message": "Logged out."})


@accounts_bp.route("/me", methods=["GET"])
@require_auth
def me(current_user):
    return jsonify({"success": True, "user": {
        "id": current_user["id"], "name": current_user["name"],
        "email": current_user["email"], "phone": current_user["phone"],
    }})
