from validators.common_validators import validate_aadhaar, validate_amount
from security.password_utils import MIN_PASSWORD_LENGTH


def validate_security_password(password: str, confirm_password: str) -> tuple[bool, str]:
    if not password or not confirm_password:
        return False, "Security password and confirm password are both required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if password != confirm_password:
        return False, "Security password and confirm password do not match."
    return True, "OK"


def validate_lending_create_payload(data: dict) -> tuple[bool, str]:
    ok, msg = validate_security_password(data.get("password"), data.get("confirm_password"))
    if not ok:
        return False, msg

    ok, msg = validate_aadhaar(data.get("aadhaar_number"))
    if not ok:
        return False, msg

    if not data.get("borrower_name") or not str(data.get("borrower_name")).strip():
        return False, "Borrower name is required."
    if not data.get("lender_name") or not str(data.get("lender_name")).strip():
        return False, "Lender name is required."

    ok, msg, _ = validate_amount(data.get("amount"))
    if not ok:
        return False, msg

    if not data.get("agreement_filename"):
        return False, "Loan agreement file is required."
    if not data.get("photo_filename"):
        return False, "Borrower photo is required."

    return True, "OK"
