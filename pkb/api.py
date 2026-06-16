from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pkb import agent
from pkb import chat as chatstore
from pkb.home import build_home
from pkb.store import query_select
from pkb.tools import AgentContext


class CaptureRequest(BaseModel):
    text: str


class ChatRequest(BaseModel):
    text: str
    chat_id: str | None = None
    context: dict | None = None


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

    return app
