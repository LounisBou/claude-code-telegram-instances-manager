import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def tmp_projects(tmp_path):
    """Create a temporary projects root with sample project dirs."""
    proj_a = tmp_path / "project-alpha"
    proj_a.mkdir()
    (proj_a / ".git").mkdir()

    proj_b = tmp_path / "project-beta"
    proj_b.mkdir()
    (proj_b / ".claude").mkdir()

    proj_c = tmp_path / "not-a-project"
    proj_c.mkdir()

    return tmp_path


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update with common attributes."""
    update = MagicMock()
    update.effective_user.id = 111
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock context with config authorizing user 111."""
    context = MagicMock()
    config = MagicMock()
    config.telegram.authorized_users = [111]
    context.bot_data = {"config": config}
    return context
