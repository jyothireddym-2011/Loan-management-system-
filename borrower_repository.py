from .database import get_db


class BorrowerRepository:
    def __init__(self, db=None):
        self.db = db or get_db()

    def find_by_hash(self, user_id: int, aadhaar_hash: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM borrowers WHERE user_id = ? AND aadhaar_hash = ?",
                (user_id, aadhaar_hash),
            )
            return cur.fetchone()

    def find_by_name(self, user_id: int, name: str):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM borrowers WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                (user_id, name),
            )
            return cur.fetchone()

    def search(self, user_id: int, name: str | None, aadhaar_hash: str | None,
               sort_by: str = "created_at", sort_dir: str = "DESC",
               limit: int | None = None, offset: int = 0):
        """
        `sort_by`/`sort_dir` are only ever populated from
        utils.pagination.parse_pagination's allow-listed values — never
        raw request input — so string-formatting them into the query here
        is safe from injection.
        """
        query = "SELECT * FROM borrowers WHERE user_id = ?"
        params: list = [user_id]
        if name:
            query += " AND LOWER(name) LIKE LOWER(?)"
            params.append(f"%{name.strip()}%")
        if aadhaar_hash:
            query += " AND aadhaar_hash = ?"
            params.append(aadhaar_hash)
        query += f" ORDER BY {sort_by} {sort_dir}"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def count_search(self, user_id: int, name: str | None, aadhaar_hash: str | None) -> int:
        query = "SELECT COUNT(*) AS cnt FROM borrowers WHERE user_id = ?"
        params: list = [user_id]
        if name:
            query += " AND LOWER(name) LIKE LOWER(?)"
            params.append(f"%{name.strip()}%")
        if aadhaar_hash:
            query += " AND aadhaar_hash = ?"
            params.append(aadhaar_hash)
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()["cnt"]

    def create(self, user_id: int, name: str, aadhaar_encrypted: str, aadhaar_hash: str,
               phone: str, address: str) -> int:
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO borrowers (user_id, name, aadhaar_encrypted, aadhaar_hash, phone, address)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, name.strip(), aadhaar_encrypted, aadhaar_hash, phone, address),
            )
            return cur.lastrowid

    def find_by_id(self, borrower_id: int, user_id: int):
        with self.db.connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM borrowers WHERE id = ? AND user_id = ?", (borrower_id, user_id))
            return cur.fetchone()
