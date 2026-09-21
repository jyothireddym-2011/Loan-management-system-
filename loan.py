"""
Loan model. Monetary fields are stored and handled as Decimal end-to-end
(production-roadmap item: "Use Decimal instead of float for monetary
calculations") — see utils/money.py for the conversion helpers used at the
SQLite boundary, where values are persisted as TEXT to avoid float drift.
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Loan:
    id: int
    user_id: int
    borrower_id: int
    borrower_name: str
    lender_name: str
    loan_amount: Decimal
    paid_amount: Decimal
    remaining_amount: Decimal
    nominee_name: Optional[str]
    nominee_signature: str
    lender_signature: str
    borrower_signature: str
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Loan":
        from utils.money import to_decimal
        return cls(
            id=row["id"], user_id=row["user_id"], borrower_id=row["borrower_id"],
            borrower_name=row["borrower_name"], lender_name=row["lender_name"],
            loan_amount=to_decimal(row["loan_amount"]), paid_amount=to_decimal(row["paid_amount"]),
            remaining_amount=to_decimal(row["remaining_amount"]),
            nominee_name=row["nominee_name"], nominee_signature=row["nominee_signature"],
            lender_signature=row["lender_signature"], borrower_signature=row["borrower_signature"],
            created_at=row["created_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "user_id": self.user_id, "borrower_id": self.borrower_id,
            "borrower_name": self.borrower_name, "lender_name": self.lender_name,
            "loan_amount": str(self.loan_amount), "paid_amount": str(self.paid_amount),
            "remaining_amount": str(self.remaining_amount), "nominee_name": self.nominee_name,
            "created_at": self.created_at,
        }
