from pkb.db import connect, init_db
from pkb.registry import describe
from pkb.store import (
    create_item,
    get_item,
    insert_event,
    insert_metric,
    list_open_activities,
    query_select,
    update_event_payload,
    update_item,
)


def _conn(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    return conn


def test_create_and_get_item(settings):
    conn = _conn(settings)
    iid = create_item(conn, "goal", "Squat 2x BW", wiki_path="wiki/goals/squat.md")
    item = get_item(conn, iid)
    assert item["type"] == "goal"
    assert item["wiki_path"] == "wiki/goals/squat.md"


def test_update_item_morphs_type(settings):
    conn = _conn(settings)
    iid = create_item(conn, "goal", "Learn guitar")
    update_item(conn, iid, type="hobby", status="active")
    assert get_item(conn, iid)["type"] == "hobby"


def test_insert_event_registers_payload_fields(settings):
    conn = _conn(settings)
    eid = insert_event(
        conn,
        "workout_set",
        {"exercise": "bench", "weight": 135, "reps": 5},
    )
    assert eid.startswith("evt_")
    fields = {f["field"] for f in describe(conn)["workout_set"]}
    assert fields == {"exercise", "weight", "reps"}


def test_update_event_payload_merges(settings):
    conn = _conn(settings)
    eid = insert_event(conn, "activity_session", {"name": "workout", "status": "in_progress"})
    update_event_payload(conn, eid, {"status": "done"})
    rows = query_select(
        conn,
        "SELECT json_extract(payload,'$.status') AS s FROM events WHERE id=?",
        (eid,),
    )
    assert rows[0]["s"] == "done"


def test_list_open_activities(settings):
    conn = _conn(settings)
    open_id = insert_event(conn, "activity_session", {"name": "workout", "status": "in_progress"})
    insert_event(conn, "activity_session", {"name": "run", "status": "done"})
    open_ids = {e["id"] for e in list_open_activities(conn)}
    assert open_ids == {open_id}


def test_query_select_rejects_writes(settings):
    conn = _conn(settings)
    import pytest

    with pytest.raises(ValueError):
        query_select(conn, "DELETE FROM items")


def test_insert_metric(settings):
    conn = _conn(settings)
    insert_metric(conn, "apple_health", "sleep_hours", 6.5, unit="h", ts="2026-06-12T07:00:00")
    rows = query_select(conn, "SELECT value FROM metrics WHERE name='sleep_hours'")
    assert rows[0]["value"] == 6.5
