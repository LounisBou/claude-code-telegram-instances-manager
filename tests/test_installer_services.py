# tests/test_installer_services.py
import os
from unittest.mock import patch

from installer.services import (
    generate_launchd_plist,
    generate_systemd_unit,
    get_service_path,
)


class TestGenerateSystemdUnit:
    def test_generates_valid_unit(self, tmp_path):
        unit = generate_systemd_unit(
            install_dir="/tmp/test-claude-ctim",
            user="testuser",
            config_path="/tmp/test-claude-ctim/config.yaml",
        )
        assert "[Unit]" in unit
        assert "[Service]" in unit
        assert "[Install]" in unit
        assert "/tmp/test-claude-ctim" in unit
        assert "testuser" in unit
        assert "python -m src.main" in unit

    def test_writes_to_file(self, tmp_path):
        unit = generate_systemd_unit(
            install_dir="/tmp/test-claude-ctim", user="testuser",
            config_path="/tmp/test-claude-ctim/config.yaml",
        )
        path = tmp_path / "test.service"
        path.write_text(unit)
        assert path.read_text().startswith("[Unit]")


class TestGenerateLaunchdPlist:
    def test_generates_valid_plist(self):
        plist = generate_launchd_plist(
            install_dir="/tmp/test-claude-ctim",
            config_path="/tmp/test-claude-ctim/config.yaml",
        )
        assert "<?xml" in plist
        assert "com.claude-ctim" in plist
        assert "/tmp/test-claude-ctim" in plist
        assert "src.main" in plist

    def test_contains_keep_alive(self):
        plist = generate_launchd_plist(
            install_dir="/tmp/test-claude-ctim",
            config_path="/tmp/test-claude-ctim/config.yaml",
        )
        assert "KeepAlive" in plist


class TestGetServicePath:
    def test_launchd(self):
        path = get_service_path("launchd", "/home/test")
        assert "LaunchAgents" in path
        assert "com.claude-ctim.plist" in path

    def test_systemd_user(self):
        path = get_service_path("systemd_user", "/home/test")
        assert ".config/systemd/user" in path
        assert "claude-ctim.service" in path
