"""
Authentication middleware: validates JWT access tokens, checks the
sessions allowlist (for revocation), and injects `g.current_user`.
Also provides `require_role` for basic RBAC.
"""
from __future__ import annotations

from functools import wraps

from flask import current_app, g, request

from middleware.errors import AuthError, ForbiddenError
from repositories.session_repository import SessionRepository
from repositories.user_repository import UserRepository
from security.jwt_utils import decode_access_token, extract_bearer_token, TokenError


def get_authenticated_user():
    token = extract_bearer_token(request.headers.get("Authorization", ""))
    if not token:
        raise AuthError("Authorization header with a Bearer token is required.")

    try:
        claims = decode_access_token(
            token, current_app.config["JWT_SECRET_KEY"], current_app.config["JWT_ALGORITHM"]
        )
    except TokenError as exc:
        raise AuthError(str(exc))

    jti = claims.get("jti")
    session = SessionRepository().find_by_jti(jti)
    if not session:
        raise AuthError("Session has been revoked or expired. Please log in again.")

    user = UserRepository().find_by_id(int(claims["sub"]))
    if not user or not user["is_active"]:
        raise AuthError("Account is inactive or no longer exists.")

    return user, jti


def require_auth(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        user, jti = get_authenticated_user()
        g.current_user = user
        g.current_jti = jti
        return route_function(user, *args, **kwargs)
    return wrapper


def require_role(*allowed_roles: str):
    def decorator(route_function):
        @wraps(route_function)
        def wrapper(current_user, *args, **kwargs):
            if current_user["role"] not in allowed_roles:
                raise ForbiddenError("You do not have permission to perform this action.")
            return route_function(current_user, *args, **kwargs)
        return wrapper
    return decorator
