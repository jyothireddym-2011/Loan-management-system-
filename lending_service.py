"""
Lending business logic — the "lending_backend" module folded into the
unified backend. Delegates risk scoring entirely to the standalone `ml`
package (see /ml/risk_model) instead of embedding a model inside the
service, per the requested "separate module for ml algorithm".
"""
from __future__ import annotations

import logging

from flask import current_app

from middleware.errors import ConflictError, NotFoundError, ValidationError
from repositories.audit_repository import AuditRepository
from repositories.lending_repository import LendingRepository
from security.encryption import AadhaarCipher, hash_aadhaar, mask_aadhaar
from security.password_utils import hash_password, verify_password
from utils.money import to_decimal, to_storage, InvalidAmountError
from validators.lending_validators import validate_lending_create_payload, validate_security_password

from ml.risk_model import RiskClassifier

logger = logging.getLogger("app.lending")

# Loaded once per process — training is fast (pure python, ~1200 samples)
# but there's no reason to redo it on every request.
_risk_classifier: RiskClassifier | None = None


def get_risk_classifier() -> RiskClassifier:
    global _risk_classifier
    if _risk_classifier is None:
        _risk_classifier = RiskClassifier.load_default()
    return _risk_classifier


def _cipher() -> AadhaarCipher:
    return AadhaarCipher(current_app.config["AADHAAR_ENCRYPTION_KEY"])


