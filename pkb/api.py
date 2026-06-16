from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from pkb import agent
from pkb.home import build_home
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

    return app
