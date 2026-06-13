from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from pkb.config import Settings


def _safe_path(wiki_dir: Path, rel_path: str) -> Path:
    """Resolve rel_path under wiki_dir, refusing paths that escape it."""
    base = wiki_dir.resolve()
    path = (base / rel_path).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"rel_path escapes wiki dir: {rel_path!r}")
    return path


def write_page(
    wiki_dir: Path, rel_path: str, frontmatter: dict, body: str
) -> Path:
    path = _safe_path(wiki_dir, rel_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(frontmatter, sort_keys=True).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n")
    return path


def read_page(wiki_dir: Path, rel_path: str) -> tuple[dict, str]:
    text = _safe_path(wiki_dir, rel_path).read_text()
    if text.startswith("---\n"):
        _, fm_block, body = text.split("---\n", 2)
        return yaml.safe_load(fm_block) or {}, body.lstrip("\n")
    return {}, text


def append_log(settings: Settings, kind: str, title: str) -> None:
    line = f"## [{date.today().isoformat()}] {kind} | {title}\n"
    with settings.log_path.open("a") as f:
        f.write(line)


def upsert_index_entry(settings: Settings, rel_path: str, summary: str) -> None:
    """Maintain one '- [path](path) — summary' line per page in index.md."""
    path = settings.index_path
    lines = path.read_text().splitlines() if path.exists() else []
    entry = f"- [{rel_path}]({rel_path}) — {summary}"
    kept = [ln for ln in lines if f"]({rel_path})" not in ln]
    kept.append(entry)
    path.write_text("\n".join(kept) + "\n")
