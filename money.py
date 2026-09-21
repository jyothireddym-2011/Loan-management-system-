"""
money.py
--------
Decimal-everywhere helpers for monetary values (production-roadmap item:
"Use Decimal instead of float for monetary calculations").

SQLite has no native DECIMAL type, so amounts are persisted as TEXT
(exact string round-trip) and converted to Decimal on the way out. This
avoids the classic `0.1 + 0.2 != 0.3` float-drift bug that floats stored
as REAL would reintroduce.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

TWO_PLACES = Decimal("0.01")


class InvalidAmountError(ValueError):
    pass


def to_decimal(value) -> Decimal:
    """Parses a request value (str/int/float/Decimal/None) into a Decimal,
    rounded to 2 decimal places (paise). Raises InvalidAmountError on bad input."""
    if value is None or value == "":
        raise InvalidAmountError("Amount is required.")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise InvalidAmountError("Amount must be a valid number.")
    return d.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_storage(value: Decimal) -> str:
    """Decimal -> TEXT for SQLite storage (exact, no float roundtrip)."""
    return str(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))
