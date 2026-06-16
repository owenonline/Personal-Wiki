# PKB Web Backend Extensions (Plan 2a) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Plan 1 FastAPI backend with the API surface the web SPA needs — a home-tiles feed, wiki read endpoints, persistent + context-aware chat, an in-process SSE event bus, and static hosting for the built SPA.

**Architecture:** Additive only — new SQLite tables (`chats`, `chat_messages`) via `CREATE TABLE IF NOT EXISTS`, new focused modules (`eventbus`, `chat`, `home`), a `context` hint threaded into the existing agent `run_live`, and new routes on the existing `create_app`. The agent/data core from Plan 1 is reused unchanged. No frontend in this plan; everything is testable with pytest + FastAPI `TestClient`.

**Tech Stack:** Python 3.11+, FastAPI + Starlette (`StreamingResponse` for SSE), `anthropic` SDK (reused via the monkeypatched `_run_tool_runner` seam), `sqlite3`, pytest + `httpx` TestClient. New deps: none.

---

## File Structure

```
pkb/
  db.py            # MODIFY: append chats / chat_messages tables to SCHEMA
  eventbus.py      # NEW: in-process async pub/sub for SSE
  chat.py          # NEW: chat session persistence (create/append/list/get/persist)
  home.py          # NEW: build the home-tiles feed from existing data
  agent.py         # MODIFY: run_live / _run_tool_runner accept optional `context`
  api.py           # MODIFY: home, wiki read, chat, SSE routes; accept a bus; static mount
  main.py          # MODIFY: construct an EventBus and pass it to create_app
tests/
  test_chat.py        # NEW
  test_eventbus.py    # NEW
  test_home.py        # NEW
  test_agent.py       # MODIFY: context-param test
  test_api.py         # MODIFY: new endpoint tests
```

Each task is TDD and ends in the **merge gate** (same convention as Plan 1): cover the listed behaviors, run the **whole suite** (`uv run pytest -v`, via `UV_CACHE_DIR="$TMPDIR/uv-cache"`; retry a uv command with the sandbox disabled if it hits a cache-permission error), confirm **0 failed / 0 errors** (the one live-API test stays SKIPPED without credentials), paste the pytest summary line, then commit. The Plan 1 suite currently stands at **40 passed, 1 skipped**; each task adds to that.

---

### Task 1: Chat + message tables (`db.py`)

