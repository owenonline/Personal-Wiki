from pkb.chat import (
    append_message,
    create_chat,
    get_chat,
    list_chats,
    mark_persistent,
)
from pkb.db import connect, init_db


def _conn(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    return conn


def test_create_and_get_chat(settings):
    conn = _conn(settings)
    cid = create_chat(conn, title="Workout review")
    chat = get_chat(conn, cid)
    assert chat["title"] == "Workout review"
    assert chat["ephemeral"] == 1
    assert chat["messages"] == []


def test_append_messages_with_tool_steps(settings):
    conn = _conn(settings)
    cid = create_chat(conn)
    append_message(conn, cid, "user", "log bench 135x5")
    append_message(
        conn, cid, "assistant", "Logged it.",
        tool_steps=[{"tool": "record_event", "input": {"kind": "workout_set"}}],
    )
    chat = get_chat(conn, cid)
    assert [m["role"] for m in chat["messages"]] == ["user", "assistant"]
    assert chat["messages"][1]["tool_steps"][0]["tool"] == "record_event"


def test_list_chats_excludes_ephemeral_by_default(settings):
    conn = _conn(settings)
    create_chat(conn, title="quick")
    keep = create_chat(conn, title="kept")
    mark_persistent(conn, keep)
    titles = {c["title"] for c in list_chats(conn)}
    assert titles == {"kept"}
    all_titles = {c["title"] for c in list_chats(conn, include_ephemeral=True)}
    assert all_titles == {"quick", "kept"}
