#!/usr/bin/env bash
# Restore a database backup produced by scripts/backup.sh.
#
# Usage:
#   ./scripts/restore.sh path/to/db_TIMESTAMP.sqlite3
#   ./scripts/restore.sh path/to/db_TIMESTAMP.dump      # Postgres
#
# IMPORTANT: stop the application before restoring — this script does not
# do it for you, since orchestration (systemd/docker/k8s) differs per
# deployment. Restoring into a live database while the app is writing to
# it can corrupt data.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <backup_file>" >&2
    exit 1
fi

BACKUP_FILE="$1"
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

echo "This will overwrite the current database with $BACKUP_FILE."
read -rp "Have you stopped the application? Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted."
    exit 1
fi

case "$BACKUP_FILE" in
    *.dump)
        : "${DATABASE_URL:?DATABASE_URL must be set to the target postgresql:// URL}"
        echo "Restoring PostgreSQL dump..."
        pg_restore --clean --if-exists --no-owner -d "$DATABASE_URL" "$BACKUP_FILE"
        ;;
    *.sqlite3)
        SQLITE_PATH="${DATABASE_URL#sqlite:///}"
        SQLITE_PATH="${SQLITE_PATH:-./data/app.db}"
        echo "Restoring SQLite database to $SQLITE_PATH..."
        cp "$SQLITE_PATH" "${SQLITE_PATH}.pre-restore.bak" 2>/dev/null || true
        cp "$BACKUP_FILE" "$SQLITE_PATH"
        ;;
    *)
        echo "Unrecognized backup file extension (expected .dump or .sqlite3)" >&2
        exit 1
        ;;
esac

echo "Restore complete. Restart the application."
