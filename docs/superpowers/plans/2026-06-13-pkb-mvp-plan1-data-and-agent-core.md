# PKB MVP — Plan 1: Data Layer + Agent Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the always-on box's data layer (markdown + SQLite + git, with a self-describing schema registry) and the agent service (single-entry tool-using loop over that data), testable end-to-end via an API/CLI with no UI.

**Architecture:** A Python package `pkb`. A configurable **vault directory** (a git repo) holds `wiki/` (markdown), `data.sqlite` (items/events/metrics/event_kinds), `inbox/`, `index.md`, `log.md`, `SCHEMA.md`. The agent is the **only writer**: it exposes a small tool surface (`record_event`, `update_event`, `query`, `describe_schema`, `write_note`, `read_note`, `list_open_activities`) to Claude via the Anthropic Python SDK's beta **tool runner**, and every filing op ends in one atomic git commit. A thin FastAPI app is the single entry point (`/capture` → LIVE agent run; read endpoints for the future UI). Plan 2 adds the web app on top.

**Tech Stack:** Python 3.11+, `anthropic` (Claude SDK, model `claude-opus-4-8`, adaptive thinking, beta tool runner), `fastapi` + `uvicorn`, `pyyaml` (frontmatter), `sqlite3` (stdlib), `git` via `subprocess`, `pytest` + `httpx` (TestClient).

---

## File Structure

```
pyproject.toml                 # package metadata + deps
pkb/
  __init__.py
  config.py                    # Settings (paths, model); get_settings()
  ids.py                       # new_id(prefix) helper
  db.py                        # connect(), init_db() — schema DDL
  registry.py                  # event_kinds: register_field, describe, known_kinds
  store.py                     # items/events/metrics data access
  gitops.py                    # ensure_repo, commit_all
  wiki.py                      # markdown read/write + frontmatter, log, index
  tools.py                     # AgentContext + pure tool logic functions
  agent.py                     # beta_tool wrappers + run_live + drain_inbox
  api.py                       # create_app(ctx) FastAPI
  main.py                      # env wiring + uvicorn entry
  schema_seed.py               # SCHEMA.md template + seeding
tests/
  conftest.py                  # tmp vault fixtures
  test_db.py
  test_registry.py
  test_store.py
  test_gitops.py
  test_wiki.py
  test_tools.py
  test_agent.py
  test_api.py
```

Each file has one responsibility. `tools.py` holds **pure logic** (takes a context, no SDK types) so it is unit-testable; `agent.py` wraps that logic as SDK tools and owns the LLM call. This keeps the non-deterministic LLM seam isolated to `agent.py` and `run_live`.

Each task is TDD: write the failing test, run it to confirm it fails, implement the minimal code, run it to confirm it passes, then pass the **merge gate** and commit. The rhythm is identical across tasks — run `pytest <path> -v`, then `git add <files> && git commit -m "<msg>"`.

**Merge gate (enforced on every task before the change is merged/committed):** the final step of each task is a gate, not just a commit. The implementing subagent MUST:
1. Confirm every behavior in that task's **Unit-test plan** (listed in the gate step) is covered by a passing test.
2. Run the **whole suite** — `pytest -v` — not just the task's file, and confirm **0 failures** and **0 errors** (skips are allowed only for tests explicitly marked `skipif` for a missing `ANTHROPIC_API_KEY`).
3. Paste/observe the actual pytest summary line (e.g. `N passed, M skipped`) as evidence — do not assert "tests pass" without the output.

Only when the gate is green does the subagent commit. A red or unrun gate means the task is not done and must not be merged.

---

### Task 1: Project scaffold + config

**Files:**
- Create: `pyproject.toml`
- Create: `pkb/__init__.py`
- Create: `pkb/config.py`
- Create: `pkb/ids.py`
- Create: `tests/conftest.py`
- Test: `tests/test_db.py` (placeholder import test first; real cases in Task 2)

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "pkb"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "anthropic>=0.69",
    "fastapi>=0.115",
    "uvicorn>=0.30",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["pkb*"]
```

- [ ] **Step 2: Create `pkb/__init__.py`** (empty)

```python
```

- [ ] **Step 3: Write `pkb/ids.py`**

```python
import uuid


