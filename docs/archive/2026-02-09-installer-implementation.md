# Installer System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete install/uninstall/upgrade system for claude-ctim with interactive CLI, service management (launchd + systemd), and a bootstrap script for curl|bash distribution.

**Architecture:** Python CLI package (`installer/`) using stdlib only, orchestrating an 8-step install flow: platform detection, prerequisites, location, config generation, venv setup, database init, service creation, and health check. A thin shell bootstrap (`scripts/bootstrap.sh`) handles curl|bash entry. Manifest JSON tracks state for uninstall/upgrade.

**Tech Stack:** Python 3.11+ stdlib (json, subprocess, shutil, pathlib, os, platform, urllib.request), bash, YAML (generated as string — no PyYAML dependency in installer).

---

### Task 1: Package Skeleton & Constants

**Files:**
- Create: `installer/__init__.py`
- Create: `installer/constants.py`
- Test: `tests/test_installer_constants.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_constants.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'installer'"

**Step 3: Write minimal implementation**

```python
# installer/__init__.py
```

```python
# installer/constants.py
APP_NAME = "claude-ctim"
DEFAULT_INSTALL_DIR = f"/opt/{APP_NAME}"
MANIFEST_FILENAME = "install_manifest.json"
SERVICE_NAME = APP_NAME
LAUNCHD_LABEL = f"com.{APP_NAME}"
LAUNCHD_PLIST_DIR = "~/Library/LaunchAgents"
SYSTEMD_USER_DIR = "~/.config/systemd/user"
SYSTEMD_SYSTEM_DIR = "/etc/systemd/system"
MIN_PYTHON = (3, 11)
CONFIG_FILENAME = "config.yaml"
VENV_DIR = ".venv"
DATA_DIR = "data"
DB_FILENAME = "sessions.db"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_constants.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/__init__.py installer/constants.py tests/test_installer_constants.py
git commit -m "feat(installer): add package skeleton and constants"
```

---

### Task 2: Platform Detection (`installer/platform.py`)

**Files:**
- Create: `installer/platform.py`
- Test: `tests/test_installer_platform.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_platform.py -v`
Expected: FAIL with "cannot import name 'PlatformInfo'"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_platform.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/platform.py tests/test_installer_platform.py
git commit -m "feat(installer): add platform detection module"
```

---

### Task 3: Prerequisites Checker (`installer/prerequisites.py`)

**Files:**
- Create: `installer/prerequisites.py`
- Test: `tests/test_installer_prerequisites.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_prerequisites.py -v`
Expected: FAIL with "cannot import name 'PrereqResult'"

**Step 3: Write minimal implementation**

