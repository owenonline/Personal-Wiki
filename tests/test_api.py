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

    def fake_runner(ctx_, user_text, client, context=None):
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


def test_home_endpoint_shape(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    client.post("/capture", json={"text": "starting a workout"})
    resp = client.get("/api/home")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"ongoing", "goals", "metrics", "approvals"}
    assert len(body["ongoing"]) == 1


def test_wiki_page_endpoint(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    ctx.write_note("ideas/x.md", "X idea", "A neat idea.", tags=["idea"])
    resp = client.get("/api/wiki/page", params={"path": "ideas/x.md"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["frontmatter"]["title"] == "X idea"
    assert "neat idea" in body["body"]


def test_wiki_page_rejects_escape(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    resp = client.get("/api/wiki/page", params={"path": "../../etc/passwd"})
    assert resp.status_code == 400


def test_chat_creates_session_and_persists_messages(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    resp = client.post("/api/chat", json={"text": "starting a workout"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Started your workout."
    cid = body["chat_id"]
    got = client.get(f"/api/chats/{cid}").json()
    roles = [m["role"] for m in got["messages"]]
    assert roles == ["user", "assistant"]
    assert got["messages"][1]["tool_steps"][0]["tool"] == "record_event"


def test_chat_continues_existing_session(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    first = client.post("/api/chat", json={"text": "one"}).json()
    cid = first["chat_id"]
    client.post("/api/chat", json={"text": "two", "chat_id": cid})
    got = client.get(f"/api/chats/{cid}").json()
    assert len(got["messages"]) == 4  # 2 turns x (user+assistant)


def test_persist_then_listed(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)
    cid = client.post("/api/chat", json={"text": "keep me"}).json()["chat_id"]
    assert client.get("/api/chats").json() == []  # ephemeral by default
    client.post(f"/api/chats/{cid}/persist")
    listed = client.get("/api/chats").json()
    assert len(listed) == 1 and listed[0]["id"] == cid
