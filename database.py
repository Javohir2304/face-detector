"""Odamlar va ularning yuz vektorlarini saqlovchi SQLite baza."""
import sqlite3
from pathlib import Path

import numpy as np

DB_PATH = Path(__file__).resolve().parent / "data" / "faces.db"
VECTOR_SIZE = 128

SCHEMA = """
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY,
    person_id INTEGER NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    vector BLOB NOT NULL,
    source TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


class FaceDatabase:
    def __init__(self, path=DB_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def add_embedding(self, name, vector, source=None):
        with self.conn:
            self.conn.execute("INSERT OR IGNORE INTO people (name) VALUES (?)", (name,))
            (person_id,) = self.conn.execute("SELECT id FROM people WHERE name = ?", (name,)).fetchone()
            self.conn.execute(
                "INSERT INTO embeddings (person_id, vector, source) VALUES (?, ?, ?)",
                (person_id, vector.astype(np.float32).tobytes(), source),
            )

    def list_people(self):
        """[(ism, saqlangan yuzlar soni)]"""
        return self.conn.execute(
            """SELECT p.name, COUNT(e.id) FROM people p
               LEFT JOIN embeddings e ON e.person_id = p.id
               GROUP BY p.id ORDER BY p.name"""
        ).fetchall()

    def delete_person(self, name):
        with self.conn:
            cursor = self.conn.execute("DELETE FROM people WHERE name = ?", (name,))
        return cursor.rowcount > 0

    def load_all(self):
        """(ismlar, vektorlar matritsasi): matritsaning har bir qatori bitta saqlangan yuz."""
        rows = self.conn.execute(
            "SELECT p.name, e.vector FROM embeddings e JOIN people p ON p.id = e.person_id"
        ).fetchall()
        if not rows:
            return [], np.empty((0, VECTOR_SIZE), dtype=np.float32)
        names = [name for name, _ in rows]
        matrix = np.stack([np.frombuffer(blob, dtype=np.float32) for _, blob in rows])
        return names, matrix