```python
# installer/prerequisites.py
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

from installer.platform import PlatformInfo


@dataclass
class PrereqResult:
    """Result of a single prerequisite check."""
    name: str
    found: bool
    version: str | None
    required: bool
    install_cmd: str | None = None


def _run_quiet(cmd: list[str]) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _check_python_version() -> tuple[bool, str | None]:
    """Check if Python 3.11+ is available."""
    import sys
    v = sys.version_info
    if v >= (3, 11):
        return True, f"{v.major}.{v.minor}.{v.micro}"
    return False, f"{v.major}.{v.minor}.{v.micro}"


def _check_claude_cli() -> tuple[bool, str | None]:
    """Check if the Claude CLI is installed."""
    if not shutil.which("claude"):
        return False, None
    output = _run_quiet(["claude", "--version"])
    return bool(output), output or None


def _check_gh_cli() -> tuple[bool, str | None]:
    """Check if the GitHub CLI is installed."""
    if not shutil.which("gh"):
        return False, None
    output = _run_quiet(["gh", "--version"])
    m = re.search(r"(\d+\.\d+\.\d+)", output)
    return True, m.group(1) if m else output


def _install_cmd_for(name: str, plat: PlatformInfo) -> str | None:
    """Suggest an install command for a missing dependency."""
    pkg_map = {
        "brew": {"git": "brew install git", "gh": "brew install gh",
                 "python": "brew install python@3.12",
                 "claude": "brew install claude-code"},
        "apt": {"git": "sudo apt install -y git", "gh": "sudo apt install -y gh",
                "python": "sudo apt install -y python3.12 python3.12-venv",
                "claude": "npm install -g @anthropic-ai/claude-code"},
        "dnf": {"git": "sudo dnf install -y git", "gh": "sudo dnf install -y gh",
                "python": "sudo dnf install -y python3.12",
                "claude": "npm install -g @anthropic-ai/claude-code"},
        "pacman": {"git": "sudo pacman -S --noconfirm git", "gh": "sudo pacman -S --noconfirm github-cli",
                   "python": "sudo pacman -S --noconfirm python",
                   "claude": "npm install -g @anthropic-ai/claude-code"},
    }
    pm = plat.package_manager
    if pm and pm in pkg_map:
        return pkg_map[pm].get(name)
    return None


def check_prerequisites(plat: PlatformInfo) -> list[PrereqResult]:
    """Check all prerequisites and return results."""
    results: list[PrereqResult] = []

    # Python
    found, version = _check_python_version()
    results.append(PrereqResult(
        name="python", found=found, version=version, required=True,
        install_cmd=_install_cmd_for("python", plat),
    ))

    # git
    git_path = shutil.which("git")
    git_version = None
    if git_path:
        out = _run_quiet(["git", "--version"])
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        git_version = m.group(1) if m else out
    results.append(PrereqResult(
        name="git", found=bool(git_path), version=git_version, required=True,
        install_cmd=_install_cmd_for("git", plat),
    ))

    # Claude CLI
    found, version = _check_claude_cli()
    results.append(PrereqResult(
        name="claude", found=found, version=version, required=True,
        install_cmd=_install_cmd_for("claude", plat),
    ))

    # gh CLI (optional)
    found, version = _check_gh_cli()
    results.append(PrereqResult(
        name="gh", found=found, version=version, required=False,
        install_cmd=_install_cmd_for("gh", plat),
    ))

    return results
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_prerequisites.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/prerequisites.py tests/test_installer_prerequisites.py
git commit -m "feat(installer): add prerequisites checker"
```

---

### Task 4: Manifest Read/Write (`installer/manifest.py`)

**Files:**
- Create: `installer/manifest.py`
- Test: `tests/test_installer_manifest.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_manifest.py -v`
Expected: FAIL with "cannot import name 'InstallManifest'"

**Step 3: Write minimal implementation**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_manifest.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/manifest.py tests/test_installer_manifest.py
git commit -m "feat(installer): add manifest read/write"
```

---

### Task 5: Interactive Config Generator (`installer/configure.py`)

**Files:**
- Create: `installer/configure.py`
- Test: `tests/test_installer_configure.py`

**Step 1: Write the failing test**

```python
# tests/test_installer_configure.py
import os

import yaml

from installer.configure import (
    generate_config_yaml,
    validate_bot_token,
    validate_user_ids,
)


class TestValidation:
    def test_valid_bot_token(self):
        assert validate_bot_token("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11") is True

    def test_invalid_bot_token_no_colon(self):
        assert validate_bot_token("invalidtoken") is False

    def test_invalid_bot_token_empty(self):
        assert validate_bot_token("") is False

    def test_valid_user_ids(self):
        assert validate_user_ids("123,456,789") == [123, 456, 789]

    def test_valid_single_user_id(self):
        assert validate_user_ids("123") == [123]

    def test_invalid_user_ids(self):
        assert validate_user_ids("abc,def") is None

    def test_empty_user_ids(self):
        assert validate_user_ids("") is None


class TestGenerateConfig:
    def test_generates_valid_yaml(self, tmp_path):
        config = {
            "bot_token": "123:abc",
            "authorized_users": [111],
            "projects_root": "/tmp/projects",
            "max_per_user": 3,
            "claude_command": "claude",
            "debug": False,
        }
        path = generate_config_yaml(config, str(tmp_path))
        assert os.path.isfile(path)
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data["telegram"]["bot_token"] == "123:abc"
        assert data["telegram"]["authorized_users"] == [111]
        assert data["projects"]["root"] == "/tmp/projects"
        assert data["sessions"]["max_per_user"] == 3
        assert data["database"]["path"] == "data/sessions.db"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_configure.py -v`
Expected: FAIL with "cannot import name 'generate_config_yaml'"

**Step 3: Write minimal implementation**

```python
# installer/configure.py
"""Interactive config generator for claude-ctim.

Prompts the user for essential and common config values,
validates input, and writes a config.yaml file.
"""
from __future__ import annotations