**Files:**
- Modify: `pkb/db.py` (append to the `SCHEMA` string)
- Test: `tests/test_db.py` (extend)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_db.py`

```python
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
    assert row["tool_steps"] == "[]"  # default
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_db.py -v`
Expected: FAIL — `no such table: chats`.

- [ ] **Step 3: Append the tables to `SCHEMA` in `pkb/db.py`** (add to the end of the existing `SCHEMA` triple-quoted string, before the closing `"""`)

```sql

CREATE TABLE IF NOT EXISTS chats (
    id         TEXT PRIMARY KEY,
    title      TEXT,
    ephemeral  INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    chat_id    TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL DEFAULT '',
    tool_steps TEXT NOT NULL DEFAULT '[]',
    ts         TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_chat ON chat_messages(chat_id, ts);
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_db.py -v`
Expected: PASS.

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `init_db` creates `chats` + `chat_messages`; columns and the `tool_steps` default (`'[]'`) are correct; additive `IF NOT EXISTS` keeps `init_db` idempotent.
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 2 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/db.py tests/test_db.py
git commit -m "feat(web): chats + chat_messages tables"
```

---

### Task 2: Event bus (`eventbus.py`)

In-process async pub/sub. The SSE endpoint subscribes; request handlers publish after they change state. Single-process, single-loop (the app runs one uvicorn process).

**Files:**
- Create: `pkb/eventbus.py`
- Test: `tests/test_eventbus.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_eventbus.py`

```python
import asyncio

import pytest

from pkb.eventbus import EventBus


@pytest.mark.asyncio
async def test_subscriber_receives_published_event():
    bus = EventBus()
    q = await bus.subscribe()
    bus.publish({"type": "home_changed"})
    event = await asyncio.wait_for(q.get(), timeout=1)
    assert event["type"] == "home_changed"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery():
    bus = EventBus()
    q = await bus.subscribe()
    bus.unsubscribe(q)
    bus.publish({"type": "x"})
    assert q.empty()


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive():
    bus = EventBus()
    q1 = await bus.subscribe()
    q2 = await bus.subscribe()
    bus.publish({"type": "ping"})
    assert (await asyncio.wait_for(q1.get(), 1))["type"] == "ping"
    assert (await asyncio.wait_for(q2.get(), 1))["type"] == "ping"
```

- [ ] **Step 2: Add the async test dependency, then run to verify it fails**

`pytest-asyncio` is needed for `@pytest.mark.asyncio`. Add it to the dev extra in `pyproject.toml` (`dev = ["pytest>=8.0", "httpx>=0.27", "pytest-asyncio>=0.23"]`) and register the mode by appending to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Then: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv pip install -e ".[dev]" && UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_eventbus.py -v`
Expected: FAIL — `No module named 'pkb.eventbus'`.

- [ ] **Step 3: Write `pkb/eventbus.py`**

```python
from __future__ import annotations

import asyncio


class EventBus:
    """Minimal in-process pub/sub. Subscribers are asyncio.Queues; publish is
    sync (callable from request handlers) and fans out via put_nowait. Single
    uvicorn process / single event loop assumed."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def publish(self, event: dict) -> None:
        for q in list(self._subscribers):
            q.put_nowait(event)
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_eventbus.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** a subscriber receives a published event; unsubscribe stops delivery; multiple subscribers each receive. (`pytest-asyncio` added; `asyncio_mode=auto` set.)
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 3 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/eventbus.py tests/test_eventbus.py pyproject.toml
git commit -m "feat(web): in-process EventBus for SSE"
```

---

### Task 3: Chat persistence (`chat.py`)

**Files:**
- Create: `pkb/chat.py`
- Test: `tests/test_chat.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_chat.py`

```python
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
    eph = create_chat(conn, title="quick")
    keep = create_chat(conn, title="kept")
    mark_persistent(conn, keep)
    titles = {c["title"] for c in list_chats(conn)}
    assert titles == {"kept"}
    all_titles = {c["title"] for c in list_chats(conn, include_ephemeral=True)}
    assert all_titles == {"quick", "kept"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_chat.py -v`
Expected: FAIL — `No module named 'pkb.chat'`.

- [ ] **Step 3: Write `pkb/chat.py`**

```python
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
            "SELECT * FROM chat_messages WHERE chat_id=? ORDER BY rowid",  # insertion order (ts is same-second; id is random)
            (chat_id,),
        )
    ]
    return chat
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_chat.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** create+get round-trips (ephemeral default, empty messages); append stores role/content/tool_steps and get returns them parsed in order; `list_chats` hides ephemeral unless asked; `mark_persistent` flips the flag.
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 3 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/chat.py tests/test_chat.py
git commit -m "feat(web): chat session persistence"
```

---

### Task 4: Home-tiles feed (`home.py`)

Builds the ordered tile list from existing data: ongoing-activity tiles (Plan 1 `list_open_activities`) + goal tiles (items whose `type` is a tracked kind). Metric and approval tiles are empty lists for now (their data sources land in later add-ons/plans), but the shape is fixed so the SPA can render them.

**Files:**
- Create: `pkb/home.py`
- Test: `tests/test_home.py`

- [ ] **Step 1: Write the failing tests** — `tests/test_home.py`

```python
from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.home import build_home
from pkb.store import create_item, insert_event
from pkb.tools import make_context


def _ctx(vault):
    ensure_repo(vault)
    settings = get_settings(vault)
    settings.wiki_dir.mkdir(exist_ok=True)
    settings.inbox_dir.mkdir(exist_ok=True)
    conn = connect(settings.db_path)
    init_db(conn)
    return make_context(conn, settings)


