from pkb.db import connect, init_db
from pkb.registry import describe, known_kinds, register_field


def _conn(settings):
    conn = connect(settings.db_path)
    init_db(conn)
    return conn


def test_register_and_describe(settings):
    conn = _conn(settings)
    register_field(conn, "workout_set", "weight", "number", unit="lb")
    register_field(conn, "workout_set", "reps", "int")
    desc = describe(conn)
    fields = {f["field"]: f for f in desc["workout_set"]}
    assert fields["weight"]["unit"] == "lb"
    assert fields["reps"]["type"] == "int"


def test_register_is_upsert(settings):
    conn = _conn(settings)
    register_field(conn, "mood", "valence", "int")
    register_field(conn, "mood", "valence", "int", description="-2..2")
    rows = describe(conn)["mood"]
    assert len(rows) == 1
    assert rows[0]["description"] == "-2..2"


def test_known_kinds(settings):
    conn = _conn(settings)
    register_field(conn, "workout_set", "reps", "int")
    register_field(conn, "mood", "valence", "int")
    assert set(known_kinds(conn)) == {"workout_set", "mood"}
