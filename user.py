"""User model. Role added for basic RBAC (admin vs user)."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    name: str
    email: str
    phone: Optional[str]
    password_hash: str
    role: str  # "user" | "admin"
    is_active: bool
    created_at: str

    @classmethod
    def from_row(cls, row) -> "User":
        return cls(
            id=row["id"], name=row["name"], email=row["email"], phone=row["phone"],
            password_hash=row["password_hash"], role=row["role"],
            is_active=bool(row["is_active"]), created_at=row["created_at"],
        )

    def to_public_dict(self) -> dict:
        """Never includes password_hash."""
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "phone": self.phone, "role": self.role, "created_at": self.created_at,
        }
