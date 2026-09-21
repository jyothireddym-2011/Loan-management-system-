"""
JWT-based authentication (production-roadmap item: "JWT-based
authentication for scalability").

Design: short-lived signed access tokens carry user_id + jti (JWT ID).
Most requests validate purely by signature/expiry — no DB hit. A `sessions`
table stores the jti as an allowlist so:
  - logout can actually revoke a specific token before it expires
  - the session-cleanup job has expired rows to sweep
This is the standard "JWT + revocation list" hybrid used when you need
both statelessness and the ability to log a user out immediately.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import jwt


class TokenError(Exception):
    pass


def issue_access_token(user_id: int, secret: str, algorithm: str, ttl) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    jti = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    expires_at = now + ttl
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return token, jti, expires_at


def decode_access_token(token: str, secret: str, algorithm: str) -> dict:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise TokenError("Token has expired.")
    except jwt.InvalidTokenError:
        raise TokenError("Token is invalid.")


def extract_bearer_token(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None
