"""
Borrower routes.
POST /borrowers
GET  /borrowers/<id>
GET  /borrowers/search
"""
from flask import Blueprint, jsonify, request

from middleware.auth import require_auth
from services.borrower_service import BorrowerService
from utils.pagination import paginated_response, parse_pagination

borrowers_bp = Blueprint("borrowers", __name__, url_prefix="/borrowers")

_BORROWER_SORT_FIELDS = {"created_at", "name", "id"}


@borrowers_bp.route("", methods=["POST"])
@require_auth
def create_borrower(current_user):
    data = request.get_json(force=True, silent=True) or {}
    borrower = BorrowerService().create_borrower(current_user["id"], data)
    return jsonify({"success": True, "borrower": borrower}), 201


@borrowers_bp.route("/search", methods=["GET"])
@require_auth
def search_borrowers(current_user):
    name = request.args.get("name")
    aadhaar_number = request.args.get("aadhaar_number")
    pagination = parse_pagination(request.args, default_sort="created_at", allowed_sort_fields=_BORROWER_SORT_FIELDS)
    results, total = BorrowerService().search(
        current_user["id"], name=name, aadhaar_number=aadhaar_number, pagination=pagination,
    )
    body = paginated_response(results, total, pagination["page"], pagination["page_size"])
    return jsonify({"success": True, "count": len(results), "borrowers": results, **body})


@borrowers_bp.route("/<int:borrower_id>", methods=["GET"])
@require_auth
def get_borrower(current_user, borrower_id):
    borrower = BorrowerService().get_borrower(borrower_id, current_user["id"])
    return jsonify({"success": True, "borrower": borrower})
