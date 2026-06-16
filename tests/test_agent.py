import os

import pytest

from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.schema_seed import seed_schema_md
from pkb.tools import make_context


def test_seed_schema_md_writes_once(vault):
    settings = get_settings(vault)
    seed_schema_md(settings)
    first = settings.schema_path.read_text()
    assert "record_event" in first
    settings.schema_path.write_text(first + "\nUSER EDIT\n")
    seed_schema_md(settings)  # must not overwrite an existing file
    assert "USER EDIT" in settings.schema_path.read_text()


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
    import json

    from pkb.agent import build_tools

    ctx = _ctx(vault)
    tools = {t.name: t for t in build_tools(ctx)}
    out = json.loads(tools["record_event"](kind="mood", payload={"valence": -1}))
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


@pytest.mark.skipif(
    not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AWS_API_KEY")),
    reason="needs ANTHROPIC_API_KEY or ANTHROPIC_AWS_API_KEY",
)
def test_run_live_against_real_api_files_a_workout(vault):
    from pkb.agent import run_live
    from pkb.llm import build_client

    ctx = _ctx(vault)
    run_live(
        ctx,
        "Starting a workout. Bench 135x5, 135x5, 155x3. Felt sluggish.",
        client=build_client(),
    )
    sets = ctx.query(
        "SELECT count(*) AS c FROM events WHERE kind LIKE '%set%'"
    )
    assert sets[0]["c"] >= 1


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
