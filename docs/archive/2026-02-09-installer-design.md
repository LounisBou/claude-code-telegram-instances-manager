# Installer System Design

**Date:** 2026-02-09
**Status:** Approved
**App name:** `claude-ctim` (variable: `APP_NAME`)

## Summary

A complete installer/uninstaller/upgrader system for claude-ctim targeting end users on macOS and Linux. Combines a Python CLI installer (structured, testable) with a thin shell bootstrap for `curl | bash` distribution and a Homebrew tap for polished macOS installs.

## Architecture

Four deliverables:

```
1. scripts/bootstrap.sh        Thin shell wrapper for curl|bash
2. installer/                  Python CLI package (stdlib only)
   ├── __init__.py
   ├── main.py                 Install orchestrator
   ├── configure.py            Interactive config generator
   ├── upgrade.py              Upgrade flow
   ├── uninstall.py            Clean removal
   ├── health.py               Post-install diagnostics
   ├── platform.py             OS/distro/service detection
   ├── prerequisites.py        Dependency checker & installer
   └── manifest.py             Install manifest read/write
3. homebrew-claude-ctim/       Separate GitHub repo (Homebrew tap)
   └── Formula/claude-ctim.rb  Homebrew formula
4. install_manifest.json       Written at install time (tracks state)
```

The Python installer is the single source of truth. Both bootstrap.sh and the Homebrew formula delegate to it.

## Bootstrap Script (`scripts/bootstrap.sh`)

Under 50 lines. Invoked two ways:

```bash
# Remote (curl | bash)
curl -fsSL https://raw.githubusercontent.com/lounisbou/claude-ctim/main/scripts/bootstrap.sh | bash

# Local (from cloned repo)
./scripts/bootstrap.sh
```

Responsibilities:
1. Detect if running inside the cloned repo (check for `installer/main.py`)
2. If not, clone to a temp directory
3. Verify Python 3.11+ exists (offer brew/apt install if missing)
4. Hand off to `python -m installer.main`

## Python Installer Flow (`installer/main.py`)

### Step 1: Platform Detection

Detect and store:
- OS: macOS / Linux
- Distro: Ubuntu, Debian, Fedora, Arch, etc. (Linux only)
- Package manager: `brew` / `apt` / `dnf` / `pacman`
- Init system: `launchd` (macOS) / `systemd` (Linux)
- Current user and home directory

### Step 2: Prerequisites Check

Verify and optionally install:

| Dependency | Required | Install method |
|-----------|----------|---------------|
| Python 3.11+ | Yes | brew / apt / dnf / pacman |
| Claude CLI | Yes | Show install instructions (npm / brew) |
| gh CLI | No | brew / apt (for `/git` command) |
| git | Yes | brew / apt / dnf / pacman |

Each missing dep prompts: what's missing, why it's needed, "Install now? [Y/n]".

### Step 3: Install Location

- Default: `/opt/claude-ctim`
- User can override with any writable path
- If path needs sudo to create, prompt for it
- Clone or copy the project into the install dir

### Step 4: Config Generation (`installer/configure.py`)

Interactive prompts with validation:

**Essential (required):**
- `telegram.bot_token` — validate format (digits:alphanumeric)
- `telegram.authorized_users` — comma-separated Telegram user IDs
- `projects.root` — validate directory exists

**Common (with defaults):**
- `sessions.max_per_user` — default 3
- `claude.command` — default auto-detected from PATH
- `debug.enabled` — default false

Writes `config.yaml` to the install directory.

### Step 5: Venv & Dependencies

```bash
python3 -m venv <install_dir>/.venv
<install_dir>/.venv/bin/pip install .
```

### Step 5.5: Database Setup

- Create `<install_dir>/data/` directory
- Initialize SQLite database with schema (run `Database.initialize()`)
- Verify schema was created

### Step 6: Service Creation

**macOS (launchd):**
- Generate plist: `~/Library/LaunchAgents/com.claude-ctim.plist`
- Contents: WorkingDirectory, ProgramArguments (python -m src.main), KeepAlive, StandardOutPath/StandardErrorPath for logging
- Load with `launchctl load`

**Linux (systemd):**
- Generate unit: `~/.config/systemd/user/claude-ctim.service` (user-level) or `/etc/systemd/system/claude-ctim.service` (system-level, needs sudo)
- Contents: match current `systemd/claude-bot.service` but with variable paths
- Enable and start with `systemctl [--user] enable --now claude-ctim`

Prompt: "Start the service now? [Y/n]"

