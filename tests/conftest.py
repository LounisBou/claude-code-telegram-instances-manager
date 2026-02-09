import asyncio

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
