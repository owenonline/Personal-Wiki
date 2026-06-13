from __future__ import annotations

import json
import sqlite3
from typing import Any

from pkb.ids import new_id
from pkb.registry import register_field


def _infer_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "number"
    return "text"


def create_item(
    conn: sqlite3.Connection,
    type: str,
    title: str,
    wiki_path: str | None = None,
    status: str = "active",
    estimated_minutes: int | None = None,
    parent_id: str | None = None,
    attrs: dict | None = None,
) -> str:
    iid = new_id("item")
    conn.execute(
        "INSERT INTO items (id, type, title, status, wiki_path, parent_id, "
        "estimated_minutes, attrs) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            iid,
            type,
            title,
            status,
            wiki_path,
            parent_id,
            estimated_minutes,
            json.dumps(attrs or {}),
        ),
    )
    conn.commit()
    return iid


def get_item(conn: sqlite3.Connection, item_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    return dict(row) if row else None


def update_item(conn: sqlite3.Connection, item_id: str, **fields: Any) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(
        f"UPDATE items SET {cols} WHERE id=?", (*fields.values(), item_id)
    )
    conn.commit()


def insert_event(
    conn: sqlite3.Connection,
    kind: str,
    payload: dict,
    item_id: str | None = None,
    location: str | None = None,
    wiki_path: str | None = None,
    ts: str | None = None,
) -> str:
    for field, value in payload.items():
        register_field(conn, kind, field, _infer_type(value))
    eid = new_id("evt")
    if ts is None:
        conn.execute(
            "INSERT INTO events (id, kind, item_id, location, payload, wiki_path) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (eid, kind, item_id, location, json.dumps(payload), wiki_path),
        )
    else:
        conn.execute(
            "INSERT INTO events (id, ts, kind, item_id, location, payload, wiki_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (eid, ts, kind, item_id, location, json.dumps(payload), wiki_path),
        )
    conn.commit()
    return eid


def update_event_payload(
    conn: sqlite3.Connection, event_id: str, changes: dict
) -> None:
    row = conn.execute(
        "SELECT payload FROM events WHERE id=?", (event_id,)
    ).fetchone()
    if row is None:
        raise KeyError(event_id)
    payload = json.loads(row["payload"])
    payload.update(changes)
    conn.execute(
        "UPDATE events SET payload=? WHERE id=?",
        (json.dumps(payload), event_id),
    )
    conn.commit()


def list_open_activities(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM events WHERE kind='activity_session' "
        "AND json_extract(payload,'$.status')='in_progress' ORDER BY ts DESC"
    )
    return [dict(r) for r in rows]


def insert_metric(
    conn: sqlite3.Connection,
    source: str,
    name: str,
    value: float,
    unit: str | None = None,
    ts: str | None = None,
) -> None:
    if ts is None:
        conn.execute(
            "INSERT INTO metrics (ts, source, name, value, unit) "
            "VALUES (datetime('now'), ?, ?, ?, ?)",
            (source, name, value, unit),
        )
    else:
        conn.execute(
            "INSERT INTO metrics (ts, source, name, value, unit) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts, source, name, value, unit),
        )
    conn.commit()


def query_select(
    conn: sqlite3.Connection, sql: str, params: tuple = ()
) -> list[dict]:
    """Run a read-only SELECT and return rows as dicts. Rejects anything else."""
    stripped = sql.strip().rstrip(";").lstrip("(")
    if not stripped[:6].lower() == "select":
        raise ValueError("query_select only permits SELECT statements")
    if ";" in stripped:
        raise ValueError("multiple statements are not allowed")
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
