from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id               TEXT PRIMARY KEY,
    type             TEXT NOT NULL,
    title            TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'active',
    wiki_path        TEXT,
    parent_id        TEXT,
    estimated_minutes INTEGER,
    last_active_at   TEXT,
    attrs            TEXT NOT NULL DEFAULT '{}',
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS events (
    id        TEXT PRIMARY KEY,
    ts        TEXT NOT NULL DEFAULT (datetime('now')),
    kind      TEXT NOT NULL,
    item_id   TEXT,
    location  TEXT,
    payload   TEXT NOT NULL DEFAULT '{}',
    wiki_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_kind_ts ON events(kind, ts);

CREATE TABLE IF NOT EXISTS metrics (
    ts     TEXT NOT NULL,
    source TEXT NOT NULL,
    name   TEXT NOT NULL,
    value  REAL NOT NULL,
    unit   TEXT
);
CREATE INDEX IF NOT EXISTS idx_metrics_name_ts ON metrics(name, ts);

CREATE TABLE IF NOT EXISTS event_kinds (
    kind        TEXT NOT NULL,
    field       TEXT NOT NULL,
    type        TEXT NOT NULL,
    unit        TEXT,
    description TEXT,
    PRIMARY KEY (kind, field)
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
