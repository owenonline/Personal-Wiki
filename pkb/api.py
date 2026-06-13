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
