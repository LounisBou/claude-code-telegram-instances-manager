# tests/test_installer_health.py
import json
import os
from unittest.mock import patch

from installer.health import CheckResult, run_health_checks


class TestHealthChecks:
    def test_config_check_passes(self, tmp_path):
        config = tmp_path / "config.yaml"
        config.write_text(
            'telegram:\n  bot_token: "123:abc"\n'
            '  authorized_users:\n    - 111\n'
            'projects:\n  root: "/tmp"\n'
        )
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(config),
        )
        config_result = next(r for r in results if r.name == "Config file")
        assert config_result.passed is True

    def test_config_check_fails_missing(self, tmp_path):
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "nonexistent.yaml"),
        )
        config_result = next(r for r in results if r.name == "Config file")
        assert config_result.passed is False

    def test_db_check_passes(self, tmp_path):
        import sqlite3
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "sessions.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY)")
        conn.close()
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "config.yaml"),
        )
        db_result = next(r for r in results if r.name == "Database")
        assert db_result.passed is True

    def test_returns_list_of_check_results(self, tmp_path):
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "nonexistent.yaml"),
        )
        assert len(results) >= 4
        assert all(isinstance(r, CheckResult) for r in results)
