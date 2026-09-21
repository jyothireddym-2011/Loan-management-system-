"""
Shared pagination/sorting helpers for list endpoints.

Keeps the "parse + validate query params" concern out of routes (which
should stay HTTP-only) and out of services (which shouldn't know about
Flask's `request` object), by taking a plain dict of query args in and
handing back clean, bounds-checked values.
"""
from __future__ import annotations

from middleware.errors import ValidationError

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def parse_pagination(args, default_sort: str, allowed_sort_fields: set[str], default_sort_dir: str = "DESC") -> dict:
    """
    args: a Flask `request.args`-like mapping (MultiDict or plain dict).
    Returns: {"page": int, "page_size": int, "offset": int, "sort_by": str, "sort_dir": "ASC"|"DESC"}
    Raises ValidationError on out-of-range or unknown values so callers get
    a consistent 400 response instead of a silent fallback.
    """
    try:
        page = int(args.get("page", 1))
    except (TypeError, ValueError):
        raise ValidationError("`page` must be an integer.")
    if page < 1:
        raise ValidationError("`page` must be >= 1.")

    try:
        page_size = int(args.get("page_size", DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        raise ValidationError("`page_size` must be an integer.")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ValidationError(f"`page_size` must be between 1 and {MAX_PAGE_SIZE}.")

    sort_by = args.get("sort_by", default_sort) or default_sort
    if sort_by not in allowed_sort_fields:
        raise ValidationError(f"`sort_by` must be one of: {', '.join(sorted(allowed_sort_fields))}.")

    sort_dir = (args.get("sort_dir", default_sort_dir) or default_sort_dir).upper()
    if sort_dir not in ("ASC", "DESC"):
        raise ValidationError("`sort_dir` must be `ASC` or `DESC`.")

    return {
        "page": page,
        "page_size": page_size,
        "offset": (page - 1) * page_size,
        "sort_by": sort_by,
        "sort_dir": sort_dir,
    }


def paginated_response(items: list, total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }
