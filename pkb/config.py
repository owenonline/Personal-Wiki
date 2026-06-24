from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MODEL = "claude-opus-4-8"
# Lightweight model used for cheap auxiliary calls (e.g. naming a chat).
DEFAULT_TITLE_MODEL = "claude-haiku-4-5"


@dataclass(frozen=True)
class Settings:
    vault_dir: Path
    model: str = DEFAULT_MODEL
    title_model: str = DEFAULT_TITLE_MODEL
    spa_dir: Path | None = None  # built SPA dist/ to serve (set by main once built)

    @property
    def db_path(self) -> Path:
        return self.vault_dir / "data.sqlite"

    @property
    def wiki_dir(self) -> Path:
        return self.vault_dir / "wiki"

    @property
    def inbox_dir(self) -> Path:
        return self.vault_dir / "inbox"

    @property
    def schema_path(self) -> Path:
        return self.vault_dir / "SCHEMA.md"

    @property
    def index_path(self) -> Path:
        return self.vault_dir / "index.md"

    @property
    def log_path(self) -> Path:
        return self.vault_dir / "log.md"


def get_settings(vault_dir: Path | None = None) -> Settings:
    if vault_dir is None:
        vault_dir = Path(os.environ.get("PKB_VAULT_DIR", "./vault"))
    spa_env = os.environ.get("PKB_SPA_DIR")
    spa_dir = Path(spa_env).resolve() if spa_env else None
    return Settings(vault_dir=Path(vault_dir).resolve(), spa_dir=spa_dir)
