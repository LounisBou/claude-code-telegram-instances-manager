from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.git_info import GitInfo, get_git_info


class TestGitInfo:
    def test_defaults(self):
        info = GitInfo()
        assert info.branch is None
        assert info.pr_url is None
        assert info.pr_title is None
        assert info.pr_state is None

    def test_format_with_pr(self):
        info = GitInfo(
            branch="feature/foo",
            pr_url="https://github.com/u/r/pull/1",
            pr_title="Fix bug",
            pr_state="OPEN",
        )
        text = info.format()
        assert "feature/foo" in text
        assert "Fix bug" in text

    def test_format_uses_html_not_markdown(self):
        """Regression: format() must produce HTML tags, not Markdown syntax."""
        info = GitInfo(
            branch="feat/branch",
            pr_url="https://github.com/u/r/pull/1",
            pr_title="My PR",
            pr_state="OPEN",
        )
        text = info.format()
        # Must use HTML tags
        assert "<code>feat/branch</code>" in text
        assert '<a href="https://github.com/u/r/pull/1">My PR</a>' in text
        # Must NOT use Markdown syntax
        assert "`feat/branch`" not in text
        assert "[My PR](" not in text

    def test_format_escapes_html_in_pr_title(self):
        """Ensure HTML special chars in PR titles are escaped."""
        info = GitInfo(
            branch="main",
            pr_url="https://github.com/u/r/pull/1",
            pr_title="Fix <script> & stuff",
            pr_state="OPEN",
        )
        text = info.format()
        assert "&lt;script&gt;" in text
        assert "&amp;" in text

    def test_format_without_pr(self):
        info = GitInfo(branch="main")
        text = info.format()
        assert "main" in text
        assert "No open PR" in text

    def test_format_no_git(self):
        info = GitInfo()
        text = info.format()
        assert "no git info" in text.lower()


class TestGetGitInfo:
    @pytest.mark.asyncio
    async def test_returns_branch_name(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                "feature/my-branch",  # git branch
                "",  # gh pr view (no PR)
            ]
            info = await get_git_info("/some/project")
            assert info.branch == "feature/my-branch"

    @pytest.mark.asyncio
    async def test_returns_pr_info(self):
        pr_json = json.dumps({
            "url": "https://github.com/user/repo/pull/42",
            "title": "My PR title",
            "state": "OPEN",
        })
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                "feature/branch",
                pr_json,
            ]
            info = await get_git_info("/some/project")
            assert info.pr_url == "https://github.com/user/repo/pull/42"
            assert info.pr_title == "My PR title"
            assert info.pr_state == "OPEN"

    @pytest.mark.asyncio
    async def test_no_pr(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = ["main", ""]
            info = await get_git_info("/some/project")
            assert info.branch == "main"
            assert info.pr_url is None
            assert info.pr_title is None

    @pytest.mark.asyncio
    async def test_git_command_fails(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("git not found")
            info = await get_git_info("/some/project")
            assert info.branch is None
            assert info.pr_url is None

    @pytest.mark.asyncio
    async def test_gh_command_fails_still_returns_branch(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                "main",
                Exception("gh not installed"),
            ]
            info = await get_git_info("/some/project")
            assert info.branch == "main"
            assert info.pr_url is None

    @pytest.mark.asyncio
    async def test_empty_branch_becomes_none(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = ["", ""]
            info = await get_git_info("/some/project")
            assert info.branch is None

    @pytest.mark.asyncio
    async def test_invalid_pr_json(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = ["main", "not valid json"]
            info = await get_git_info("/some/project")
            assert info.branch == "main"
            assert info.pr_url is None
