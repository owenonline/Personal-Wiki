from fastapi.testclient import TestClient

from pkb.api import create_app
from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.schema_seed import seed_schema_md
from pkb.tools import make_context


def _client(vault, monkeypatch):
    ensure_repo(vault)
    settings = get_settings(vault)
    settings.wiki_dir.mkdir(exist_ok=True)
    settings.inbox_dir.mkdir(exist_ok=True)
    seed_schema_md(settings)
    conn = connect(settings.db_path)
    init_db(conn)
    ctx = make_context(conn, settings)

    import pkb.agent as agent

    def fake_runner(ctx_, user_text, client):
        ctx_.record_event("activity_session", {"name": "workout", "status": "in_progress"})
        return {"reply": "Started your workout.", "actions": [{"tool": "record_event", "input": {}}]}

    monkeypatch.setattr(agent, "_run_tool_runner", fake_runner)
    return TestClient(create_app(ctx, client=object())), ctx


def test_capture_returns_reply_and_actions(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    resp = client.post("/capture", json={"text": "starting a workout"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Started your workout."
    assert body["actions"][0]["tool"] == "record_event"


def test_open_activities_endpoint(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    client.post("/capture", json={"text": "starting a workout"})
    resp = client.get("/activities/open")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_items_endpoint_empty(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    resp = client.get("/items")
    assert resp.status_code == 200
    assert resp.json() == []
