"""Append-only audit log (review recommendations: "Authentication auditing
and logging", "Audit logs" for documents, "Payment auditing")."""
from .database import get_db


class AuditRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def log(self, action: str, user_id: int | None = None, entity_type: str | None = None,
             entity_id: int | None = None, detail: str | None = None, ip_address: str | None = None):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO audit_log (user_id, action, entity_type, entity_id, detail, ip_address)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, action, entity_type, entity_id, detail, ip_address),
            )
