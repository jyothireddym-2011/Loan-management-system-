from validators.common_validators import validate_email, validate_phone
from security.password_utils import validate_password_strength


def validate_registration(data: dict) -> tuple[bool, str]:
    if not data.get("name") or not str(data.get("name")).strip():
        return False, "Name is required."

    ok, msg = validate_email(data.get("email"))
    if not ok:
        return False, msg

    ok, msg = validate_phone(data.get("phone", ""), required=False)
    if not ok:
        return False, msg

    if data.get("password") != data.get("confirm_password"):
        return False, "Password and confirm password do not match."

    ok, msg = validate_password_strength(data.get("password"))
    if not ok:
        return False, msg

    return True, "OK"


def validate_login(data: dict) -> tuple[bool, str]:
    if not data.get("email") or not data.get("password"):
        return False, "Email and password are required."
    return True, "OK"
