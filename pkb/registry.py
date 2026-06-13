from __future__ import annotations

import sqlite3


def register_field(
    conn: sqlite3.Connection,
    kind: str,
    field: str,
    type: str,
    unit: str | None = None,
    description: str | None = None,
) -> None:
    """Insert or update a (kind, field) entry in the schema registry."""
    conn.execute(
        """
        INSERT INTO event_kinds (kind, field, type, unit, description)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(kind, field) DO UPDATE SET
            type=excluded.type,
            unit=COALESCE(excluded.unit, event_kinds.unit),
            description=COALESCE(excluded.description, event_kinds.description)
        """,
        (kind, field, type, unit, description),
    )
    conn.commit()


def describe(conn: sqlite3.Connection) -> dict[str, list[dict]]:
    """Return {kind: [{field,type,unit,description}, ...]} for all kinds."""
    out: dict[str, list[dict]] = {}
    for r in conn.execute(
        "SELECT kind, field, type, unit, description FROM event_kinds "
        "ORDER BY kind, field"
    ):
        out.setdefault(r["kind"], []).append(dict(r))
    return out


def known_kinds(conn: sqlite3.Connection) -> list[str]:
    return [
        r["kind"]
        for r in conn.execute(
            "SELECT DISTINCT kind FROM event_kinds ORDER BY kind"
        )
    ]
