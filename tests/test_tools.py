import pytest

from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.store import query_select
from pkb.tools import AgentContext, make_context


def _ctx(vault) -> AgentContext:
    ensure_repo(vault)
    settings = get_settings(vault)
    settings.wiki_dir.mkdir(exist_ok=True)
    settings.inbox_dir.mkdir(exist_ok=True)
    conn = connect(settings.db_path)
    init_db(conn)
    return make_context(conn, settings)


def test_record_event_inserts_and_commits(vault):
    ctx = _ctx(vault)
    res = ctx.record_event("workout_set", {"exercise": "bench", "weight": 135, "reps": 5})
    assert res["event_id"].startswith("evt_")
    rows = query_select(ctx.conn, "SELECT count(*) AS c FROM events")
    assert rows[0]["c"] == 1
    # committed
    import subprocess

    log = subprocess.run(
        ["git", "-C", str(vault), "log", "--oneline"], capture_output=True, text=True
    ).stdout
    assert "record_event" in log


def test_update_event_changes_status(vault):
    ctx = _ctx(vault)
    started = ctx.record_event("activity_session", {"name": "workout", "status": "in_progress"})
    ctx.update_event(started["event_id"], {"status": "done"})
    rows = query_select(
        ctx.conn,
        "SELECT json_extract(payload,'$.status') AS s FROM events WHERE id=?",
        (started["event_id"],),
    )
    assert rows[0]["s"] == "done"


def test_describe_schema_reports_registered_fields(vault):
    ctx = _ctx(vault)
    ctx.record_event("mood", {"valence": -1, "note": "sluggish"})
    desc = ctx.describe_schema()
    assert "mood" in desc["event_kinds"]
    assert "tables" in desc


def test_query_runs_select(vault):
    ctx = _ctx(vault)
    ctx.record_event("workout_set", {"weight": 135})
    rows = ctx.query("SELECT count(*) AS c FROM events")
    assert rows[0]["c"] == 1


def test_query_rejects_non_select(vault):
    ctx = _ctx(vault)
    with pytest.raises(ValueError):
        ctx.query("DROP TABLE events")


def test_write_note_creates_page_index_log_and_commits(vault):
    ctx = _ctx(vault)
    res = ctx.write_note("ideas/llm-wiki.md", "LLM Wiki idea", "Build a second brain.", tags=["idea"])
    fm, body = ctx.read_note("ideas/llm-wiki.md")
    assert res["wiki_path"] == "ideas/llm-wiki.md"
    assert fm["tags"] == ["idea"]
    assert "second brain" in body
    assert "ideas/llm-wiki.md" in ctx.settings.index_path.read_text()
    assert "LLM Wiki idea" in ctx.settings.log_path.read_text()


def test_list_open_activities(vault):
    ctx = _ctx(vault)
    ctx.record_event("activity_session", {"name": "workout", "status": "in_progress"})
    assert len(ctx.list_open_activities()) == 1
