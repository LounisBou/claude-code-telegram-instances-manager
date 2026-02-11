from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.handlers import (
    handle_callback_query,
    handle_exit,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_unknown_command,
)
from src.project_scanner import Project


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
        with patch("src.telegram.handlers.scan_projects") as mock_scan:
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
        with patch("src.telegram.handlers.scan_projects") as mock_scan:
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

    @pytest.mark.asyncio
    async def test_exit_message_uses_html_parse_mode(self):
        """Regression: /exit reply must use parse_mode=HTML, not raw tags."""
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(session_id=1, project_name="my-proj")
        sm = AsyncMock()
        sm.get_active_session = MagicMock(side_effect=[session, None])
        sm.kill_session = AsyncMock()
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_exit(update, context)
        call_kwargs = update.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"


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
        with patch("src.telegram.handlers.get_git_info", new_callable=AsyncMock) as mock_git:
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
            "src.telegram.handlers._run_update_command", new_callable=AsyncMock
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
        with patch("src.telegram.handlers.scan_projects") as mock_scan:
            mock_scan.return_value = [
                Project(name=f"p{i}", path=f"/a/p{i}") for i in range(12)
            ]
            await handle_callback_query(update, context)
            update.callback_query.edit_message_text.assert_called_once()


class TestToolApprovalCallback:
    """Tests for tool approval inline keyboard callback handling."""

    @pytest.mark.asyncio
    async def test_tool_yes_sends_enter_to_pty(self):
        """Allow button sends Enter to PTY to accept the default option."""
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "tool:yes:1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message.text = "Do you want to create test.txt?"
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = MagicMock()
        session = MagicMock()
        session.process.write = AsyncMock()
        sm._sessions = {111: {1: session}}
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        session.process.write.assert_called_once_with("\r")
        update.callback_query.answer.assert_called_once_with("Allowed")

    @pytest.mark.asyncio
    async def test_tool_no_sends_escape_to_pty(self):
        """Deny button sends Escape to PTY to cancel the tool request."""
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "tool:no:1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message.text = "Do you want to create test.txt?"
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = MagicMock()
        session = MagicMock()
        session.process.write = AsyncMock()
        sm._sessions = {111: {1: session}}
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        session.process.write.assert_called_once_with("\x1b")
        update.callback_query.answer.assert_called_once_with("Denied")

    @pytest.mark.asyncio
    async def test_tool_callback_no_session(self):
        """Tool callback with dead session returns error."""
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "tool:yes:99"
        update.callback_query.answer = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = MagicMock()
        sm._sessions = {111: {}}
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        update.callback_query.answer.assert_called_once_with(
            "Session no longer active"
        )


class TestHandlerLogging:
    @pytest.mark.asyncio
    async def test_handle_start_logs_handler_entry(self, mock_update, mock_context, caplog):
        from src.core.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        mock_context.bot_data["config"].projects.root = "/nonexistent"
        mock_context.bot_data["config"].projects.scan_depth = 1
        with caplog.at_level(logging.DEBUG, logger="src.telegram.handlers"):
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
        with patch("src.telegram.handlers.get_git_info", new_callable=AsyncMock) as mock_git:
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
