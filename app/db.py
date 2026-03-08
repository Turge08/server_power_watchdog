from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from app.models import Event


class EventRepository:
    def __init__(self, sqlite_path: str):
        self.sqlite_path = sqlite_path
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    level TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def add_event(self, event: Event) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (ts, level, source, message) VALUES (?, ?, ?, ?)",
                (event.ts.isoformat(), event.level, event.source, event.message),
            )
            conn.commit()

    def recent_events(self, limit: int = 50) -> List[Event]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, level, source, message FROM events ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()

        return [
            Event(
                ts=datetime.fromisoformat(row["ts"]),
                level=row["level"],
                source=row["source"],
                message=row["message"],
            )
            for row in rows
        ]