def new_id(prefix: str) -> str:
    """Return a short unique id like 'evt_3f9a1c2b8d4e'."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
```

- [ ] **Step 4: Write `pkb/config.py`**

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-opus-4-8"


@dataclass(frozen=True)
class Settings:
    vault_dir: Path
    model: str = DEFAULT_MODEL

    @property
    def db_path(self) -> Path:
        return self.vault_dir / "data.sqlite"

    @property
    def wiki_dir(self) -> Path:
        return self.vault_dir / "wiki"

    @property
    def inbox_dir(self) -> Path:
        return self.vault_dir / "inbox"

    @property
    def schema_path(self) -> Path:
        return self.vault_dir / "SCHEMA.md"

    @property
    def index_path(self) -> Path:
        return self.vault_dir / "index.md"

    @property
    def log_path(self) -> Path:
        return self.vault_dir / "log.md"


def get_settings(vault_dir: Path | None = None) -> Settings:
    if vault_dir is None:
        vault_dir = Path(os.environ.get("PKB_VAULT_DIR", "./vault"))
    return Settings(vault_dir=Path(vault_dir).resolve())
```

- [ ] **Step 5: Write `tests/conftest.py`**

```python
import sqlite3
from pathlib import Path

import pytest

from pkb.config import Settings, get_settings


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """A fresh vault directory with the expected subdirs created."""
    (tmp_path / "wiki").mkdir()
    (tmp_path / "inbox").mkdir()
    return tmp_path


@pytest.fixture
def settings(vault: Path) -> Settings:
    return get_settings(vault)
```

- [ ] **Step 6: Write the scaffold smoke test** in `tests/test_db.py`

```python
from pkb.config import get_settings


def test_settings_paths_resolve(vault):
    s = get_settings(vault)
    assert s.db_path == vault.resolve() / "data.sqlite"
    assert s.wiki_dir == vault.resolve() / "wiki"
    assert s.model == "claude-opus-4-8"
```

- [ ] **Step 7: Install and run**

Run: `pip install -e ".[dev]" && pytest tests/test_db.py -v`
Expected: PASS (1 test).

- [ ] **Step 8: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `Settings` resolves `db_path`, `wiki_dir`, `inbox_dir`, `schema_path`, `index_path`, `log_path` under the vault dir.
- `Settings.model` defaults to `claude-opus-4-8`.

Gate: run `pytest -v` (whole suite). Expected summary: `1 passed`. Commit only if green.

```bash
git add pyproject.toml pkb/ tests/
git commit -m "feat: project scaffold, config, id helper"
```

---

### Task 2: SQLite schema (`db.py`)

**Files:**
- Create: `pkb/db.py`
- Test: `tests/test_db.py` (extend)

- [ ] **Step 1: Write failing tests** — append to `tests/test_db.py`

```python
from pkb.db import connect, init_db


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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.db'`.

- [ ] **Step 3: Write `pkb/db.py`**

```python
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
    conn = sqlite3.connect(db_path, check_same_thread=False)  # FastAPI dispatches on worker threads
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `init_db` creates the `items`, `events`, `metrics`, `event_kinds` tables.
- `init_db` is idempotent (re-running does not raise or duplicate data).
- `connect` returns dict-like rows (`row["col"]` access works).

Gate: run `pytest -v` (whole suite). Expected: all prior tests still pass + 4 new tests pass; `0 failed`. Commit only if green.

```bash
git add pkb/db.py tests/test_db.py
git commit -m "feat: sqlite schema (items/events/metrics/event_kinds)"
```

---

### Task 3: Schema registry (`registry.py`)

**Files:**
- Create: `pkb/registry.py`
- Test: `tests/test_registry.py`

- [ ] **Step 1: Write failing tests** — `tests/test_registry.py`

```python
from pkb.db import connect, init_db
from pkb.registry import describe, known_kinds, register_field


def _conn(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    return conn


def test_register_and_describe(settings):
    conn = _conn(settings)
    register_field(conn, "workout_set", "weight", "number", unit="lb")
    register_field(conn, "workout_set", "reps", "int")
    desc = describe(conn)
    fields = {f["field"]: f for f in desc["workout_set"]}
    assert fields["weight"]["unit"] == "lb"
    assert fields["reps"]["type"] == "int"


def test_register_is_upsert(settings):
    conn = _conn(settings)
    register_field(conn, "mood", "valence", "int")
    register_field(conn, "mood", "valence", "int", description="-2..2")
    rows = describe(conn)["mood"]
    assert len(rows) == 1
    assert rows[0]["description"] == "-2..2"


def test_known_kinds(settings):
    conn = _conn(settings)
    register_field(conn, "workout_set", "reps", "int")
    register_field(conn, "mood", "valence", "int")
    assert set(known_kinds(conn)) == {"workout_set", "mood"}
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.registry'`.

- [ ] **Step 3: Write `pkb/registry.py`**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_registry.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `register_field` + `describe` round-trip a kind's fields with `type`/`unit`.
- `register_field` is an upsert (re-registering a field updates, does not duplicate, and preserves prior `description` when not re-supplied).
- `known_kinds` returns the distinct kinds.

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + 3 new tests pass; `0 failed`. Commit only if green.

```bash
git add pkb/registry.py tests/test_registry.py
git commit -m "feat: self-describing schema registry (event_kinds)"
```

---

### Task 4: Data access (`store.py`)

**Files:**
- Create: `pkb/store.py`
- Test: `tests/test_store.py`

- [ ] **Step 1: Write failing tests** — `tests/test_store.py`

```python
from pkb.db import connect, init_db
from pkb.registry import describe
from pkb.store import (
    create_item,
    get_item,
    insert_event,
    insert_metric,
    list_open_activities,
    query_select,
    update_event_payload,
    update_item,
)


def _conn(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    return conn


def test_create_and_get_item(settings):
    conn = _conn(settings)
    iid = create_item(conn, "goal", "Squat 2x BW", wiki_path="wiki/goals/squat.md")
    item = get_item(conn, iid)
    assert item["type"] == "goal"
    assert item["wiki_path"] == "wiki/goals/squat.md"


def test_update_item_morphs_type(settings):
    conn = _conn(settings)
    iid = create_item(conn, "goal", "Learn guitar")
    update_item(conn, iid, type="hobby", status="active")
    assert get_item(conn, iid)["type"] == "hobby"


def test_insert_event_registers_payload_fields(settings):
    conn = _conn(settings)
    eid = insert_event(
        conn,
        "workout_set",
        {"exercise": "bench", "weight": 135, "reps": 5},
    )
    assert eid.startswith("evt_")
    fields = {f["field"] for f in describe(conn)["workout_set"]}
    assert fields == {"exercise", "weight", "reps"}


def test_update_event_payload_merges(settings):
    conn = _conn(settings)
    eid = insert_event(conn, "activity_session", {"name": "workout", "status": "in_progress"})
    update_event_payload(conn, eid, {"status": "done"})
    rows = query_select(
        conn,
        "SELECT json_extract(payload,'$.status') AS s FROM events WHERE id=?",
        (eid,),
    )
    assert rows[0]["s"] == "done"


def test_list_open_activities(settings):
    conn = _conn(settings)
    open_id = insert_event(conn, "activity_session", {"name": "workout", "status": "in_progress"})
    insert_event(conn, "activity_session", {"name": "run", "status": "done"})
    open_ids = {e["id"] for e in list_open_activities(conn)}
    assert open_ids == {open_id}


def test_query_select_rejects_writes(settings):
    conn = _conn(settings)
    import pytest

    with pytest.raises(ValueError):
        query_select(conn, "DELETE FROM items")


def test_insert_metric(settings):
    conn = _conn(settings)
    insert_metric(conn, "apple_health", "sleep_hours", 6.5, unit="h", ts="2026-06-12T07:00:00")
    rows = query_select(conn, "SELECT value FROM metrics WHERE name='sleep_hours'")
    assert rows[0]["value"] == 6.5
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.store'`.

- [ ] **Step 3: Write `pkb/store.py`**

```python
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
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_store.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `create_item` + `get_item` round-trip (type, wiki_path).
- `update_item` can morph an item's `type` (the open-schema invariant).
- `insert_event` auto-registers each payload field in `event_kinds`.
- `update_event_payload` merges changes (e.g. status → done).
- `list_open_activities` returns only in-progress `activity_session` events.
- `query_select` runs SELECTs and **rejects** non-SELECT statements (`ValueError`).
- `insert_metric` writes a queryable metric row.

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + 7 new tests pass; `0 failed`. Commit only if green.

```bash
git add pkb/store.py tests/test_store.py
git commit -m "feat: data access (items/events/metrics) with SELECT-only query guard"
```

---

### Task 5: Git operations (`gitops.py`)

**Files:**
- Create: `pkb/gitops.py`
- Test: `tests/test_gitops.py`

- [ ] **Step 1: Write failing tests** — `tests/test_gitops.py`

```python
import subprocess

from pkb.gitops import commit_all, ensure_repo


def test_ensure_repo_initializes(vault):
    ensure_repo(vault)
    assert (vault / ".git").is_dir()


def test_ensure_repo_is_idempotent(vault):
    ensure_repo(vault)
    ensure_repo(vault)  # must not raise
    assert (vault / ".git").is_dir()


def test_commit_all_returns_sha_then_none(vault):
    ensure_repo(vault)
    (vault / "note.md").write_text("hello")
    sha = commit_all(vault, "add note")
    assert sha and len(sha) >= 7
    # nothing changed since last commit
    assert commit_all(vault, "noop") is None


def test_commit_is_in_log(vault):
    ensure_repo(vault)
    (vault / "a.md").write_text("x")
    commit_all(vault, "msg one")
    log = subprocess.run(
        ["git", "-C", str(vault), "log", "--oneline"],
        capture_output=True,
        text=True,
    ).stdout
    assert "msg one" in log
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_gitops.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.gitops'`.

- [ ] **Step 3: Write `pkb/gitops.py`**

```python
from __future__ import annotations

import subprocess
from pathlib import Path


def _git(vault_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(vault_dir), *args],
        capture_output=True,
        text=True,
    )


def ensure_repo(vault_dir: Path) -> None:
    """Initialize the vault as a git repo with a committer identity."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    if not (vault_dir / ".git").is_dir():
        _git(vault_dir, "init", "-q")
    # Local identity so commits succeed in any environment.
    _git(vault_dir, "config", "user.name", "PKB Agent")
    _git(vault_dir, "config", "user.email", "pkb@localhost")


