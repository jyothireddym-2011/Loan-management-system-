"""
Field-level encryption for Aadhaar numbers (production-roadmap item:
"Encrypt or mask Aadhaar values").

Two representations are stored for every Aadhaar number:
  - aadhaar_encrypted: Fernet ciphertext (AES-128-CBC + HMAC), reversible
    only with AADHAAR_ENCRYPTION_KEY, for authorized display/download.
  - aadhaar_hash: SHA-256 of the normalized (digits-only) number. Fernet
    ciphertext is non-deterministic (random nonce per encryption), so it
    can't be used for uniqueness lookups — the hash is the actual
    duplicate-detection / WHERE-clause key.

Masking (mask_aadhaar) is used anywhere the number is merely displayed —
API responses never need to show more than the last 4 digits.
"""
from __future__ import annotations

import hashlib

from cryptography.fernet import Fernet, InvalidToken


class AadhaarCipher:
    def __init__(self, key: str):
        if not key:
            raise ValueError("AADHAAR_ENCRYPTION_KEY is not configured.")
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, aadhaar_number: str) -> str:
        normalized = normalize_aadhaar(aadhaar_number)
        return self._fernet.encrypt(normalized.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Could not decrypt Aadhaar value (bad key or corrupted data).") from exc


def normalize_aadhaar(aadhaar_number: str) -> str:
    return "".join(ch for ch in str(aadhaar_number) if ch.isdigit())


def hash_aadhaar(aadhaar_number: str) -> str:
    normalized = normalize_aadhaar(aadhaar_number)
    return hashlib.sha256(normalized.encode()).hexdigest()


def mask_aadhaar(aadhaar_number: str) -> str:
    """e.g. '999988887777' -> 'XXXX-XXXX-7777'"""
    normalized = normalize_aadhaar(aadhaar_number)
    if len(normalized) < 4:
        return "XXXX-XXXX-XXXX"
    last4 = normalized[-4:]
    return f"XXXX-XXXX-{last4}"
