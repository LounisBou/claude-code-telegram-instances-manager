from unittest.mock import MagicMock

from src.telegram.keyboards import (
    _format_timestamp,
    build_project_keyboard,
    build_sessions_keyboard,
    build_tool_approval_keyboard,
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

    def test_session_started_uses_html_not_markdown(self):
        """Regression: session start must use HTML bold, not Markdown asterisks."""
        msg = format_session_started("my-project", 1)
        assert "<b>my-project</b>" in msg
        assert "*my-project*" not in msg

    def test_session_started_escapes_html(self):
        """Ensure HTML special chars in project names are escaped."""
        msg = format_session_started("<script>", 1)
        assert "&lt;script&gt;" in msg
        assert "<script>" not in msg.split("<b>")[1].split("</b>")[0] if "<b>" in msg else True

    def test_session_ended(self):
        msg = format_session_ended("my-project", 1)
        assert "my-project" in msg
        assert "ended" in msg.lower()

    def test_session_ended_uses_html_not_markdown(self):
        """Regression: session end must use HTML bold, not Markdown asterisks."""
        msg = format_session_ended("my-project", 1)
        assert "<b>my-project</b>" in msg
        assert "*my-project*" not in msg

    def test_history_entry(self):
        entry = {
            "id": 3,
            "project": "my-proj",
            "started_at": "2026-02-09T10:00:00",
            "ended_at": "2026-02-09T11:00:00",
            "status": "ended",
            "exit_code": 0,
        }
        msg = format_history_entry(entry)
        assert "⚪" in msg
        assert "<b>#3 my-proj</b>" in msg
        assert "ended" in msg.lower()

    def test_history_entry_no_end(self):
        entry = {
            "id": 5,
            "project": "my-proj",
            "started_at": "2026-02-09T10:00:00",
            "ended_at": None,
            "status": "active",
            "exit_code": None,
        }
        msg = format_history_entry(entry)
        assert "🟢" in msg
        assert "<b>#5 my-proj</b>" in msg
        assert "active" in msg.lower()

    def test_history_entry_uses_html_not_markdown(self):
        """Regression: history entry must use HTML bold, not Markdown asterisks."""
        entry = {
            "id": 1,
            "project": "my-proj",
            "started_at": "2026-02-09T10:00:00.123456+00:00",
            "ended_at": None,
            "status": "active",
            "exit_code": None,
        }
        msg = format_history_entry(entry)
        assert "<b>#1 my-proj</b>" in msg
        assert "*my-proj*" not in msg

    def test_history_entry_short_timestamps(self):
        """Regression: timestamps must be short, not raw ISO with microseconds."""
        entry = {
            "project": "my-proj",
            "started_at": "2026-02-09T10:02:35.958687+00:00",
            "ended_at": "2026-02-09T11:03:45.307838+00:00",
            "status": "ended",
            "exit_code": None,
        }
        msg = format_history_entry(entry)
        assert "2026-02-09 10:02" in msg
        assert "2026-02-09 11:03" in msg
        assert ".958687" not in msg
        assert "+00:00" not in msg

    def test_history_entry_escapes_html(self):
        """Project names with special chars must be HTML-escaped."""
        entry = {
            "id": 2,
            "project": "my<proj>&test",
            "started_at": "2026-02-09T10:00:00",
            "ended_at": None,
            "status": "active",
            "exit_code": None,
        }
        msg = format_history_entry(entry)
        assert "<b>#2 my&lt;proj&gt;&amp;test</b>" in msg


class TestFormatTimestamp:
    """Tests for the _format_timestamp helper."""

    def test_strips_microseconds_and_timezone(self):
        assert _format_timestamp("2026-02-09T10:02:35.958687+00:00") == "2026-02-09 10:02"

    def test_no_microseconds(self):
        assert _format_timestamp("2026-02-09T10:02:35+00:00") == "2026-02-09 10:02"

    def test_no_timezone(self):
        assert _format_timestamp("2026-02-09T10:02:35") == "2026-02-09 10:02"

    def test_z_timezone(self):
        assert _format_timestamp("2026-02-09T10:02:35Z") == "2026-02-09 10:02"

    def test_already_short(self):
        assert _format_timestamp("2026-02-09T10:02") == "2026-02-09 10:02"


class TestBuildToolApprovalKeyboard:
    """Tests for the tool approval inline keyboard builder."""

    def test_returns_allow_deny_buttons(self):
        keyboard = build_tool_approval_keyboard(session_id=1)
        assert len(keyboard) == 1  # one row
        assert len(keyboard[0]) == 2  # two buttons
        assert keyboard[0][0]["text"] == "Allow"
        assert keyboard[0][1]["text"] == "Deny"

    def test_callback_data_includes_session_id(self):
        keyboard = build_tool_approval_keyboard(session_id=42)
        assert keyboard[0][0]["callback_data"] == "tool:yes:42"
        assert keyboard[0][1]["callback_data"] == "tool:no:42"