import os
import re
import shutil

from installer.constants import CONFIG_FILENAME


def validate_bot_token(token: str) -> bool:
    """Validate Telegram bot token format (digits:alphanumeric+special)."""
    return bool(re.match(r"^\d+:[A-Za-z0-9_-]+$", token.strip()))


def validate_user_ids(raw: str) -> list[int] | None:
    """Parse comma-separated user IDs. Returns list or None on failure."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        return ids if ids else None
    except ValueError:
        return None


def _prompt(message: str, default: str | None = None) -> str:
    """Prompt user for input with optional default."""
    if default is not None:
        message = f"{message} [{default}]: "
    else:
        message = f"{message}: "
    value = input(message).strip()
    return value if value else (default or "")


def _detect_claude_command() -> str:
    """Auto-detect Claude CLI path."""
    path = shutil.which("claude")
    return path if path else "claude"


def generate_config_yaml(config: dict, install_dir: str) -> str:
    """Generate config.yaml from a config dict. Returns the file path.

    Uses string formatting (not PyYAML) since the installer must be stdlib-only.
    """
    yaml_content = f"""telegram:
  bot_token: "{config['bot_token']}"
  authorized_users:
{_format_user_ids(config['authorized_users'])}

projects:
  root: "{config['projects_root']}"
  scan_depth: 1

sessions:
  max_per_user: {config.get('max_per_user', 3)}
  output_debounce_ms: 500
  output_max_buffer: 2000
  silence_warning_minutes: 10

claude:
  command: "{config.get('claude_command', 'claude')}"
  env: {{}}
  default_args: []
  update_command: "claude update"

database:
  path: "data/sessions.db"

debug:
  enabled: {str(config.get('debug', False)).lower()}
"""
    path = os.path.join(install_dir, CONFIG_FILENAME)
    with open(path, "w") as f:
        f.write(yaml_content)
    return path


def _format_user_ids(ids: list[int]) -> str:
    """Format user IDs as YAML list items."""
    return "\n".join(f"    - {uid}" for uid in ids)


def interactive_configure(install_dir: str) -> str:
    """Run interactive config prompts and write config.yaml. Returns path."""
    print("\n=== claude-ctim Configuration ===\n")

    # Essential
    while True:
        token = _prompt("Telegram bot token (from @BotFather)")
        if validate_bot_token(token):
            break
        print("  Invalid token format. Expected: 123456:ABCdef...")

    while True:
        raw_ids = _prompt("Authorized Telegram user IDs (comma-separated)")
        ids = validate_user_ids(raw_ids)
        if ids:
            break
        print("  Invalid format. Expected: 123456789 or 123,456,789")

    while True:
        projects_root = _prompt("Projects root directory", "/home")
        if os.path.isdir(projects_root):
            break
        print(f"  Directory not found: {projects_root}")

    # Common
    max_per_user = _prompt("Max sessions per user", "3")
    claude_cmd = _prompt("Claude CLI command", _detect_claude_command())
    debug = _prompt("Enable debug logging? (y/N)", "N")

    config = {
        "bot_token": token.strip(),
        "authorized_users": ids,
        "projects_root": projects_root,
        "max_per_user": int(max_per_user) if max_per_user.isdigit() else 3,
        "claude_command": claude_cmd,
        "debug": debug.lower().startswith("y"),
    }

    path = generate_config_yaml(config, install_dir)
    print(f"\n  Config written to: {path}")
    return path


def main():
    """Entry point for claude-ctim-configure console script."""
    import sys
    install_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    interactive_configure(install_dir)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_configure.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/configure.py tests/test_installer_configure.py
git commit -m "feat(installer): add interactive config generator"
```

---

### Task 6: Service Templates (`installer/services.py`)

**Files:**
- Create: `installer/services.py`
- Test: `tests/test_installer_services.py`

**Step 1: Write the failing test**

```python
# tests/test_installer_services.py
import os
from unittest.mock import patch

from installer.services import (
    generate_launchd_plist,
    generate_systemd_unit,
    get_service_path,
)


class TestGenerateSystemdUnit:
    def test_generates_valid_unit(self, tmp_path):
        unit = generate_systemd_unit(
            install_dir="/opt/claude-ctim",
            user="lounis",
            config_path="/opt/claude-ctim/config.yaml",
        )
        assert "[Unit]" in unit
        assert "[Service]" in unit
        assert "[Install]" in unit
        assert "/opt/claude-ctim" in unit
        assert "lounis" in unit
        assert "python -m src.main" in unit

    def test_writes_to_file(self, tmp_path):
        unit = generate_systemd_unit(
            install_dir="/opt/claude-ctim", user="test",
            config_path="/opt/claude-ctim/config.yaml",
        )
        path = tmp_path / "test.service"
        path.write_text(unit)
        assert path.read_text().startswith("[Unit]")


class TestGenerateLaunchdPlist:
    def test_generates_valid_plist(self):
        plist = generate_launchd_plist(
            install_dir="/opt/claude-ctim",
            config_path="/opt/claude-ctim/config.yaml",
        )
        assert "<?xml" in plist
        assert "com.claude-ctim" in plist
        assert "/opt/claude-ctim" in plist
        assert "src.main" in plist

    def test_contains_keep_alive(self):
        plist = generate_launchd_plist(
            install_dir="/opt/claude-ctim",
            config_path="/opt/claude-ctim/config.yaml",
        )
        assert "KeepAlive" in plist


class TestGetServicePath:
    def test_launchd(self):
        path = get_service_path("launchd", "/home/test")
        assert "LaunchAgents" in path
        assert "com.claude-ctim.plist" in path

    def test_systemd_user(self):
        path = get_service_path("systemd_user", "/home/test")
        assert ".config/systemd/user" in path
        assert "claude-ctim.service" in path
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_services.py -v`
Expected: FAIL with "cannot import name 'generate_launchd_plist'"

**Step 3: Write minimal implementation**

```python
# installer/services.py
"""Service file generation for launchd (macOS) and systemd (Linux)."""
from __future__ import annotations

import os

from installer.constants import APP_NAME, LAUNCHD_LABEL


def generate_systemd_unit(install_dir: str, user: str, config_path: str) -> str:
    """Generate a systemd unit file for the bot."""
    venv_python = os.path.join(install_dir, ".venv", "bin", "python")
    return f"""[Unit]