def commit_all(vault_dir: Path, message: str) -> str | None:
    """Stage everything and commit. Returns the commit sha, or None if the
    working tree was already clean (nothing to commit)."""
    _git(vault_dir, "add", "-A")
    status = _git(vault_dir, "status", "--porcelain")
    if not status.stdout.strip():
        return None
    _git(vault_dir, "commit", "-q", "-m", message)
    sha = _git(vault_dir, "rev-parse", "HEAD").stdout.strip()
    return sha or None
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_gitops.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `ensure_repo` initializes a git repo (`.git` exists) and is idempotent.
- `commit_all` returns a sha when there are changes, then `None` on a clean tree.
- The commit message appears in `git log`.

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + 4 new tests pass; `0 failed`. Commit only if green.

```bash
git add pkb/gitops.py tests/test_gitops.py
git commit -m "feat: git ensure_repo + atomic commit_all"
```

---

### Task 6: Markdown wiki I/O (`wiki.py`)

**Files:**
- Create: `pkb/wiki.py`
- Test: `tests/test_wiki.py`

- [ ] **Step 1: Write failing tests** — `tests/test_wiki.py`

```python
from pkb.wiki import append_log, read_page, upsert_index_entry, write_page


def test_write_and_read_page_roundtrip(settings):
    write_page(
        settings.wiki_dir,
        "goals/squat.md",
        {"id": "item_abc", "type": "goal"},
        "# Squat 2x BW\n\nBuild to a double-bodyweight squat.\n",
    )
    fm, body = read_page(settings.wiki_dir, "goals/squat.md")
    assert fm["id"] == "item_abc"
    assert "double-bodyweight" in body


def test_append_log_uses_parseable_prefix(settings):
    append_log(settings, "ingest", "Some Article")
    text = settings.log_path.read_text()
    assert text.startswith("## [")
    assert "ingest | Some Article" in text


def test_upsert_index_entry_is_idempotent(settings):
    upsert_index_entry(settings, "goals/squat.md", "Squat goal")
    upsert_index_entry(settings, "goals/squat.md", "Squat strength goal")
    text = settings.index_path.read_text()
    assert text.count("](goals/squat.md)") == 1  # one entry; link target appears once
    assert "Squat strength goal" in text
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_wiki.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.wiki'`.