def test_home_has_fixed_sections(vault):
    ctx = _ctx(vault)
    home = build_home(ctx)
    assert set(home.keys()) == {"ongoing", "goals", "metrics", "approvals"}
    assert home["metrics"] == []
    assert home["approvals"] == []


def test_ongoing_lists_open_activities(vault):
    ctx = _ctx(vault)
    insert_event(ctx.conn, "activity_session", {"name": "workout", "status": "in_progress"})
    insert_event(ctx.conn, "activity_session", {"name": "run", "status": "done"})
    home = build_home(ctx)
    assert len(home["ongoing"]) == 1
    assert home["ongoing"][0]["title"] == "workout"


def test_goals_lists_goal_items(vault):
    ctx = _ctx(vault)
    create_item(ctx.conn, "goal", "Squat 2x BW")
    create_item(ctx.conn, "hobby", "Guitar")
    create_item(ctx.conn, "concept", "Not a goal")  # excluded
    home = build_home(ctx)
    titles = {t["title"] for t in home["goals"]}
    assert titles == {"Squat 2x BW", "Guitar"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_home.py -v`
Expected: FAIL — `No module named 'pkb.home'`.

- [ ] **Step 3: Write `pkb/home.py`**

```python
from __future__ import annotations

import json

from pkb.store import list_open_activities
from pkb.tools import AgentContext

# Item types that represent trackable goals/objectives shown on the home screen.
GOAL_TYPES = ("goal", "skill", "hobby", "project")


def build_home(ctx: AgentContext) -> dict:
    """Return the home-tiles feed. Fixed sections so the SPA can always render;
    metrics/approvals are populated by later add-ons."""
    ongoing = [
        {
            "type": "ongoing",
            "id": e["id"],
            "title": json.loads(e["payload"]).get("name", "Activity"),
            "started_at": e["ts"],
        }
        for e in list_open_activities(ctx.conn)
    ]
    placeholders = ",".join("?" for _ in GOAL_TYPES)
    goals = [
        {
            "type": "goal",
            "id": r["id"],
            "title": r["title"],
            "status": r["status"],
            "wiki_path": r["wiki_path"],
        }
        for r in ctx.conn.execute(
            f"SELECT * FROM items WHERE type IN ({placeholders}) "
            "AND status='active' ORDER BY last_active_at IS NULL, last_active_at DESC",
            GOAL_TYPES,
        )
    ]
    return {"ongoing": ongoing, "goals": goals, "metrics": [], "approvals": []}
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_home.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `build_home` always returns the four sections with `metrics`/`approvals` empty; `ongoing` reflects open activities (name from payload); `goals` lists only active items of the tracked types.
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 3 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/home.py tests/test_home.py
git commit -m "feat(web): home-tiles feed (ongoing + goals)"
```

---

### Task 5: Context-aware chat (`agent.py`)

Thread an optional `context` hint through `run_live` / `_run_tool_runner` so the desktop "ask about what I'm viewing" feature is grounded. For a `wiki_page` context, the page body is injected as a system note before the user message.

**Files:**
- Modify: `pkb/agent.py` (`run_live`, `_run_tool_runner`, add a context-rendering helper)
- Test: `tests/test_agent.py` (extend)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_agent.py`

```python
def test_run_live_passes_context_to_runner(vault, monkeypatch):
    import pkb.agent as agent

    ctx = _ctx(vault)
    seen = {}

    def fake_runner(ctx_, user_text, client, context=None):
        seen["context"] = context
        return {"reply": "ok", "actions": []}

    monkeypatch.setattr(agent, "_run_tool_runner", fake_runner)
    agent.run_live(ctx, "why is this?", client=object(),
                   context={"type": "wiki_page", "path": "goals/squat.md"})
    assert seen["context"] == {"type": "wiki_page", "path": "goals/squat.md"}


def test_render_context_note_reads_wiki_page(vault):
    from pkb.agent import render_context_note

    ctx = _ctx(vault)
    ctx.write_note("goals/squat.md", "Squat", "Build to a 2x bodyweight squat.")
    note = render_context_note(ctx, {"type": "wiki_page", "path": "goals/squat.md"})
    assert "2x bodyweight squat" in note
    assert "goals/squat.md" in note


def test_render_context_note_none_is_empty(vault):
    from pkb.agent import render_context_note

    ctx = _ctx(vault)
    assert render_context_note(ctx, None) == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_agent.py -v`
Expected: FAIL — `cannot import name 'render_context_note'` / `run_live() got an unexpected keyword argument 'context'`.

- [ ] **Step 3: Edit `pkb/agent.py`**

Add the helper (near `build_system_prompt`):

```python
def render_context_note(ctx: AgentContext, context: dict | None) -> str:
    """Render an optional view-context hint into a system note. Currently
    supports {'type': 'wiki_page', 'path': ...}."""
    if not context:
        return ""
    if context.get("type") == "wiki_page":
        try:
            _fm, body = ctx.read_note(context["path"])
        except FileNotFoundError:
            return ""
        return (
            f"The user is currently viewing the wiki page '{context['path']}'. "
            f"Its content:\n\n{body}\n\nAnswer with this page in mind."
        )
    return ""
```

Change `_run_tool_runner` to accept and use `context` (add the param; prepend the note to `system`):

```python
def _run_tool_runner(ctx: AgentContext, user_text: str, client: Any,
                     context: dict | None = None) -> dict:
    tools = build_tools(ctx)
    system = build_system_prompt(ctx)
    note = render_context_note(ctx, context)
    if note:
        system = system + "\n\n" + note
    runner = client.beta.messages.tool_runner(
        model=ctx.settings.model,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": user_text}],
    )
    actions: list[dict] = []
    reply_parts: list[str] = []
    for message in runner:
        for block in message.content:
            if block.type == "tool_use":
                actions.append({"tool": block.name, "input": block.input})
            elif block.type == "text":
                reply_parts.append(block.text)
    return {"reply": "".join(reply_parts).strip(), "actions": actions}
```

Change `run_live` to forward `context`:

```python
def run_live(ctx: AgentContext, user_text: str, client: Any,
             context: dict | None = None) -> dict:
    """LIVE-mode entry point: process one piece of user text synchronously."""
    return _run_tool_runner(ctx, user_text, client, context=context)
```

(`drain_inbox` calls `_run_tool_runner(ctx, text, client)` — unchanged, `context` defaults to None.)

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_agent.py -v`
Expected: PASS (the 3 new tests plus all prior agent tests; the live-API test stays SKIPPED).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `run_live` forwards `context` to the runner; `render_context_note` reads the named wiki page into a note; `None`/missing context renders empty (and a missing page is tolerated).
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 3 new pass (1 skipped); 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/agent.py tests/test_agent.py
git commit -m "feat(web): context-aware run_live (view-grounded chat)"
```

---

### Task 6: Read endpoints — home & wiki (`api.py`)

**Files:**
- Modify: `pkb/api.py`
- Test: `tests/test_api.py` (extend)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_api.py`

```python
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
```

(The existing `_client` helper in `tests/test_api.py` already monkeypatches `pkb.agent._run_tool_runner` and builds a context whose `record_event` runs on capture.)

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: FAIL — 404 for `/api/home`.

- [ ] **Step 3: Edit `pkb/api.py`** — add imports and routes inside `create_app`

Add imports at the top:

```python
from fastapi import HTTPException

from pkb.home import build_home
```

Add routes inside `create_app(ctx, client)` (before `return app`):

```python
    @app.get("/api/home")
    def home() -> dict:
        return build_home(ctx)

    @app.get("/api/wiki/page")
    def wiki_page(path: str) -> dict:
        try:
            fm, body = ctx.read_note(path)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid path")
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="not found")
        return {"path": path, "frontmatter": fm, "body": body}

    @app.get("/api/wiki/index")
    def wiki_index() -> dict:
        p = ctx.settings.index_path
        return {"index": p.read_text() if p.exists() else ""}
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: PASS (3 new + prior).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `/api/home` returns the four-section feed reflecting an open activity; `/api/wiki/page` returns frontmatter+body for a real page; a traversal path is rejected with 400 (404 for a missing in-bounds page).
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 3 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/api.py tests/test_api.py
git commit -m "feat(web): /api/home and /api/wiki read endpoints"
```

---

### Task 7: Chat endpoints (`api.py`)

`POST /api/chat` runs the agent (LIVE), persists the user + assistant messages (with tool steps), and returns `{chat_id, reply, actions}`. `GET /api/chats` lists persistent chats; `GET /api/chats/{id}` returns a chat with messages; `POST /api/chats/{id}/persist` keeps an ephemeral chat.

**Files:**
- Modify: `pkb/api.py`
- Test: `tests/test_api.py` (extend)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_api.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: FAIL — 404 for `/api/chat`.

- [ ] **Step 3: Edit `pkb/api.py`** — add imports, a request model, and routes

Add imports:

```python
from pkb import chat as chatstore
```

Add a request model near `CaptureRequest`:

```python
class ChatRequest(BaseModel):
    text: str
    chat_id: str | None = None
    context: dict | None = None
