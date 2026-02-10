# installer/prerequisites.py
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from installer.platform import PlatformInfo


@dataclass
class PrereqResult:
    """Result of a single prerequisite check."""
    name: str
    found: bool
    version: str | None
    required: bool
    install_cmd: str | None = None


def _run_quiet(cmd: list[str]) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _check_python_version() -> tuple[bool, str | None]:
    """Check if Python 3.11+ is available."""
    import sys
    v = sys.version_info
    if v >= (3, 11):
        return True, f"{v.major}.{v.minor}.{v.micro}"
    return False, f"{v.major}.{v.minor}.{v.micro}"


def _check_claude_cli() -> tuple[bool, str | None]:
    """Check if the Claude CLI is installed."""
    if not shutil.which("claude"):
        return False, None
    output = _run_quiet(["claude", "--version"])
    return bool(output), output or None


def _check_gh_cli() -> tuple[bool, str | None]:
    """Check if the GitHub CLI is installed."""
    if not shutil.which("gh"):
        return False, None
    output = _run_quiet(["gh", "--version"])
    m = re.search(r"(\d+\.\d+\.\d+)", output)
    return True, m.group(1) if m else output


def _install_cmd_for(name: str, plat: PlatformInfo) -> str | None:
    """Suggest an install command for a missing dependency."""
    pkg_map = {
        "brew": {"git": "brew install git", "gh": "brew install gh",
                 "python": "brew install python@3.12",
                 "claude": "brew install claude-code"},
        "apt": {"git": "sudo apt install -y git", "gh": "sudo apt install -y gh",
                "python": "sudo apt install -y python3.12 python3.12-venv",
                "claude": "npm install -g @anthropic-ai/claude-code"},
        "dnf": {"git": "sudo dnf install -y git", "gh": "sudo dnf install -y gh",
                "python": "sudo dnf install -y python3.12",
                "claude": "npm install -g @anthropic-ai/claude-code"},
        "pacman": {"git": "sudo pacman -S --noconfirm git", "gh": "sudo pacman -S --noconfirm github-cli",
                   "python": "sudo pacman -S --noconfirm python",
                   "claude": "npm install -g @anthropic-ai/claude-code"},
    }
    pm = plat.package_manager
    if pm and pm in pkg_map:
        return pkg_map[pm].get(name)
    return None


def check_prerequisites(plat: PlatformInfo) -> list[PrereqResult]:
    """Check all prerequisites and return results."""
    results: list[PrereqResult] = []

    # Python
    found, version = _check_python_version()
    results.append(PrereqResult(
        name="python", found=found, version=version, required=True,
        install_cmd=_install_cmd_for("python", plat),
    ))

    # git
    git_path = shutil.which("git")
    git_version = None
    if git_path:
        out = _run_quiet(["git", "--version"])
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        git_version = m.group(1) if m else out
    results.append(PrereqResult(
        name="git", found=bool(git_path), version=git_version, required=True,
        install_cmd=_install_cmd_for("git", plat),
    ))

    # Claude CLI
    found, version = _check_claude_cli()
    results.append(PrereqResult(
        name="claude", found=found, version=version, required=True,
        install_cmd=_install_cmd_for("claude", plat),
    ))

    # gh CLI (optional)
    found, version = _check_gh_cli()
    results.append(PrereqResult(
        name="gh", found=found, version=version, required=False,
        install_cmd=_install_cmd_for("gh", plat),
    ))

    return results
