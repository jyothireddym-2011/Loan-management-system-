from dataclasses import dataclass
from typing import Optional


@dataclass
class Document:
    id: int
    user_id: int
    borrower_id: Optional[int]
    loan_id: Optional[int]
    doc_type: Optional[str]
    original_filename: str
    stored_filename: str
    stored_path: str
    uploaded_at: str

    @classmethod
    def from_row(cls, row) -> "Document":
        return cls(
            id=row["id"], user_id=row["user_id"], borrower_id=row["borrower_id"],
            loan_id=row["loan_id"], doc_type=row["doc_type"],
            original_filename=row["original_filename"], stored_filename=row["stored_filename"],
            stored_path=row["stored_path"], uploaded_at=row["uploaded_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "borrower_id": self.borrower_id, "loan_id": self.loan_id,
            "doc_type": self.doc_type, "original_filename": self.original_filename,
            "uploaded_at": self.uploaded_at,
        }
