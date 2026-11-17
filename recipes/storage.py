"""Сохранение снимков расчётов в SQLite."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class CalculationStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        try:
            with self._connection:
                self._connection.execute("""
                    CREATE TABLE IF NOT EXISTS calculations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                """)
        except sqlite3.Error:
            self._connection.close()
            raise

    def save(self, recipe):
        payload = json.dumps(recipe.snapshot(), ensure_ascii=False)
        with self._connection:
            cursor = self._connection.execute(
                "INSERT INTO calculations (created_at, payload) VALUES (?, ?)",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), payload),
            )
        return cursor.lastrowid

    @staticmethod
    def _decode(row):
        result = json.loads(row["payload"])
        result.update(id=row["id"], created_at=row["created_at"])
        return result

    def history(self, limit=20):
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("Лимит истории: целое число от 1 до 1000.")
        rows = self._connection.execute(
            "SELECT * FROM calculations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._decode(row) for row in rows]

    def get(self, calculation_id):
        row = self._connection.execute(
            "SELECT * FROM calculations WHERE id = ?", (calculation_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Расчёт №{calculation_id} не найден.")
        return self._decode(row)

    def close(self):
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __len__(self):
        return self._connection.execute("SELECT COUNT(*) FROM calculations").fetchone()[0]

    def __str__(self):
        return f"История расчётов: {self.path}"
