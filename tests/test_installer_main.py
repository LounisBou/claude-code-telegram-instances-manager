# tests/test_installer_main.py
import os
from unittest.mock import MagicMock, call, patch

from installer.main import Installer


class TestInstaller:
    def test_copy_project_creates_target(self, tmp_path):
        source = tmp_path / "source"
        source.mkdir()
        (source / "src").mkdir()
        (source / "src" / "main.py").write_text("# test")
        (source / "pyproject.toml").write_text("[project]")

        target = tmp_path / "target"
        installer = Installer.__new__(Installer)
        installer._copy_project(str(source), str(target))
        assert (target / "src" / "main.py").exists()
        assert (target / "pyproject.toml").exists()

    def test_create_venv(self, tmp_path):
        installer = Installer.__new__(Installer)
        installer.install_dir = str(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            installer._create_venv()
            assert any("venv" in str(c) for c in mock_run.call_args_list)

    def test_setup_database(self, tmp_path):
        installer = Installer.__new__(Installer)
        installer.install_dir = str(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            installer._setup_database()
        assert (tmp_path / "data").is_dir()
