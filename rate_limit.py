"""
Minimal in-process rate limiter (sliding window, per-IP + per-route-key).
No Redis dependency, so it only protects a single process — fine for the
current single-instance deployment, and documented as a Phase-2 upgrade
target (swap the in-memory dict for Redis once running >1 instance).
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request

from middleware.errors import AppError

_lock = threading.Lock()
_hits: dict[str, deque] = defaultdict(deque)


class RateLimitExceeded(AppError):
    status_code = 429


def rate_limited(bucket: str, max_requests: int, window_seconds: int):
    """
    Usage:
        @rate_limited("login", max_requests=10, window_seconds=60)
        def login(): ...
    """
    def decorator(route_function):
        @wraps(route_function)
        def wrapper(*args, **kwargs):
            if not current_app.config.get("RATE_LIMIT_ENABLED", True):
                return route_function(*args, **kwargs)

            key = f"{bucket}:{request.headers.get('X-Forwarded-For', request.remote_addr)}"
            now = time.monotonic()
            with _lock:
                window = _hits[key]
                while window and now - window[0] > window_seconds:
                    window.popleft()
                if len(window) >= max_requests:
                    raise RateLimitExceeded(
                        "Too many requests. Please slow down and try again shortly."
                    )
                window.append(now)
            return route_function(*args, **kwargs)
        return wrapper
    return decorator
