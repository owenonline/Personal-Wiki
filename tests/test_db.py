from pkb.config import get_settings


def test_settings_paths_resolve(vault):
    s = get_settings(vault)
    assert s.db_path == vault.resolve() / "data.sqlite"
    assert s.wiki_dir == vault.resolve() / "wiki"
    assert s.model == "claude-opus-4-8"
