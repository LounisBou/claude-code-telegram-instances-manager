# tests/test_installer_upgrade.py
import os
from unittest.mock import MagicMock, patch

from installer.manifest import InstallManifest, save_manifest
from installer.upgrade import Upgrader


def _setup_manifest(tmp_path):
    manifest = InstallManifest(
        app_name="claude-ctim", version="0.1.0",
        install_dir=str(tmp_path), config_path=str(tmp_path / "config.yaml"),
        venv_path=str(tmp_path / ".venv"), db_path=str(tmp_path / "data" / "sessions.db"),
        service_file=str(tmp_path / "test.service"), service_type="systemd_user",
        platform="linux",
    )
    save_manifest(manifest, str(tmp_path))
    (tmp_path / "config.yaml").write_text("test: true")
    return manifest


class TestUpgrader:
    def test_loads_manifest(self, tmp_path):
        _setup_manifest(tmp_path)
        u = Upgrader(str(tmp_path))
        assert u.manifest is not None

    def test_backup_config(self, tmp_path):
        _setup_manifest(tmp_path)
        u = Upgrader(str(tmp_path))
        u._backup_config()
        assert (tmp_path / "config.yaml.bak").exists()
        assert (tmp_path / "config.yaml.bak").read_text() == "test: true"

    def test_update_deps(self, tmp_path):
        _setup_manifest(tmp_path)
        u = Upgrader(str(tmp_path))
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            u._update_deps()
            assert mock_run.called
