"""
Password hashing (accounts + lending-record security passwords).
PBKDF2-SHA256 via Werkzeug — one-way, salted, never reversible.
Stronger policy per review recommendation ("Stronger password policies").
"""
from __future__ import annotations

import re
from werkzeug.security import generate_password_hash, check_password_hash

MIN_PASSWORD_LENGTH = 10
_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_SPECIAL = re.compile(r"[^A-Za-z0-9]")

COMMON_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "qwerty123",
    "letmein1", "admin123", "welcome1", "iloveyou", "password123",
}


def validate_password_strength(password: str) -> tuple[bool, str]:
    if not password:
        return False, "Password is required."
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
    if not _UPPER.search(password):
        return False, "Password must contain at least one uppercase letter."
    if not _LOWER.search(password):
        return False, "Password must contain at least one lowercase letter."
    if not _DIGIT.search(password):
        return False, "Password must contain at least one digit."
    if not _SPECIAL.search(password):
        return False, "Password must contain at least one special character."
    if password.lower() in COMMON_PASSWORDS:
        return False, "This password is too common. Choose something less guessable."
    return True, "OK"


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return check_password_hash(password_hash, password)
