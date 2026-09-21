"""
Borrower business logic. Aadhaar is validated, then only ever stored as
(encrypted, hashed) — the plaintext number never touches the database
(review recommendations: "Aadhaar encryption/masking",
"Use Aadhaar as primary uniqueness key").
"""
from __future__ import annotations

import logging

from flask import current_app

from middleware.errors import ConflictError, NotFoundError, ValidationError
from repositories.borrower_repository import BorrowerRepository
from security.encryption import AadhaarCipher, hash_aadhaar, mask_aadhaar
from validators.borrower_validators import validate_borrower_payload
from validators.common_validators import validate_aadhaar

logger = logging.getLogger("app.borrowers")


def _cipher() -> AadhaarCipher:
    return AadhaarCipher(current_app.config["AADHAAR_ENCRYPTION_KEY"])


def _borrower_public_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "aadhaar_number": mask_aadhaar(_cipher().decrypt(row["aadhaar_encrypted"])),
        "phone": row["phone"],
        "address": row["address"],
        "created_at": row["created_at"],
    }


class BorrowerService:
    def __init__(self, repo: BorrowerRepository = None):
        self.repo = repo or BorrowerRepository()

    def create_borrower(self, user_id: int, data: dict) -> dict:
        ok, msg = validate_borrower_payload(data)
        if not ok:
            raise ValidationError(msg)

        aadhaar_number = str(data["aadhaar_number"]).strip()
        aadhaar_hash = hash_aadhaar(aadhaar_number)

        # Aadhaar is the primary uniqueness key, per review recommendation —
        # duplicate check is by hash, not by name.
        existing = self.repo.find_by_hash(user_id, aadhaar_hash)
        if existing:
            raise ConflictError(
                "Borrower already exists.",
                payload={"existing_borrower": _borrower_public_dict(existing)},
            )

        aadhaar_encrypted = _cipher().encrypt(aadhaar_number)
        borrower_id = self.repo.create(
            user_id=user_id, name=data["name"], aadhaar_encrypted=aadhaar_encrypted,
            aadhaar_hash=aadhaar_hash, phone=data.get("phone", ""), address=data.get("address", ""),
        )
        logger.info("borrower_created", extra={"user_id": user_id, "borrower_id": borrower_id})

        row = self.repo.find_by_id(borrower_id, user_id)
        return _borrower_public_dict(row)

    def get_borrower(self, borrower_id: int, user_id: int) -> dict:
        row = self.repo.find_by_id(borrower_id, user_id)
        if not row:
            raise NotFoundError("Borrower not found.")
        return _borrower_public_dict(row)

    def search(self, user_id: int, name: str | None, aadhaar_number: str | None,
               pagination: dict | None = None) -> tuple[list[dict], int]:
        aadhaar_hash = None
        if aadhaar_number:
            ok, _ = validate_aadhaar(aadhaar_number)
            if ok:
                aadhaar_hash = hash_aadhaar(aadhaar_number)

        total = self.repo.count_search(user_id, name=name, aadhaar_hash=aadhaar_hash)

        if pagination is None:
            rows = self.repo.search(user_id, name=name, aadhaar_hash=aadhaar_hash)
            return [_borrower_public_dict(r) for r in rows], total

        rows = self.repo.search(
            user_id, name=name, aadhaar_hash=aadhaar_hash,
            sort_by=pagination["sort_by"], sort_dir=pagination["sort_dir"],
            limit=pagination["page_size"], offset=pagination["offset"],
        )
        return [_borrower_public_dict(r) for r in rows], total

    def get_borrower_row_for_loan(self, borrower_id: int, user_id: int):
        """Internal use by LoanService — returns the raw row (loan_service needs borrower['name'])."""
        row = self.repo.find_by_id(borrower_id, user_id)
        if not row:
            raise NotFoundError("Borrower not found. Register the borrower first (with valid Aadhaar).")
        return row
