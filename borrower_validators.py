from validators.common_validators import validate_aadhaar, validate_phone


def validate_borrower_payload(data: dict) -> tuple[bool, str]:
    if not data.get("name") or not str(data.get("name")).strip():
        return False, "Borrower name is required."

    ok, msg = validate_aadhaar(data.get("aadhaar_number"))
    if not ok:
        return False, f"Aadhaar validation failed: {msg}"

    ok, msg = validate_phone(data.get("phone", ""), required=False)
    if not ok:
        return False, msg

    return True, "OK"
