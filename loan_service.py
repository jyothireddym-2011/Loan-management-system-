"""
Loan business logic. Amounts are Decimal end-to-end; payments are recorded
inside a single DB transaction to avoid the two-concurrent-payments race
(review recommendations: "Replace float with Decimal", "Prevent race
conditions", "Transaction boundaries", "Payment auditing").
"""
from __future__ import annotations

import logging

from middleware.errors import NotFoundError, ValidationError
from repositories.audit_repository import AuditRepository
from repositories.loan_repository import LoanRepository
from services.borrower_service import BorrowerService
from utils.money import to_decimal, to_storage, InvalidAmountError
from validators.loan_validators import validate_loan_payload, validate_payment_payload

logger = logging.getLogger("app.loans")


class LoanService:
    def __init__(self, repo: LoanRepository = None, borrower_service: BorrowerService = None,
                 audit_repo: AuditRepository = None):
        self.repo = repo or LoanRepository()
        self.borrower_service = borrower_service or BorrowerService()
        self.audit_repo = audit_repo or AuditRepository()

    def create_loan(self, user_id: int, data: dict) -> dict:
        ok, msg = validate_loan_payload(data)
        if not ok:
            raise ValidationError(msg)

        borrower_row = self.borrower_service.get_borrower_row_for_loan(data.get("borrower_id"), user_id)

        loan_amount = to_decimal(data["loan_amount"])

        loan_id = self.repo.create(
            user_id=user_id, borrower_id=borrower_row["id"], borrower_name=borrower_row["name"],
            lender_name=data["lender_name"], loan_amount=to_storage(loan_amount),
            nominee_name=data.get("nominee_name", ""), nominee_signature=data["nominee_signature"],
            lender_signature=data["lender_signature"], borrower_signature=data["borrower_signature"],
        )
        self.audit_repo.log("loan_created", user_id=user_id, entity_type="loan", entity_id=loan_id,
                             detail=f"amount={loan_amount}")
        logger.info("loan_created", extra={"user_id": user_id, "loan_id": loan_id})

        return self.get_loan(loan_id, user_id)

    def get_loan(self, loan_id: int, user_id: int | None = None) -> dict:
        row = self.repo.find_by_id(loan_id, user_id)
        if not row:
            raise NotFoundError("Loan not found.")
        return _loan_dict(row)

    def get_loans_for_borrower(self, borrower_id: int, user_id: int,
                                pagination: dict | None = None) -> tuple[list[dict], int]:
        total = self.repo.count_for_borrower(borrower_id, user_id)
        if pagination is None:
            rows = self.repo.find_for_borrower(borrower_id, user_id)
            return [_loan_dict(r) for r in rows], total
        rows = self.repo.find_for_borrower(
            borrower_id, user_id, sort_by=pagination["sort_by"], sort_dir=pagination["sort_dir"],
            limit=pagination["page_size"], offset=pagination["offset"],
        )
        return [_loan_dict(r) for r in rows], total

    def record_payment(self, loan_id: int, user_id: int, data: dict) -> dict:
        ok, msg = validate_payment_payload(data)
        if not ok:
            raise ValidationError(msg)

        loan_row = self.repo.find_by_id(loan_id, user_id)
        if not loan_row:
            raise NotFoundError("Loan not found.")

        try:
            amount_paid = to_decimal(data["amount_paid"])
        except InvalidAmountError as exc:
            raise ValidationError(str(exc))

        remaining = to_decimal(loan_row["remaining_amount"])
        if amount_paid > remaining:
            raise ValidationError(f"Payment of {amount_paid} exceeds remaining amount of {remaining}.")

        new_paid = to_decimal(loan_row["paid_amount"]) + amount_paid
        new_remaining = to_decimal(loan_row["loan_amount"]) - new_paid

        self.repo.record_payment_atomically(
            loan_id, to_storage(amount_paid), to_storage(new_paid), to_storage(new_remaining),
        )
        self.audit_repo.log("payment_recorded", user_id=user_id, entity_type="loan", entity_id=loan_id,
                             detail=f"amount_paid={amount_paid}")
        logger.info("payment_recorded", extra={"user_id": user_id, "loan_id": loan_id, "amount": str(amount_paid)})

        return self.get_loan(loan_id, user_id)

    def get_payment_history(self, loan_id: int, pagination: dict | None = None) -> tuple[list[dict], int]:
        total = self.repo.count_payments(loan_id)
        if pagination is None:
            rows = self.repo.payment_history(loan_id)
        else:
            rows = self.repo.payment_history(
                loan_id, sort_dir=pagination["sort_dir"],
                limit=pagination["page_size"], offset=pagination["offset"],
            )
        items = [{"id": r["id"], "amount_paid": r["amount_paid"], "paid_on": r["paid_on"]} for r in rows]
        return items, total


def _loan_dict(row) -> dict:
    return {
        "id": row["id"], "borrower_id": row["borrower_id"], "borrower_name": row["borrower_name"],
        "lender_name": row["lender_name"], "loan_amount": row["loan_amount"],
        "paid_amount": row["paid_amount"], "remaining_amount": row["remaining_amount"],
        "nominee_name": row["nominee_name"], "created_at": row["created_at"],
    }
