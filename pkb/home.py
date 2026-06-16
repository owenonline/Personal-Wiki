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
