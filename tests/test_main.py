from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import _on_startup, _setup_logging


class TestOnStartup:
    @pytest.mark.asyncio
    async def test_initializes_db_and_marks_lost(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(
            return_value=[{"id": 1, "project": "p1"}]
        )
        app = MagicMock()
        app.bot_data = {"db": db}
        await _on_startup(app)
        db.initialize.assert_called_once()
        db.mark_active_sessions_lost.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_lost_sessions(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app = MagicMock()
        app.bot_data = {"db": db}
        await _on_startup(app)
        db.initialize.assert_called_once()


class TestSetupLogging:
    def test_debug_mode(self):
        import logging

        logger = _setup_logging(debug=True)
        assert logger is not None

    def test_info_mode(self):
        import logging

        logger = _setup_logging(debug=False)
        assert logger is not None
