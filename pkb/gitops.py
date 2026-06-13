from __future__ import annotations

import subprocess
from pathlib import Path


def _git(vault_dir: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(vault_dir), *args],
        capture_output=True,
        text=True,
    )


def ensure_repo(vault_dir: Path) -> None:
    """Initialize the vault as a git repo with a committer identity."""
    vault_dir.mkdir(parents=True, exist_ok=True)
    if not (vault_dir / ".git").is_dir():
        _git(vault_dir, "init", "-q")
    # Local identity so commits succeed in any environment.
    _git(vault_dir, "config", "user.name", "PKB Agent")
    _git(vault_dir, "config", "user.email", "pkb@localhost")


def commit_all(vault_dir: Path, message: str) -> str | None:
    """Stage everything and commit. Returns the commit sha, or None if the
    working tree was already clean (nothing to commit)."""
    _git(vault_dir, "add", "-A")
    status = _git(vault_dir, "status", "--porcelain")
    if not status.stdout.strip():
        return None
    _git(vault_dir, "commit", "-q", "-m", message)
    sha = _git(vault_dir, "rev-parse", "HEAD").stdout.strip()
    return sha or None
