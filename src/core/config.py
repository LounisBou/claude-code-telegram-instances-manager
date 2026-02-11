from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


@dataclass
class TelegramConfig:
    """Telegram bot connection and authorization settings."""

    bot_token: str
    authorized_users: list[int]


@dataclass
class ProjectsConfig:
    """Project discovery and scanning settings."""

    root: str
    scan_depth: int = 1


@dataclass
class SessionsConfig:
    """Per-user session limits and output buffering settings."""

    max_per_user: int = 3
    output_debounce_ms: int = 500
    output_max_buffer: int = 2000
    silence_warning_minutes: int = 10


@dataclass
class ClaudeConfig:
    """Claude Code CLI invocation and environment settings."""

    command: str = "claude"
    env: dict[str, str] = field(default_factory=dict)
    default_args: list[str] = field(default_factory=list)
    update_command: str = "claude update"


@dataclass
class DatabaseConfig:
    """SQLite database location settings."""

    path: str = "data/sessions.db"


@dataclass
class DebugConfig:
    """Debug mode settings."""

    enabled: bool = False
    trace: bool = False
    verbose: bool = False


@dataclass
class AppConfig:
    """Top-level application configuration aggregating all subsections."""

    telegram: TelegramConfig
    projects: ProjectsConfig
    sessions: SessionsConfig
    claude: ClaudeConfig
    database: DatabaseConfig
    debug: DebugConfig = field(default_factory=DebugConfig)

    def is_authorized(self, user_id: int) -> bool:
        """Check whether a Telegram user is allowed to use the bot."""
        return user_id in self.telegram.authorized_users


def load_config(path: str) -> AppConfig:
    """Load and validate application configuration from a YAML file.

    Reads the YAML file at the given path, validates that all required
    fields are present, and constructs a fully populated AppConfig with
    defaults applied for optional fields.

    Args:
        path: Filesystem path to the YAML configuration file.

    Returns:
        A fully populated AppConfig instance.

    Raises:
        ConfigError: If the file does not exist or required fields
            (bot_token, authorized_users, projects.root) are missing.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    telegram_raw = raw.get("telegram", {})
    if not telegram_raw.get("bot_token"):
        raise ConfigError("telegram.bot_token is required")
    if not telegram_raw.get("authorized_users"):
        raise ConfigError("telegram.authorized_users must not be empty")

    projects_raw = raw.get("projects", {})
    if not projects_raw.get("root"):
        raise ConfigError("projects.root is required")

    # `or {}` fallback handles YAML null values for optional sections
    sessions_raw = raw.get("sessions", {}) or {}
    claude_raw = raw.get("claude", {}) or {}
    database_raw = raw.get("database", {}) or {}

    logger.debug("Loaded config from %s", path)
    logger.debug("Projects root=%s scan_depth=%d", projects_raw["root"], projects_raw.get("scan_depth", 1))

    return AppConfig(
        telegram=TelegramConfig(
            bot_token=telegram_raw["bot_token"],
            authorized_users=telegram_raw["authorized_users"],
        ),
        projects=ProjectsConfig(
            root=projects_raw["root"],
            scan_depth=projects_raw.get("scan_depth", 1),
        ),
        sessions=SessionsConfig(
            max_per_user=sessions_raw.get("max_per_user", 3),
            output_debounce_ms=sessions_raw.get("output_debounce_ms", 500),
            output_max_buffer=sessions_raw.get("output_max_buffer", 2000),
            silence_warning_minutes=sessions_raw.get("silence_warning_minutes", 10),
        ),
        claude=ClaudeConfig(
            command=claude_raw.get("command", "claude"),
            env=claude_raw.get("env", {}),
            default_args=claude_raw.get("default_args", []),
            update_command=claude_raw.get("update_command", "claude update"),
        ),
        database=DatabaseConfig(
            path=database_raw.get("path", "data/sessions.db"),
        ),
        debug=DebugConfig(
            enabled=bool((raw.get("debug", {}) or {}).get("enabled", False)),
        ),
    )
