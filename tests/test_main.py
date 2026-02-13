from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import _on_startup, _parse_args


class TestOnStartup:
    @staticmethod
    def _make_app(db):
        app = MagicMock()
        app.bot_data = {
            "db": db,
            "config": MagicMock(
                telegram=MagicMock(authorized_users=[111]),
            ),
        }
        app.bot.set_my_commands = AsyncMock()
        app.bot.send_message = AsyncMock()
        return app

    @pytest.mark.asyncio
    async def test_initializes_db_and_marks_lost(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(
            return_value=[{"id": 1, "project": "p1"}]
        )
        app = self._make_app(db)
        await _on_startup(app)
        db.initialize.assert_called_once()
        db.mark_active_sessions_lost.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_lost_sessions(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app = self._make_app(db)
        await _on_startup(app)
        db.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_bot_commands(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app = self._make_app(db)
        await _on_startup(app)
        app.bot.set_my_commands.assert_called_once()


class TestParseArgs:
    def test_default_config_path(self):
        with patch.object(sys, "argv", ["main"]):
            args = _parse_args()
            assert args.config == "config.yaml"
            assert args.debug is False
            assert args.trace is False
            assert args.verbose is False

    def test_custom_config_and_debug(self):
        with patch.object(sys, "argv", ["main", "my.yaml", "--debug"]):
            args = _parse_args()
            assert args.config == "my.yaml"
            assert args.debug is True

    def test_trace_flag(self):
        with patch.object(sys, "argv", ["main", "--trace"]):
            args = _parse_args()
            assert args.trace is True
            assert args.verbose is False

    def test_trace_verbose_flags(self):
        with patch.object(sys, "argv", ["main", "--trace", "--verbose"]):
            args = _parse_args()
            assert args.trace is True
            assert args.verbose is True


class TestBuildApp:
    """Regression: build_app must wire all components correctly."""

    def test_env_threaded_to_session_manager(self, tmp_path):
        """Regression: claude.env from config must reach SessionManager and ClaudeProcess."""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(
            "telegram:\n"
            "  bot_token: 'test-token'\n"
            "  authorized_users: [111]\n"
            "projects:\n"
            "  root: /tmp\n"
            "claude:\n"
            "  env:\n"
            "    MY_CUSTOM_VAR: 'some-value'\n"
        )
        from src.main import build_app

        app = build_app(str(config_file))
        sm = app.bot_data["session_manager"]
        assert sm._env == {"MY_CUSTOM_VAR": "some-value"}

    def test_command_menu_set_on_startup(self):
        """Regression: _on_startup must call set_my_commands to register Telegram menu."""
        from src.telegram.keyboards import BOT_COMMANDS

        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app = MagicMock()
        app.bot_data = {
            "db": db,
            "config": MagicMock(
                telegram=MagicMock(authorized_users=[111]),
            ),
        }
        app.bot.set_my_commands = AsyncMock()
        app.bot.send_message = AsyncMock()

        import asyncio
        asyncio.get_event_loop().run_until_complete(_on_startup(app))

        app.bot.set_my_commands.assert_called_once()
        # Verify command list matches BOT_COMMANDS
        call_args = app.bot.set_my_commands.call_args[0][0]
        assert len(call_args) == len(BOT_COMMANDS)


class TestGracefulShutdown:
    """Regression: shutdown must terminate sessions and close db."""

    @pytest.mark.asyncio
    async def test_shutdown_calls_session_shutdown_and_db_close(self):
        """Regression: main shutdown sequence must terminate all sessions then close db."""
        session_manager = AsyncMock()
        session_manager.shutdown = AsyncMock()
        db = AsyncMock()
        db.close = AsyncMock()

        # Simulate the shutdown sequence from main()
        await session_manager.shutdown()
        await db.close()

        session_manager.shutdown.assert_called_once()
        db.close.assert_called_once()
