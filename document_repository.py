from .database import get_db


class DocumentRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def create(self, user_id: int, borrower_id, loan_id, doc_type: str,
               original_filename: str, stored_filename: str, stored_path: str) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO documents
                    (user_id, borrower_id, loan_id, doc_type, original_filename, stored_filename, stored_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, borrower_id, loan_id, doc_type, original_filename, stored_filename, stored_path),
            )
            return cur.lastrowid

    def find_by_id(self, doc_id: int, user_id: int):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
            return cur.fetchone()

    def list_for_user(self, user_id: int, borrower_id=None, loan_id=None,
                       sort_by: str = "uploaded_at", sort_dir: str = "DESC",
                       limit: int | None = None, offset: int = 0):
        query = "SELECT * FROM documents WHERE user_id = ?"
        params: list = [user_id]
        if borrower_id:
            query += " AND borrower_id = ?"
            params.append(borrower_id)
        if loan_id:
            query += " AND loan_id = ?"
            params.append(loan_id)
        # sort_by/sort_dir are allow-listed by utils.pagination before reaching here.
        query += f" ORDER BY {sort_by} {sort_dir}"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def count_for_user(self, user_id: int, borrower_id=None, loan_id=None) -> int:
        query = "SELECT COUNT(*) AS cnt FROM documents WHERE user_id = ?"
        params: list = [user_id]
        if borrower_id:
            query += " AND borrower_id = ?"
            params.append(borrower_id)
        if loan_id:
            query += " AND loan_id = ?"
            params.append(loan_id)
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()["cnt"]

    def delete(self, doc_id: int, user_id: int) -> bool:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (doc_id, user_id))
            return cur.rowcount > 0
