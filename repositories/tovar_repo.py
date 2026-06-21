import sqlite3
from db.connection import Database
from models.tovar import Tovar


VALID_SORT_COLUMNS = {"nazov", "cena", "mnozstvo", "kategoria"}


class TovarRepo:
    def __init__(self, db: Database):
        self._db = db

    def create_table(self):
        cursor = self._db.get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tovar (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                nazov     TEXT    NOT NULL,
                cena      REAL    NOT NULL CHECK(cena >= 0),
                mnozstvo  INTEGER NOT NULL CHECK(mnozstvo >= 0),
                kategoria TEXT    NOT NULL
            )
        """)
        self._db.commit()

    def add(self, tovar: Tovar) -> int:
        cursor = self._db.get_cursor()
        try:
            cursor.execute(
                "INSERT INTO tovar (nazov, cena, mnozstvo, kategoria) VALUES (?, ?, ?, ?)",
                (tovar.nazov, tovar.cena, tovar.mnozstvo, tovar.kategoria)
            )
            self._db.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            self._db.rollback()
            raise ValueError(f"Chyba pri vkladaní tovaru: {e}")

    def get_all(self, sort_by: str = "nazov", descending: bool = False) -> list[Tovar]:
        if sort_by not in VALID_SORT_COLUMNS:
            raise ValueError(f"Neplatný stĺpec na triedenie: {sort_by}")
        order = "DESC" if descending else "ASC"
        cursor = self._db.get_cursor()
        cursor.execute(f"SELECT * FROM tovar ORDER BY {sort_by} {order}")
        return [Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                      mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])
                for r in cursor.fetchall()]

    def get_by_id(self, tovar_id: int) -> Tovar | None:
        cursor = self._db.get_cursor()
        cursor.execute("SELECT * FROM tovar WHERE id = ?", (tovar_id,))
        r = cursor.fetchone()
        if r is None:
            return None
        return Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                     mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])

    def update(self, tovar: Tovar):
        if tovar.id is None:
            raise ValueError("Tovar nemá id, nedá sa aktualizovať")
        cursor = self._db.get_cursor()
        cursor.execute(
            "UPDATE tovar SET nazov=?, cena=?, mnozstvo=?, kategoria=? WHERE id=?",
            (tovar.nazov, tovar.cena, tovar.mnozstvo, tovar.kategoria, tovar.id)
        )
        self._db.commit()

    def delete(self, tovar_id: int):
        cursor = self._db.get_cursor()
        try:
            cursor.execute("DELETE FROM tovar WHERE id = ?", (tovar_id,))
            self._db.commit()
        except sqlite3.IntegrityError as e:
            self._db.rollback()
            raise ValueError(f"Nedá sa vymazať tovar, má závislé objednávky: {e}")

    def search(self, query: str) -> list[Tovar]:
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM tovar WHERE nazov LIKE ? OR kategoria LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        return [Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                      mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])
                for r in cursor.fetchall()]

    def update_mnozstvo(self, tovar_id: int, zmena: int):
        """Zmení množstvo o zadanú hodnotu (kladná = príjem, záporná = výdaj)."""
        cursor = self._db.get_cursor()
        cursor.execute(
            "UPDATE tovar SET mnozstvo = mnozstvo + ? WHERE id = ?",
            (zmena, tovar_id)
        )
        self._db.commit()

    def filter_by_kategoria(self, kategoria: str) -> list[Tovar]:
        """Vráti všetky tovary danej kategórie."""
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM tovar WHERE kategoria = ? ORDER BY nazov",
            (kategoria,)
        )
        return [Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                      mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])
                for r in cursor.fetchall()]

    def filter_by_cena(self, min_cena: float = 0, max_cena: float = 9999) -> list[Tovar]:
        """Vráti tovary v cenovom rozsahu."""
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM tovar WHERE cena BETWEEN ? AND ? ORDER BY cena",
            (min_cena, max_cena)
        )
        return [Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                      mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])
                for r in cursor.fetchall()]

    def filter_dostupne(self) -> list[Tovar]:
        """Vráti len tovary, ktoré sú na sklade (mnozstvo > 0)."""
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM tovar WHERE mnozstvo > 0 ORDER BY nazov"
        )
        return [Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                      mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])
                for r in cursor.fetchall()]

    def filter_malo_na_sklade(self, limit: int = 5) -> list[Tovar]:
        """Vráti tovary, ktorých množstvo je pod zadaným limitom — upozornenie na doplnenie."""
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM tovar WHERE mnozstvo <= ? ORDER BY mnozstvo",
            (limit,)
        )
        return [Tovar(id=r["id"], nazov=r["nazov"], cena=r["cena"],
                      mnozstvo=r["mnozstvo"], kategoria=r["kategoria"])
                for r in cursor.fetchall()]

    def get_kategorie(self) -> list[str]:
        """Vráti zoznam všetkých unikátnych kategórií."""
        cursor = self._db.get_cursor()
        cursor.execute("SELECT DISTINCT kategoria FROM tovar ORDER BY kategoria")
        return [r["kategoria"] for r in cursor.fetchall()]