```

Add routes inside `create_app` (before `return app`):

```python
    @app.post("/api/chat")
    def chat(req: ChatRequest) -> dict:
        cid = req.chat_id or chatstore.create_chat(ctx.conn)
        chatstore.append_message(ctx.conn, cid, "user", req.text)
        result = agent.run_live(ctx, req.text, client=client, context=req.context)
        chatstore.append_message(
            ctx.conn, cid, "assistant", result["reply"],
            tool_steps=result.get("actions", []),
        )
        return {"chat_id": cid, **result}

    @app.get("/api/chats")
    def chats() -> list[dict]:
        return chatstore.list_chats(ctx.conn)

    @app.get("/api/chats/{chat_id}")
    def chat_detail(chat_id: str) -> dict:
        c = chatstore.get_chat(ctx.conn, chat_id)
        if c is None:
            raise HTTPException(status_code=404, detail="no such chat")
        return c

    @app.post("/api/chats/{chat_id}/persist")
    def persist_chat(chat_id: str) -> dict:
        chatstore.mark_persistent(ctx.conn, chat_id)
        return {"chat_id": chat_id, "ephemeral": False}
```

- [ ] **Step 4: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: PASS (3 new + prior).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan:** `POST /api/chat` runs the agent, creates a session, and persists user+assistant messages (assistant carries tool steps); passing `chat_id` continues a session; chats are ephemeral until `/persist`, after which `GET /api/chats` lists them.
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 3 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/api.py tests/test_api.py
git commit -m "feat(web): chat endpoints (persisted, context-aware)"
```

