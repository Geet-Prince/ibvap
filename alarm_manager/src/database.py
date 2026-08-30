"""
alarm_manager/src/database.py
SQLite-based activity and event logger.
Owner: Prince
"""
from __future__ import annotations
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "events.db"


def get_connection() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            camera_id   TEXT,
            module      TEXT,
            track_id    TEXT,
            object_type TEXT,
            confidence  REAL,
            bbox        TEXT,
            attributes  TEXT,
            frame_id    INTEGER,
            score       INTEGER DEFAULT 0,
            created_at  TEXT
        );

        CREATE TABLE IF NOT EXISTS events (
            event_id        TEXT PRIMARY KEY,
            event_type      TEXT,
            severity        TEXT,
            camera_id       TEXT,
            track_id        TEXT,
            danger_score    INTEGER,
            snapshot_path   TEXT,
            module          TEXT,
            attributes      TEXT,
            status          TEXT DEFAULT 'new',
            created_at      TEXT
        );
    """)
    conn.commit()
    conn.close()


def log_activity(camera_id: str, module: str, track_id: str,
                 object_type: str, confidence: float, bbox: tuple,
                 attributes: dict, frame_id: int, score: int) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT INTO activity_log
            (camera_id, module, track_id, object_type, confidence,
             bbox, attributes, frame_id, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        camera_id, module, track_id, object_type, confidence,
        json.dumps(bbox), json.dumps(attributes), frame_id, score,
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()


def log_event(event_id: str, event_type: str, severity: str, camera_id: str,
              track_id: str, danger_score: int, snapshot_path: str,
              module: str, attributes: dict) -> None:
    conn = get_connection()
    conn.execute("""
        INSERT OR REPLACE INTO events
            (event_id, event_type, severity, camera_id, track_id,
             danger_score, snapshot_path, module, attributes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
    """, (
        event_id, event_type, severity, camera_id, track_id,
        danger_score, snapshot_path, module, json.dumps(attributes),
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()


def get_recent_events(limit: int = 50) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
