# installer/uninstall.py
"""Uninstaller for claude-ctim — reads manifest and reverses the install."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from installer.constants import APP_NAME, MANIFEST_FILENAME
from installer.manifest import InstallManifest, load_manifest


def _confirm(message: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"{message} {suffix}: ").strip().lower()
    if not answer:
        return default_yes
    return answer.startswith("y")


class Uninstaller:
    """Reads install manifest and reverses the installation."""

    def __init__(self, install_dir: str):
        self.install_dir = install_dir
        self.manifest: InstallManifest | None = load_manifest(install_dir)

    def run(self):
        """Execute the full uninstall flow."""
        if self.manifest is None:
            print(f"No install manifest found in {self.install_dir}")
            print("Cannot determine what to uninstall.")
            sys.exit(1)

        print(f"\n{'='*50}")
        print(f"  {APP_NAME} Uninstaller")
        print(f"{'='*50}\n")
        print(f"  Install dir: {self.manifest.install_dir}")
        print(f"  Service:     {self.manifest.service_file}")
        print()

        if not _confirm("Proceed with uninstall?"):
            print("Aborted.")
            return

        print("Stopping service...")
        self._stop_service()

        print("Removing service file...")
        self._remove_service_file()

        keep_data = _confirm("Keep config and database?", default_yes=True)

        print("Removing virtual environment...")
        self._remove_venv()

        if not keep_data:
            print("Removing config and database...")
            self._remove_data()

        self._remove_manifest()
        self._remove_install_dir_if_empty()

        print(f"\n  {APP_NAME} uninstalled successfully.")
        if keep_data:
            print(f"  Config and database preserved in {self.install_dir}")
        print()

    def _stop_service(self):
        """Stop the running service."""
        if not self.manifest.service_file:
            return
        try:
            if self.manifest.service_type == "launchd":
                subprocess.run(
                    ["launchctl", "unload", self.manifest.service_file],
                    check=False, capture_output=True,
                )
            elif self.manifest.service_type == "systemd_user":
                subprocess.run(
                    ["systemctl", "--user", "stop", APP_NAME],
                    check=False, capture_output=True,
                )
                subprocess.run(
                    ["systemctl", "--user", "disable", APP_NAME],
                    check=False, capture_output=True,
                )
            elif self.manifest.service_type == "systemd_system":
                subprocess.run(
                    ["sudo", "systemctl", "stop", APP_NAME],
                    check=False, capture_output=True,
                )
                subprocess.run(
                    ["sudo", "systemctl", "disable", APP_NAME],
                    check=False, capture_output=True,
                )
        except Exception as e:
            print(f"  Warning: could not stop service: {e}")

    def _remove_service_file(self):
        """Delete the service file."""
        if self.manifest.service_file and os.path.isfile(self.manifest.service_file):
            os.remove(self.manifest.service_file)
            print(f"  Removed: {self.manifest.service_file}")

    def _remove_venv(self):
        """Delete the virtual environment."""
        venv = self.manifest.venv_path
        if os.path.isdir(venv):
            shutil.rmtree(venv)
            print(f"  Removed: {venv}")

    def _remove_data(self):
        """Delete config.yaml and the data directory."""
        if os.path.isfile(self.manifest.config_path):
            os.remove(self.manifest.config_path)
        data_dir = os.path.dirname(self.manifest.db_path)
        if os.path.isdir(data_dir):
            shutil.rmtree(data_dir)

    def _remove_manifest(self):
        """Delete the install manifest."""
        path = os.path.join(self.install_dir, MANIFEST_FILENAME)
        if os.path.isfile(path):
            os.remove(path)

    def _remove_install_dir_if_empty(self):
        """Remove the install directory if it's empty."""
        try:
            remaining = os.listdir(self.install_dir)
            if not remaining:
                os.rmdir(self.install_dir)
                print(f"  Removed empty directory: {self.install_dir}")
        except OSError:
            pass


def main():
    """Entry point for claude-ctim-uninstall console script."""
    install_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    uninstaller = Uninstaller(install_dir)
    uninstaller.run()
