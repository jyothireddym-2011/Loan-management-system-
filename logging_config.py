"""
logging_config.py
------------------
Structured (JSON) logging, configured once at app startup. No third-party
logging dependency — a small JSON formatter over the stdlib `logging`
module is enough and keeps the dependency surface small.

Every log line includes: timestamp, level, logger name, message, and any
extra fields passed via `logger.info(msg, extra={...})` — request_id,
user_id, path, status_code, duration_ms, etc.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_RESERVED = set(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload:
                try:
                    json.dumps(value)  # only include JSON-serializable extras
                    payload[key] = value
                except TypeError:
                    payload[key] = str(value)

        return json.dumps(payload, default=str)


class PlainFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    # Clear any handlers left over from a previous configure_logging() call
    # (relevant in tests, which spin up the app repeatedly).
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if json_output else PlainFormatter())
    root.addHandler(handler)

    # Werkzeug's own request logger is noisy and duplicates our request
    # logging middleware — keep it at WARNING.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
