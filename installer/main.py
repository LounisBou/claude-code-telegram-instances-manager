# installer/main.py
"""Main install orchestrator for claude-ctim."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from installer.configure import interactive_configure
from installer.constants import (
    APP_NAME,
    CONFIG_FILENAME,
    DATA_DIR,
    DB_FILENAME,
    DEFAULT_INSTALL_DIR,
    VENV_DIR,
)
from installer.health import print_health_report, run_health_checks
from installer.manifest import InstallManifest, save_manifest
from installer.platform import PlatformInfo, detect_platform
from installer.prerequisites import check_prerequisites
from installer.services import (
    generate_launchd_plist,
    generate_systemd_unit,
    get_service_path,
)


def _prompt(message: str, default: str | None = None) -> str:
    if default is not None:
        message = f"{message} [{default}]: "
    else:
        message = f"{message}: "
    value = input(message).strip()
    return value if value else (default or "")


def _confirm(message: str, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"{message} {suffix}: ").strip().lower()
    if not answer:
        return default_yes
    return answer.startswith("y")


class Installer:
    """Orchestrates the full install flow."""

    def __init__(self):
        self.platform: PlatformInfo | None = None
        self.install_dir: str = ""
        self.config_path: str = ""
        self.service_path: str = ""
        self.service_type: str = ""

    def run(self):
        """Execute the full install flow."""
        print(f"\n{'='*50}")
        print(f"  {APP_NAME} Installer")
        print(f"{'='*50}\n")

        # Step 1: Platform detection
        print("Step 1/8: Detecting platform...")
        self.platform = detect_platform()
        print(f"  OS: {self.platform.os}")
        if self.platform.distro:
            print(f"  Distro: {self.platform.distro}")
        print(f"  Package manager: {self.platform.package_manager or 'none detected'}")
        print(f"  Init system: {self.platform.init_system}")
        print()

        # Step 2: Prerequisites
        print("Step 2/8: Checking prerequisites...")
        results = check_prerequisites(self.platform)
        all_ok = True
        for r in results:
            icon = "\u2713" if r.found else "\u2717"
            label = f" ({r.version})" if r.version else ""
            print(f"  {icon} {r.name}{label}")
            if not r.found and r.required:
                all_ok = False
                if r.install_cmd and _confirm(f"    Install {r.name}?"):
                    print(f"    Running: {r.install_cmd}")
                    subprocess.run(r.install_cmd, shell=True, check=False)
                elif r.required:
                    print(f"    ERROR: {r.name} is required. Aborting.")
                    sys.exit(1)
            elif not r.found and not r.required:
                if r.install_cmd:
                    print(f"    Optional. Install later with: {r.install_cmd}")
        print()

        # Step 3: Install location
        print("Step 3/8: Install location")
        self.install_dir = _prompt(
            "Install directory", DEFAULT_INSTALL_DIR,
        )
        self._prepare_install_dir()
        print()

        # Step 4: Config generation
        print("Step 4/8: Configuration")
        self.config_path = interactive_configure(self.install_dir)
        print()

        # Step 5: Venv & dependencies
        print("Step 5/8: Setting up Python environment...")
        self._create_venv()
        self._install_deps()
        print()

        # Step 5.5: Database setup
        print("Step 6/8: Setting up database...")
        self._setup_database()
        print()

        # Step 6: Service creation
        print("Step 7/8: Creating service...")
        self._create_service()
        print()

        # Step 7: Manifest
        print("Step 8/8: Saving install manifest...")
        self._save_manifest()
        print()

        # Step 8: Health check
        print("Running health check...\n")
        results = run_health_checks(
            self.install_dir, self.config_path, self.service_path,
        )
        ok = print_health_report(results)
        print()

        if ok:
            print(f"  {APP_NAME} installed successfully!")
        else:
            print(f"  {APP_NAME} installed with warnings. Check above.")

        print(f"\n  Install dir:  {self.install_dir}")
        print(f"  Config:       {self.config_path}")
        print(f"  Service:      {self.service_path}")
        print()

    def _prepare_install_dir(self):
        """Create install directory, copying project files into it."""
        if os.path.isdir(self.install_dir):
            if not _confirm(f"  {self.install_dir} exists. Overwrite?", default_yes=False):
                print("  Aborting.")
                sys.exit(0)

        source = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if source != os.path.abspath(self.install_dir):
            self._copy_project(source, self.install_dir)
        else:
            print(f"  Already in install dir: {self.install_dir}")

    def _copy_project(self, source: str, target: str):
        """Copy project files to install directory."""
        os.makedirs(target, exist_ok=True)
        for item in ("src", "installer", "pyproject.toml", "requirements.txt",
                      "config.yaml.example", "scripts"):
            src_path = os.path.join(source, item)
            dst_path = os.path.join(target, item)
            if os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
            elif os.path.isfile(src_path):
                shutil.copy2(src_path, dst_path)
        print(f"  Copied project to {target}")

    def _create_venv(self):
        """Create a Python virtual environment."""
        venv_path = os.path.join(self.install_dir, VENV_DIR)
        subprocess.run(
            [sys.executable, "-m", "venv", venv_path],
            check=True,
        )
        print(f"  Created venv at {venv_path}")

    def _install_deps(self):
        """Install project dependencies into the venv."""
        pip = os.path.join(self.install_dir, VENV_DIR, "bin", "pip")
        subprocess.run(
            [pip, "install", "--quiet", "."],
            cwd=self.install_dir,
            check=True,
        )
        print("  Dependencies installed.")

    def _setup_database(self):
        """Create the data directory and initialize the database schema."""
        data_dir = os.path.join(self.install_dir, DATA_DIR)
        os.makedirs(data_dir, exist_ok=True)
        db_path = os.path.join(data_dir, DB_FILENAME)
        venv_python = os.path.join(self.install_dir, VENV_DIR, "bin", "python")
        init_script = (
            "import asyncio; "
            f"from src.database import Database; "
            f"db = Database('{db_path}'); "
            "asyncio.run(db.initialize()); "
            "asyncio.run(db.close()); "
            "print('  Database initialized.')"
        )
        subprocess.run(
            [venv_python, "-c", init_script],
            cwd=self.install_dir,
            check=True,
        )

    def _create_service(self):
        """Generate and install the appropriate service file."""
        if self.platform.init_system == "launchd":
            self.service_type = "launchd"
            content = generate_launchd_plist(self.install_dir, self.config_path)
            self.service_path = get_service_path("launchd", self.platform.home)
            os.makedirs(os.path.join(self.install_dir, "logs"), exist_ok=True)
        elif self.platform.init_system == "systemd":
            if _confirm("  Install as user service (no sudo)?"):
                self.service_type = "systemd_user"
            else:
                self.service_type = "systemd_system"
            content = generate_systemd_unit(
                self.install_dir, self.platform.user, self.config_path,
            )
            self.service_path = get_service_path(self.service_type, self.platform.home)
        else:
            print("  Unknown init system. Skipping service creation.")
            return

        os.makedirs(os.path.dirname(self.service_path), exist_ok=True)
        with open(self.service_path, "w") as f:
            f.write(content)
        print(f"  Service file written to: {self.service_path}")

        if _confirm("  Start the service now?"):
            self._start_service()

    def _start_service(self):
        """Start the service."""
        try:
            if self.service_type == "launchd":
                subprocess.run(
                    ["launchctl", "load", self.service_path], check=True,
                )
            elif self.service_type == "systemd_user":
                subprocess.run(
                    ["systemctl", "--user", "daemon-reload"], check=True,
                )
                subprocess.run(
                    ["systemctl", "--user", "enable", "--now", APP_NAME],
                    check=True,
                )
            elif self.service_type == "systemd_system":
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                subprocess.run(
                    ["sudo", "systemctl", "enable", "--now", APP_NAME],
                    check=True,
                )
            print("  Service started.")
        except subprocess.CalledProcessError as e:
            print(f"  Warning: Failed to start service: {e}")

    def _save_manifest(self):
        """Write the install manifest."""
        manifest = InstallManifest(
            app_name=APP_NAME,
            version="0.1.0",
            install_dir=self.install_dir,
            config_path=self.config_path,
            venv_path=os.path.join(self.install_dir, VENV_DIR),
            db_path=os.path.join(self.install_dir, DATA_DIR, DB_FILENAME),
            service_file=self.service_path,
            service_type=self.service_type,
            platform=self.platform.os,
        )
        path = save_manifest(manifest, self.install_dir)
        print(f"  Manifest saved to: {path}")


def main():
    """Entry point for claude-ctim-install console script."""
    installer = Installer()
    installer.run()


if __name__ == "__main__":
    main()
