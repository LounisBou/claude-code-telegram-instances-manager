# tests/test_installer_constants.py
from installer.constants import APP_NAME, DEFAULT_INSTALL_DIR, MANIFEST_FILENAME


class TestConstants:
    def test_app_name(self):
        assert APP_NAME == "claude-ctim"

    def test_default_install_dir(self):
        assert APP_NAME in DEFAULT_INSTALL_DIR
        assert DEFAULT_INSTALL_DIR.startswith("/opt/")

    def test_manifest_filename(self):
        assert MANIFEST_FILENAME == "install_manifest.json"
