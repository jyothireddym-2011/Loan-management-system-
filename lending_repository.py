from .database import get_db


class LendingRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def find_by_hash(self, aadhaar_hash: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM lending_records WHERE aadhaar_hash = ?", (aadhaar_hash,))
            return cur.fetchone()

    def create(self, borrower_name, aadhaar_encrypted, aadhaar_hash, phone_number, lender_name,
               amount, agreement_filename, photo_filename, password_hash, risk_level) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            # Re-check for a duplicate INSIDE the transaction to close the
            # race window between the service-layer duplicate check and
            # this insert (production-roadmap item: "Prevent race conditions").
            cur.execute("SELECT id FROM lending_records WHERE aadhaar_hash = ?", (aadhaar_hash,))
            if cur.fetchone():
                raise ValueError("DUPLICATE")
            cur.execute(
                """
                INSERT INTO lending_records
                    (borrower_name, aadhaar_encrypted, aadhaar_hash, phone_number, lender_name, amount,
                     agreement_filename, photo_filename, password_hash, update_count, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (borrower_name.strip(), aadhaar_encrypted, aadhaar_hash, phone_number, lender_name.strip(),
                 amount, agreement_filename, photo_filename, password_hash, risk_level),
            )
            record_id = cur.lastrowid
            cur.execute(
                """INSERT INTO amount_history (record_id, action, old_amount, change_amount, new_amount, risk_level)
                   VALUES (?, 'create', '0.00', ?, ?, ?)""",
                (record_id, amount, amount, risk_level),
            )
            return record_id

    def update_after_payment(self, record_id: int, new_amount: str, new_update_count: int,
                              risk_level: str, agreement_filename: str, old_amount: str, paying_amount: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(
                """UPDATE lending_records
                   SET amount = ?, update_count = ?, risk_level = ?, agreement_filename = ?,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (new_amount, new_update_count, risk_level, agreement_filename, record_id),
            )
            cur.execute(
                """INSERT INTO amount_history (record_id, action, old_amount, change_amount, new_amount, risk_level)
                   VALUES (?, 'payment', ?, ?, ?, ?)""",
                (record_id, old_amount, paying_amount, new_amount, risk_level),
            )

    def delete(self, record_id: int, amount: str, risk_level: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO amount_history (record_id, action, old_amount, change_amount, new_amount, risk_level)
                   VALUES (?, 'remove', ?, '0.00', '0.00', ?)""",
                (record_id, amount, risk_level),
            )
            cur.execute("DELETE FROM lending_records WHERE id = ?", (record_id,))

    def update_frequency_for(self, record_id: int) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT update_count FROM lending_records WHERE id = ?", (record_id,))
            row = cur.fetchone()
            return row["update_count"] if row else 0