def _public_record(row) -> dict:
    return {
        "id": row["id"], "borrower_name": row["borrower_name"],
        "aadhaar_number": mask_aadhaar(_cipher().decrypt(row["aadhaar_encrypted"])),
        "phone_number": row["phone_number"], "lender_name": row["lender_name"],
        "amount": row["amount"], "update_count": row["update_count"],
        "risk_level": row["risk_level"], "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


class LendingService:
    def __init__(self, repo: LendingRepository = None, audit_repo: AuditRepository = None):
        self.repo = repo or LendingRepository()
        self.audit_repo = audit_repo or AuditRepository()

    def check_duplicate(self, aadhaar_number: str, new_amount) -> dict:
        if not aadhaar_number:
            return {"duplicate": False}
        aadhaar_hash = hash_aadhaar(aadhaar_number)
        existing = self.repo.find_by_hash(aadhaar_hash)
        if not existing:
            return {"duplicate": False}

        try:
            new_amount_dec = to_decimal(new_amount) if new_amount else to_decimal(0)
        except InvalidAmountError:
            new_amount_dec = to_decimal(0)

        existing_amount = to_decimal(existing["amount"])
        dual_amount = existing_amount + new_amount_dec
        risk = get_risk_classifier().predict(float(dual_amount), existing["update_count"])

        return {
            "duplicate": True,
            "existing_record": {
                "borrower_name": existing["borrower_name"], "lender_name": existing["lender_name"],
                "amount": str(existing_amount),
                "phone_number": existing["phone_number"],
                "created_at": existing["created_at"], "updated_at": existing["updated_at"],
            },
            "new_amount": str(new_amount_dec),
            "dual_amount": str(dual_amount),
            "risk": risk.to_dict(),
        }

    def create_record(self, data: dict) -> dict:
        ok, msg = validate_lending_create_payload(data)
        if not ok:
            raise ValidationError(msg)

        aadhaar_number = str(data["aadhaar_number"]).strip()
        amount = to_decimal(data["amount"])

        dup = self.check_duplicate(aadhaar_number, new_amount=data["amount"])
        if dup["duplicate"]:
            raise ConflictError(
                "A lending record already exists for this Aadhaar number.",
                payload={"duplicate": dup},
            )

        risk = get_risk_classifier().predict(float(amount), update_frequency=0)
        aadhaar_hash = hash_aadhaar(aadhaar_number)
        aadhaar_encrypted = _cipher().encrypt(aadhaar_number)

        try:
            record_id = self.repo.create(
                borrower_name=data["borrower_name"], aadhaar_encrypted=aadhaar_encrypted,
                aadhaar_hash=aadhaar_hash, phone_number=data.get("phone_number"),
                lender_name=data["lender_name"], amount=to_storage(amount),
                agreement_filename=data["agreement_filename"], photo_filename=data["photo_filename"],
                password_hash=hash_password(data["password"]), risk_level=risk.risk,
            )
        except ValueError:
            # Duplicate insert raced past the check above and was caught
            # by the repository's transactional re-check.
            raise ConflictError("A lending record already exists for this Aadhaar number.")

        self.audit_repo.log("lending_record_created", entity_type="lending_record", entity_id=record_id,
                             detail=f"risk={risk.risk}")
        logger.info("lending_record_created", extra={"record_id": record_id, "risk": risk.risk})

        return {"record_id": record_id, "risk": risk.to_dict()}

    def record_payment(self, data: dict) -> dict:
        ok, msg = validate_security_password(data.get("password"), data.get("confirm_password"))
        if not ok:
            raise ValidationError(msg)

        if not data.get("agreement_filename"):
            raise ValidationError("Loan agreement file is required to edit this record.")

        record = self.repo.find_by_hash(hash_aadhaar(data.get("aadhaar_number", "")))
        if not record:
            raise NotFoundError("No lending record found for this Aadhaar number.")

        if record["borrower_name"].strip().lower() != (data.get("borrower_name") or "").strip().lower():
            raise ValidationError("Borrower name does not match our record.")

        if not verify_password(data["password"], record["password_hash"]):
            raise ValidationError("Security password is incorrect.")

        try:
            paying_amount = to_decimal(data.get("paying_amount"))
        except InvalidAmountError as exc:
            raise ValidationError(str(exc).replace("Amount", "Paying amount"))

        old_amount = to_decimal(record["amount"])
        new_amount = old_amount - paying_amount
        if new_amount < 0:
            raise ValidationError(f"Paying amount exceeds the outstanding balance of {old_amount}.")

        new_update_count = record["update_count"] + 1
        risk = get_risk_classifier().predict(float(new_amount), new_update_count)

        self.repo.update_after_payment(
            record_id=record["id"], new_amount=to_storage(new_amount), new_update_count=new_update_count,
            risk_level=risk.risk, agreement_filename=data["agreement_filename"],
            old_amount=to_storage(old_amount), paying_amount=to_storage(paying_amount),
        )
        self.audit_repo.log("lending_payment_recorded", entity_type="lending_record", entity_id=record["id"],
                             detail=f"paying_amount={paying_amount} risk={risk.risk}")
        logger.info("lending_payment_recorded", extra={"record_id": record["id"], "risk": risk.risk})

        return {
            "borrower_name": record["borrower_name"], "lender_name": record["lender_name"],
            "phone_number": record["phone_number"], "old_amount": str(old_amount),
            "paying_amount": str(paying_amount), "new_amount": str(new_amount),
            "agreement_filename": data["agreement_filename"], "update_count": new_update_count,
            "risk": risk.to_dict(),
        }

    def remove_record(self, data: dict) -> dict:
        ok, msg = validate_security_password(data.get("password"), data.get("confirm_password"))
        if not ok:
            raise ValidationError(msg)

        record = self.repo.find_by_hash(hash_aadhaar(data.get("aadhaar_number", "")))
        if not record:
            raise NotFoundError("No lending record found for this Aadhaar number.")

        if record["borrower_name"].strip().lower() != (data.get("borrower_name") or "").strip().lower():
            raise ValidationError("Borrower name does not match our record.")

        if not verify_password(data["password"], record["password_hash"]):
            raise ValidationError("Security password is incorrect.")

        self.repo.delete(record["id"], amount=record["amount"], risk_level=record["risk_level"])
        self.audit_repo.log("lending_record_removed", entity_type="lending_record", entity_id=record["id"])
        logger.info("lending_record_removed", extra={"record_id": record["id"]})

        return {"message": f"Lending record for {record['borrower_name']} has been removed."}

    def find_by_aadhaar(self, aadhaar_number: str):
        row = self.repo.find_by_hash(hash_aadhaar(aadhaar_number))
        if not row:
            raise NotFoundError("Not found")
        return _public_record(row)
