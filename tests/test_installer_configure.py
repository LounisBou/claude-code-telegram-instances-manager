# tests/test_installer_configure.py
import os

import yaml

from installer.configure import (
    generate_config_yaml,
    validate_bot_token,
    validate_user_ids,
)


class TestValidation:
    def test_valid_bot_token(self):
        assert validate_bot_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is True

    def test_invalid_bot_token_no_colon(self):
        assert validate_bot_token("invalidtoken") is False

    def test_invalid_bot_token_empty(self):
        assert validate_bot_token("") is False

    def test_valid_user_ids(self):
        assert validate_user_ids("123,456,789") == [123, 456, 789]

    def test_valid_single_user_id(self):
        assert validate_user_ids("123") == [123]

    def test_invalid_user_ids(self):
        assert validate_user_ids("abc,def") is None

    def test_empty_user_ids(self):
        assert validate_user_ids("") is None


class TestGenerateConfig:
    def test_generates_valid_yaml(self, tmp_path):
        config = {
            "bot_token": "123:abc",
            "authorized_users": [111],
            "projects_root": "/tmp/projects",
            "max_per_user": 3,
            "claude_command": "claude",
            "debug": False,
        }
        path = generate_config_yaml(config, str(tmp_path))
        assert os.path.isfile(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["telegram"]["bot_token"] == "123:abc"
        assert data["telegram"]["authorized_users"] == [111]
        assert data["projects"]["root"] == "/tmp/projects"
        assert data["sessions"]["max_per_user"] == 3
        assert data["database"]["path"] == "data/sessions.db"
