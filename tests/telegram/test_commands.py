from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.commands import (
    _run_update_command,
    handle_context,
    handle_download,
    handle_file_upload,
    handle_git,
    handle_history,
    handle_update_claude,
)
from src.telegram.handlers import (
    handle_callback_query,
    handle_exit,
    handle_sessions,
    handle_start,
    handle_text_message,
)


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
    async def test_history_uses_html_parse_mode(self):
        """Regression: /history must use parse_mode=HTML, not raw text."""
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        db = AsyncMock()
        db.list_sessions = AsyncMock(
            return_value=[
                {
                    "id": 7,
                    "project": "my-proj",
                    "started_at": "2026-02-09T10:02:35.958687+00:00",
                    "ended_at": None,
                    "status": "active",
                    "exit_code": None,
                }
            ]
        )
        context.bot_data = {"config": config, "db": db}
        await handle_history(update, context)
        call_kwargs = update.message.reply_text.call_args
        assert call_kwargs.kwargs.get("parse_mode") == "HTML"
        body = call_kwargs.args[0]
        assert "🟢" in body
        assert "<b>#7 my-proj</b>" in body
        assert "*my-proj*" not in body
        assert ".958687" not in body

    @pytest.mark.asyncio
    async def test_history_readability(self):
        """Regression for issue 001: /history must have header, entry limit, and visual structure."""
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        db = AsyncMock()
        # 15 sessions — only first 10 should be shown
        sessions = [
            {
                "id": i,
                "project": f"proj-{i}",
                "started_at": f"2026-02-09T10:0{i % 10}:00",
                "ended_at": None,
                "status": "active" if i <= 2 else "ended",
                "exit_code": None if i <= 2 else 0,
            }
            for i in range(1, 16)
        ]
        db.list_sessions = AsyncMock(return_value=sessions)
        context.bot_data = {"config": config, "db": db}
        await handle_history(update, context)
        body = update.message.reply_text.call_args.args[0]
        # Header with count
        assert "<b>Session history</b> (last 10):" in body
        # Only 10 entries shown (not 15)
        assert "proj-11" not in body
        assert "proj-10" in body
        # Double newline separation between entries
        assert "\n\n" in body

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
        with patch("src.telegram.commands.get_git_info", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = MagicMock(
                format=MagicMock(return_value="Branch: main | No open PR")
            )
            await handle_git(update, context)
            update.message.reply_text.assert_called_once()
            assert "main" in update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_git_uses_html_parse_mode(self):
        """Regression: /git must use parse_mode=HTML since format() produces HTML."""
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(project_path="/a/proj")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.telegram.commands.get_git_info", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = MagicMock(
                format=MagicMock(
                    return_value='Branch: <code>main</code> | No open PR'
                )
            )
            await handle_git(update, context)
            call_kwargs = update.message.reply_text.call_args
            assert call_kwargs.kwargs.get("parse_mode") == "HTML"

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
            "src.telegram.commands._run_update_command", new_callable=AsyncMock
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
        session = MagicMock(project_path="/some/project")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "file_handler": fh, "session_manager": sm}
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


class TestNoSessionMessagesIncludeStartHint:
    """Regression for issue 005: all no-session messages must include /start hint."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("handler,bot_data_extras", [
        (handle_git, {"session_manager": MagicMock(get_active_session=MagicMock(return_value=None))}),
        (handle_context, {"session_manager": MagicMock(get_active_session=MagicMock(return_value=None))}),
    ])
    async def test_command_no_session_includes_start_hint(self, handler, bot_data_extras):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        context.bot_data = {"config": config, **bot_data_extras}
        await handler(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "/start" in call_text, f"{handler.__name__} no-session message missing /start hint: {call_text!r}"

    @pytest.mark.asyncio
    async def test_file_upload_no_session_includes_start_hint(self):
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
        assert "/start" in call_text, f"file_upload no-session message missing /start hint: {call_text!r}"

    @pytest.mark.asyncio
    async def test_sessions_no_session_includes_start_hint(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(list_sessions=MagicMock(return_value=[]))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_sessions(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "/start" in call_text, f"sessions no-session message missing /start hint: {call_text!r}"

    @pytest.mark.asyncio
    async def test_exit_no_session_includes_start_hint(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_exit(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "/start" in call_text, f"exit no-session message missing /start hint: {call_text!r}"

    @pytest.mark.asyncio
    async def test_text_message_no_session_includes_start_hint(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "hello"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(get_active_session=MagicMock(return_value=None))
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_text_message(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "/start" in call_text, f"text_message no-session message missing /start hint: {call_text!r}"


class TestDownloadUsageFormatting:
    """Regression for issue 007: /download usage path must not be parsed as Telegram commands."""

    @pytest.mark.asyncio
    async def test_usage_text_uses_html_code_tags(self):
        """The example path in usage must be wrapped in <code> to prevent command parsing."""
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "/download"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        fh = MagicMock()
        session = MagicMock(project_path="/some/project")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "file_handler": fh, "session_manager": sm}
        await handle_download(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        call_kwargs = update.message.reply_text.call_args[1]
        # Must use HTML parse mode
        assert call_kwargs.get("parse_mode") == "HTML"
        # Path must be inside <code> tags so Telegram doesn't parse slashes as commands
        assert "<code>" in call_text
        assert "</code>" in call_text


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
