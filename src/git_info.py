from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass


@dataclass
class GitInfo:
    """Git repository metadata including branch and pull request info."""

    branch: str | None = None
    pr_url: str | None = None
    pr_title: str | None = None
    pr_state: str | None = None

    def format(self) -> str:
        """Format git info as a human-readable Markdown string.

        Returns:
            A pipe-separated string containing the branch name and
            PR link (or "No open PR" / "No git info available").
        """
        if not self.branch:
            return "No git info available"
        parts = [f"Branch: `{self.branch}`"]
        if self.pr_url and self.pr_title:
            parts.append(f"PR: [{self.pr_title}]({self.pr_url})")
        else:
            parts.append("No open PR")
        return " | ".join(parts)


async def _run_command(cmd: list[str], cwd: str) -> str:
    """Run a shell command asynchronously and return its stdout.

    Args:
        cmd: Command and arguments to execute (e.g. ["git", "status"]).
        cwd: Working directory in which to run the command.

    Returns:
        Decoded and stripped stdout output from the command.
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def get_git_info(project_path: str) -> GitInfo:
    """Gather git branch and GitHub PR info for a project directory.

    Runs ``git branch --show-current`` to get the current branch, then
    ``gh pr view`` to fetch any associated pull request metadata. Failures
    at either step are silently caught so the caller always receives a
    valid GitInfo (possibly with None fields).

    Args:
        project_path: Absolute path to the git repository root.

    Returns:
        A GitInfo instance populated with whatever data could be retrieved.
    """
    try:
        branch = await _run_command(
            ["git", "branch", "--show-current"], cwd=project_path
        )
    except Exception:
        # git may not be installed or path may not be a repo — fail gracefully
        return GitInfo()

    pr_url = None
    pr_title = None
    pr_state = None

    try:
        pr_raw = await _run_command(
            ["gh", "pr", "view", "--json", "url,title,state"], cwd=project_path
        )
        if pr_raw:
            pr_data = json.loads(pr_raw)
            pr_url = pr_data.get("url")
            pr_title = pr_data.get("title")
            pr_state = pr_data.get("state")
    except Exception:
        # gh CLI may not be installed or no PR exists — fail gracefully
        pass

    return GitInfo(
        branch=branch or None,
        pr_url=pr_url,
        pr_title=pr_title,
        pr_state=pr_state,
    )
