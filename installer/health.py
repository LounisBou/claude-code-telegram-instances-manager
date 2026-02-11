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