---

### Task 8: SSE stream + publish on writes (`api.py`, `main.py`)

`create_app` accepts an `EventBus`; `GET /api/events` streams it as SSE; `/capture` and `/api/chat` publish a `home_changed` event so connected clients refresh.

**Files:**
- Modify: `pkb/api.py` (accept `bus`, SSE route, publish in capture/chat)
- Modify: `pkb/main.py` (construct a bus, pass it)
- Test: `tests/test_api.py` (extend)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_api.py`

```python
import json as _json


def test_capture_publishes_home_changed(vault, monkeypatch):
    import asyncio

    from pkb.eventbus import EventBus

    # Build an app with a real bus, reusing the monkeypatched runner from _client.
    client, ctx = _client(vault, monkeypatch)
    bus = EventBus()
    from pkb.api import create_app

    app = create_app(ctx, client=object(), bus=bus)
    from fastapi.testclient import TestClient

    c2 = TestClient(app)

    async def run():
        q = await bus.subscribe()
        c2.post("/capture", json={"text": "go"})
        return await asyncio.wait_for(q.get(), 1)

    event = asyncio.run(run())
    assert event["type"] == "home_changed"


def test_events_endpoint_streams_sse(vault, monkeypatch):
    from pkb.eventbus import EventBus
    from pkb.api import create_app
    from fastapi.testclient import TestClient

    client, ctx = _client(vault, monkeypatch)
    bus = EventBus()
    app = create_app(ctx, client=object(), bus=bus)
    c2 = TestClient(app)
    with c2.stream("GET", "/api/events") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: FAIL — `create_app() got an unexpected keyword argument 'bus'`.

