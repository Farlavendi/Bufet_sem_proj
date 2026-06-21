import sqlite3
from db.connection import Database
from models.pouzivatel import Pouzivatel


class PouzivatelRepo:
    def __init__(self, db: Database):
        self._db = db

    def create_table(self):
        cursor = self._db.get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pouzivatelia (
                id    INTEGER PRIMARY KEY AUTOINCREMENT,
                meno  TEXT    NOT NULL UNIQUE,
                heslo TEXT    NOT NULL,
                rola  TEXT    NOT NULL DEFAULT 'obsluha'
            )
        """)
        self._db.commit()

    def add(self, pouzivatel: Pouzivatel) -> int:
        cursor = self._db.get_cursor()
        try:
            cursor.execute(
                "INSERT INTO pouzivatelia (meno, heslo, rola) VALUES (?, ?, ?)",
                (pouzivatel.meno, pouzivatel.hash_heslo(), pouzivatel.rola)
            )
            self._db.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            self._db.rollback()
            raise ValueError(f"Používateľ '{pouzivatel.meno}' už existuje")

    def get_all(self) -> list[Pouzivatel]:
        cursor = self._db.get_cursor()
        cursor.execute("SELECT * FROM pouzivatelia ORDER BY meno")
        return [Pouzivatel(id=r["id"], meno=r["meno"], heslo=r["heslo"], rola=r["rola"])
                for r in cursor.fetchall()]

    def get_by_meno(self, meno: str) -> Pouzivatel | None:
        cursor = self._db.get_cursor()
        cursor.execute("SELECT * FROM pouzivatelia WHERE meno = ?", (meno,))
        r = cursor.fetchone()
        if r is None:
            return None
        return Pouzivatel(id=r["id"], meno=r["meno"], heslo=r["heslo"], rola=r["rola"])

    def verify(self, meno: str, heslo: str) -> Pouzivatel | None:
        """Vráti používateľa ak meno+heslo sedí, inak None."""
        pouzivatel = self.get_by_meno(meno)
        if pouzivatel is None:
            return None
        import hashlib
        if pouzivatel.heslo == hashlib.sha256(heslo.encode()).hexdigest():
            return pouzivatel
        return None

    def delete(self, pouzivatel_id: int):
        cursor = self._db.get_cursor()
        cursor.execute("DELETE FROM pouzivatelia WHERE id = ?", (pouzivatel_id,))
        self._db.commit()

    def update_rola(self, pouzivatel_id: int, nova_rola: str):
        if nova_rola not in Pouzivatel.ROLES:
            raise ValueError(f"Neplatná rola: {nova_rola}")
        cursor = self._db.get_cursor()
        cursor.execute(
            "UPDATE pouzivatelia SET rola = ? WHERE id = ?",
            (nova_rola, pouzivatel_id)
        )
        self._db.commit()