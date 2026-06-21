import sqlite3
import shutil
import os


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection = None
        self._connect()
        self._enable_foreign_keys()

    def _connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row

    def _enable_foreign_keys(self):
        self._connection.execute("PRAGMA foreign_keys = ON")

    def get_connection(self) -> sqlite3.Connection:
        return self._connection

    def get_cursor(self) -> sqlite3.Cursor:
        return self._connection.cursor()

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def save(self, filepath: str):
        """Save current database to a file (backup)."""
        self.commit()
        shutil.copy2(self.db_path, filepath)

    def load(self, filepath: str):
        """Load database from a file, replacing current state."""
        self.close()
        shutil.copy2(filepath, self.db_path)
        self._connect()
        self._enable_foreign_keys()