- [ ] **Step 3: Edit `pkb/api.py`**

Add imports:

```python
import asyncio
import json

from fastapi.responses import StreamingResponse

from pkb.eventbus import EventBus
```

Change the signature and default-construct a bus when none is given:

```python
def create_app(ctx: AgentContext, client: Any, bus: EventBus | None = None) -> FastAPI:
    app = FastAPI(title="PKB")
    bus = bus or EventBus()
```

In the existing `/capture` handler, publish after running:

```python
    @app.post("/capture")
    def capture(req: CaptureRequest) -> dict:
        result = agent.run_live(ctx, req.text, client=client)
        bus.publish({"type": "home_changed"})
        return result
```

In the `/api/chat` handler (from Task 7), add `bus.publish({"type": "home_changed", "chat_id": cid})` right before `return`.

Add the SSE route (before `return app`):

```python
    @app.get("/api/events")
    async def events() -> StreamingResponse:
        async def stream():
            q = await bus.subscribe()
            try:
                while True:
                    event = await q.get()
                    yield f"data: {json.dumps(event)}\n\n"
            finally:
                bus.unsubscribe(q)
        return StreamingResponse(stream(), media_type="text/event-stream")
```

- [ ] **Step 4: Edit `pkb/main.py`** — construct and pass a bus

```python
from pkb.eventbus import EventBus
```

and in `build_app`, change the final line to:

```python
    return create_app(ctx, client=build_client(), bus=EventBus())
```

- [ ] **Step 5: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: PASS (2 new + prior).

- [ ] **Step 6: Merge gate, then commit**

**Unit-test plan:** `/capture` publishes a `home_changed` event to bus subscribers; `/api/events` responds `200` with `text/event-stream`; existing capture/chat behavior unchanged.
Gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — all prior + 2 new pass; 0 failed. Commit only if green; paste the summary line.

```bash
git add pkb/api.py pkb/main.py tests/test_api.py
git commit -m "feat(web): SSE /api/events + publish on writes"
```

---

### Task 9: Serve the built SPA (`api.py`)

Mount the SPA build at `/` when it exists, with a catch-all so client-side routes deep-link. `/api/*` keeps priority. The build itself comes from Plan 2b; this task only wires hosting and is a no-op until `dist/` exists.

**Files:**
- Modify: `pkb/api.py`
- Modify: `pkb/config.py` (a `spa_dir` setting)
- Test: `tests/test_api.py` (extend)

- [ ] **Step 1: Write the failing tests** — append to `tests/test_api.py`

```python
def test_spa_served_when_present(vault, monkeypatch, tmp_path):
    from pkb.api import create_app
    from fastapi.testclient import TestClient

    client, ctx = _client(vault, monkeypatch)
    spa = tmp_path / "dist"
    spa.mkdir()
    (spa / "index.html").write_text("<!doctype html><title>PKB</title>")
    app = create_app(ctx, client=object(), spa_dir=spa)
    c2 = TestClient(app)
    # API still works
    assert c2.get("/api/home").status_code == 200
    # SPA root and a deep link both return index.html
    assert "PKB" in c2.get("/").text
    assert "PKB" in c2.get("/some/client/route").text


def test_no_spa_dir_leaves_api_only(vault, monkeypatch):
    client, ctx = _client(vault, monkeypatch)  # built without spa_dir
    assert client.get("/api/home").status_code == 200
    assert client.get("/").status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: FAIL — `create_app() got an unexpected keyword argument 'spa_dir'`.

- [ ] **Step 3: Add `spa_dir` to `pkb/config.py`** — add a field + default

In the `Settings` dataclass add a field `spa_dir: Path | None = None`. (Place it after `model`.) No change to `get_settings` is required.

- [ ] **Step 4: Edit `pkb/api.py`** — accept `spa_dir`, mount a catch-all

Add import:

```python
from fastapi.responses import FileResponse
```

Change the signature:

```python
def create_app(ctx: AgentContext, client: Any, bus: EventBus | None = None,
               spa_dir: "Path | None" = None) -> FastAPI:
