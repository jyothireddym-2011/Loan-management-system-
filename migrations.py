"""
migrations.py
-------------
Simple, dependency-free migration runner (production-roadmap item:
"Database migrations"). Each migration is a numbered, named, idempotent
SQL block. Applied migrations are recorded in `schema_migrations` so
re-running `run_migrations()` on an already-migrated database is a no-op.

This intentionally does NOT pull in Alembic/Flask-Migrate — the schema
here is small enough that a linear list of migrations is easier to review
than a generated migration graph. If/when the schema grows a lot, swap
this runner for Alembic without changing how repositories talk to the DB.

Postgres portability: the two places SQLite and Postgres DDL actually
differ in this schema are (1) the autoincrementing primary key syntax and
(2) the "current timestamp" default expression. Every CREATE TABLE below
is written with `{pk}` / `{now}` placeholders and rendered per-backend by
`_render()` before executing, so the exact same migration list produces
correct DDL on both backends instead of maintaining two parallel schemas.
This has been verified by rendering + inspecting the Postgres-flavored
SQL text (see tests/test_migrations_portability.py) but — like the query
placeholder translation in database.py — has NOT been run against a live
Postgres server in this sandbox (no network access to install psycopg2 +
stand up a server here). Run the migration suite against a real
`postgresql://` DSN before relying on this in production.
"""

from __future__ import annotations

from .database import Database

Migration = tuple[int, str, str]  # (version, name, sql_template)

_PLACEHOLDERS = {
    "sqlite": {"pk": "INTEGER PRIMARY KEY AUTOINCREMENT", "now": "datetime('now')"},
    "postgresql": {"pk": "SERIAL PRIMARY KEY", "now": "NOW()"},
}


def _render(sql_template: str, backend: str) -> str:
    values = _PLACEHOLDERS[backend]
    return sql_template.format(pk=values["pk"], now=values["now"])


