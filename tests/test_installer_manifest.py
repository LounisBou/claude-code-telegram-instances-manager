# tests/test_installer_manifest.py
import json

from installer.manifest import InstallManifest, load_manifest, save_manifest


class TestManifest:
    def test_save_and_load(self, tmp_path):
        manifest = InstallManifest(
            app_name="claude-ctim",
            version="1.0.0",
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "config.yaml"),
            venv_path=str(tmp_path / ".venv"),
            db_path=str(tmp_path / "data" / "sessions.db"),
            service_file="/tmp/test.service",
            service_type="systemd_user",
            platform="linux",
        )
        save_manifest(manifest, str(tmp_path))
        loaded = load_manifest(str(tmp_path))
        assert loaded.app_name == "claude-ctim"
        assert loaded.install_dir == str(tmp_path)
        assert loaded.service_type == "systemd_user"

    def test_load_missing_returns_none(self, tmp_path):
        loaded = load_manifest(str(tmp_path))
        assert loaded is None

    def test_manifest_file_is_valid_json(self, tmp_path):
        manifest = InstallManifest(
            app_name="test", version="0.1", install_dir=str(tmp_path),
            config_path="c", venv_path="v", db_path="d",
            service_file="s", service_type="launchd", platform="macos",
        )
        save_manifest(manifest, str(tmp_path))
        with open(tmp_path / "install_manifest.json") as f:
            data = json.load(f)
        assert data["app_name"] == "test"
        assert "installed_at" in data
