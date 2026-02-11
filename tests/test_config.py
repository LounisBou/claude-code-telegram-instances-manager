# tests/test_config.py
import pytest
import yaml

from src.core.config import AppConfig, load_config, ConfigError


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {
                "bot_token": "test-token-123",
                "authorized_users": [111, 222],
            },
            "projects": {"root": "/tmp/projects", "scan_depth": 1},
            "sessions": {
                "max_per_user": 3,
                "output_debounce_ms": 500,
                "output_max_buffer": 2000,
                "silence_warning_minutes": 10,
            },
            "claude": {
                "command": "claude",
                "default_args": [],
                "update_command": "claude update",
            },
            "database": {"path": "data/sessions.db"},
        }))
        config = load_config(str(config_file))
        assert config.telegram.bot_token == "test-token-123"
        assert config.telegram.authorized_users == [111, 222]
        assert config.projects.root == "/tmp/projects"
        assert config.sessions.max_per_user == 3
        assert config.claude.command == "claude"
        assert config.database.path == "data/sessions.db"

    def test_missing_file_raises(self):
        with pytest.raises(ConfigError, match="not found"):
            load_config("/nonexistent/config.yaml")

    def test_missing_bot_token_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"authorized_users": [111]},
            "projects": {"root": "/tmp"},
            "sessions": {},
            "claude": {},
            "database": {},
        }))
        with pytest.raises(ConfigError, match="bot_token"):
            load_config(str(config_file))

    def test_empty_authorized_users_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": []},
            "projects": {"root": "/tmp"},
            "sessions": {},
            "claude": {},
            "database": {},
        }))
        with pytest.raises(ConfigError, match="authorized_users"):
            load_config(str(config_file))

    def test_defaults_applied(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1]},
            "projects": {"root": "/tmp"},
        }))
        config = load_config(str(config_file))
        assert config.sessions.max_per_user == 3
        assert config.sessions.output_debounce_ms == 500
        assert config.sessions.output_max_buffer == 2000
        assert config.sessions.silence_warning_minutes == 10
        assert config.claude.command == "claude"
        assert config.claude.env == {}
        assert config.claude.default_args == []
        assert config.claude.update_command == "claude update"
        assert config.database.path == "data/sessions.db"

    def test_claude_env_loaded(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1]},
            "projects": {"root": "/tmp"},
            "claude": {
                "command": "claude",
                "env": {"CLAUDE_CONFIG_DIR": "~/.claude-work", "FOO": "bar"},
            },
        }))
        config = load_config(str(config_file))
        assert config.claude.env == {
            "CLAUDE_CONFIG_DIR": "~/.claude-work",
            "FOO": "bar",
        }


class TestAppConfig:
    def test_is_authorized(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [111, 222]},
            "projects": {"root": "/tmp"},
        }))
        config = load_config(str(config_file))
        assert config.is_authorized(111) is True
        assert config.is_authorized(999) is False


class TestEditRateLimit:
    """Config must support telegram.edit_rate_limit."""

    def test_default_edit_rate_limit(self, tmp_path):
        """TelegramConfig defaults edit_rate_limit to 3."""
        import yaml
        from src.core.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1]},
            "projects": {"root": "/tmp"},
        }))
        cfg = load_config(str(config_file))
        assert cfg.telegram.edit_rate_limit == 3

    def test_custom_edit_rate_limit(self, tmp_path):
        """edit_rate_limit can be overridden in config."""
        import yaml
        from src.core.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1], "edit_rate_limit": 5},
            "projects": {"root": "/tmp"},
        }))
        cfg = load_config(str(config_file))
        assert cfg.telegram.edit_rate_limit == 5


class TestDebugConfig:
    def test_debug_config_defaults(self):
        from src.core.config import DebugConfig
        dc = DebugConfig()
        assert dc.enabled is False
        assert dc.trace is False
        assert dc.verbose is False
