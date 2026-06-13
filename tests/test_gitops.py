import subprocess

from pkb.gitops import commit_all, ensure_repo


def test_ensure_repo_initializes(vault):
    ensure_repo(vault)
    assert (vault / ".git").is_dir()


def test_ensure_repo_is_idempotent(vault):
    ensure_repo(vault)
    ensure_repo(vault)  # must not raise
    assert (vault / ".git").is_dir()


def test_commit_all_returns_sha_then_none(vault):
    ensure_repo(vault)
    (vault / "note.md").write_text("hello")
    sha = commit_all(vault, "add note")
    assert sha and len(sha) >= 7
    # nothing changed since last commit
    assert commit_all(vault, "noop") is None


def test_commit_is_in_log(vault):
    ensure_repo(vault)
    (vault / "a.md").write_text("x")
    commit_all(vault, "msg one")
    log = subprocess.run(
        ["git", "-C", str(vault), "log", "--oneline"],
        capture_output=True,
        text=True,
    ).stdout
    assert "msg one" in log
