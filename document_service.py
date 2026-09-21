"""
Document business logic: safe upload (extension + MIME allow-list, size
limit, path-traversal-proof storage), ownership-scoped download, delete,
and template download.
Review recommendations addressed: "MIME validation", "Upload size limits",
"Audit logs".
"""
from __future__ import annotations

import logging
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

from middleware.errors import NotFoundError, ValidationError
from repositories.audit_repository import AuditRepository
from repositories.document_repository import DocumentRepository

logger = logging.getLogger("app.documents")

try:
    import magic  # python-magic; optional — see _sniff_mime below
    _HAS_MAGIC = True
except ImportError:
    _HAS_MAGIC = False


def _allowed_extension(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"]


def _sniff_mime(file_storage) -> str | None:
    """
    Best-effort MIME sniff from file content (not just the extension/
    Content-Type header, which are trivially spoofable). Falls back to
    skipping the check (with a warning) if python-magic / libmagic isn't
    installed on this host, rather than hard-failing every upload.
    """
    if not _HAS_MAGIC:
        logger.warning("mime_sniff_skipped_no_libmagic")
        return None
    file_storage.stream.seek(0)
    head = file_storage.stream.read(2048)
    file_storage.stream.seek(0)
    try:
        return magic.from_buffer(head, mime=True)
    except Exception:
        logger.warning("mime_sniff_failed")
        return None


class DocumentService:
    def __init__(self, repo: DocumentRepository = None, audit_repo: AuditRepository = None):
        self.repo = repo or DocumentRepository()
        self.audit_repo = audit_repo or AuditRepository()

    def upload(self, user_id: int, file_storage, doc_type: str, borrower_id, loan_id) -> dict:
        if file_storage is None or file_storage.filename == "":
            raise ValidationError("No file provided.")

        original_filename = secure_filename(file_storage.filename)
        if not original_filename:
            raise ValidationError("Invalid filename.")

        if not _allowed_extension(original_filename):
            allowed = ", ".join(sorted(current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"]))
            raise ValidationError(f"File type not allowed. Allowed types: {allowed}.")

        mime = _sniff_mime(file_storage)
        if mime and mime not in current_app.config["ALLOWED_DOCUMENT_MIME_TYPES"]:
            raise ValidationError(f"File content does not match an allowed document type (detected: {mime}).")

        file_storage.stream.seek(0, os.SEEK_END)
        size_bytes = file_storage.stream.tell()
        file_storage.stream.seek(0)
        max_bytes = current_app.config["MAX_DOCUMENT_SIZE_MB"] * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValidationError(f"File exceeds maximum size of {current_app.config['MAX_DOCUMENT_SIZE_MB']} MB.")

        storage_dir = current_app.config["DOCUMENTS_STORAGE_DIR"]
        os.makedirs(storage_dir, exist_ok=True)

        ext = original_filename.rsplit(".", 1)[1].lower()
        stored_filename = f"{uuid.uuid4().hex}.{ext}"
        stored_path = os.path.join(storage_dir, stored_filename)

        # Defense in depth: confirm the resolved path is still inside storage_dir.
        storage_root = os.path.realpath(storage_dir)
        resolved = os.path.realpath(stored_path)
        if not resolved.startswith(storage_root + os.sep):
            raise ValidationError("Invalid storage path.")

        file_storage.save(stored_path)

        doc_id = self.repo.create(
            user_id=user_id, borrower_id=borrower_id, loan_id=loan_id, doc_type=doc_type,
            original_filename=original_filename, stored_filename=stored_filename, stored_path=stored_path,
        )
        self.audit_repo.log("document_uploaded", user_id=user_id, entity_type="document", entity_id=doc_id,
                             detail=f"filename={original_filename} size={size_bytes}")
        logger.info("document_uploaded", extra={"user_id": user_id, "document_id": doc_id, "size_bytes": size_bytes})

        return {
            "id": doc_id, "original_filename": original_filename, "doc_type": doc_type,
            "borrower_id": borrower_id, "loan_id": loan_id, "size_bytes": size_bytes,
        }

    def get_for_download(self, doc_id: int, user_id: int):
        row = self.repo.find_by_id(doc_id, user_id)
        if not row:
            raise NotFoundError("Document not found.")
        self.audit_repo.log("document_downloaded", user_id=user_id, entity_type="document", entity_id=doc_id)
        return row

    def list_documents(self, user_id: int, borrower_id=None, loan_id=None,
                        pagination: dict | None = None) -> tuple[list[dict], int]:
        total = self.repo.count_for_user(user_id, borrower_id=borrower_id, loan_id=loan_id)

        if pagination is None:
            rows = self.repo.list_for_user(user_id, borrower_id=borrower_id, loan_id=loan_id)
        else:
            rows = self.repo.list_for_user(
                user_id, borrower_id=borrower_id, loan_id=loan_id,
                sort_by=pagination["sort_by"], sort_dir=pagination["sort_dir"],
                limit=pagination["page_size"], offset=pagination["offset"],
            )
        items = [
            {"id": r["id"], "borrower_id": r["borrower_id"], "loan_id": r["loan_id"],
             "doc_type": r["doc_type"], "original_filename": r["original_filename"],
             "uploaded_at": r["uploaded_at"]}
            for r in rows
        ]
        return items, total

    def delete(self, doc_id: int, user_id: int) -> None:
        row = self.repo.find_by_id(doc_id, user_id)
        if not row:
            raise NotFoundError("Document not found.")
        try:
            if os.path.exists(row["stored_path"]):
                os.remove(row["stored_path"])
        except OSError as exc:
            raise ValidationError(f"Could not delete file from storage: {exc}")

        self.repo.delete(doc_id, user_id)
        self.audit_repo.log("document_deleted", user_id=user_id, entity_type="document", entity_id=doc_id)
        logger.info("document_deleted", extra={"user_id": user_id, "document_id": doc_id})

    def get_agreement_template_path(self) -> str:
        path = current_app.config["DOCUMENT_TEMPLATE_PATH"]
        if not os.path.exists(path):
            raise NotFoundError("Template not found on server.")
        return path
