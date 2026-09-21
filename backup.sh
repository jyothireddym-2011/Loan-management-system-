#!/usr/bin/env bash
# Back up the application database and uploaded documents.
#
# SQLite (default/dev deployment):
#   Uses the sqlite3 `.backup` command (not a plain `cp`) so a backup can
#   safely be taken while the app is writing to the database — a raw file
#   copy of an open SQLite DB can capture a half-written page.
#
# Postgres (production):
#   Shells out to `pg_dump` with a custom-format (-Fc) archive, which is
#   compressed and restorable with `pg_restore` (including selective
#   table restores), unlike a plain SQL text dump.
#
# Usage:
#   ./scripts/backup.sh                # uses DATABASE_URL from the environment
#   BACKUP_DIR=/mnt/backups ./scripts/backup.sh
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DOCS_DIR="${DOCUMENTS_STORAGE_DIR:-./documents/storage}"

mkdir -p "$BACKUP_DIR"

if [[ "${DATABASE_URL:-}" == postgresql://* || "${DATABASE_URL:-}" == postgres://* ]]; then
    echo "Backing up PostgreSQL database..."
    OUT="$BACKUP_DIR/db_${TIMESTAMP}.dump"
    pg_dump -Fc --no-owner --no-privileges "$DATABASE_URL" -f "$OUT"
    echo "Postgres dump written to $OUT"
    echo "Restore with: pg_restore --clean --if-exists --no-owner -d \$DATABASE_URL $OUT"
else
    SQLITE_PATH="${DATABASE_URL#sqlite:///}"
    SQLITE_PATH="${SQLITE_PATH:-./data/app.db}"
    if [[ ! -f "$SQLITE_PATH" ]]; then
        echo "SQLite database not found at $SQLITE_PATH" >&2
        exit 1
    fi
    echo "Backing up SQLite database at $SQLITE_PATH..."
    OUT="$BACKUP_DIR/db_${TIMESTAMP}.sqlite3"
    sqlite3 "$SQLITE_PATH" ".backup '$OUT'"
    echo "SQLite backup written to $OUT"
    echo "Restore by stopping the app and copying this file back over the live DB path."
fi

if [[ -d "$DOCS_DIR" ]]; then
    echo "Archiving uploaded documents from $DOCS_DIR..."
    DOCS_OUT="$BACKUP_DIR/documents_${TIMESTAMP}.tar.gz"
    tar -czf "$DOCS_OUT" -C "$(dirname "$DOCS_DIR")" "$(basename "$DOCS_DIR")"
    echo "Documents archived to $DOCS_OUT"
fi

echo "Backup complete: $BACKUP_DIR"
echo "Reminder: encrypt and copy backups off-host (they contain encrypted-at-rest Aadhaar data and password hashes)."
