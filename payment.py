from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Payment:
    id: int
    loan_id: int
    amount_paid: Decimal
    paid_on: str

    @classmethod
    def from_row(cls, row) -> "Payment":
        from utils.money import to_decimal
        return cls(id=row["id"], loan_id=row["loan_id"],
                    amount_paid=to_decimal(row["amount_paid"]), paid_on=row["paid_on"])

    def to_dict(self) -> dict:
        return {"id": self.id, "loan_id": self.loan_id,
                "amount_paid": str(self.amount_paid), "paid_on": self.paid_on}