MIGRATIONS: list[Migration] = [
    (1, "create_users", """
        CREATE TABLE IF NOT EXISTS users (
            id {pk},
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT ({now})
        )
    """),
    (2, "create_sessions", """
        CREATE TABLE IF NOT EXISTS sessions (
            id {pk},
            user_id INTEGER NOT NULL,
            jti TEXT NOT NULL UNIQUE,
            created_at TEXT DEFAULT ({now}),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """),
    (3, "create_sessions_expires_index", """
        CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions (expires_at)
    """),
    (4, "create_borrowers", """
        CREATE TABLE IF NOT EXISTS borrowers (
            id {pk},
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            aadhaar_encrypted TEXT NOT NULL,
            aadhaar_hash TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TEXT DEFAULT ({now}),
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE (user_id, aadhaar_hash)
        )
    """),
    (5, "create_loans", """
        CREATE TABLE IF NOT EXISTS loans (
            id {pk},
            user_id INTEGER NOT NULL,
            borrower_id INTEGER NOT NULL,
            borrower_name TEXT NOT NULL,
            lender_name TEXT NOT NULL,
            loan_amount TEXT NOT NULL,
            paid_amount TEXT NOT NULL DEFAULT '0.00',
            remaining_amount TEXT NOT NULL,
            nominee_name TEXT,
            nominee_signature TEXT NOT NULL,
            lender_signature TEXT NOT NULL,
            borrower_signature TEXT NOT NULL,
            created_at TEXT DEFAULT ({now}),
            FOREIGN KEY (borrower_id) REFERENCES borrowers (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """),
    (6, "create_payments", """
        CREATE TABLE IF NOT EXISTS payments (
            id {pk},
            loan_id INTEGER NOT NULL,
            amount_paid TEXT NOT NULL,
            paid_on TEXT DEFAULT ({now}),
            FOREIGN KEY (loan_id) REFERENCES loans (id)
        )
    """),
    (7, "create_documents", """
        CREATE TABLE IF NOT EXISTS documents (
            id {pk},
            user_id INTEGER NOT NULL,
            borrower_id INTEGER,
            loan_id INTEGER,
            doc_type TEXT,
            original_filename TEXT NOT NULL,
            stored_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            uploaded_at TEXT DEFAULT ({now}),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """),
    (8, "create_lending_records", """
        CREATE TABLE IF NOT EXISTS lending_records (
            id {pk},
            borrower_name TEXT NOT NULL,
            aadhaar_encrypted TEXT NOT NULL,
            aadhaar_hash TEXT NOT NULL UNIQUE,
            phone_number TEXT,
            lender_name TEXT NOT NULL,
            amount TEXT NOT NULL,
            agreement_filename TEXT,
            photo_filename TEXT,
            password_hash TEXT NOT NULL,
            update_count INTEGER NOT NULL DEFAULT 0,
            risk_level TEXT NOT NULL DEFAULT 'Low',
            created_at TEXT DEFAULT ({now}),
            updated_at TEXT DEFAULT ({now})
        )
    """),
    (9, "create_amount_history", """
        CREATE TABLE IF NOT EXISTS amount_history (
            id {pk},
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            old_amount TEXT,
            change_amount TEXT,
            new_amount TEXT,
            risk_level TEXT,
            event_at TEXT DEFAULT ({now})
        )
    """),
    (10, "create_audit_log", """
        CREATE TABLE IF NOT EXISTS audit_log (
            id {pk},
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id INTEGER,
            detail TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT ({now})
        )
    """),
    # --- Indexes on every foreign key + hot lookup/filter column ---------
    # None of these change existing data or table shape (CREATE INDEX IF
    # NOT EXISTS is purely additive and safe to run against a populated
    # table on both SQLite and Postgres), so they're plain new migrations
    # rather than edits to the CREATE TABLE statements above. Without
    # these, every join/filter on a foreign key (e.g. "loans for this
    # borrower", "payments for this loan", "audit log for this user")
    # forces a full table scan as the tables grow.
    (11, "create_sessions_user_id_index", """
        CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions (user_id)
    """),
    (12, "create_borrowers_user_id_index", """
        CREATE INDEX IF NOT EXISTS idx_borrowers_user_id ON borrowers (user_id)
    """),
    (13, "create_loans_borrower_id_index", """
        CREATE INDEX IF NOT EXISTS idx_loans_borrower_id ON loans (borrower_id)
    """),
    (14, "create_loans_user_id_index", """
        CREATE INDEX IF NOT EXISTS idx_loans_user_id ON loans (user_id)
    """),
    (15, "create_payments_loan_id_index", """
        CREATE INDEX IF NOT EXISTS idx_payments_loan_id ON payments (loan_id)
    """),
    (16, "create_documents_user_id_index", """
        CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents (user_id)
    """),
    (17, "create_documents_borrower_loan_index", """
        CREATE INDEX IF NOT EXISTS idx_documents_borrower_loan ON documents (borrower_id, loan_id)
    """),
    (18, "create_amount_history_record_id_index", """
        CREATE INDEX IF NOT EXISTS idx_amount_history_record_id ON amount_history (record_id)
    """),
    (19, "create_audit_log_user_id_index", """
        CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log (user_id)
    """),
    (20, "create_audit_log_entity_index", """
        CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log (entity_type, entity_id)
    """),
    (21, "create_audit_log_created_at_index", """
        CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log (created_at)
    """),
    (22, "create_lending_records_phone_index", """
        CREATE INDEX IF NOT EXISTS idx_lending_records_phone ON lending_records (phone_number)
    """),
]


def run_migrations(db: Database) -> list[str]:
    applied = []
    with db.connection() as conn:
        cur = conn.cursor()
        cur.execute(_render("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT DEFAULT ({now})
            )
        """, db.backend))
        cur.execute("SELECT version FROM schema_migrations")
        already_applied = {row[0] for row in cur.fetchall()}

        for version, name, sql_template in MIGRATIONS:
            if version in already_applied:
                continue
            cur.execute(_render(sql_template, db.backend))
            cur.execute("INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (version, name))
            applied.append(f"{version:03d}_{name}")

    return applied
