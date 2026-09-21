"""
Session model — backs JWT revocation.

Access tokens are short-lived signed JWTs (see security/jwt_utils.py), so
most requests never touch the database to authenticate. This table exists
so logout / admin-forced-logout actually works (a bare JWT can't be
revoked once issued) and so expired entries can be swept by the session
cleanup job (production-roadmap item: "Add session cleanup jobs").
"""
from dataclasses import dataclass


@dataclass
class Session:
    id: int
    user_id: int
    jti: str          # JWT ID claim — the thing we can revoke
    created_at: str
    expires_at: str

    @classmethod
    def from_row(cls, row) -> "Session":
        return cls(
            id=row["id"], user_id=row["user_id"], jti=row["jti"],
            created_at=row["created_at"], expires_at=row["expires_at"],
        )
