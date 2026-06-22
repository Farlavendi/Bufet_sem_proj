import sqlite3
from db.connection import Database
from models.zakaznik import Zakaznik


VALID_SORT_COLUMNS = {"meno", "email"}


class ZakaznikRepo:
    def __init__(self, db: Database):
        self._db = db

    def create_table(self):
        cursor = self._db.get_cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zakaznici (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                meno    TEXT    NOT NULL,
                email   TEXT    NOT NULL UNIQUE,
                telefon TEXT
            )
        """)
        self._db.commit()

    def add(self, zakaznik: Zakaznik) -> int:
        cursor = self._db.get_cursor()
        try:
            cursor.execute(
                "INSERT INTO zakaznici (meno, email, telefon) VALUES (?, ?, ?)",
                (zakaznik.meno, zakaznik.email, zakaznik.telefon)
            )
            self._db.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            self._db.rollback()
            raise ValueError(f"Zákazník s emailom '{zakaznik.email}' už existuje")

    def get_all(self, sort_by: str = "meno", descending: bool = False) -> list[Zakaznik]:
        if sort_by not in VALID_SORT_COLUMNS:
            raise ValueError(f"Neplatný stĺpec na triedenie: {sort_by}")
        order = "DESC" if descending else "ASC"
        cursor = self._db.get_cursor()
        cursor.execute(f"SELECT * FROM zakaznici ORDER BY {sort_by} {order}")
        return [Zakaznik(id=r["id"], meno=r["meno"],
                         email=r["email"], telefon=r["telefon"])
                for r in cursor.fetchall()]

    def get_by_id(self, zakaznik_id: int) -> Zakaznik | None:
        cursor = self._db.get_cursor()
        cursor.execute("SELECT * FROM zakaznici WHERE id = ?", (zakaznik_id,))
        r = cursor.fetchone()
        if r is None:
            return None
        return Zakaznik(id=r["id"], meno=r["meno"],
                        email=r["email"], telefon=r["telefon"])

    def update(self, zakaznik: Zakaznik):
        if zakaznik.id is None:
            raise ValueError("Zákazník nemá id, nedá sa aktualizovať")
        cursor = self._db.get_cursor()
        try:
            cursor.execute(
                "UPDATE zakaznici SET meno=?, email=?, telefon=? WHERE id=?",
                (zakaznik.meno, zakaznik.email, zakaznik.telefon, zakaznik.id)
            )
            self._db.commit()
        except sqlite3.IntegrityError:
            self._db.rollback()
            raise ValueError(f"Email '{zakaznik.email}' už používa iný zákazník")

    def delete(self, zakaznik_id: int):
        cursor = self._db.get_cursor()
        try:
            cursor.execute("DELETE FROM zakaznici WHERE id = ?", (zakaznik_id,))
            self._db.commit()
        except sqlite3.IntegrityError as e:
            self._db.rollback()
            raise ValueError(f"Nedá sa vymazať zákazník, má závislé objednávky: {e}")

    def search(self, query: str) -> list[Zakaznik]:
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM zakaznici WHERE meno LIKE ? OR email LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        return [Zakaznik(id=r["id"], meno=r["meno"],
                         email=r["email"], telefon=r["telefon"])
                for r in cursor.fetchall()]

    def get_zakaznici_s_objednavkami(self) -> list[dict]:
        """Vráti zákazníkov, ktorí majú aspoň jednu objednávku, s počtom objednávok."""
        cursor = self._db.get_cursor()
        cursor.execute("""
            SELECT z.id, z.meno, z.email,
                   COUNT(o.id) AS pocet_objednavok
            FROM zakaznici z
            JOIN objednavky o ON o.id_zakaznika = z.id
            GROUP BY z.id
            ORDER BY pocet_objednavok DESC
        """)
        return [dict(r) for r in cursor.fetchall()]