### Step 7: Manifest

Write `<install_dir>/install_manifest.json`:

```json
{
  "app_name": "claude-ctim",
  "version": "1.0.0",
  "install_dir": "/opt/claude-ctim",
  "config_path": "/opt/claude-ctim/config.yaml",
  "venv_path": "/opt/claude-ctim/.venv",
  "db_path": "/opt/claude-ctim/data/sessions.db",
  "service_file": "~/.config/systemd/user/claude-ctim.service",
  "service_type": "systemd_user",
  "platform": "linux",
  "installed_at": "2026-02-09T12:00:00Z",
  "installed_by": "lounis"
}
```

### Step 8: Health Check (`installer/health.py`)

Post-install validation:

| Check | Method |
|-------|--------|
| Config file | Parse YAML, verify required fields |
| Python version | Check venv python `--version` |
| Dependencies | `pip check` in venv |
| Claude CLI | `claude --version` |
| Database schema | Open DB, verify `sessions` table exists |
| Bot token | Call Telegram `getMe` API (one HTTP request) |
| Service status | Check if service file is loaded and running |

Output:
```
 Config file        valid
 Python 3.12.1      ok
 Dependencies       all satisfied
 Claude CLI v1.2.3  ok
 Database schema    ok
 Bot token          valid (@MyBotName)
 Service            loaded and running
```

Failures show specific errors with suggested fixes.

## Uninstaller (`installer/uninstall.py`)

Reads `install_manifest.json`, reverses install:

1. Stop service (`launchctl unload` / `systemctl stop`)
2. Remove service file
3. Prompt: "Keep config and database? [Y/n]" (default: keep)
4. Remove `.venv/`
5. Remove install directory (if empty or user confirmed data removal)
6. Remove manifest

Invoked via: `python -m installer.uninstall` or `claude-ctim-uninstall` (console_scripts entry).

## Upgrader (`installer/upgrade.py`)

1. Read manifest for install dir and service info
2. Stop service
3. Backup `config.yaml` to `config.yaml.bak`
4. Pull latest code (`git pull` or download new tarball)
5. Update deps (`pip install .` in existing venv)
6. Run migration check (no-op for now, future-proofing)
7. Restart service
8. Run health check

Invoked via: `python -m installer.upgrade` or `claude-ctim-upgrade`.

For Homebrew users: `brew upgrade claude-ctim` handles code + deps natively, then restarts the service.

## Homebrew Tap

Separate repo: `github.com/lounisbou/homebrew-claude-ctim`

### Formula (`Formula/claude-ctim.rb`)

- `url`: GitHub release tarball
- `depends_on "python@3.12"`
- `install`: create venv, pip install, copy to prefix
- `service` block: launchd plist definition (working dir, command, keep-alive)
- `post_install`: prompt to run `claude-ctim-configure`
- `caveats`: remind user to configure if not done

User experience:
```bash
brew tap lounisbou/claude-ctim
brew install claude-ctim
claude-ctim-configure          # Interactive config
brew services start claude-ctim
```

## Console Scripts

Added to `pyproject.toml`:

```toml
[project.scripts]
claude-ctim-install = "installer.main:main"
claude-ctim-configure = "installer.configure:main"
claude-ctim-upgrade = "installer.upgrade:main"
claude-ctim-uninstall = "installer.uninstall:main"
claude-ctim-health = "installer.health:main"
```

## Implementation Phases

| Phase | Scope | Priority |
|-------|-------|----------|
| A | `installer/platform.py`, `installer/prerequisites.py` | Foundation |
| B | `installer/configure.py` (interactive config gen) | Core |
| C | `installer/main.py` (full install flow) | Core |
| D | `installer/manifest.py` | Core |
| E | Service creation (launchd + systemd templates) | Core |
| F | `installer/health.py` (diagnostics) | Core |
| G | `installer/uninstall.py` | Core |
| H | `installer/upgrade.py` | Important |
| I | `scripts/bootstrap.sh` | Distribution |
| J | Homebrew tap (separate repo) | Distribution |
| K | Tests for installer package | Quality |

## Constraints

- **No external deps in installer package** — stdlib only (so it runs before venv exists)
- **`APP_NAME` variable** — all paths use `APP_NAME = "claude-ctim"`, easy to rebrand
- **Non-destructive defaults** — uninstaller keeps config/data by default
- **Idempotent** — running install twice doesn't break anything
- **Manifest-driven** — uninstaller and upgrader read the same manifest
