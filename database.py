import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, path):
        self.path = Path(path)
        self._create()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _create(self):
        with self._connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    materia TEXT NOT NULL,
                    classe TEXT NOT NULL,
                    points REAL NOT NULL,
                    time_minutes REAL NOT NULL,
                    seed INTEGER
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS test_exercises (
                    test_id INTEGER NOT NULL,
                    exercise_id TEXT NOT NULL,
                    FOREIGN KEY(test_id) REFERENCES tests(id)
                )
            """)

    def get_recent_used_ids(self, limit_tests=3):
        if limit_tests <= 0:
            return set()
        with self._connect() as con:
            rows = con.execute(
                "SELECT id FROM tests ORDER BY id DESC LIMIT ?",
                (limit_tests,),
            ).fetchall()
            test_ids = [r[0] for r in rows]
            if not test_ids:
                return set()
            marks = ",".join("?" for _ in test_ids)
            rows = con.execute(
                f"SELECT DISTINCT exercise_id FROM test_exercises WHERE test_id IN ({marks})",
                test_ids,
            ).fetchall()
            return {r[0] for r in rows}

    def save_test(self, materia, classe, points, time_minutes, seed, exercise_ids):
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as con:
            cur = con.execute(
                "INSERT INTO tests(created_at,materia,classe,points,time_minutes,seed) VALUES(?,?,?,?,?,?)",
                (now, materia, classe, points, time_minutes, seed),
            )
            test_id = cur.lastrowid
            con.executemany(
                "INSERT INTO test_exercises(test_id,exercise_id) VALUES(?,?)",
                [(test_id, x) for x in exercise_ids],
            )
            return test_id

    def get_tests(self, limit=20):
        with self._connect() as con:
            return con.execute(
                "SELECT id,created_at,materia,classe,points,time_minutes,seed FROM tests ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()

    def clear_history(self):
        with self._connect() as con:
            con.execute("DELETE FROM test_exercises")
            con.execute("DELETE FROM tests")
