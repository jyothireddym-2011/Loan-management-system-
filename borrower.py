"""
Borrower model.

Aadhaar is never stored in plaintext:
  - aadhaar_encrypted: Fernet ciphertext (reversible, for authorized display)
  - aadhaar_hash:      SHA-256 of the normalized number (deterministic,
                        used as the uniqueness key / lookup index, since you
                        cannot query on Fernet ciphertext directly)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Borrower:
    id: int
    user_id: int
    name: str
    aadhaar_encrypted: str
    aadhaar_hash: str
    phone: Optional[str]
    address: Optional[str]
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Borrower":
        return cls(
            id=row["id"], user_id=row["user_id"], name=row["name"],
            aadhaar_encrypted=row["aadhaar_encrypted"], aadhaar_hash=row["aadhaar_hash"],
            phone=row["phone"], address=row["address"], created_at=row["created_at"],
        )