```

(Add `from pathlib import Path` at the top for the annotation.) Then, as the **last** thing before `return app`, register the SPA fallback so it doesn't shadow `/api/*`:

```python
    if spa_dir is not None:
        index = spa_dir / "index.html"

        @app.get("/{full_path:path}")
        def spa(full_path: str):
            candidate = (spa_dir / full_path)
            if full_path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)
```

- [ ] **Step 5: Edit `pkb/main.py`** — pass `settings.spa_dir`

In `build_app`, pass `spa_dir=settings.spa_dir` to `create_app(...)`. Document (a comment) that `PKB` will set `spa_dir` to the Vite `dist/` once Plan 2b builds it.

- [ ] **Step 6: Run to verify it passes**

Run: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest tests/test_api.py -v`
Expected: PASS (2 new + prior).

- [ ] **Step 7: Final merge gate, then commit**

**Unit-test plan:** with a `dist/` present, `/` and deep links return `index.html` while `/api/*` still works; with no `spa_dir`, the app is API-only (`/` → 404). Full plan green end to end.
Final gate: `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest -v` — the whole suite (Plan 1 + all Plan 2a tasks) green, 0 failed/0 errors, only the live-API test skipped. Commit only if green; paste the summary line.

```bash
git add pkb/api.py pkb/config.py pkb/main.py tests/test_api.py
git commit -m "feat(web): serve built SPA with client-route fallback"
```

---

## Self-Review

**Spec coverage (against the web-app spec's "Backend additions required"):**
- Tiles feed → Task 4 (`build_home`) + Task 6 (`/api/home`).
- Wiki read → Task 6 (`/api/wiki/page`, `/api/wiki/index`).
- Context-aware + persistent chat → Task 5 (context in `run_live`) + Task 3 (persistence) + Task 7 (chat endpoints).
- Approvals → **deliberately deferred to Plan 2d** (built with its Tier-3 UI); `build_home` returns an empty `approvals` list so the shape is stable now. Noted in the spec's "real-now vs later" section.
- Live updates (SSE) → Task 2 (`EventBus`) + Task 8 (`/api/events` + publish).
- Static hosting → Task 9.

**Placeholder scan:** none — every step has concrete code/commands. The empty `metrics`/`approvals` lists are intentional, spec-sanctioned seams, not placeholders.

**Type/signature consistency:** `create_app(ctx, client, bus=None, spa_dir=None)` is introduced additively across Tasks 8–9 and every test/`main.py` call matches. `run_live(ctx, text, client, context=None)` and `_run_tool_runner(..., context=None)` match across Tasks 5/7. `chatstore` functions (`create_chat`, `append_message`, `mark_persistent`, `list_chats`, `get_chat`) match Task 3 ↔ Task 7. `build_home(ctx)` returns the same four-section dict in Task 4 ↔ Task 6. The existing `tests/test_api.py::_client` helper (monkeypatches `_run_tool_runner`, returns `(client, ctx)`) is reused throughout.

**Note for the implementer:** Tasks 1–5 are independent modules (db, eventbus, chat, home, agent-context) and could run in parallel worktrees; Tasks 6–9 all modify `pkb/api.py` and must run sequentially after their dependencies.
