from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from pkb import agent
from pkb import chat as chatstore
from pkb.eventbus import EventBus
from pkb.home import build_home
from pkb.store import query_select
from pkb.tools import AgentContext


class CaptureRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    text: str
    chat_id: str | None = None
    context: dict | None = None


async def sse_stream(bus: EventBus):
    """Yield SSE `data:` frames for each event published to `bus`, until the
    consumer disconnects (the generator is cancelled/closed)."""
    q = await bus.subscribe()
    try:
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
    finally:
        bus.unsubscribe(q)


def create_app(ctx: AgentContext, client: Any, bus: EventBus | None = None) -> FastAPI:
    app = FastAPI(title="PKB")
    bus = bus or EventBus()

    @app.post("/capture")
    def capture(req: CaptureRequest) -> dict:
        result = agent.run_live(ctx, req.text, client=client)
        bus.publish({"type": "home_changed"})
        return result

    @app.get("/activities/open")
    def open_activities() -> list[dict]:
        return ctx.list_open_activities()

    @app.get("/items")
    def items() -> list[dict]:
        return query_select(ctx.conn, "SELECT * FROM items ORDER BY created_at DESC")

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

    @app.post("/api/chat")
    def chat(req: ChatRequest) -> dict:
        cid = req.chat_id or chatstore.create_chat(ctx.conn)
        chatstore.append_message(ctx.conn, cid, "user", req.text)
        result = agent.run_live(ctx, req.text, client=client, context=req.context)
        chatstore.append_message(
            ctx.conn, cid, "assistant", result["reply"],
            tool_steps=result.get("actions", []),
        )
        bus.publish({"type": "home_changed", "chat_id": cid})
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

    @app.get("/api/events")
    async def events() -> StreamingResponse:
        return StreamingResponse(sse_stream(bus), media_type="text/event-stream")

    return app