- [ ] **Step 3: Write `pkb/wiki.py`**

```python
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from pkb.config import Settings


def write_page(
    wiki_dir: Path, rel_path: str, frontmatter: dict, body: str
) -> Path:
    path = wiki_dir / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(frontmatter, sort_keys=True).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n")
    return path


def read_page(wiki_dir: Path, rel_path: str) -> tuple[dict, str]:
    text = (wiki_dir / rel_path).read_text()
    if text.startswith("---\n"):
        _, fm_block, body = text.split("---\n", 2)
        return yaml.safe_load(fm_block) or {}, body.lstrip("\n")
    return {}, text


def append_log(settings: Settings, kind: str, title: str) -> None:
    line = f"## [{date.today().isoformat()}] {kind} | {title}\n"
    with settings.log_path.open("a") as f:
        f.write(line)


def upsert_index_entry(settings: Settings, rel_path: str, summary: str) -> None:
    """Maintain one '- [path](path) — summary' line per page in index.md."""
    path = settings.index_path
    lines = path.read_text().splitlines() if path.exists() else []
    entry = f"- [{rel_path}]({rel_path}) — {summary}"
    kept = [ln for ln in lines if f"]({rel_path})" not in ln]
    kept.append(entry)
    path.write_text("\n".join(kept) + "\n")
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_wiki.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `write_page` + `read_page` round-trip frontmatter and body.
- `append_log` writes a `## [YYYY-MM-DD] kind | title` parseable prefix.
- `upsert_index_entry` keeps exactly one line per page and updates its summary.

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + 3 new tests pass; `0 failed`. Commit only if green.

```bash
git add pkb/wiki.py tests/test_wiki.py
git commit -m "feat: markdown page I/O, log append, index upsert"
```

---

### Task 7: Tool logic + context (`tools.py`)

These are the pure functions the agent's tools wrap. Each filing tool ends in a git commit. `AgentContext` bundles the connection + settings.

**Files:**
- Create: `pkb/tools.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests** — `tests/test_tools.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.tools'`.

- [ ] **Step 3: Write `pkb/tools.py`**

