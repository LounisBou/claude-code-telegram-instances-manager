from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass


@dataclass
class GitInfo:
    branch: str | None = None
    pr_url: str | None = None
    pr_title: str | None = None
    pr_state: str | None = None

    def format(self) -> str:
        if not self.branch:
            return "No git info available"
        parts = [f"Branch: `{self.branch}`"]
        if self.pr_url and self.pr_title:
            parts.append(f"PR: [{self.pr_title}]({self.pr_url})")
        else:
            parts.append("No open PR")
        return " | ".join(parts)


async def _run_command(cmd: list[str], cwd: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def get_git_info(project_path: str) -> GitInfo:
    try:
        branch = await _run_command(
            ["git", "branch", "--show-current"], cwd=project_path
        )
    except Exception:
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
        pass

    return GitInfo(
        branch=branch or None,
        pr_url=pr_url,
        pr_title=pr_title,
        pr_state=pr_state,
    )
