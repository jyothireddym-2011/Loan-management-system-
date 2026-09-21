from .database import get_db


class LoanRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def create(self, user_id: int, borrower_id: int, borrower_name: str, lender_name: str,
               loan_amount: str, nominee_name: str, nominee_signature: str,
               lender_signature: str, borrower_signature: str) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO loans (
                    user_id, borrower_id, borrower_name, lender_name, loan_amount,
                    paid_amount, remaining_amount, nominee_name,
                    nominee_signature, lender_signature, borrower_signature
                ) VALUES (?, ?, ?, ?, ?, '0.00', ?, ?, ?, ?, ?)
                """,
                (user_id, borrower_id, borrower_name, lender_name.strip(), loan_amount,
                 loan_amount, nominee_name, nominee_signature, lender_signature, borrower_signature),
            )
            return cur.lastrowid

    def find_by_id(self, loan_id: int, user_id: int | None = None):
        query = "SELECT * FROM loans WHERE id = ?"
        params: list = [loan_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()

    def find_for_borrower(self, borrower_id: int, user_id: int,
                           sort_by: str = "created_at", sort_dir: str = "DESC",
                           limit: int | None = None, offset: int = 0):
        query = "SELECT * FROM loans WHERE borrower_id = ? AND user_id = ?"
        params: list = [borrower_id, user_id]
        # sort_by/sort_dir are allow-listed by utils.pagination before reaching here.
        query += f" ORDER BY {sort_by} {sort_dir}"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def count_for_borrower(self, borrower_id: int, user_id: int) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM loans WHERE borrower_id = ? AND user_id = ?",
                (borrower_id, user_id),
            )
            return cur.fetchone()["cnt"]

    def update_balance_for_payment(self, loan_id: int, new_paid_amount: str, new_remaining_amount: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE loans SET paid_amount = ?, remaining_amount = ? WHERE id = ?",
                (new_paid_amount, new_remaining_amount, loan_id),
            )

    def insert_payment(self, loan_id: int, amount_paid: str) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO payments (loan_id, amount_paid) VALUES (?, ?)",
                (loan_id, amount_paid),
            )
            return cur.lastrowid

    def payment_history(self, loan_id: int, sort_dir: str = "ASC",
                         limit: int | None = None, offset: int = 0):
        query = f"SELECT * FROM payments WHERE loan_id = ? ORDER BY paid_on {sort_dir}"
        params: list = [loan_id]
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def count_payments(self, loan_id: int) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS cnt FROM payments WHERE loan_id = ?", (loan_id,))
            return cur.fetchone()["cnt"]

    def record_payment_atomically(self, loan_id: int, amount_paid: str, new_paid_amount: str,
                                   new_remaining_amount: str) -> None:
        """
        Payment insert + balance update happen inside ONE connection/transaction
        (production-roadmap items: "Prevent race conditions", "Transaction
        boundaries"). Two concurrent payments against the same loan can no
        longer both read the same stale balance and overwrite each other —
        SQLite's default transaction takes an exclusive write lock for the
        life of this block.
        """
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute("SELECT loan_amount, paid_amount FROM loans WHERE id = ?", (loan_id,))
            row = cur.fetchone()
            if row is None:
                raise LookupError(f"Loan {loan_id} not found.")
            cur.execute(
                "INSERT INTO payments (loan_id, amount_paid) VALUES (?, ?)",
                (loan_id, amount_paid),
            )
            cur.execute(
                "UPDATE loans SET paid_amount = ?, remaining_amount = ? WHERE id = ?",
                (new_paid_amount, new_remaining_amount, loan_id),
            )
