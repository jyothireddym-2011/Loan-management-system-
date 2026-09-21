"""
Confirms the foreign-key/hot-column indexes added on top of the base
schema actually exist on a migrated database, and that they render
without SQLite-only syntax for Postgres (same portability guarantee as
the table-creation migrations).
"""
from repositories.migrations import MIGRATIONS, _render

EXPECTED_INDEXES = {
    "idx_sessions_user_id",
    "idx_borrowers_user_id",
    "idx_loans_borrower_id",
    "idx_loans_user_id",
    "idx_payments_loan_id",
    "idx_documents_user_id",
    "idx_documents_borrower_loan",
    "idx_amount_history_record_id",
    "idx_audit_log_user_id",
    "idx_audit_log_entity",
    "idx_audit_log_created_at",
    "idx_lending_records_phone",
}


def test_expected_indexes_are_declared_in_migrations():
    declared_sql = " ".join(sql for _, _, sql in MIGRATIONS)
    for index_name in EXPECTED_INDEXES:
        assert index_name in declared_sql, f"missing migration for {index_name}"


def test_indexes_exist_on_a_freshly_migrated_sqlite_database(app):
    from repositories.database import get_db

    db = get_db()
    with db.connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    existing = {row["name"] if hasattr(row, "keys") else row[0] for row in rows}
    missing = EXPECTED_INDEXES - existing
    assert not missing, f"indexes not created on migrated DB: {missing}"


def test_index_migrations_render_cleanly_for_postgres():
    for version, name, sql in MIGRATIONS:
        if "CREATE INDEX" in sql:
            rendered = _render(sql, "postgresql")
            assert "{pk}" not in rendered
            assert "{now}" not in rendered
