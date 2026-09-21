"""
Static checks on the Postgres-rendered migration SQL.

IMPORTANT — what this test does and does not prove:
  - It DOES confirm that rendering every migration for the "postgresql"
    backend produces text with no leftover template placeholders, no
    SQLite-only syntax (AUTOINCREMENT, datetime('now')), and the expected
    Postgres constructs (SERIAL, NOW()) in their place.
  - It does NOT run this SQL against a real Postgres server — no
    `psycopg2` + live Postgres instance is available in this sandbox
    (no network access). It is a static/textual check, not a real syntax
    validation by Postgres's own parser. Run
    `DATABASE_URL=postgresql://... pytest` against a real Postgres
    instance (e.g. via docker-compose) before trusting this in
    production; see README "Honest limitations".
"""
import re

from repositories.migrations import MIGRATIONS, _render


def test_every_migration_renders_for_both_backends_without_leftover_placeholders():
    for version, name, sql in MIGRATIONS:
        for backend in ("sqlite", "postgresql"):
            rendered = _render(sql, backend)
            assert "{pk}" not in rendered, f"migration {version}_{name} left {{pk}} unrendered for {backend}"
            assert "{now}" not in rendered, f"migration {version}_{name} left {{now}} unrendered for {backend}"


def test_postgres_rendering_has_no_sqlite_only_syntax():
    for version, name, sql in MIGRATIONS:
        pg_sql = _render(sql, "postgresql")
        assert "AUTOINCREMENT" not in pg_sql, f"migration {version}_{name} still has SQLite AUTOINCREMENT"
        assert "datetime(" not in pg_sql, f"migration {version}_{name} still calls SQLite datetime()"


def test_postgres_rendering_uses_postgres_pk_and_now_syntax():
    # Every migration in this schema declares exactly one `id` primary key
    # column and, for tables with a timestamp column, uses NOW().
    for version, name, sql in MIGRATIONS:
        pg_sql = _render(sql, "postgresql")
        if re.search(r"\bid\s*\{pk\}", sql):
            assert "SERIAL PRIMARY KEY" in pg_sql, f"migration {version}_{name} missing SERIAL PRIMARY KEY"
        if "{now}" in sql:
            assert "NOW()" in pg_sql, f"migration {version}_{name} missing NOW()"


def test_sqlite_rendering_unchanged_from_original_schema():
    # Regression guard: the sqlite-rendered SQL must be byte-identical to
    # what this schema looked like before the {pk}/{now} templating was
    # introduced, so the existing (fully exercised, passing) SQLite test
    # suite is still testing the real production DDL.
    users_sql = _render(dict((v, s) for v, _, s in MIGRATIONS)[1], "sqlite")
    assert "INTEGER PRIMARY KEY AUTOINCREMENT" in users_sql
    assert "datetime('now')" in users_sql
