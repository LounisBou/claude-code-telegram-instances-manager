# installer/configure.py
"""Interactive config generator for claude-ctim.

Prompts the user for essential and common config values,
validates input, and writes a config.yaml file.
"""
from __future__ import annotations

import os
import re
import shutil

from installer.constants import CONFIG_FILENAME


def validate_bot_token(token: str) -> bool:
    """Validate Telegram bot token format (digits:alphanumeric+special)."""
    return bool(re.match(r"^\d+:[A-Za-z0-9_-]+$", token.strip()))


def validate_user_ids(raw: str) -> list[int] | None:
    """Parse comma-separated user IDs. Returns list or None on failure."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        return ids if ids else None
    except ValueError:
        return None


def _prompt(message: str, default: str | None = None) -> str:
    """Prompt user for input with optional default."""
    if default is not None:
        message = f"{message} [{default}]: "
    else:
        message = f"{message}: "
    value = input(message).strip()
    return value if value else (default or "")


def _detect_claude_command() -> str:
    """Auto-detect Claude CLI path."""
    path = shutil.which("claude")
    return path if path else "claude"


def _format_user_ids(ids: list[int]) -> str:
    """Format user IDs as YAML list items."""
    return "\n".join(f"    - {uid}" for uid in ids)


def generate_config_yaml(config: dict, install_dir: str) -> str:
    """Generate config.yaml from a config dict. Returns the file path.

    Uses string formatting (not PyYAML) since the installer must be stdlib-only.
    """
    user_ids_yaml = _format_user_ids(config["authorized_users"])
    bot_token = config["bot_token"]
    projects_root = config["projects_root"]
    max_per_user = config.get("max_per_user", 3)
    claude_command = config.get("claude_command", "claude")
    debug_enabled = str(config.get("debug", False)).lower()

    yaml_content = (
        f'telegram:\n'
        f'  bot_token: "{bot_token}"\n'
        f'  authorized_users:\n'
        f'{user_ids_yaml}\n'
        f'\n'
        f'projects:\n'
        f'  root: "{projects_root}"\n'
        f'  scan_depth: 1\n'
        f'\n'
        f'sessions:\n'
        f'  max_per_user: {max_per_user}\n'
        f'  output_debounce_ms: 500\n'
        f'  output_max_buffer: 2000\n'
        f'  silence_warning_minutes: 10\n'
        f'\n'
        f'claude:\n'
        f'  command: "{claude_command}"\n'
        f'  env: {{}}\n'
        f'  default_args: []\n'
        f'  update_command: "claude update"\n'
        f'\n'
        f'database:\n'
        f'  path: "data/sessions.db"\n'
        f'\n'
        f'debug:\n'
        f'  enabled: {debug_enabled}\n'
    )
    path = os.path.join(install_dir, CONFIG_FILENAME)
    with open(path, "w") as f:
        f.write(yaml_content)
    return path


def interactive_configure(install_dir: str) -> str:
    """Run interactive config prompts and write config.yaml. Returns path."""
    print("\n=== claude-ctim Configuration ===\n")

    # Essential
    while True:
        token = _prompt("Telegram bot token (from @BotFather)")
        if validate_bot_token(token):
            break
        print("  Invalid token format. Expected: 123456:ABCdef...")

    while True:
        raw_ids = _prompt("Authorized Telegram user IDs (comma-separated)")
        ids = validate_user_ids(raw_ids)
        if ids:
            break
        print("  Invalid format. Expected: 123456789 or 123,456,789")

    while True:
        projects_root = _prompt("Projects root directory", "/home")
        if os.path.isdir(projects_root):
            break
        print(f"  Directory not found: {projects_root}")

    # Common
    max_per_user = _prompt("Max sessions per user", "3")
    claude_cmd = _prompt("Claude CLI command", _detect_claude_command())
    debug = _prompt("Enable debug logging? (y/N)", "N")

    config = {
        "bot_token": token.strip(),
        "authorized_users": ids,
        "projects_root": projects_root,
        "max_per_user": int(max_per_user) if max_per_user.isdigit() else 3,
        "claude_command": claude_cmd,
        "debug": debug.lower().startswith("y"),
    }

    path = generate_config_yaml(config, install_dir)
    print(f"\n  Config written to: {path}")
    return path


def main():
    """Entry point for claude-ctim-configure console script."""
    import sys
    install_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    interactive_configure(install_dir)
