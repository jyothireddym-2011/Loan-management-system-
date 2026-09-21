"""
database.py
-----------
Single connection factory shared by every repository. Deliberately thin:
repositories still write their own SQL (this is not an ORM), but nothing
outside this file knows whether it's talking to SQLite or PostgreSQL.

Postgres support: set DATABASE_URL to a postgresql:// URL and install
psycopg2-binary (already included in this image's Dockerfile; uncomment
in requirements.txt for non-Docker installs). Every repository writes
sqlite3-style `?` positional placeholders; `_TranslatingCursor` below
rewrites those to psycopg2's `%s` style transparently at the cursor level
so no repository file needs to know or care which backend is live. This
was previously a documented-but-unimplemented "Phase 2" TODO — the
translation is now real, but it has only been exercised against SQLite
in this sandbox (no network access to install/run psycopg2 + a Postgres
server here). Run the test suite against a real `postgresql://` DSN
before relying on this in production.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from urllib.parse import urlparse

_local = threading.local()

# Matches `?` placeholders that are NOT inside a single-quoted SQL string
# literal, so a literal question mark inside quoted text (none currently
# exist in this codebase, but this is defensive) is left untouched.
_PLACEHOLDER_RE = re.compile(r"'(?:[^']|'')*'|(\?)")


def _translate_placeholders(sql: str) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: "%s" if m.group(1) else m.group(0), sql)


class _TranslatingCursor:
    """Wraps a psycopg2 cursor so callers can keep using `?` placeholders."""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=None):
        translated = _translate_placeholders(sql)
        return self._cursor.execute(translated, params or ())

    def executemany(self, sql, seq_of_params):
        translated = _translate_placeholders(sql)
        return self._cursor.executemany(translated, seq_of_params)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _TranslatingConnection:
    """Wraps a psycopg2 connection so `.cursor()` yields a translating cursor."""

    def __init__(self, conn):
        self._conn = conn

    def cursor(self, *args, **kwargs):
        return _TranslatingCursor(self._conn.cursor(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self._conn, name)


class Database:
    """
    Thin wrapper that:
      - resolves DATABASE_URL into either a sqlite3 or (optionally) a
        psycopg2 connection,
      - exposes context-managed connections with automatic commit/rollback,
      - gives repositories a single `?`-style placeholder regardless of
        backend (translated to `%s` for Postgres).
    """

    def __init__(self, database_url: str):
        self.database_url = database_url
        parsed = urlparse(database_url)
        self.backend = "postgresql" if parsed.scheme.startswith("postgres") else "sqlite"

        self._memory_conn = None  # kept alive for the life of the process when using :memory:

        if self.backend == "sqlite":
            if parsed.path in ("/:memory:", ":memory:"):
                self.sqlite_path = ":memory:"
                # A bare ":memory:" DB is destroyed the instant its one
                # connection closes — sqlite3.connect(":memory:") called
                # twice gives two *different*, empty databases. Since our
                # connection() context manager closes after every request,
                # we keep a single long-lived connection open here (used
                # by every repository call) so schema + data persist for
                # the lifetime of the app (tests use this path).
                self._memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
                self._memory_conn.execute("PRAGMA foreign_keys = ON")
            else:
                self.sqlite_path = parsed.path or database_url.replace("sqlite:///", "")
                os.makedirs(os.path.dirname(os.path.abspath(self.sqlite_path)) or ".", exist_ok=True)
        else:  # pragma: no cover - exercised only when psycopg2 is installed
            try:
                import psycopg2  # noqa: F401
            except ImportError as exc:
                raise RuntimeError(
                    "DATABASE_URL points to PostgreSQL but psycopg2-binary is not "
                    "installed. Run: pip install psycopg2-binary"
                ) from exc

    @property
    def placeholder(self) -> str:
        return "?" if self.backend == "sqlite" else "%s"

    def _raw_connect(self):
        if self.backend == "sqlite":
            conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            return conn
        else:  # pragma: no cover - exercised only when psycopg2 + a Postgres server are available
            import psycopg2
            import psycopg2.extras

            conn = psycopg2.connect(self.database_url, cursor_factory=psycopg2.extras.RealDictCursor)
            return _TranslatingConnection(conn)

    @contextmanager
    def connection(self):
        """
        Context manager: commits on clean exit, rolls back on exception.
        Usage:
            with db.connection() as conn:
                cur = conn.cursor()
                cur.execute(...)
        """
        if self._memory_conn is not None:
            # Reuse the single long-lived in-memory connection; never close it.
            conn = self._memory_conn
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return

        conn = self._raw_connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def run_ddl(self, statements: list[str]) -> None:
        with self.connection() as conn:
            cur = conn.cursor()
            for stmt in statements:
                cur.execute(stmt)


_db_instance: Database | None = None
_db_lock = threading.Lock()


def init_database(database_url: str) -> Database:
    global _db_instance
    with _db_lock:
        _db_instance = Database(database_url)
    return _db_instance


def get_db() -> Database:
    if _db_instance is None:
        raise RuntimeError("Database not initialized. Call init_database(app.config['DATABASE_URL']) at startup.")
    return _db_instance