```python
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from pkb import store, wiki
from pkb.config import Settings
from pkb.gitops import commit_all


@dataclass
class AgentContext:
    conn: sqlite3.Connection
    settings: Settings

    # --- structured data ---
    def record_event(
        self,
        kind: str,
        payload: dict,
        item_id: str | None = None,
        location: str | None = None,
    ) -> dict:
        eid = store.insert_event(
            self.conn, kind, payload, item_id=item_id, location=location
        )
        commit_all(self.settings.vault_dir, f"record_event {kind} {eid}")
        return {"event_id": eid, "kind": kind, "payload": payload}

    def update_event(self, event_id: str, changes: dict) -> dict:
        store.update_event_payload(self.conn, event_id, changes)
        commit_all(self.settings.vault_dir, f"update_event {event_id}")
        return {"event_id": event_id, "changes": changes}

    def list_open_activities(self) -> list[dict]:
        return store.list_open_activities(self.conn)

    # --- introspection + query ---
    def describe_schema(self) -> dict:
        from pkb.registry import describe

        tables = [
            r["name"]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        ]
        return {"tables": tables, "event_kinds": describe(self.conn)}

    def query(self, sql: str) -> list[dict]:
        return store.query_select(self.conn, sql)

    # --- knowledge (markdown) ---
    def write_note(
        self, rel_path: str, title: str, body: str, tags: list[str] | None = None
    ) -> dict:
        frontmatter = {"title": title, "tags": tags or []}
        wiki.write_page(self.settings.wiki_dir, rel_path, frontmatter, body)
        wiki.upsert_index_entry(self.settings, rel_path, title)
        wiki.append_log(self.settings, "note", title)
        commit_all(self.settings.vault_dir, f"write_note {rel_path}")
        return {"wiki_path": rel_path, "title": title}

    def read_note(self, rel_path: str) -> tuple[dict, str]:
        return wiki.read_page(self.settings.wiki_dir, rel_path)


def make_context(conn: sqlite3.Connection, settings: Settings) -> AgentContext:
    return AgentContext(conn=conn, settings=settings)
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_tools.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `record_event` inserts an event **and** produces a git commit (`record_event` in `git log`).
- `update_event` changes a session's status.
- `describe_schema` reports registered kinds + the `tables` list.
- `query` runs a SELECT; `query` raises `ValueError` on non-SELECT.
- `write_note` creates the page, the index entry, the log line, and commits.
- `list_open_activities` returns in-progress sessions.

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + 7 new tests pass; `0 failed`. Commit only if green.

```bash
git add pkb/tools.py tests/test_tools.py
git commit -m "feat: AgentContext tool logic (record/update/query/describe/note)"
```

---

### Task 8: SCHEMA.md seed (`schema_seed.py`)

**Files:**
- Create: `pkb/schema_seed.py`
- Test: `tests/test_agent.py` (the seed test; agent run tests added in Task 9... actually agent in this task)

We add the seed first because the agent's system prompt includes `SCHEMA.md`.

- [ ] **Step 1: Write failing test** — create `tests/test_agent.py`

```python
from pkb.config import get_settings
from pkb.schema_seed import seed_schema_md


def test_seed_schema_md_writes_once(vault):
    settings = get_settings(vault)
    seed_schema_md(settings)
    first = settings.schema_path.read_text()
    assert "record_event" in first
    settings.schema_path.write_text(first + "\nUSER EDIT\n")
    seed_schema_md(settings)  # must not overwrite an existing file
    assert "USER EDIT" in settings.schema_path.read_text()
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.schema_seed'`.

- [ ] **Step 3: Write `pkb/schema_seed.py`**

```python
from __future__ import annotations

from pkb.config import Settings

SCHEMA_TEMPLATE = """# PKB Schema & Conventions

You maintain a personal knowledge base: a markdown wiki plus a SQLite store.

## Tools
- `describe_schema()` — ALWAYS call first before querying or filing structured
  data, so you know which event kinds and fields already exist.
- `record_event(kind, payload, item_id?, location?)` — file ONE atomic fact as a
  flat event row (e.g. one workout set per call). Reuse existing kinds/fields
  from describe_schema; only introduce a new kind/field when nothing fits.
- `update_event(event_id, changes)` — e.g. flip a session's status to "done".
- `query(sql)` — read-only SELECT over the store. Use json_extract for payload.
- `write_note(rel_path, title, body, tags?)` — file prose knowledge in the wiki.
- `read_note(rel_path)` — read a wiki page.
- `list_open_activities()` — currently in-progress activity_session events.

## Conventions
- Activities: start one with record_event("activity_session",
  {"name": ..., "status": "in_progress"}); log child facts (e.g. "workout_set",
  "mood") with a "session" field pointing at the session event id; end with
  update_event(session_id, {"status": "done"}).
- Keep payloads flat. One row per atomic fact.
- After filing, briefly tell the user what you recorded so they can correct it.
"""


def seed_schema_md(settings: Settings) -> None:
    """Write the SCHEMA.md template only if it does not already exist."""
    if settings.schema_path.exists():
        return
    settings.schema_path.parent.mkdir(parents=True, exist_ok=True)
    settings.schema_path.write_text(SCHEMA_TEMPLATE)
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_agent.py -v`
Expected: PASS (1 test).

