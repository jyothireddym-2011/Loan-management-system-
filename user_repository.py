"""Data access for users. No business logic here — that's services/auth_service.py."""
from .database import get_db


class UserRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def find_by_email(self, email: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
            return cur.fetchone()

    def find_by_id(self, user_id: int):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            return cur.fetchone()

    def create(self, name: str, email: str, phone: str, password_hash: str, role: str = "user") -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, email, phone, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (name.strip(), email.strip().lower(), phone, password_hash, role),
            )
            return cur.lastrowid
