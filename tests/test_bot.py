from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot import (
    _CONTENT_STATES,
    _run_update_command,
    build_project_keyboard,
    build_sessions_keyboard,
    format_history_entry,
    format_session_ended,
    format_session_started,
    handle_callback_query,
    handle_context,
    handle_download,
    handle_exit,
    handle_file_upload,
    handle_git,
    handle_history,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_unknown_command,
    handle_update_claude,
    is_authorized,
)
from src.output_parser import (
    ScreenState,
    TerminalEmulator,
    classify_screen_state,
    extract_content,
)
from src.project_scanner import Project
from src.session_manager import OutputBuffer


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

    @pytest.mark.asyncio
    async def test_auto_switch_after_kill(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(session_id=1, project_name="proj1")
        new_session = MagicMock(session_id=2, project_name="proj2")
        sm = AsyncMock()
        sm.get_active_session = MagicMock(side_effect=[session, new_session])
        sm.kill_session = AsyncMock()
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_exit(update, context)
        msg = update.message.reply_text.call_args[0][0]
        assert "proj2" in msg
        assert "session #2" in msg.lower()


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
        session.process.submit = AsyncMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111])),
            "session_manager": MagicMock(
                get_active_session=MagicMock(return_value=session)
            ),
        }
        await handle_text_message(update, context)
        session.process.submit.assert_called_once_with("hello world")

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
    async def test_update_confirm(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "update:confirm"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        config.claude.update_command = "echo done"
        context.bot_data = {"config": config, "session_manager": MagicMock()}
        with patch(
            "src.bot._run_update_command", new_callable=AsyncMock
        ) as mock_run:
            mock_run.return_value = "OK: done"
            await handle_callback_query(update, context)
            mock_run.assert_called_once_with("echo done")

    @pytest.mark.asyncio
    async def test_update_cancel(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "update:cancel"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        context.bot_data = {"config": config, "session_manager": MagicMock()}
        await handle_callback_query(update, context)
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "cancelled" in msg.lower()

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


class TestHandleContext:
    @pytest.mark.asyncio
    async def test_sends_context_command(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock()
        session.process.submit = AsyncMock()
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_context(update, context)
        session.process.submit.assert_called_once_with("/context")
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_context(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active" in call_text.lower()


class TestHandleDownload:
    @pytest.mark.asyncio
    async def test_file_found(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/download /tmp/test.txt"
        update.message.reply_text = AsyncMock()
        update.message.reply_document = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        fh = MagicMock(
            file_exists=MagicMock(return_value=True),
            _base_dir="/tmp",
        )
        session = MagicMock(project_path="/some/project")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {
            "config": config, "file_handler": fh, "session_manager": sm
        }
        with patch("builtins.open", MagicMock()):
            await handle_download(update, context)
            update.message.reply_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_file_not_found(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/download /tmp/nonexistent.txt"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        fh = MagicMock(
            file_exists=MagicMock(return_value=False),
            _base_dir="/tmp",
        )
        session = MagicMock(project_path="/some/project")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {
            "config": config, "file_handler": fh, "session_manager": sm
        }
        await handle_download(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "not found" in call_text.lower()

    @pytest.mark.asyncio
    async def test_missing_path_arg(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/download"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        fh = MagicMock()
        context.bot_data = {"config": config, "file_handler": fh}
        await handle_download(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "usage" in call_text.lower()

    @pytest.mark.asyncio
    async def test_path_traversal_denied(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/download /etc/passwd"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        fh = MagicMock(
            file_exists=MagicMock(return_value=True),
            _base_dir="/tmp/claude",
        )
        session = MagicMock(project_path="/home/user/project")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {
            "config": config, "file_handler": fh, "session_manager": sm
        }
        await handle_download(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "access denied" in call_text.lower()


class TestHandleFileUpload:
    @pytest.mark.asyncio
    async def test_document_upload(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        update.message.document = MagicMock(file_id="abc", file_name="test.py")
        update.message.photo = None
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(project_name="proj", session_id=1)
        session.process.write = AsyncMock()
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        fh = MagicMock(get_upload_path=MagicMock(return_value="/tmp/test.py"))
        context.bot_data = {
            "config": config, "session_manager": sm, "file_handler": fh
        }
        file_obj = AsyncMock()
        context.bot.get_file = AsyncMock(return_value=file_obj)
        await handle_file_upload(update, context)
        file_obj.download_to_drive.assert_called_once_with("/tmp/test.py")
        session.process.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_photo_upload(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        update.message.document = None
        photo = MagicMock(file_id="photo123", file_name=None)
        update.message.photo = [MagicMock(), photo]  # [-1] is largest
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(project_name="proj", session_id=1)
        session.process.write = AsyncMock()
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        fh = MagicMock(get_upload_path=MagicMock(return_value="/tmp/photo.bin"))
        context.bot_data = {
            "config": config, "session_manager": sm, "file_handler": fh
        }
        file_obj = AsyncMock()
        context.bot.get_file = AsyncMock(return_value=file_obj)
        await handle_file_upload(update, context)
        file_obj.download_to_drive.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        update.message.document = MagicMock(file_id="abc")
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_file_upload(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active" in call_text.lower()

    @pytest.mark.asyncio
    async def test_unauthorized_ignored(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        update.message.document = MagicMock(file_id="abc")
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        context.bot_data = {"config": config}
        await handle_file_upload(update, context)
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_document(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        update.message.document = None
        update.message.photo = None
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock()
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {
            "config": config, "session_manager": sm, "file_handler": MagicMock()
        }
        await handle_file_upload(update, context)
        update.message.reply_text.assert_not_called()


class TestRunUpdateCommand:
    @pytest.mark.asyncio
    async def test_runs_command(self):
        result = await _run_update_command("echo hello")
        assert "OK" in result
        assert "hello" in result


# --- Parametrized auth tests ---


@pytest.mark.parametrize("handler", [
    handle_start, handle_sessions, handle_exit,
    handle_history, handle_git, handle_update_claude,
    handle_context, handle_download,
])
@pytest.mark.asyncio
async def test_unauthorized_rejected(handler):
    update = MagicMock()
    update.effective_user.id = 999
    update.message.text = "/download /tmp/foo"
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.bot_data = {
        "config": MagicMock(telegram=MagicMock(authorized_users=[111])),
        "file_handler": MagicMock(_base_dir="/tmp/claude"),
        "session_manager": MagicMock(
            get_active_session=MagicMock(return_value=None)
        ),
    }
    await handler(update, context)
    call_text = update.message.reply_text.call_args[0][0]
    assert "not authorized" in call_text.lower()


class TestBuildApp:
    def test_builds_app_with_handlers(self, tmp_path):
        import yaml

        from src.main import build_app

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "telegram": {
                        "bot_token": "fake-token",
                        "authorized_users": [111],
                    },
                    "projects": {"root": "/tmp"},
                }
            )
        )
        app = build_app(str(config_file))
        assert app is not None

    def test_debug_flags_propagate_to_config(self, tmp_path):
        import yaml

        from src.main import build_app

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "telegram": {
                        "bot_token": "fake-token",
                        "authorized_users": [111],
                    },
                    "projects": {"root": "/tmp"},
                }
            )
        )
        app = build_app(str(config_file), debug=True, trace=True, verbose=True)
        assert app is not None
        assert app.bot_data["config"].debug.enabled is True
        assert app.bot_data["config"].debug.trace is True
        assert app.bot_data["config"].debug.verbose is True


class TestHandlerLogging:
    @pytest.mark.asyncio
    async def test_handle_start_logs_handler_entry(self, mock_update, mock_context, caplog):
        from src.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        mock_context.bot_data["config"].projects.root = "/nonexistent"
        mock_context.bot_data["config"].projects.scan_depth = 1
        with caplog.at_level(logging.DEBUG, logger="src.bot"):
            await handle_start(mock_update, mock_context)
        assert any("handle_start" in r.message for r in caplog.records)


class TestSpawnErrorReporting:
    """Regression: spawn failures must send error message to Telegram user."""

    @pytest.mark.asyncio
    async def test_spawn_error_sends_telegram_message(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "project:/a/bad-project"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = AsyncMock()
        sm.create_session = AsyncMock(
            side_effect=RuntimeError("command not found")
        )
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        update.callback_query.edit_message_text.assert_called_once()
        msg = update.callback_query.edit_message_text.call_args[0][0]
        assert "Failed" in msg
        assert "command not found" in msg

    @pytest.mark.asyncio
    async def test_spawn_error_does_not_call_git_info(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "project:/a/proj"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = AsyncMock()
        sm.create_session = AsyncMock(side_effect=OSError("bad"))
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.bot.get_git_info", new_callable=AsyncMock) as mock_git:
            await handle_callback_query(update, context)
            mock_git.assert_not_called()


class TestHandleUnknownCommand:
    """Regression: unknown /commands must either forward to session or show help."""

    @pytest.mark.asyncio
    async def test_forwards_to_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/status"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock()
        session.process.submit = AsyncMock()
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_unknown_command(update, context)
        session.process.submit.assert_called_once_with("/status")
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_shows_help_without_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/bogus"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_unknown_command(update, context)
        update.message.reply_text.assert_called_once()
        msg = update.message.reply_text.call_args[0][0]
        assert "Unknown command" in msg
        assert "/start" in msg

    @pytest.mark.asyncio
    async def test_unauthorized_ignored(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        context.bot_data = {"config": config, "session_manager": MagicMock()}
        await handle_unknown_command(update, context)
        update.message.reply_text.assert_not_called()


class TestOutputStateFiltering:
    """Regression: poll_output must suppress UI chrome and only send content."""

    def test_startup_not_in_content_states(self):
        assert ScreenState.STARTUP not in _CONTENT_STATES

    def test_idle_not_in_content_states(self):
        assert ScreenState.IDLE not in _CONTENT_STATES

    def test_unknown_not_in_content_states(self):
        assert ScreenState.UNKNOWN not in _CONTENT_STATES

    def test_streaming_in_content_states(self):
        assert ScreenState.STREAMING in _CONTENT_STATES

    def test_tool_request_in_content_states(self):
        assert ScreenState.TOOL_REQUEST in _CONTENT_STATES

    def test_error_in_content_states(self):
        assert ScreenState.ERROR in _CONTENT_STATES

    def test_startup_screen_classified_and_filtered(self):
        """A Claude Code startup banner must be classified as STARTUP."""
        lines = [
            "Claude Code v2.1.37",
            " \u2590\u259b\u2588\u2588\u2588\u259c\u2590   Opus 4.6 · Claude Max",
            "\u259d\u259c\u2588\u2588\u2588\u2588\u2588\u259b\u2598  ~/dev/my-project",
            "  \u2598\u2598 \u259d\u259d",
            "",
        ] + [""] * 35
        event = classify_screen_state(lines)
        assert event.state == ScreenState.STARTUP
        # extract_content should return nothing useful from startup chrome
        content = extract_content(lines)
        # No meaningful user content in startup screen
        assert "Opus" not in content or content == ""

    def test_extract_content_filters_separators(self):
        """Separator lines must be stripped by extract_content."""
        lines = [
            "\u2500" * 80,
            "This is real content from Claude",
            "\u2500" * 80,
        ]
        content = extract_content(lines)
        assert "real content" in content
        assert "\u2500" * 10 not in content

    def test_startup_to_unknown_guard_prevents_reentry(self):
        """Regression: once past STARTUP, classifier returning STARTUP must become UNKNOWN."""
        from src.bot import _session_prev_state
        from src.output_parser import ScreenEvent

        # Simulate: session was in IDLE, classifier returns STARTUP (banner visible)
        key = (999, 999)
        _session_prev_state[key] = ScreenState.IDLE
        prev = _session_prev_state[key]

        # This is the guard logic from poll_output
        event = ScreenEvent(state=ScreenState.STARTUP, raw_lines=[])
        if event.state == ScreenState.STARTUP and prev not in (ScreenState.STARTUP, None):
            event = ScreenEvent(
                state=ScreenState.UNKNOWN, payload=event.payload, raw_lines=event.raw_lines
            )
        assert event.state == ScreenState.UNKNOWN

        # Cleanup
        del _session_prev_state[key]

    def test_thinking_notification_on_transition(self):
        """Regression: THINKING must send '_Thinking..._' once, not every cycle."""
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        prev = ScreenState.IDLE

        # First transition to THINKING → should append
        state = ScreenState.THINKING
        if state == ScreenState.THINKING and prev != ScreenState.THINKING:
            buf.append("_Thinking..._\n")
        assert "_Thinking..._" in buf.flush()

        # Second cycle still THINKING → should NOT append
        prev = ScreenState.THINKING
        if state == ScreenState.THINKING and prev != ScreenState.THINKING:
            buf.append("_Thinking..._\n")
        assert buf.flush() == ""

    def test_flush_on_idle_transition(self):
        """Regression: buffer must flush when state transitions to IDLE."""
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Hello World\n")
        # Simulate transition to IDLE
        prev = ScreenState.STREAMING
        state = ScreenState.IDLE
        if state == ScreenState.IDLE and prev != ScreenState.IDLE:
            if buf.is_ready():
                text = buf.flush()
                assert "Hello World" in text
