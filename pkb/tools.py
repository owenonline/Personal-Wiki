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
