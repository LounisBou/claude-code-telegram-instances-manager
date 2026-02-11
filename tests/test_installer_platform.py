# tests/test_installer_platform.py
from unittest.mock import patch

from installer.platform import PlatformInfo, detect_platform


class TestDetectPlatform:
    @patch("platform.system", return_value="Darwin")
    @patch("shutil.which", return_value="/opt/homebrew/bin/brew")
    def test_macos(self, mock_which, mock_system):
        info = detect_platform()
        assert info.os == "macos"
        assert info.init_system == "launchd"
        assert info.package_manager == "brew"

    @patch("platform.system", return_value="Linux")
    @patch("installer.platform._detect_distro", return_value="ubuntu")
    @patch("shutil.which", side_effect=lambda cmd: "/usr/bin/apt" if cmd == "apt" else None)
    @patch("installer.platform._has_systemd", return_value=True)
    def test_linux_ubuntu(self, mock_sys, mock_distro, mock_which, mock_system):
        info = detect_platform()
        assert info.os == "linux"
        assert info.distro == "ubuntu"
        assert info.package_manager == "apt"
        assert info.init_system == "systemd"

    def test_platform_info_fields(self):
        info = PlatformInfo(
            os="linux", distro="debian", package_manager="apt",
            init_system="systemd", user="testuser", home="/home/testuser",
        )
        assert info.os == "linux"
        assert info.user == "testuser"
