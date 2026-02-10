# tests/test_installer_uninstall.py
import json
import os
from unittest.mock import patch

from installer.manifest import InstallManifest, save_manifest
from installer.uninstall import Uninstaller


def _write_manifest(tmp_path, **overrides):
    defaults = dict(
        app_name="claude-ctim", version="0.1.0",
        install_dir=str(tmp_path), config_path=str(tmp_path / "config.yaml"),
        venv_path=str(tmp_path / ".venv"), db_path=str(tmp_path / "data" / "sessions.db"),
        service_file=str(tmp_path / "test.service"), service_type="systemd_user",
        platform="linux",
    )
    defaults.update(overrides)
    manifest = InstallManifest(**defaults)
    save_manifest(manifest, str(tmp_path))
    return manifest


class TestUninstaller:
    def test_loads_manifest(self, tmp_path):
        _write_manifest(tmp_path)
        u = Uninstaller(str(tmp_path))
        assert u.manifest is not None
        assert u.manifest.app_name == "claude-ctim"

    def test_missing_manifest_raises(self, tmp_path):
        u = Uninstaller(str(tmp_path))
        assert u.manifest is None

    def test_remove_venv(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "bin").mkdir()
        _write_manifest(tmp_path)
        u = Uninstaller(str(tmp_path))
        u._remove_venv()
        assert not venv.exists()

    def test_remove_service_file(self, tmp_path):
        svc = tmp_path / "test.service"
        svc.write_text("[Unit]")
        _write_manifest(tmp_path, service_file=str(svc))
        u = Uninstaller(str(tmp_path))
        with patch("subprocess.run"):
            u._stop_service()
        u._remove_service_file()
        assert not svc.exists()
