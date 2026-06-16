from __future__ import annotations

import json
import sqlite3

from pkb.ids import new_id


def create_chat(conn: sqlite3.Connection, title: str | None = None,
                ephemeral: bool = True) -> str:
    cid = new_id("chat")
    conn.execute(
        "INSERT INTO chats (id, title, ephemeral) VALUES (?, ?, ?)",
        (cid, title, 1 if ephemeral else 0),
    )
    conn.commit()
    return cid


def append_message(conn: sqlite3.Connection, chat_id: str, role: str,
                   content: str, tool_steps: list | None = None) -> str:
    mid = new_id("msg")
    conn.execute(
        "INSERT INTO chat_messages (id, chat_id, role, content, tool_steps) "
        "VALUES (?, ?, ?, ?, ?)",
        (mid, chat_id, role, content, json.dumps(tool_steps or [])),
    )
    conn.commit()
    return mid


def mark_persistent(conn: sqlite3.Connection, chat_id: str) -> None:
    conn.execute("UPDATE chats SET ephemeral=0 WHERE id=?", (chat_id,))
    conn.commit()


def list_chats(conn: sqlite3.Connection, include_ephemeral: bool = False) -> list[dict]:
    sql = "SELECT * FROM chats"
    if not include_ephemeral:
        sql += " WHERE ephemeral=0"
    sql += " ORDER BY created_at DESC"
    return [dict(r) for r in conn.execute(sql)]


def get_chat(conn: sqlite3.Connection, chat_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
    if row is None:
        return None
    chat = dict(row)
    chat["messages"] = [
        {**dict(m), "tool_steps": json.loads(m["tool_steps"])}
        for m in conn.execute(
            "SELECT * FROM chat_messages WHERE chat_id=? ORDER BY rowid",
            (chat_id,),
        )
    ]
    return chat
