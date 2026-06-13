from __future__ import annotations

import uvicorn

from pkb.api import create_app
from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.llm import build_client
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
    return create_app(ctx, client=build_client())


def main() -> None:
    uvicorn.run(build_app(), host="0.0.0.0", port=8787)


if __name__ == "__main__":
    main()
