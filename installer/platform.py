# installer/platform.py
from __future__ import annotations

import getpass
import os
import platform as _platform
import shutil
from dataclasses import dataclass


@dataclass
class PlatformInfo:
    """Detected platform information."""
    os: str              # "macos" or "linux"
    distro: str | None   # "ubuntu", "debian", "fedora", "arch", etc. (Linux only)
    package_manager: str | None  # "brew", "apt", "dnf", "pacman"
    init_system: str     # "launchd" or "systemd"
    user: str
    home: str


def _detect_distro() -> str | None:
    """Detect Linux distribution from /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.strip().split("=", 1)[1].strip('"').lower()
    except FileNotFoundError:
        pass
    return None


def _has_systemd() -> bool:
    """Check if systemd is the init system."""
    return os.path.isdir("/run/systemd/system")


def _detect_package_manager() -> str | None:
    """Detect available package manager."""
    for cmd in ("brew", "apt", "dnf", "pacman"):
        if shutil.which(cmd):
            return cmd
    return None


def detect_platform() -> PlatformInfo:
    """Detect the current platform, distro, package manager, and init system."""
    system = _platform.system()

    if system == "Darwin":
        return PlatformInfo(
            os="macos",
            distro=None,
            package_manager="brew" if shutil.which("brew") else None,
            init_system="launchd",
            user=getpass.getuser(),
            home=os.path.expanduser("~"),
        )

    # Linux
    return PlatformInfo(
        os="linux",
        distro=_detect_distro(),
        package_manager=_detect_package_manager(),
        init_system="systemd" if _has_systemd() else "unknown",
        user=getpass.getuser(),
        home=os.path.expanduser("~"),
    )
