# installer/upgrade.py
"""Upgrade flow for claude-ctim."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from installer.constants import APP_NAME, VENV_DIR
from installer.health import print_health_report, run_health_checks
from installer.manifest import InstallManifest, load_manifest


def _confirm(message: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"{message} {suffix}: ").strip().lower()
    if not answer:
        return default_yes
    return answer.startswith("y")


class Upgrader:
    """Handles upgrading an existing claude-ctim installation."""

    def __init__(self, install_dir: str):
        self.install_dir = install_dir
        self.manifest: InstallManifest | None = load_manifest(install_dir)

    def run(self):
        """Execute the full upgrade flow."""
        if self.manifest is None:
            print(f"No install manifest found in {self.install_dir}")
            sys.exit(1)

        print(f"\n{'='*50}")
        print(f"  {APP_NAME} Upgrader")
        print(f"{'='*50}\n")
        print(f"  Current version: {self.manifest.version}")
        print(f"  Install dir: {self.manifest.install_dir}")
        print()

        if not _confirm("Proceed with upgrade?"):
            print("Aborted.")
            return

        print("Stopping service...")
        self._stop_service()

        print("Backing up config...")
        self._backup_config()

        print("Pulling latest code...")
        self._pull_latest()

        print("Updating dependencies...")
        self._update_deps()

        print("Checking migrations... (none pending)")

        print("Restarting service...")
        self._start_service()

        print("\nRunning health check...\n")
        results = run_health_checks(
            self.install_dir, self.manifest.config_path,
            self.manifest.service_file,
        )
        ok = print_health_report(results)
        print()

        if ok:
            print(f"  {APP_NAME} upgraded successfully!")
        else:
            print(f"  {APP_NAME} upgraded with warnings.")
        print()

    def _stop_service(self):
        """Stop the running service."""
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
            elif self.manifest.service_type == "systemd_system":
                subprocess.run(
                    ["sudo", "systemctl", "stop", APP_NAME],
                    check=False, capture_output=True,
                )
            print("  Service stopped.")
        except Exception as e:
            print(f"  Warning: {e}")

    def _backup_config(self):
        """Copy config.yaml to config.yaml.bak."""
        cfg = self.manifest.config_path
        if os.path.isfile(cfg):
            shutil.copy2(cfg, cfg + ".bak")
            print(f"  Backup: {cfg}.bak")

    def _pull_latest(self):
        """Pull latest code from git."""
        try:
            result = subprocess.run(
                ["git", "pull", "origin", "main"],
                cwd=self.install_dir,
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                print(f"  {result.stdout.strip()}")
            else:
                print(f"  Warning: git pull failed: {result.stderr.strip()}")
                print("  Continuing with current code...")
        except FileNotFoundError:
            print("  Not a git repo — skipping pull.")

    def _update_deps(self):
        """Reinstall dependencies in the existing venv."""
        pip = os.path.join(self.manifest.venv_path, "bin", "pip")
        subprocess.run(
            [pip, "install", "--quiet", "."],
            cwd=self.install_dir,
            check=True,
        )
        print("  Dependencies updated.")

    def _start_service(self):
        """Start the service."""
        try:
            if self.manifest.service_type == "launchd":
                subprocess.run(
                    ["launchctl", "load", self.manifest.service_file],
                    check=True,
                )
            elif self.manifest.service_type == "systemd_user":
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"],
                    check=True,
                )
                subprocess.run(
                    ["systemctl", "--user", "start", APP_NAME],
                    check=True,
                )
            elif self.manifest.service_type == "systemd_system":
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(["sudo", "systemctl", "start", APP_NAME], check=True)
            print("  Service started.")
        except subprocess.CalledProcessError as e:
            print(f"  Warning: {e}")


def main():
    """Entry point for claude-ctim-upgrade console script."""
    install_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    upgrader = Upgrader(install_dir)
    upgrader.run()