Description=Claude Instance Manager Telegram Bot
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={install_dir}
ExecStart={venv_python} -m src.main {config_path}
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""


def generate_launchd_plist(install_dir: str, config_path: str) -> str:
    """Generate a launchd plist file for the bot."""
    venv_python = os.path.join(install_dir, ".venv", "bin", "python")
    log_dir = os.path.join(install_dir, "logs")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{venv_python}</string>
        <string>-m</string>
        <string>src.main</string>
        <string>{config_path}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{install_dir}</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_dir}/claude-ctim.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/claude-ctim-error.log</string>
</dict>
</plist>
"""


def get_service_path(service_type: str, home: str) -> str:
    """Return the filesystem path where the service file should be written."""
    if service_type == "launchd":
        return os.path.join(home, "Library", "LaunchAgents", f"{LAUNCHD_LABEL}.plist")
    if service_type == "systemd_user":
        return os.path.join(home, ".config", "systemd", "user", f"{APP_NAME}.service")
    # systemd_system
    return os.path.join("/etc", "systemd", "system", f"{APP_NAME}.service")
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_services.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/services.py tests/test_installer_services.py
git commit -m "feat(installer): add service file generators (launchd + systemd)"
```

---

### Task 7: Health Check (`installer/health.py`)

**Files:**
- Create: `installer/health.py`
- Test: `tests/test_installer_health.py`

**Step 1: Write the failing test**

```python
# tests/test_installer_health.py
import json
import os
from unittest.mock import patch

from installer.health import CheckResult, run_health_checks


class TestHealthChecks:
    def test_config_check_passes(self, tmp_path):
        config = tmp_path / "config.yaml"
        config.write_text(
            'telegram:\n  bot_token: "123:abc"\n'
            '  authorized_users:\n    - 111\n'
            'projects:\n  root: "/tmp"\n'
        )
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(config),
        )
        config_result = next(r for r in results if r.name == "Config file")
        assert config_result.passed is True

    def test_config_check_fails_missing(self, tmp_path):
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "nonexistent.yaml"),
        )
        config_result = next(r for r in results if r.name == "Config file")
        assert config_result.passed is False

    def test_db_check_passes(self, tmp_path):
        import sqlite3
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        db_path = data_dir / "sessions.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY)")
        conn.close()
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "config.yaml"),
        )
        db_result = next(r for r in results if r.name == "Database")
        assert db_result.passed is True

    def test_returns_list_of_check_results(self, tmp_path):
        results = run_health_checks(
            install_dir=str(tmp_path),
            config_path=str(tmp_path / "nonexistent.yaml"),
        )
        assert len(results) >= 4
        assert all(isinstance(r, CheckResult) for r in results)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_health.py -v`
Expected: FAIL with "cannot import name 'CheckResult'"

**Step 3: Write minimal implementation**

```python
# installer/health.py
"""Post-install health check diagnostics."""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
from dataclasses import dataclass

from installer.constants import DATA_DIR, DB_FILENAME


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    passed: bool
    detail: str
    suggestion: str = ""


def _check_config(config_path: str) -> CheckResult:
    """Verify config.yaml exists and has required fields."""
    if not os.path.isfile(config_path):
        return CheckResult("Config file", False, "not found",
                           f"Run: claude-ctim-configure {os.path.dirname(config_path)}")
    try:
        with open(config_path) as f:
            content = f.read()
        # Minimal check without PyYAML: look for required keys
        for key in ("bot_token:", "authorized_users:", "root:"):
            if key not in content:
                return CheckResult("Config file", False, f"missing {key}",
                                   "Re-run claude-ctim-configure")
        return CheckResult("Config file", True, "valid")
    except Exception as e:
        return CheckResult("Config file", False, str(e))


def _check_python(install_dir: str) -> CheckResult:
    """Check venv Python version."""
    venv_python = os.path.join(install_dir, ".venv", "bin", "python")
    if not os.path.isfile(venv_python):
        return CheckResult("Python", False, "venv not found",
                           "Re-run installer to create venv")
    try:
        result = subprocess.run(
            [venv_python, "--version"], capture_output=True, text=True, timeout=5,
        )
        version = result.stdout.strip()
        return CheckResult("Python", True, version)
    except Exception as e:
        return CheckResult("Python", False, str(e))


def _check_deps(install_dir: str) -> CheckResult:
    """Run pip check in the venv."""
    venv_pip = os.path.join(install_dir, ".venv", "bin", "pip")
    if not os.path.isfile(venv_pip):
        return CheckResult("Dependencies", False, "pip not found")
    try:
        result = subprocess.run(
            [venv_pip, "check"], capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return CheckResult("Dependencies", True, "all satisfied")
        return CheckResult("Dependencies", False, result.stdout.strip(),
                           f"Run: {venv_pip} install .")
    except Exception as e:
        return CheckResult("Dependencies", False, str(e))


def _check_claude_cli() -> CheckResult:
    """Check Claude CLI is available."""
    if not shutil.which("claude"):
        return CheckResult("Claude CLI", False, "not found",
                           "Install: npm install -g @anthropic-ai/claude-code")
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, text=True, timeout=5,
        )
        return CheckResult("Claude CLI", True, result.stdout.strip())
    except Exception as e:
        return CheckResult("Claude CLI", False, str(e))


def _check_database(install_dir: str) -> CheckResult:
    """Verify SQLite database has the sessions table."""
    db_path = os.path.join(install_dir, DATA_DIR, DB_FILENAME)
    if not os.path.isfile(db_path):
        return CheckResult("Database", False, "not found",
                           "Database will be created on first bot startup")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        has_table = cursor.fetchone() is not None
        conn.close()
        if has_table:
            return CheckResult("Database", True, "schema ok")
        return CheckResult("Database", False, "sessions table missing")
    except Exception as e:
        return CheckResult("Database", False, str(e))


def _check_bot_token(config_path: str) -> CheckResult:
    """Validate bot token by calling Telegram getMe API."""
    if not os.path.isfile(config_path):
        return CheckResult("Bot token", False, "config not found")
    try:
        with open(config_path) as f:
            for line in f:
                if "bot_token:" in line:
                    token = line.split(":", 1)[1].strip().strip('"').strip("'")
                    break
            else:
                return CheckResult("Bot token", False, "not found in config")
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json
            data = json.loads(resp.read())
        if data.get("ok"):
            username = data["result"].get("username", "unknown")
            return CheckResult("Bot token", True, f"valid (@{username})")
        return CheckResult("Bot token", False, "API returned not ok")
    except Exception as e:
        return CheckResult("Bot token", False, str(e),
                           "Check your bot_token in config.yaml")


def _check_service(service_path: str | None) -> CheckResult:
    """Check if the service file exists."""
    if not service_path:
        return CheckResult("Service", False, "no service configured")
    if os.path.isfile(service_path):
        return CheckResult("Service", True, f"installed at {service_path}")
    return CheckResult("Service", False, "service file not found",
                       "Re-run installer to create service")


def run_health_checks(
    install_dir: str,
    config_path: str,
    service_path: str | None = None,
) -> list[CheckResult]:
    """Run all health checks and return results."""
    return [
        _check_config(config_path),
        _check_python(install_dir),
        _check_deps(install_dir),
        _check_claude_cli(),
        _check_database(install_dir),
        _check_bot_token(config_path),
        _check_service(service_path),
    ]


def print_health_report(results: list[CheckResult]) -> bool:
    """Print health check results. Returns True if all passed."""
    all_passed = True
    for r in results:
        icon = "\u2713" if r.passed else "\u2717"
        print(f"  {icon} {r.name:20s} {r.detail}")
        if not r.passed:
            all_passed = False
            if r.suggestion:
                print(f"    -> {r.suggestion}")
    return all_passed


def main():
    """Entry point for claude-ctim-health console script."""
    import sys
    install_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    config_path = os.path.join(install_dir, "config.yaml")
    results = run_health_checks(install_dir, config_path)
    print("\n=== claude-ctim Health Check ===\n")
    ok = print_health_report(results)
    sys.exit(0 if ok else 1)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_health.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/health.py tests/test_installer_health.py
git commit -m "feat(installer): add health check diagnostics"
```

---

### Task 8: Install Orchestrator (`installer/main.py`)

**Files:**
- Create: `installer/main.py`
- Test: `tests/test_installer_main.py`

**Step 1: Write the failing test**

```python
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
            # Should call python -m venv
            assert any("venv" in str(c) for c in mock_run.call_args_list)

    def test_setup_database(self, tmp_path):
        installer = Installer.__new__(Installer)
        installer.install_dir = str(tmp_path)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            installer._setup_database()
        assert (tmp_path / "data").is_dir()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_main.py -v`
Expected: FAIL with "cannot import name 'Installer'"

**Step 3: Write minimal implementation**

```python
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
from installer.health import main as health_main
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

        # Determine source: either current repo or parent of installer/
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
        # Use the venv Python to run the DB initialization
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
            # Create logs directory for launchd
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_main.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/main.py tests/test_installer_main.py
git commit -m "feat(installer): add install orchestrator"
```

---

### Task 9: Uninstaller (`installer/uninstall.py`)

**Files:**
- Create: `installer/uninstall.py`
- Test: `tests/test_installer_uninstall.py`

**Step 1: Write the failing test**

```python
# tests/test_installer_uninstall.py
import json
import os
from unittest.mock import patch

from installer.manifest import InstallManifest, save_manifest
from installer.uninstall import Uninstaller


def _write_manifest(tmp_path, **overrides):
    defaults = dict(
        app_name="claude-ctim", version="0.1.0",
        install_dir=str(tmp_path), config_path=str(tmp_path / "config.yaml"),
        venv_path=str(tmp_path / ".venv"), db_path=str(tmp_path / "data" / "sessions.db"),
        service_file=str(tmp_path / "test.service"), service_type="systemd_user",
        platform="linux",
    )
    defaults.update(overrides)
    manifest = InstallManifest(**defaults)
    save_manifest(manifest, str(tmp_path))
    return manifest


class TestUninstaller:
    def test_loads_manifest(self, tmp_path):
        _write_manifest(tmp_path)
        u = Uninstaller(str(tmp_path))
        assert u.manifest is not None
        assert u.manifest.app_name == "claude-ctim"

    def test_missing_manifest_raises(self, tmp_path):
        u = Uninstaller(str(tmp_path))
        assert u.manifest is None

    def test_remove_venv(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "bin").mkdir()
        _write_manifest(tmp_path)
        u = Uninstaller(str(tmp_path))
        u._remove_venv()
        assert not venv.exists()

    def test_remove_service_file(self, tmp_path):
        svc = tmp_path / "test.service"
        svc.write_text("[Unit]")
        _write_manifest(tmp_path, service_file=str(svc))
        u = Uninstaller(str(tmp_path))
        with patch("subprocess.run"):
            u._stop_service()
        u._remove_service_file()
        assert not svc.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_uninstall.py -v`
Expected: FAIL with "cannot import name 'Uninstaller'"

**Step 3: Write minimal implementation**

```python
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

        # 1. Stop service
        print("Stopping service...")
        self._stop_service()

        # 2. Remove service file
        print("Removing service file...")
        self._remove_service_file()

        # 3. Ask about data
        keep_data = _confirm("Keep config and database?", default_yes=True)

        # 4. Remove venv
        print("Removing virtual environment...")
        self._remove_venv()

        # 5. Remove data if requested
        if not keep_data:
            print("Removing config and database...")
            self._remove_data()

        # 6. Remove manifest
        self._remove_manifest()

        # 7. Try to remove install dir if empty
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_uninstall.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/uninstall.py tests/test_installer_uninstall.py
git commit -m "feat(installer): add uninstaller"
```

---

### Task 10: Upgrader (`installer/upgrade.py`)

**Files:**
- Create: `installer/upgrade.py`
- Test: `tests/test_installer_upgrade.py`

**Step 1: Write the failing test**

```python
# tests/test_installer_upgrade.py
import os
from unittest.mock import MagicMock, patch

from installer.manifest import InstallManifest, save_manifest
from installer.upgrade import Upgrader


def _setup_manifest(tmp_path):
    manifest = InstallManifest(
        app_name="claude-ctim", version="0.1.0",
        install_dir=str(tmp_path), config_path=str(tmp_path / "config.yaml"),
        venv_path=str(tmp_path / ".venv"), db_path=str(tmp_path / "data" / "sessions.db"),
        service_file=str(tmp_path / "test.service"), service_type="systemd_user",
        platform="linux",
    )
    save_manifest(manifest, str(tmp_path))
    (tmp_path / "config.yaml").write_text("test: true")
    return manifest


class TestUpgrader:
    def test_loads_manifest(self, tmp_path):
        _setup_manifest(tmp_path)
        u = Upgrader(str(tmp_path))
        assert u.manifest is not None

    def test_backup_config(self, tmp_path):
        _setup_manifest(tmp_path)
        u = Upgrader(str(tmp_path))
        u._backup_config()
        assert (tmp_path / "config.yaml.bak").exists()
        assert (tmp_path / "config.yaml.bak").read_text() == "test: true"

    def test_update_deps(self, tmp_path):
        _setup_manifest(tmp_path)
        u = Upgrader(str(tmp_path))
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            u._update_deps()
            assert mock_run.called
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_installer_upgrade.py -v`
Expected: FAIL with "cannot import name 'Upgrader'"

**Step 3: Write minimal implementation**

```python
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

        # 1. Stop service
        print("Stopping service...")
        self._stop_service()

        # 2. Backup config
        print("Backing up config...")
        self._backup_config()

        # 3. Pull latest
        print("Pulling latest code...")
        self._pull_latest()

        # 4. Update deps
        print("Updating dependencies...")
        self._update_deps()

        # 5. Migration check (no-op for now)
        print("Checking migrations... (none pending)")

        # 6. Restart service
        print("Restarting service...")
        self._start_service()

        # 7. Health check
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_installer_upgrade.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add installer/upgrade.py tests/test_installer_upgrade.py
git commit -m "feat(installer): add upgrader"
```

---

### Task 11: Bootstrap Script (`scripts/bootstrap.sh`)

**Files:**
- Create: `scripts/bootstrap.sh`

**Step 1: Write the script**

```bash
#!/usr/bin/env bash
# bootstrap.sh — Thin wrapper for installing claude-ctim.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lounisbou/claude-ctim/main/scripts/bootstrap.sh | bash
#   ./scripts/bootstrap.sh
set -euo pipefail

APP_NAME="claude-ctim"
REPO_URL="https://github.com/lounisbou/claude-ctim.git"
MIN_PYTHON="3.11"

info()  { echo "  [INFO]  $*"; }
error() { echo "  [ERROR] $*" >&2; }

# Check Python version
check_python() {
    for cmd in python3.12 python3.11 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
                PYTHON_CMD="$cmd"
                info "Found Python $version ($cmd)"
                return 0
            fi
        fi
    done
    return 1
}

# Detect if we're inside the cloned repo
detect_repo() {
    if [ -f "installer/main.py" ] && [ -f "pyproject.toml" ]; then
        REPO_DIR="$(pwd)"
        return 0
    fi
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    if [ -f "$SCRIPT_DIR/../installer/main.py" ]; then
        REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
        return 0
    fi
    return 1
}

echo ""
echo "=============================="
echo "  $APP_NAME Bootstrap"
echo "=============================="
echo ""

# Step 1: Find Python
if ! check_python; then
    error "Python $MIN_PYTHON+ is required but not found."
    if command -v brew &>/dev/null; then
        echo "  Install with: brew install python@3.12"
    elif command -v apt &>/dev/null; then
        echo "  Install with: sudo apt install python3.12 python3.12-venv"
    fi
    exit 1
fi

# Step 2: Find or clone repo
if detect_repo; then
    info "Found repo at: $REPO_DIR"
else
    REPO_DIR=$(mktemp -d)
    info "Cloning $APP_NAME to $REPO_DIR..."
    git clone --depth 1 "$REPO_URL" "$REPO_DIR"
fi

# Step 3: Hand off to Python installer
info "Starting installer..."
cd "$REPO_DIR"
exec "$PYTHON_CMD" -m installer.main "$@"
```

**Step 2: Make executable**

Run: `chmod +x scripts/bootstrap.sh`

**Step 3: Commit**

```bash
git add scripts/bootstrap.sh
git commit -m "feat(installer): add bootstrap shell script for curl|bash"
```

---

### Task 12: Console Scripts & pyproject.toml Update

**Files:**
- Modify: `pyproject.toml:1-30`

**Step 1: Add console scripts to pyproject.toml**

Add this section after `[project.optional-dependencies]`:

```toml
[project.scripts]
claude-ctim-install = "installer.main:main"
claude-ctim-configure = "installer.configure:main"
claude-ctim-upgrade = "installer.upgrade:main"
claude-ctim-uninstall = "installer.uninstall:main"
claude-ctim-health = "installer.health:main"
```

**Step 2: Verify pyproject.toml is valid**

Run: `python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('valid')"`
Expected: `valid`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(installer): add console script entry points to pyproject.toml"
```

---

### Task 13: Add installer to .gitignore exceptions & update docs

**Files:**
- Modify: `.gitignore`
- Modify: `docs/installation.md`

**Step 1: Update .gitignore**

Add to `.gitignore` to ensure the installer package is tracked but manifest files aren't:

```
install_manifest.json
```

**Step 2: Update docs/installation.md**

Add a "Quick Install" section at the top, after Prerequisites:

```markdown
## Quick Install

One-line install:

\```bash
curl -fsSL https://raw.githubusercontent.com/lounisbou/claude-ctim/main/scripts/bootstrap.sh | bash
\```

Or clone and run:

\```bash
git clone https://github.com/lounisbou/claude-ctim.git
cd claude-ctim
./scripts/bootstrap.sh
\```

### Management Commands

| Command | Description |
|---------|-------------|
| `claude-ctim-configure` | Re-run interactive configuration |
| `claude-ctim-health` | Run health check diagnostics |
| `claude-ctim-upgrade` | Upgrade to latest version |
| `claude-ctim-uninstall` | Remove installation |
```

**Step 3: Commit**

```bash
git add .gitignore docs/installation.md
git commit -m "docs: add quick install section and management commands"
```

---

### Task 14: Final Integration Test

**Files:**
- Test: Run full test suite

**Step 1: Run full test suite**

Run: `pytest --cov=src --cov=installer -q`
Expected: All tests pass

**Step 2: Run a dry-run of health check on current repo**

Run: `python -m installer.health .`
Expected: Prints health check results (some may fail — that's expected in dev environment)

**Step 3: Verify bootstrap.sh syntax**

Run: `bash -n scripts/bootstrap.sh && echo "syntax ok"`
Expected: `syntax ok`

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(installer): complete install/uninstall/upgrade system"
```
