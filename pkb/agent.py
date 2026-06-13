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
    def write_note(rel_path: str, title: str, body: str, tags: list | None = None) -> dict:
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