- [ ] **Step 5: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `seed_schema_md` writes a `SCHEMA.md` containing the tool conventions (`record_event`).
- `seed_schema_md` does **not** overwrite an existing `SCHEMA.md` (user edits survive).

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + 1 new test passes; `0 failed`. Commit only if green.

```bash
git add pkb/schema_seed.py tests/test_agent.py
git commit -m "feat: SCHEMA.md seed template"
```

---

### Task 9: Agent service (`agent.py`)

Wraps `AgentContext` methods as SDK tools, runs the tool runner, and collects tool calls (for receipts / tap-to-correct). The LLM call is isolated behind `_run_tool_runner`, which tests monkeypatch; a real integration test is skipped without an API key.

**Files:**
- Create: `pkb/agent.py`
- Test: `tests/test_agent.py` (extend)

- [ ] **Step 1: Write failing tests** — append to `tests/test_agent.py`

```python
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.tools import make_context


def _ctx(vault):
    ensure_repo(vault)
    settings = get_settings(vault)
    settings.wiki_dir.mkdir(exist_ok=True)
    settings.inbox_dir.mkdir(exist_ok=True)
    seed_schema_md(settings)
    conn = connect(settings.db_path)
    init_db(conn)
    return make_context(conn, settings)


def test_build_tools_record_event_executes(vault):
    from pkb.agent import build_tools

    ctx = _ctx(vault)
    tools = {t.name: t for t in build_tools(ctx)}  # SDK BetaFunctionTool exposes .name
    out = tools["record_event"](kind="mood", payload={"valence": -1})
    assert out["event_id"].startswith("evt_")
    assert ctx.query("SELECT count(*) AS c FROM events")[0]["c"] == 1


def test_system_prompt_includes_schema(vault):
    from pkb.agent import build_system_prompt

    ctx = _ctx(vault)
    prompt = build_system_prompt(ctx)
    assert "record_event" in prompt


def test_run_live_collects_actions(vault, monkeypatch):
    import pkb.agent as agent

    ctx = _ctx(vault)

    def fake_runner(ctx_, user_text, client):
        # Simulate the model deciding to file a mood event, then replying.
        ctx_.record_event("mood", {"valence": -1, "note": "tired"})
        return {
            "reply": "Logged that you felt tired.",
            "actions": [{"tool": "record_event", "input": {"kind": "mood"}}],
        }

    monkeypatch.setattr(agent, "_run_tool_runner", fake_runner)
    result = agent.run_live(ctx, "felt really tired today", client=object())
    assert result["reply"] == "Logged that you felt tired."
    assert result["actions"][0]["tool"] == "record_event"
    assert ctx.query("SELECT count(*) AS c FROM events")[0]["c"] == 1


def test_drain_inbox_processes_and_removes_files(vault, monkeypatch):
    import pkb.agent as agent

    ctx = _ctx(vault)
    (ctx.settings.inbox_dir / "001.txt").write_text("remember to read Dune")

    def fake_runner(ctx_, user_text, client):
        ctx_.write_note("lists/reading.md", "Reading list", user_text)
        return {"reply": "filed", "actions": []}

    monkeypatch.setattr(agent, "_run_tool_runner", fake_runner)
    processed = agent.drain_inbox(ctx, client=object())
    assert len(processed) == 1
    assert not (ctx.settings.inbox_dir / "001.txt").exists()
    assert (ctx.settings.wiki_dir / "lists/reading.md").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.agent'`.

- [ ] **Step 3: Write `pkb/agent.py`**

