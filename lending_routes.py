"""
Lending routes (folded in from the standalone lending_backend module).
GET  /api/lending/check-duplicate
POST /api/lending/create
POST /api/lending/pay
POST /api/lending/remove
GET  /api/lending/<aadhaar_number>

SECURITY FIX (this refactor): every route below previously had NO platform
authentication at all — only the per-record "security password" gated
pay/remove, and the GET-by-Aadhaar and check-duplicate endpoints had no
gate whatsoever. That meant anyone who knew or guessed a valid Aadhaar
number could pull a borrower's name, phone number, and loan amount with
a single unauthenticated GET request — a PII exposure (IDOR) bug, and
inconsistent with every other domain in this codebase (borrowers, loans,
documents), which all require a logged-in user. `require_auth` has been
added to all five endpoints. The record-level password check inside the
service (pay/remove) is preserved as a second factor on top of platform
auth, not a replacement for it. If a public, no-login kiosk flow was
actually intended here, treat this as a flagged design decision to
revisit rather than a silent behavior change.
"""
from flask import Blueprint, jsonify, request

from middleware.auth import require_auth
from middleware.rate_limit import rate_limited
from services.lending_service import LendingService

lending_bp = Blueprint("lending", __name__, url_prefix="/api/lending")


@lending_bp.route("/check-duplicate", methods=["GET"])
@require_auth
def api_check_duplicate(current_user):
    aadhaar_number = request.args.get("aadhaar_number", "")
    new_amount = request.args.get("new_amount", 0)
    result = LendingService().check_duplicate(aadhaar_number, new_amount=new_amount)
    return jsonify({"success": True, **result})


@lending_bp.route("/create", methods=["POST"])
@require_auth
@rate_limited("lending_create", max_requests=20, window_seconds=60)
def api_create(current_user):
    data = request.get_json(force=True, silent=True) or {}
    result = LendingService().create_record(data)
    return jsonify({"success": True, **result}), 201


@lending_bp.route("/pay", methods=["POST"])
@require_auth
@rate_limited("lending_pay", max_requests=20, window_seconds=60)
def api_pay(current_user):
    data = request.get_json(force=True, silent=True) or {}
    result = LendingService().record_payment(data)
    return jsonify({"success": True, **result})


@lending_bp.route("/remove", methods=["POST"])
@require_auth
@rate_limited("lending_remove", max_requests=20, window_seconds=60)
def api_remove(current_user):
    data = request.get_json(force=True, silent=True) or {}
    result = LendingService().remove_record(data)
    return jsonify({"success": True, **result})


@lending_bp.route("/<aadhaar_number>", methods=["GET"])
@require_auth
def api_get_record(current_user, aadhaar_number):
    record = LendingService().find_by_aadhaar(aadhaar_number)
    return jsonify({"success": True, "record": record})
