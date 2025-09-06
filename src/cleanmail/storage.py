from __future__ import annotations

from datetime import datetime, timezone
import sqlite3
from typing import Iterable, Optional

from .models import Decision


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            message_id TEXT NOT NULL,
            action TEXT NOT NULL,
            by TEXT NOT NULL,
            reason TEXT,
            subject TEXT,
            sender TEXT
        );
        """
    )
    conn.commit()


def get_last_run(db_path: str) -> Optional[datetime]:
    """Return the timestamp of the last successful run, if available."""
    conn = _connect(db_path)
    try:
        _ensure_schema(conn)
        cur = conn.execute("SELECT value FROM meta WHERE key='last_run' LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None
    finally:
        conn.close()


def set_last_run(db_path: str, ts: datetime) -> None:
    """Persist the timestamp of the latest completed run."""
    conn = _connect(db_path)
    try:
        _ensure_schema(conn)
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('last_run', ?)\n"
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (ts.isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()


def append_audit_records(db_path: str, decisions: Iterable[Decision]) -> None:
    """Append decisions to an immutable audit log for traceability."""
    conn = _connect(db_path)
    try:
        _ensure_schema(conn)
        rows = [
            (
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
                d.message.id,
                d.action.value,
                d.by,
                d.reason,
                d.message.subject,
                d.message.from_addr,
            )
            for d in decisions
        ]
        conn.executemany(
            "INSERT INTO audit(ts, message_id, action, by, reason, subject, sender)\n"
            "VALUES(?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
