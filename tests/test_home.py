from pkb.config import get_settings
from pkb.db import connect, init_db
from pkb.gitops import ensure_repo
from pkb.home import build_home
from pkb.store import create_item, insert_event
from pkb.tools import make_context


def _ctx(vault):
    ensure_repo(vault)
    settings = get_settings(vault)
    settings.wiki_dir.mkdir(exist_ok=True)
    settings.inbox_dir.mkdir(exist_ok=True)
    conn = connect(settings.db_path)
    init_db(conn)
    return make_context(conn, settings)


def test_home_has_fixed_sections(vault):
    ctx = _ctx(vault)
    home = build_home(ctx)
    assert set(home.keys()) == {"ongoing", "goals", "metrics", "approvals"}
    assert home["metrics"] == []
    assert home["approvals"] == []


def test_ongoing_lists_open_activities(vault):
    ctx = _ctx(vault)
    insert_event(ctx.conn, "activity_session", {"name": "workout", "status": "in_progress"})
    insert_event(ctx.conn, "activity_session", {"name": "run", "status": "done"})
    home = build_home(ctx)
    assert len(home["ongoing"]) == 1
    assert home["ongoing"][0]["title"] == "workout"


def test_goals_lists_goal_items(vault):
    ctx = _ctx(vault)
    create_item(ctx.conn, "goal", "Squat 2x BW")
    create_item(ctx.conn, "hobby", "Guitar")
    create_item(ctx.conn, "concept", "Not a goal")  # excluded
    home = build_home(ctx)
    titles = {t["title"] for t in home["goals"]}
    assert titles == {"Squat 2x BW", "Guitar"}
