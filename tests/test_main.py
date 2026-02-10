from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import _on_startup, _parse_args


class TestOnStartup:
    @staticmethod
    def _make_app(db):
        app = MagicMock()
        app.bot_data = {"db": db}
        app.bot.set_my_commands = AsyncMock()
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
