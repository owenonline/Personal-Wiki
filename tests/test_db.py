from pkb.config import get_settings
from pkb.db import connect, init_db


def test_settings_paths_resolve(vault):
    s = get_settings(vault)
    assert s.db_path == vault.resolve() / "data.sqlite"
    assert s.wiki_dir == vault.resolve() / "wiki"
    assert s.model == "claude-opus-4-8"


def test_init_db_creates_tables(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    names = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"items", "events", "metrics", "event_kinds"} <= names


def test_init_db_is_idempotent(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    init_db(conn)  # must not raise
    assert conn.execute("SELECT count(*) AS c FROM items").fetchone()["c"] == 0


def test_rows_are_dict_like(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    conn.execute(
        "INSERT INTO items (id, type, title) VALUES ('i1', 'goal', 'Squat 2x BW')"
    )
    row = conn.execute("SELECT * FROM items WHERE id='i1'").fetchone()
    assert row["title"] == "Squat 2x BW"


def test_init_db_creates_chat_tables(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    names = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"chats", "chat_messages"} <= names


def test_chat_tables_columns(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    conn.execute("INSERT INTO chats (id, title) VALUES ('c1', 'First')")
    conn.execute(
        "INSERT INTO chat_messages (id, chat_id, role, content) "
        "VALUES ('m1', 'c1', 'user', 'hi')"
    )
    row = conn.execute("SELECT * FROM chat_messages WHERE id='m1'").fetchone()
    assert row["role"] == "user"
    assert row["tool_steps"] == "[]"
