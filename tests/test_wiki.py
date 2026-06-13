from pkb.wiki import append_log, read_page, upsert_index_entry, write_page


def test_write_and_read_page_roundtrip(settings):
    write_page(
        settings.wiki_dir,
        "goals/squat.md",
        {"id": "item_abc", "type": "goal"},
        "# Squat 2x BW\n\nBuild to a double-bodyweight squat.\n",
    )
    fm, body = read_page(settings.wiki_dir, "goals/squat.md")
    assert fm["id"] == "item_abc"
    assert "double-bodyweight" in body


def test_append_log_uses_parseable_prefix(settings):
    append_log(settings, "ingest", "Some Article")
    text = settings.log_path.read_text()
    assert text.startswith("## [")
    assert "ingest | Some Article" in text


def test_upsert_index_entry_is_idempotent(settings):
    upsert_index_entry(settings, "goals/squat.md", "Squat goal")
    upsert_index_entry(settings, "goals/squat.md", "Squat strength goal")
    text = settings.index_path.read_text()
    assert text.count("](goals/squat.md)") == 1
    assert "Squat strength goal" in text
