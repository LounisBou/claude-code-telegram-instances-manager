# installer/manifest.py
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from getpass import getuser

from installer.constants import MANIFEST_FILENAME


@dataclass
class InstallManifest:
    """Tracks what was installed and where, for uninstall/upgrade."""
    app_name: str
    version: str
    install_dir: str
    config_path: str
    venv_path: str
    db_path: str
    service_file: str
    service_type: str    # "launchd", "systemd_user", "systemd_system"
    platform: str        # "macos", "linux"
    installed_at: str = ""
    installed_by: str = ""

    def __post_init__(self):
        if not self.installed_at:
            self.installed_at = datetime.now(timezone.utc).isoformat()
        if not self.installed_by:
            self.installed_by = getuser()


def save_manifest(manifest: InstallManifest, install_dir: str) -> str:
    """Write the manifest to install_dir/install_manifest.json. Returns path."""
    path = os.path.join(install_dir, MANIFEST_FILENAME)
    with open(path, "w") as f:
        json.dump(asdict(manifest), f, indent=2)
    return path


def load_manifest(install_dir: str) -> InstallManifest | None:
    """Load manifest from install_dir. Returns None if not found."""
    path = os.path.join(install_dir, MANIFEST_FILENAME)
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        data = json.load(f)
    return InstallManifest(**data)
