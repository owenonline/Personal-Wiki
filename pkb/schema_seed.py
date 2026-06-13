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
