# tests/test_installer_prerequisites.py
from unittest.mock import MagicMock, patch

from installer.platform import PlatformInfo
from installer.prerequisites import PrereqResult, check_prerequisites


def _make_platform(**kwargs) -> PlatformInfo:
    defaults = dict(
        os="linux", distro="ubuntu", package_manager="apt",
        init_system="systemd", user="test", home="/home/test",
    )
    defaults.update(kwargs)
    return PlatformInfo(**defaults)


class TestCheckPrerequisites:
    @patch("shutil.which", return_value="/usr/bin/git")
    @patch("installer.prerequisites._check_python_version", return_value=(True, "3.12.1"))
    @patch("installer.prerequisites._check_claude_cli", return_value=(True, "1.2.3"))
    @patch("installer.prerequisites._check_gh_cli", return_value=(True, "2.40.0"))
    def test_all_present(self, *mocks):
        results = check_prerequisites(_make_platform())
        assert all(r.found for r in results)

    @patch("shutil.which", return_value=None)
    @patch("installer.prerequisites._check_python_version", return_value=(True, "3.12.1"))
    @patch("installer.prerequisites._check_claude_cli", return_value=(False, None))
    @patch("installer.prerequisites._check_gh_cli", return_value=(False, None))
    def test_missing_deps(self, *mocks):
        results = check_prerequisites(_make_platform())
        missing = [r for r in results if not r.found]
        assert len(missing) >= 1

    def test_prereq_result_has_install_hint(self):
        r = PrereqResult(name="git", found=False, version=None,
                         required=True, install_cmd="apt install git")
        assert r.install_cmd == "apt install git"
