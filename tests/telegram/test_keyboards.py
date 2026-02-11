from unittest.mock import MagicMock

from src.telegram.keyboards import (
    build_project_keyboard,
    build_sessions_keyboard,
    format_history_entry,
    format_session_ended,
    format_session_started,
    is_authorized,
)
from src.project_scanner import Project


class TestIsAuthorized:
    def test_authorized_user(self):
        assert is_authorized(111, [111, 222]) is True

    def test_unauthorized_user(self):
        assert is_authorized(999, [111, 222]) is False

    def test_empty_allowlist(self):
        assert is_authorized(111, []) is False


class TestBuildProjectKeyboard:
    def test_creates_keyboard_from_projects(self):
        projects = [
            Project(name="alpha", path="/a/alpha"),
            Project(name="beta", path="/a/beta"),
        ]
        keyboard = build_project_keyboard(projects)
        assert len(keyboard) == 2
        assert keyboard[0][0]["text"] == "alpha"
        assert keyboard[0][0]["callback_data"] == "project:/a/alpha"

    def test_empty_projects(self):
        keyboard = build_project_keyboard([])
        assert keyboard == []

    def test_pagination_over_8_projects(self):
        projects = [Project(name=f"p{i}", path=f"/a/p{i}") for i in range(12)]
        keyboard = build_project_keyboard(projects, page=0, page_size=8)
        project_rows = [
            row
            for row in keyboard
            if any("project:" in btn.get("callback_data", "") for btn in row)
        ]
        nav_rows = [
            row
            for row in keyboard
            if any("page:" in btn.get("callback_data", "") for btn in row)
        ]
        assert len(project_rows) == 8
        assert len(nav_rows) == 1

    def test_pagination_page_2(self):
        projects = [Project(name=f"p{i}", path=f"/a/p{i}") for i in range(12)]
        keyboard = build_project_keyboard(projects, page=1, page_size=8)
        project_rows = [
            row
            for row in keyboard
            if any("project:" in btn.get("callback_data", "") for btn in row)
        ]
        # 4 remaining projects + 1 nav row with "< Prev"
        assert len(project_rows) == 4


class TestBuildSessionsKeyboard:
    def test_creates_session_buttons(self):
        sessions = [
            MagicMock(session_id=1, project_name="alpha"),
            MagicMock(session_id=2, project_name="beta"),
        ]
        keyboard = build_sessions_keyboard(sessions, active_id=1)
        assert len(keyboard) >= 2

    def test_marks_active_session(self):
        sessions = [MagicMock(session_id=1, project_name="alpha")]
        keyboard = build_sessions_keyboard(sessions, active_id=1)
        first_row_text = keyboard[0][0]["text"]
        assert "alpha" in first_row_text

    def test_empty_sessions(self):
        keyboard = build_sessions_keyboard([], active_id=None)
        assert keyboard == []


class TestFormatMessages:
    def test_session_started(self):
        msg = format_session_started("my-project", 1)
        assert "my-project" in msg
        assert "1" in msg

    def test_session_ended(self):
        msg = format_session_ended("my-project", 1)
        assert "my-project" in msg
        assert "ended" in msg.lower()

    def test_history_entry(self):
        entry = {
            "project": "my-proj",
            "started_at": "2026-02-09T10:00:00",
            "ended_at": "2026-02-09T11:00:00",
            "status": "ended",
            "exit_code": 0,
        }
        msg = format_history_entry(entry)
        assert "my-proj" in msg
        assert "ended" in msg.lower()

    def test_history_entry_no_end(self):
        entry = {
            "project": "my-proj",
            "started_at": "2026-02-09T10:00:00",
            "ended_at": None,
            "status": "active",
            "exit_code": None,
        }
        msg = format_history_entry(entry)
        assert "my-proj" in msg
        assert "active" in msg.lower()