```python
from __future__ import annotations

import json
from typing import Any

from anthropic import beta_tool

from pkb.tools import AgentContext

BASE_PROMPT = (
    "You are the maintainer of the user's personal knowledge base. "
    "Turn the user's free text into the right structured events and/or wiki "
    "notes using your tools. Always call describe_schema() before filing "
    "structured data or writing a query, so you reuse existing kinds and "
    "fields. After filing, briefly state what you recorded.\n\n"
)


def build_system_prompt(ctx: AgentContext) -> str:
    schema_doc = (
        ctx.settings.schema_path.read_text()
        if ctx.settings.schema_path.exists()
        else ""
    )
    return BASE_PROMPT + schema_doc


def build_tools(ctx: AgentContext) -> list:
    """Return SDK tool callables bound to this context. Each is a thin wrapper
    over an AgentContext method; its name + docstring + signature define the
    schema the model sees."""

    @beta_tool
    def describe_schema() -> str:
        """Return the current tables and the event-kind registry (which event
        kinds and payload fields already exist). Call this before filing
        structured data or writing a query."""
        return json.dumps(ctx.describe_schema())

    @beta_tool
    def record_event(
        kind: str, payload: dict, item_id: str = "", location: str = ""
    ) -> dict:
        """File one atomic structured fact as a flat event row. `kind` is the
        event type (e.g. 'activity_session', 'workout_set', 'mood'); `payload`
        is a flat dict of fields. Reuse existing kinds/fields where possible."""
        return ctx.record_event(
            kind, payload, item_id=item_id or None, location=location or None
        )

    @beta_tool
    def update_event(event_id: str, changes: dict) -> dict:
        """Merge `changes` into an existing event's payload, e.g. set a
        session's status to 'done'."""
        return ctx.update_event(event_id, changes)

    @beta_tool
    def query(sql: str) -> str:
        """Run a read-only SELECT over the SQLite store and return rows as JSON.
        Use json_extract(payload, '$.field') to read event payload fields."""
        return json.dumps(ctx.query(sql))

    @beta_tool
    def write_note(rel_path: str, title: str, body: str, tags: list = []) -> dict:
        """Create or replace a markdown wiki page (prose knowledge). `rel_path`
        is relative to the wiki dir, e.g. 'lists/reading.md'."""
        return ctx.write_note(rel_path, title, body, tags=tags)

    @beta_tool
    def read_note(rel_path: str) -> str:
        """Read a wiki page; returns its frontmatter and body as JSON."""
        fm, body = ctx.read_note(rel_path)
        return json.dumps({"frontmatter": fm, "body": body})

    @beta_tool
    def list_open_activities() -> str:
        """Return currently in-progress activity_session events as JSON."""
        return json.dumps(ctx.list_open_activities())

    return [
        describe_schema,
        record_event,
        update_event,
        query,
        write_note,
        read_note,
        list_open_activities,
    ]


def _run_tool_runner(ctx: AgentContext, user_text: str, client: Any) -> dict:
    """Run the Anthropic beta tool runner. Returns {reply, actions}. Isolated so
    tests can monkeypatch it without an API key."""
    tools = build_tools(ctx)
    runner = client.beta.messages.tool_runner(
        model=ctx.settings.model,
        max_tokens=8000,
        thinking={"type": "adaptive"},
        system=build_system_prompt(ctx),
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


def run_live(ctx: AgentContext, user_text: str, client: Any) -> dict:
    """LIVE-mode entry point: process one piece of user text synchronously."""
    return _run_tool_runner(ctx, user_text, client)


def drain_inbox(ctx: AgentContext, client: Any) -> list[dict]:
    """Process each raw capture file in inbox/ through the agent, then remove
    it. Returns one result per file."""
    results: list[dict] = []
    for path in sorted(ctx.settings.inbox_dir.glob("*")):
        if not path.is_file():
            continue
        text = path.read_text()
        results.append(_run_tool_runner(ctx, text, client))
        path.unlink()
    return results
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_agent.py -v`
Expected: PASS (the seed test from Task 8 plus 5 new tests).

- [ ] **Step 5: Add a real integration test (skipped without a key)** — append to `tests/test_agent.py`

```python
import os

import pytest


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"), reason="needs ANTHROPIC_API_KEY"
)
def test_run_live_against_real_api_files_a_workout(vault):
    import anthropic

    from pkb.agent import run_live

    ctx = _ctx(vault)
    run_live(
        ctx,
        "Starting a workout. Bench 135x5, 135x5, 155x3. Felt sluggish.",
        client=anthropic.Anthropic(),
    )
    sets = ctx.query(
        "SELECT count(*) AS c FROM events WHERE kind LIKE '%set%'"
    )
    assert sets[0]["c"] >= 1
```

- [ ] **Step 6: Run the unit suite (integration test skips)**

Run: `pytest tests/test_agent.py -v`
Expected: PASS; the integration test reports SKIPPED.

- [ ] **Step 7: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `build_tools` returns callables; the `record_event` tool executes and inserts.
- `build_system_prompt` includes the seeded SCHEMA conventions.
- `run_live` returns `{reply, actions}` and the agent's tool calls actually mutate the store (verified via the monkeypatched `_run_tool_runner`).
- `drain_inbox` processes each inbox file and removes it after.
- The real-API integration test (`test_run_live_against_real_api_files_a_workout`) is present and marked `skipif` on missing `ANTHROPIC_API_KEY`.

Gate: run `pytest -v` (whole suite). Expected: all prior tests pass + the new agent tests pass, with the integration test reported **SKIPPED** (not failed) when no key is set; `0 failed`, `0 errors`. Commit only if green.

```bash
git add pkb/agent.py tests/test_agent.py
git commit -m "feat: agent service (tool wiring, run_live, drain_inbox)"
```

---

### Task 10: FastAPI app + entry point (`api.py`, `main.py`)

**Files:**
- Create: `pkb/api.py`
- Create: `pkb/main.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing tests** — `tests/test_api.py`

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pkb.api'`.

- [ ] **Step 3: Write `pkb/api.py`**

