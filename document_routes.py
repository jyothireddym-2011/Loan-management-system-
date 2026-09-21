"""
Document routes.
POST   /documents/upload
GET    /documents/template/download
GET    /documents
GET    /documents/<id>/download
DELETE /documents/<id>
"""
from flask import Blueprint, jsonify, request, send_file

from middleware.auth import require_auth
from services.document_service import DocumentService
from utils.pagination import paginated_response, parse_pagination

documents_bp = Blueprint("documents", __name__, url_prefix="/documents")

_DOCUMENT_SORT_FIELDS = {"uploaded_at", "id", "doc_type"}


@documents_bp.route("/upload", methods=["POST"])
@require_auth
def upload(current_user):
    file_storage = request.files.get("document")
    doc_type = request.form.get("doc_type", "")
    borrower_id = request.form.get("borrower_id", type=int)
    loan_id = request.form.get("loan_id", type=int)

    document = DocumentService().upload(
        user_id=current_user["id"], file_storage=file_storage, doc_type=doc_type,
        borrower_id=borrower_id, loan_id=loan_id,
    )
    return jsonify({"success": True, "document": document}), 201


@documents_bp.route("/template/download", methods=["GET"])
def download_template():
    path = DocumentService().get_agreement_template_path()
    return send_file(path, as_attachment=True, download_name="loan_agreement_template.txt", mimetype="text/plain")


@documents_bp.route("", methods=["GET"])
@require_auth
def list_my_documents(current_user):
    borrower_id = request.args.get("borrower_id", type=int)
    loan_id = request.args.get("loan_id", type=int)
    pagination = parse_pagination(request.args, default_sort="uploaded_at", allowed_sort_fields=_DOCUMENT_SORT_FIELDS)
    docs, total = DocumentService().list_documents(
        current_user["id"], borrower_id=borrower_id, loan_id=loan_id, pagination=pagination,
    )
    body = paginated_response(docs, total, pagination["page"], pagination["page_size"])
    return jsonify({"success": True, "count": len(docs), "documents": docs, **body})


@documents_bp.route("/<int:doc_id>/download", methods=["GET"])
@require_auth
def download_document(current_user, doc_id):
    doc = DocumentService().get_for_download(doc_id, current_user["id"])
    return send_file(doc["stored_path"], as_attachment=True, download_name=doc["original_filename"])


@documents_bp.route("/<int:doc_id>", methods=["DELETE"])
@require_auth
def remove_document(current_user, doc_id):
    DocumentService().delete(doc_id, current_user["id"])
    return jsonify({"success": True, "message": "Document deleted."})
