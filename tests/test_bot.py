from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot import (
    build_project_keyboard,
    build_sessions_keyboard,
    format_history_entry,
    format_session_ended,
    format_session_started,
    handle_callback_query,
    handle_exit,
    handle_git,
    handle_history,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_update_claude,
    is_authorized,
)
from src.project_scanner import Project


# --- Task 10.1: Helper functions ---


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


# --- Task 10.2: Command handlers ---


class TestHandleStart:
    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111]))
        }
        await handle_start(update, context)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()

    @pytest.mark.asyncio
    async def test_authorized_user_sees_projects(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        config.projects.root = "/tmp"
        config.projects.scan_depth = 1
        context.bot_data = {"config": config}
        with patch("src.bot.scan_projects") as mock_scan:
            mock_scan.return_value = [Project(name="proj", path="/a/proj")]
            await handle_start(update, context)
            update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_projects_found(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        config.projects.root = "/tmp"
        config.projects.scan_depth = 1
        context.bot_data = {"config": config}
        with patch("src.bot.scan_projects") as mock_scan:
            mock_scan.return_value = []
            await handle_start(update, context)
            call_text = update.message.reply_text.call_args[0][0]
            assert "no projects" in call_text.lower()


class TestHandleSessions:
    @pytest.mark.asyncio
    async def test_no_sessions(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(list_sessions=MagicMock(return_value=[]))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_sessions(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active" in call_text.lower()

    @pytest.mark.asyncio
    async def test_shows_sessions(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(session_id=1, project_name="proj")
        sm = MagicMock(
            list_sessions=MagicMock(return_value=[session]),
            get_active_session=MagicMock(return_value=session),
        )
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_sessions(update, context)
        update.message.reply_text.assert_called_once()


class TestHandleExit:
    @pytest.mark.asyncio
    async def test_no_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_exit(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active" in call_text.lower()

    @pytest.mark.asyncio
    async def test_kills_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(session_id=1, project_name="proj")
        sm = AsyncMock()
        sm.get_active_session = MagicMock(side_effect=[session, None])
        sm.kill_session = AsyncMock()
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_exit(update, context)
        sm.kill_session.assert_called_once_with(111, 1)


class TestHandleTextMessage:
    @pytest.mark.asyncio
    async def test_no_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "hello"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111])),
            "session_manager": MagicMock(
                get_active_session=MagicMock(return_value=None)
            ),
        }
        await handle_text_message(update, context)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active session" in call_text.lower()

    @pytest.mark.asyncio
    async def test_forwards_text_to_process(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "hello world"
        context = MagicMock()
        session = MagicMock()
        session.process.write = AsyncMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111])),
            "session_manager": MagicMock(
                get_active_session=MagicMock(return_value=session)
            ),
        }
        await handle_text_message(update, context)
        session.process.write.assert_called_once_with("hello world\n")

    @pytest.mark.asyncio
    async def test_unauthorized_ignored(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.text = "hello"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111])),
        }
        await handle_text_message(update, context)
        update.message.reply_text.assert_not_called()


# --- Task 10.3: Callback query handlers and remaining commands ---


class TestHandleSessionsAuth:
    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111]))
        }
        await handle_sessions(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()


class TestHandleExitAuth:
    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111]))
        }
        await handle_exit(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()


class TestHandleCallbackQuery:
    @pytest.mark.asyncio
    async def test_project_selection_creates_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "project:/a/my-project"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = AsyncMock()
        session = MagicMock(session_id=1, project_name="my-project")
        sm.create_session = AsyncMock(return_value=session)
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.bot.get_git_info", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = MagicMock(
                format=MagicMock(return_value="Branch: main")
            )
            await handle_callback_query(update, context)
            sm.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_switch_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "switch:2"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = MagicMock()
        sm.switch_session = MagicMock()
        session = MagicMock(session_id=2, project_name="proj")
        sm.get_active_session = MagicMock(return_value=session)
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        sm.switch_session.assert_called_once_with(111, 2)

    @pytest.mark.asyncio
    async def test_kill_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "kill:1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = AsyncMock()
        sm.kill_session = AsyncMock()
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        sm.kill_session.assert_called_once_with(111, 1)

    @pytest.mark.asyncio
    async def test_unauthorized_callback(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.callback_query.data = "project:/a/proj"
        update.callback_query.answer = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        context.bot_data = {"config": config}
        await handle_callback_query(update, context)
        update.callback_query.answer.assert_called_once_with("Not authorized")

    @pytest.mark.asyncio
    async def test_page_navigation(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "page:1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        config.projects.root = "/tmp"
        config.projects.scan_depth = 1
        context.bot_data = {"config": config, "session_manager": MagicMock()}
        with patch("src.bot.scan_projects") as mock_scan:
            mock_scan.return_value = [
                Project(name=f"p{i}", path=f"/a/p{i}") for i in range(12)
            ]
            await handle_callback_query(update, context)
            update.callback_query.edit_message_text.assert_called_once()


class TestHandleHistoryAuth:
    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111]))
        }
        await handle_history(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()


class TestHandleGitAuth:
    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111]))
        }
        await handle_git(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()


class TestHandleUpdateAuth:
    @pytest.mark.asyncio
    async def test_unauthorized(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111]))
        }
        await handle_update_claude(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()


class TestHandleHistory:
    @pytest.mark.asyncio
    async def test_shows_history(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        db = AsyncMock()
        db.list_sessions = AsyncMock(
            return_value=[
                {
                    "project": "p1",
                    "started_at": "2026-01-01",
                    "ended_at": "2026-01-02",
                    "status": "ended",
                    "exit_code": 0,
                }
            ]
        )
        context.bot_data = {"config": config, "db": db}
        await handle_history(update, context)
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_history(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        db = AsyncMock()
        db.list_sessions = AsyncMock(return_value=[])
        context.bot_data = {"config": config, "db": db}
        await handle_history(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no" in call_text.lower()


class TestHandleGit:
    @pytest.mark.asyncio
    async def test_shows_git_info(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(project_path="/a/proj")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.bot.get_git_info", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = MagicMock(
                format=MagicMock(return_value="Branch: main | No open PR")
            )
            await handle_git(update, context)
            update.message.reply_text.assert_called_once()
            assert "main" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_no_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_git(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active" in call_text.lower()


class TestHandleUpdateClaude:
    @pytest.mark.asyncio
    async def test_no_active_sessions_updates_directly(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(
            telegram=MagicMock(authorized_users=[111]),
            claude=MagicMock(update_command="echo updated"),
        )
        sm = MagicMock(has_active_sessions=MagicMock(return_value=False))
        context.bot_data = {"config": config, "session_manager": sm}
        with patch(
            "src.bot._run_update_command", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "Updated to v2.0"
            await handle_update_claude(update, context)
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_active_sessions_warns(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(
            has_active_sessions=MagicMock(return_value=True),
            active_session_count=MagicMock(return_value=2),
        )
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_update_claude(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "2" in call_text
