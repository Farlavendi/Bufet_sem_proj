from db.connection import Database
from repositories.tovar_repo import TovarRepo
from repositories.zakaznik_repo import ZakaznikRepo
from repositories.objednavka_repo import ObjednavkaRepo
from repositories.pouzivatel_repo import PouzivatelRepo


class BufetApp:
    def __init__(self, db_path: str = "data/bufet.db"):
        self.db = Database(db_path)
        self.tovar_repo = TovarRepo(self.db)
        self.zakaznik_repo = ZakaznikRepo(self.db)
        self.objednavka_repo = ObjednavkaRepo(self.db)
        self.pouzivatel_repo = PouzivatelRepo(self.db)
        self._init_tables()

    def _init_tables(self):
        self.tovar_repo.create_table()
        self.zakaznik_repo.create_table()
        self.objednavka_repo.create_table()
        self.pouzivatel_repo.create_table()

    def close(self):
        self.db.close()


if __name__ == "__main__":
    app = BufetApp()
    print("Bufet app started. DB ready.")
    app.close()