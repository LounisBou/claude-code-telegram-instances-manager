from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


@dataclass
class TelegramConfig:
    bot_token: str
    authorized_users: list[int]


@dataclass
class ProjectsConfig:
    root: str
    scan_depth: int = 1


@dataclass
class SessionsConfig:
    max_per_user: int = 3
    output_debounce_ms: int = 500
    output_max_buffer: int = 2000
    silence_warning_minutes: int = 10


@dataclass
class ClaudeConfig:
    command: str = "claude"
    env: dict[str, str] = field(default_factory=dict)
    default_args: list[str] = field(default_factory=list)
    update_command: str = "claude update"


@dataclass
class DatabaseConfig:
    path: str = "data/sessions.db"


@dataclass
class AppConfig:
    telegram: TelegramConfig
    projects: ProjectsConfig
    sessions: SessionsConfig
    claude: ClaudeConfig
    database: DatabaseConfig

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self.telegram.authorized_users


def load_config(path: str) -> AppConfig:
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

    sessions_raw = raw.get("sessions", {}) or {}
    claude_raw = raw.get("claude", {}) or {}
    database_raw = raw.get("database", {}) or {}

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
    )
