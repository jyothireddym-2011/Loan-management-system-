"""
LendingRecord: the "lending_backend" module's core entity, folded into the
unified backend. Aadhaar is encrypted+hashed the same way as Borrower.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class LendingRecord:
    id: int
    borrower_name: str
    aadhaar_encrypted: str
    aadhaar_hash: str
    phone_number: Optional[str]
    lender_name: str
    amount: Decimal
    agreement_filename: Optional[str]
    photo_filename: Optional[str]
    password_hash: str
    update_count: int
    risk_level: str
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row) -> "LendingRecord":
        from utils.money import to_decimal
        return cls(
            id=row["id"], borrower_name=row["borrower_name"],
            aadhaar_encrypted=row["aadhaar_encrypted"], aadhaar_hash=row["aadhaar_hash"],
            phone_number=row["phone_number"], lender_name=row["lender_name"],
            amount=to_decimal(row["amount"]), agreement_filename=row["agreement_filename"],
            photo_filename=row["photo_filename"], password_hash=row["password_hash"],
            update_count=row["update_count"], risk_level=row["risk_level"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def to_public_dict(self) -> dict:
        return {
            "id": self.id, "borrower_name": self.borrower_name,
            "phone_number": self.phone_number, "lender_name": self.lender_name,
            "amount": str(self.amount), "update_count": self.update_count,
            "risk_level": self.risk_level, "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AmountHistoryEntry:
    id: int
    record_id: int
    action: str
    old_amount: Decimal
    change_amount: Decimal
    new_amount: Decimal
    risk_level: str
    event_at: str
