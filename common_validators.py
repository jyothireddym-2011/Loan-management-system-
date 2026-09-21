"""Validators shared across every module's routes."""
import re
from decimal import Decimal

from utils.money import to_decimal, InvalidAmountError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^\d{10}$")
AADHAAR_PATTERN = re.compile(r"^\d{12}$")


def validate_email(email: str) -> tuple[bool, str]:
    if not email or not email.strip():
        return False, "Email is required."
    if not EMAIL_PATTERN.match(email.strip()):
        return False, "Email format is invalid."
    return True, "OK"


def validate_phone(phone: str, required: bool = False) -> tuple[bool, str]:
    if not phone:
        return (False, "Phone number is required.") if required else (True, "OK")
    if not PHONE_PATTERN.match(str(phone).strip()):
        return False, "Phone number must be exactly 10 digits."
    return True, "OK"


def validate_aadhaar(aadhaar_number: str) -> tuple[bool, str]:
    if aadhaar_number is None:
        return False, "Aadhaar number is required."
    normalized = str(aadhaar_number).strip()
    if normalized == "":
        return False, "Aadhaar number is required."
    if not normalized.isdigit():
        return False, "Aadhaar number must contain digits only (no alphabets or symbols)."
    if len(normalized) != 12:
        return False, f"Aadhaar number must be exactly 12 digits (got {len(normalized)})."
    return True, "OK"


def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, str]:
    missing = [f for f in required_fields if data.get(f) in (None, "", [])]
    if missing:
        return False, f"Missing required field(s): {', '.join(missing)}."
    return True, "OK"


def validate_amount(value, field_name: str = "Amount") -> tuple[bool, str, Decimal | None]:
    try:
        amount = to_decimal(value)
    except InvalidAmountError as exc:
        return False, str(exc).replace("Amount", field_name), None
    if amount <= 0:
        return False, f"{field_name} must be greater than zero.", None
    return True, "OK", amount
