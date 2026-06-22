from db.connection import Database
from models.objednavka import Objednavka

VALID_SORT_COLUMNS = {"datum", "mnozstvo", "id_tovaru", "id_zakaznika"}


class ObjednavkaRepo:
    def __init__(self, db: Database):
        self._db = db

    def create_table(self):
        cursor = self._db.get_cursor()
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS objednavky
                       (
                           id           INTEGER PRIMARY KEY AUTOINCREMENT,
                           id_tovaru    INTEGER NOT NULL REFERENCES tovar (id),
                           id_zakaznika INTEGER NOT NULL REFERENCES zakaznici (id),
                           mnozstvo     INTEGER NOT NULL CHECK (mnozstvo > 0),
                           datum        TEXT    NOT NULL
                       )
                       """)
        self._db.commit()

    def add(self, objednavka: Objednavka) -> int:
        """Pridá objednávku a zníži množstvo tovaru — v jednej transakcii."""
        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:

            cursor.execute("SELECT mnozstvo FROM tovar WHERE id = ?", (objednavka.id_tovaru,))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Tovar s id {objednavka.id_tovaru} neexistuje")
            if row["mnozstvo"] < objednavka.mnozstvo:
                raise ValueError(f"Nedostatok tovaru na sklade (dostupné: {row['mnozstvo']})")

            cursor.execute(
                "INSERT INTO objednavky (id_tovaru, id_zakaznika, mnozstvo, datum) VALUES (?, ?, ?, ?)",
                (objednavka.id_tovaru, objednavka.id_zakaznika,
                 objednavka.mnozstvo, objednavka.datum)
            )

            cursor.execute(
                "UPDATE tovar SET mnozstvo = mnozstvo - ? WHERE id = ?",
                (objednavka.mnozstvo, objednavka.id_tovaru)
            )
            conn.commit()
            return cursor.lastrowid
        except Exception:
            conn.rollback()
            raise

    def get_all(self, sort_by: str = "datum", descending: bool = False) -> list[Objednavka]:
        if sort_by not in VALID_SORT_COLUMNS:
            raise ValueError(f"Neplatný stĺpec na triedenie: {sort_by}")
        order = "DESC" if descending else "ASC"
        cursor = self._db.get_cursor()
        cursor.execute(f"SELECT * FROM objednavky ORDER BY {sort_by} {order}")
        return [Objednavka(id=r["id"], id_tovaru=r["id_tovaru"],
                           id_zakaznika=r["id_zakaznika"], mnozstvo=r["mnozstvo"],
                           datum=r["datum"])
                for r in cursor.fetchall()]

    def get_by_zakaznik(self, zakaznik_id: int) -> list[Objednavka]:
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM objednavky WHERE id_zakaznika = ? ORDER BY datum DESC",
            (zakaznik_id,)
        )
        return [Objednavka(id=r["id"], id_tovaru=r["id_tovaru"],
                           id_zakaznika=r["id_zakaznika"], mnozstvo=r["mnozstvo"],
                           datum=r["datum"])
                for r in cursor.fetchall()]

    def get_by_tovar(self, tovar_id: int) -> list[Objednavka]:
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM objednavky WHERE id_tovaru = ? ORDER BY datum DESC",
            (tovar_id,)
        )
        return [Objednavka(id=r["id"], id_tovaru=r["id_tovaru"],
                           id_zakaznika=r["id_zakaznika"], mnozstvo=r["mnozstvo"],
                           datum=r["datum"])
                for r in cursor.fetchall()]

    def delete(self, objednavka_id: int):
        """Vymaze objednavku a vrati mnozstvo spat na sklad v jednej transakcii."""
        conn = self._db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id_tovaru, mnozstvo FROM objednavky WHERE id = ?",
                (objednavka_id,)
            )
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Objednavka {objednavka_id} neexistuje")
            cursor.execute("DELETE FROM objednavky WHERE id = ?", (objednavka_id,))
            cursor.execute(
                "UPDATE tovar SET mnozstvo = mnozstvo + ? WHERE id = ?",
                (row["mnozstvo"], row["id_tovaru"])
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def filter_by_datum(self, od: str, do: str) -> list[Objednavka]:
        """Vráti objednávky v zadanom časovom rozsahu (formát: 'YYYY-MM-DD')."""
        cursor = self._db.get_cursor()
        cursor.execute(
            "SELECT * FROM objednavky WHERE datum BETWEEN ? AND ? ORDER BY datum DESC",
            (od, do + " 23:59")
        )
        return [Objednavka(id=r["id"], id_tovaru=r["id_tovaru"],
                           id_zakaznika=r["id_zakaznika"], mnozstvo=r["mnozstvo"],
                           datum=r["datum"])
                for r in cursor.fetchall()]

    def get_all_with_names(self, sort_by: str = "datum", descending: bool = False) -> list[dict]:
        """Vráti objednávky s názvom tovaru a menom zákazníka (JOIN)."""
        if sort_by not in VALID_SORT_COLUMNS:
            raise ValueError(f"Neplatný stĺpec na triedenie: {sort_by}")
        order = "DESC" if descending else "ASC"
        cursor = self._db.get_cursor()
        cursor.execute(f"""
            SELECT o.id, o.mnozstvo, o.datum,
                   t.nazov AS nazov_tovaru, t.cena,
                   z.meno  AS meno_zakaznika
            FROM objednavky o
            JOIN tovar     t ON o.id_tovaru    = t.id
            JOIN zakaznici z ON o.id_zakaznika = z.id
            ORDER BY o.{sort_by} {order}
        """)
        return [dict(r) for r in cursor.fetchall()]

    def get_suma_by_zakaznik(self) -> list[dict]:
        """Vráti celkovú sumu objednávok pre každého zákazníka."""
        cursor = self._db.get_cursor()
        cursor.execute("""
                       SELECT z.meno,
                              COUNT(o.id)              AS pocet_objednavok,
                              SUM(o.mnozstvo * t.cena) AS celkova_suma
                       FROM objednavky o
                                JOIN zakaznici z ON o.id_zakaznika = z.id
                                JOIN tovar t ON o.id_tovaru = t.id
                       GROUP BY z.id
                       ORDER BY celkova_suma DESC
                       """)
        return [dict(r) for r in cursor.fetchall()]

    def get_statistiky_tovaru(self) -> list[dict]:
        """Koľko kusov každého tovaru bolo predaných celkovo."""
        cursor = self._db.get_cursor()
        cursor.execute("""
                       SELECT t.nazov,
                              t.kategoria,
                              COUNT(o.id)     AS pocet_objednavok,
                              SUM(o.mnozstvo) AS predanych_kusov
                       FROM objednavky o
                                JOIN tovar t ON o.id_tovaru = t.id
                       GROUP BY t.id
                       ORDER BY predanych_kusov DESC
                       """)
        return [dict(r) for r in cursor.fetchall()]
