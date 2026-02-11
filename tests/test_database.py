# tests/test_database.py
import pytest
from datetime import datetime, timezone

from src.database import Database


@pytest.fixture
async def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


class TestDatabaseInitialize:
    """Regression: initialize() must create parent dir before connecting."""

    async def test_creates_missing_parent_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "dir"
        db_path = str(nested / "sessions.db")
        database = Database(db_path)
        await database.initialize()
        assert nested.exists()
        await database.close()

    async def test_works_when_dir_exists(self, tmp_path):
        db_path = str(tmp_path / "sessions.db")
        database = Database(db_path)
        await database.initialize()
        # Should not raise
        sessions = await database.list_sessions(user_id=1)
        assert sessions == []
        await database.close()


class TestDatabase:
    async def test_initialize_creates_table(self, db):
        sessions = await db.list_sessions(user_id=1)
        assert sessions == []

    async def test_create_session(self, db):
        session_id = await db.create_session(
            user_id=111,
            project="my-project",
            project_path="/home/user/dev/my-project",
        )
        assert isinstance(session_id, int)
        assert session_id > 0

    async def test_get_session(self, db):
        sid = await db.create_session(
            user_id=111, project="proj", project_path="/a/proj"
        )
        session = await db.get_session(sid)
        assert session["user_id"] == 111
        assert session["project"] == "proj"
        assert session["status"] == "active"
        assert session["ended_at"] is None

    async def test_end_session(self, db):
        sid = await db.create_session(
            user_id=111, project="proj", project_path="/a/proj"
        )
        await db.end_session(sid, exit_code=0, status="ended")
        session = await db.get_session(sid)
        assert session["status"] == "ended"
        assert session["exit_code"] == 0
        assert session["ended_at"] is not None

    async def test_end_session_crashed(self, db):
        sid = await db.create_session(
            user_id=111, project="proj", project_path="/a/proj"
        )
        await db.end_session(sid, exit_code=1, status="crashed")
        session = await db.get_session(sid)
        assert session["status"] == "crashed"
        assert session["exit_code"] == 1

    async def test_list_sessions_filters_by_user(self, db):
        await db.create_session(user_id=111, project="a", project_path="/a")
        await db.create_session(user_id=222, project="b", project_path="/b")
        sessions = await db.list_sessions(user_id=111)
        assert len(sessions) == 1
        assert sessions[0]["project"] == "a"

    async def test_list_sessions_ordered_by_most_recent(self, db):
        await db.create_session(user_id=111, project="first", project_path="/a")
        await db.create_session(user_id=111, project="second", project_path="/b")
        sessions = await db.list_sessions(user_id=111)
        assert sessions[0]["project"] == "second"
        assert sessions[1]["project"] == "first"

    async def test_get_nonexistent_session_returns_none(self, db):
        session = await db.get_session(999)
        assert session is None

    async def test_mark_active_sessions_lost(self, db):
        sid1 = await db.create_session(user_id=111, project="a", project_path="/a")
        sid2 = await db.create_session(user_id=111, project="b", project_path="/b")
        await db.end_session(sid1, exit_code=0, status="ended")
        lost = await db.mark_active_sessions_lost()
        assert len(lost) == 1
        assert lost[0]["id"] == sid2
        session = await db.get_session(sid2)
        assert session["status"] == "lost"
