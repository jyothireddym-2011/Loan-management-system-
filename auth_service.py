"""
Auth business logic: registration, login (issues JWT), logout (revokes
jti), session cleanup. Routes call this — never touch repositories or
password/JWT internals directly.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import current_app

from middleware.errors import AuthError, ConflictError, ValidationError
from repositories.audit_repository import AuditRepository
from repositories.session_repository import SessionRepository
from repositories.user_repository import UserRepository
from security.jwt_utils import issue_access_token
from security.password_utils import hash_password, verify_password
from validators.auth_validators import validate_login, validate_registration

logger = logging.getLogger("app.auth")


class AuthService:
    def __init__(self, user_repo: UserRepository = None, session_repo: SessionRepository = None,
                 audit_repo: AuditRepository = None):
        self.user_repo = user_repo or UserRepository()
        self.session_repo = session_repo or SessionRepository()
        # Auth events (register/login success+failure/logout) are the most
        # security-sensitive actions in the system, so — unlike loans/
        # documents/lending, which already had this — they now also write
        # to the persistent audit_log table, not just the app log stream.
        self.audit_repo = audit_repo or AuditRepository()

    def register(self, data: dict) -> dict:
        ok, msg = validate_registration(data)
        if not ok:
            raise ValidationError(msg)

        email = data["email"].strip().lower()
        if self.user_repo.find_by_email(email):
            raise ConflictError("An account with this email already exists.")

        password_hash = hash_password(data["password"])
        user_id = self.user_repo.create(
            name=data["name"], email=email, phone=data.get("phone", ""), password_hash=password_hash,
        )
        self.audit_repo.log("user_registered", user_id=user_id, entity_type="user", entity_id=user_id)
        logger.info("user_registered", extra={"user_id": user_id})
        return {"id": user_id, "name": data["name"].strip(), "email": email}

    def login(self, data: dict) -> dict:
        ok, msg = validate_login(data)
        if not ok:
            raise ValidationError(msg)

        row = self.user_repo.find_by_email(data["email"])
        if not row or not verify_password(data["password"], row["password_hash"]):
            self.audit_repo.log("login_failed", detail=f"email={data.get('email', '')[:64]}")
            logger.warning("login_failed", extra={"email": data.get("email", "")[:64]})
            raise AuthError("Invalid email or password.")

        if not row["is_active"]:
            self.audit_repo.log("login_rejected_inactive", user_id=row["id"])
            raise AuthError("This account has been deactivated.")

        token, jti, expires_at = issue_access_token(
            user_id=row["id"],
            secret=current_app.config["JWT_SECRET_KEY"],
            algorithm=current_app.config["JWT_ALGORITHM"],
            ttl=current_app.config["JWT_ACCESS_TTL"],
        )
        self.session_repo.create(row["id"], jti, expires_at.isoformat())
        self.audit_repo.log("login_success", user_id=row["id"], entity_type="session")
        logger.info("login_success", extra={"user_id": row["id"]})

        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "user": {"id": row["id"], "name": row["name"], "email": row["email"]},
        }

    def logout(self, jti: str, user_id: int | None = None) -> bool:
        revoked = self.session_repo.revoke(jti)
        self.audit_repo.log("logout", user_id=user_id, entity_type="session", detail=f"revoked={revoked}")
        logger.info("logout", extra={"revoked": revoked})
        return revoked

    def cleanup_expired_sessions(self) -> int:
        """
        Session cleanup job (production-roadmap item: "Add session
        cleanup jobs"). Called on an interval by scheduler.py and
        available as a one-off CLI command (`flask cleanup-sessions`).
        """
        removed = self.session_repo.delete_expired()
        if removed:
            logger.info("sessions_cleaned_up", extra={"removed_count": removed})
        return removed
