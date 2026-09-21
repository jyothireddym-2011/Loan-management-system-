"""
Loan routes.
POST /loans
GET  /loans/<id>
GET  /borrowers/<id>/loans
POST /loans/<id>/payments
GET  /loans/<id>/payments
"""
from flask import Blueprint, jsonify, request

from middleware.auth import require_auth
from services.loan_service import LoanService
from utils.pagination import paginated_response, parse_pagination

loans_bp = Blueprint("loans", __name__)

_LOAN_SORT_FIELDS = {"created_at", "id", "loan_amount"}
_PAYMENT_SORT_FIELDS = {"paid_on", "id"}


@loans_bp.route("/loans", methods=["POST"])
@require_auth
def create_loan(current_user):
    data = request.get_json(force=True, silent=True) or {}
    loan = LoanService().create_loan(current_user["id"], data)
    return jsonify({"success": True, "loan": loan}), 201


@loans_bp.route("/loans/<int:loan_id>", methods=["GET"])
@require_auth
def get_loan(current_user, loan_id):
    loan = LoanService().get_loan(loan_id, current_user["id"])
    return jsonify({"success": True, "loan": loan})


@loans_bp.route("/borrowers/<int:borrower_id>/loans", methods=["GET"])
@require_auth
def get_borrower_loans(current_user, borrower_id):
    pagination = parse_pagination(request.args, default_sort="created_at", allowed_sort_fields=_LOAN_SORT_FIELDS)
    loans, total = LoanService().get_loans_for_borrower(borrower_id, current_user["id"], pagination=pagination)
    body = paginated_response(loans, total, pagination["page"], pagination["page_size"])
    return jsonify({"success": True, "count": len(loans), "loans": loans, **body})


@loans_bp.route("/loans/<int:loan_id>/payments", methods=["POST"])
@require_auth
def add_payment(current_user, loan_id):
    data = request.get_json(force=True, silent=True) or {}
    loan = LoanService().record_payment(loan_id, current_user["id"], data)
    return jsonify({"success": True, "loan": loan}), 201


@loans_bp.route("/loans/<int:loan_id>/payments", methods=["GET"])
@require_auth
def list_payments(current_user, loan_id):
    service = LoanService()
    loan = service.get_loan(loan_id, current_user["id"])
    pagination = parse_pagination(
        request.args, default_sort="paid_on", allowed_sort_fields=_PAYMENT_SORT_FIELDS, default_sort_dir="ASC",
    )
    history, total = service.get_payment_history(loan_id, pagination=pagination)
    body = paginated_response(history, total, pagination["page"], pagination["page_size"])
    return jsonify({
        "success": True, "loan_amount": loan["loan_amount"], "paid_amount": loan["paid_amount"],
        "remaining_amount": loan["remaining_amount"], "payments": history, **body,
    })
