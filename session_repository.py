"""Data access for the JWT-revocation sessions table."""
from .database import get_db


class SessionRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def create(self, user_id: int, jti: str, expires_at_iso: str) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sessions (user_id, jti, expires_at) VALUES (?, ?, ?)",
                (user_id, jti, expires_at_iso),
            )
            return cur.lastrowid

    def find_by_jti(self, jti: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sessions WHERE jti = ?", (jti,))
            return cur.fetchone()

    def revoke(self, jti: str) -> bool:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE jti = ?", (jti,))
            return cur.rowcount > 0

    def delete_expired(self) -> int:
        """Used by the session-cleanup job."""
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
            return cur.rowcount
