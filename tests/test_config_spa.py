from pathlib import Path

from pkb.config import get_settings


def test_spa_dir_none_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PKB_SPA_DIR", raising=False)
    assert get_settings(tmp_path).spa_dir is None


def test_spa_dir_from_env(monkeypatch, tmp_path):
    dist = tmp_path / "frontend" / "dist"
    monkeypatch.setenv("PKB_SPA_DIR", str(dist))
    s = get_settings(tmp_path)
    assert s.spa_dir == dist.resolve()
