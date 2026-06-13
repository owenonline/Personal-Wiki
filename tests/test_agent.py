from pkb.config import get_settings
from pkb.schema_seed import seed_schema_md


def test_seed_schema_md_writes_once(vault):
    settings = get_settings(vault)
    seed_schema_md(settings)
    first = settings.schema_path.read_text()
    assert "record_event" in first
    settings.schema_path.write_text(first + "\nUSER EDIT\n")
    seed_schema_md(settings)  # must not overwrite an existing file
    assert "USER EDIT" in settings.schema_path.read_text()
