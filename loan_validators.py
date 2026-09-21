from validators.common_validators import validate_amount, validate_required_fields

REQUIRED_LOAN_FIELDS = ["lender_name", "nominee_signature", "lender_signature", "borrower_signature"]


def validate_loan_payload(data: dict) -> tuple[bool, str]:
    ok, msg = validate_required_fields(data, REQUIRED_LOAN_FIELDS)
    if not ok:
        return False, f"Loan agreement rejected. {msg}"

    ok, msg, _ = validate_amount(data.get("loan_amount"), field_name="Loan amount")
    if not ok:
        return False, msg

    return True, "OK"


def validate_payment_payload(data: dict) -> tuple[bool, str]:
    ok, msg, _ = validate_amount(data.get("amount_paid"), field_name="Payment amount")
    if not ok:
        return False, msg
    return True, "OK"
