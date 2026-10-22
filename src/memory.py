"""Historial de conversación por sesión (chat_id de Telegram o session_id del
widget web), persistido en SQLite para que sobreviva a reinicios del bot/API."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

MAX_HISTORY_MESSAGES = 12  # ~6 turnos de ida y vuelta (usuario + asistente)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


@contextmanager
def _connect():
    conn = sqlite3.connect(config.MEMORY_DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def append_turn(session_id: str, role: str, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat()),
        )


def get_history(session_id: str, limit: int = MAX_HISTORY_MESSAGES) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]