```python
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from pkb import agent
from pkb.store import query_select
from pkb.tools import AgentContext


class CaptureRequest(BaseModel):
    text: str


def create_app(ctx: AgentContext, client: Any) -> FastAPI:
    app = FastAPI(title="PKB")

    @app.post("/capture")
    def capture(req: CaptureRequest) -> dict:
        return agent.run_live(ctx, req.text, client=client)

    @app.get("/activities/open")
    def open_activities() -> list[dict]:
        return ctx.list_open_activities()

    @app.get("/items")
    def items() -> list[dict]:
        return query_select(ctx.conn, "SELECT * FROM items ORDER BY created_at DESC")

    return app
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/test_api.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Write `pkb/main.py`**

```python
from __future__ import annotations

import anthropic
import uvicorn

from pkb.api import create_app
from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.schema_seed import seed_schema_md
from pkb.tools import make_context


def build_app():
    settings = get_settings()
    ensure_repo(settings.vault_dir)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.inbox_dir.mkdir(parents=True, exist_ok=True)
    seed_schema_md(settings)
    conn = connect(settings.db_path)
    init_db(conn)
    ctx = make_context(conn, settings)
    return create_app(ctx, client=anthropic.Anthropic())


def main() -> None:
    uvicorn.run(build_app(), host="0.0.0.0", port=8787)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests; the one real-API integration test SKIPPED without a key).

- [ ] **Step 7: Manual smoke test (optional, needs a key)**

Run:
```bash
export ANTHROPIC_API_KEY=...   # if not already set
export PKB_VAULT_DIR=./vault
python -m pkb.main &
curl -s localhost:8787/capture -H 'content-type: application/json' \
  -d '{"text":"starting a workout. bench 135x5, 135x5, 155x3, felt sluggish"}' | python -m json.tool
curl -s localhost:8787/activities/open | python -m json.tool
git -C ./vault log --oneline
```
Expected: a JSON reply + actions; an open activity; commits in the vault repo.

- [ ] **Step 8: Merge gate, then commit**

**Unit-test plan (all must pass before merge):**
- `POST /capture` returns the agent's `{reply, actions}` (the `actions` list is the tap-to-correct payload).
- `GET /activities/open` reflects an open activity created via capture.
- `GET /items` returns `[]` on an empty store.

Final-task gate: run the **whole suite** — `pytest -v` — and confirm the full plan is green end to end: all tests across all 10 tasks pass, with only the real-API integration test SKIPPED when `ANTHROPIC_API_KEY` is unset; `0 failed`, `0 errors`. Commit only if green.

```bash
git add pkb/api.py pkb/main.py tests/test_api.py
git commit -m "feat: FastAPI app (/capture, read endpoints) + uvicorn entry"
```

---

## Self-Review

**Spec coverage (against the design doc's MVP "spine"):**
- Repo skeleton (`wiki/`, `data.sqlite`, `inbox/`, `index.md`, `log.md`, `SCHEMA.md`) — Tasks 1, 2, 6, 8, 10 (`main.build_app` creates dirs + seeds).
- SQLite items/events/metrics + `event_kinds` registry — Tasks 2, 3.
- Agent service, single smart entry, LIVE + BACKGROUND, tool surface, registry read/extend/query — Tasks 7, 9 (`run_live` = LIVE, `drain_inbox` = BACKGROUND; `record_event` auto-registers fields; `describe_schema`/`query` read the registry).
- Activity/workout hero flow (start → log sets/feeling → tap-to-correct data) — supported by `record_event`/`update_event`/`list_open_activities` and the `actions` list returned from `/capture` (the tap-to-correct payload); end-to-end exercised by the real-API integration test in Task 9.
- Knowledge capture (note → markdown page → index/log) — Tasks 6, 7, 9.
- Conversational query over both stores — `query` tool + the agent (Task 9).
- Git-backed undo (every filing = one atomic commit) — Task 5, called by every filing tool in Task 7.
- API entry point for the future web app — Task 10.

Deferred to Plan 2 (web app) and later add-ons, per the design doc — correctly out of scope here: device-native UI, objective-scheduling home screen, Apple Health, Linear, weekly reviews, background planners, lint/reconcile.

**Placeholder scan:** none — every step has complete code and concrete commands.

**Type/signature consistency:** `AgentContext` method names used in `agent.py`/`api.py` match Task 7 (`record_event`, `update_event`, `query`, `describe_schema`, `write_note`, `read_note`, `list_open_activities`). `store.insert_event`/`update_event_payload`/`query_select` signatures match their callers. `register_field(conn, kind, field, type, unit, description)` is called consistently. `Settings` properties (`db_path`, `wiki_dir`, `inbox_dir`, `schema_path`, `index_path`, `log_path`, `model`, `vault_dir`) match every use. `_run_tool_runner(ctx, user_text, client)` is the single monkeypatch seam used by all agent/API tests.

**Open items intentionally left for implementation discretion:** exact `max_tokens` for the agent (8000 chosen as a safe default), and the precise wording of `SCHEMA.md` (will co-evolve with use, per the Karpathy pattern).
