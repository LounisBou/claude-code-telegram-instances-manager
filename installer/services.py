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
