# ClaudeInstanceManager Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python Telegram bot that proxies between Telegram chat and Claude Code CLI instances running on a server, with session management, file transfer, context alerts, and git info.

**Architecture:** Three-layer async Python app — Telegram Bot Layer (python-telegram-bot), Session Manager Layer (routing + lifecycle), Claude Process Layer (pexpect PTY). SQLite for session history. Systemd for deployment.

**Tech Stack:** Python 3.11+, python-telegram-bot, pexpect, aiosqlite, pyyaml, pytest, pytest-asyncio, pytest-cov

**Design doc:** `docs/plans/2026-02-09-claude-instance-manager-design.md`

**Telegram API docs:** `docs/telegram/api/bots/` and `docs/telegram/python-telegram-bot/`

---

## Phase 1: Project Scaffolding

### Task 1.1: Initialize project structure and dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `src/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `config.yaml.example`
- Modify: `.gitignore`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "claude-instance-manager"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
source = ["src"]

[tool.coverage.report]
fail_under = 90
show_missing = true
```

**Step 2: Create `requirements.txt`**

```
python-telegram-bot[ext]>=21.0
pexpect>=4.9
pyyaml>=6.0
aiosqlite>=0.20
```

**Step 3: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest>=8.0
pytest-asyncio>=0.24
pytest-cov>=5.0
```

**Step 4: Create empty `src/__init__.py` and `tests/__init__.py`**

Empty files.

**Step 5: Create `tests/conftest.py`**

```python
import asyncio

import pytest


@pytest.fixture
def tmp_projects(tmp_path):
    """Create a temporary projects root with sample project dirs."""
    proj_a = tmp_path / "project-alpha"
    proj_a.mkdir()
    (proj_a / ".git").mkdir()

    proj_b = tmp_path / "project-beta"
    proj_b.mkdir()
    (proj_b / ".claude").mkdir()

    proj_c = tmp_path / "not-a-project"
    proj_c.mkdir()

    return tmp_path
```

**Step 6: Create `config.yaml.example`**

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN_HERE"
  authorized_users:
    - 123456789

projects:
  root: "/home/lounis/dev"
  scan_depth: 1

sessions:
  max_per_user: 3
  output_debounce_ms: 500
  output_max_buffer: 2000
  silence_warning_minutes: 10

claude:
  command: "claude"
  default_args: []
  update_command: "claude update"

database:
  path: "data/sessions.db"
```

**Step 7: Update `.gitignore`**

Append:

```
config.yaml
data/
__pycache__/
*.pyc
.pytest_cache/
.coverage
htmlcov/
*.egg-info/
venv/
.venv/
```

**Step 8: Install dependencies and verify**

Run: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt`

**Step 9: Run pytest to verify setup**

Run: `pytest --co`
Expected: "no tests ran" (collected 0 items), no errors.

**Step 10: Commit**

```bash
git add pyproject.toml requirements.txt requirements-dev.txt src/__init__.py tests/__init__.py tests/conftest.py config.yaml.example .gitignore
git commit -m "feat: initialize project scaffolding with dependencies and test setup"
```

---

## Phase 2: Config Module

### Task 2.1: Config loading and validation

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing tests**

```python
# tests/test_config.py
import pytest
import yaml

from src.config import AppConfig, load_config, ConfigError


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {
                "bot_token": "test-token-123",
                "authorized_users": [111, 222],
            },
            "projects": {"root": "/tmp/projects", "scan_depth": 1},
            "sessions": {
                "max_per_user": 3,
                "output_debounce_ms": 500,
                "output_max_buffer": 2000,
                "silence_warning_minutes": 10,
            },
            "claude": {
                "command": "claude",
                "default_args": [],
                "update_command": "claude update",
            },
            "database": {"path": "data/sessions.db"},
        }))
        config = load_config(str(config_file))
        assert config.telegram.bot_token == "test-token-123"
        assert config.telegram.authorized_users == [111, 222]
        assert config.projects.root == "/tmp/projects"
        assert config.sessions.max_per_user == 3
        assert config.claude.command == "claude"
        assert config.database.path == "data/sessions.db"

    def test_missing_file_raises(self):
        with pytest.raises(ConfigError, match="not found"):
            load_config("/nonexistent/config.yaml")

    def test_missing_bot_token_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"authorized_users": [111]},
            "projects": {"root": "/tmp"},
            "sessions": {},
            "claude": {},
            "database": {},
        }))
        with pytest.raises(ConfigError, match="bot_token"):
            load_config(str(config_file))

    def test_empty_authorized_users_raises(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": []},
            "projects": {"root": "/tmp"},
            "sessions": {},
            "claude": {},
            "database": {},
        }))
        with pytest.raises(ConfigError, match="authorized_users"):
            load_config(str(config_file))

    def test_defaults_applied(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1]},
            "projects": {"root": "/tmp"},
        }))
        config = load_config(str(config_file))
        assert config.sessions.max_per_user == 3
        assert config.sessions.output_debounce_ms == 500
        assert config.sessions.output_max_buffer == 2000
        assert config.sessions.silence_warning_minutes == 10
        assert config.claude.command == "claude"
        assert config.claude.default_args == []
        assert config.claude.update_command == "claude update"
        assert config.database.path == "data/sessions.db"


class TestAppConfig:
    def test_is_authorized(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [111, 222]},
            "projects": {"root": "/tmp"},
        }))
        config = load_config(str(config_file))
        assert config.is_authorized(111) is True
        assert config.is_authorized(999) is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.config'`

**Step 3: Implement `src/config.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    pass


@dataclass
class TelegramConfig:
    bot_token: str
    authorized_users: list[int]


@dataclass
class ProjectsConfig:
    root: str
    scan_depth: int = 1


@dataclass
class SessionsConfig:
    max_per_user: int = 3
    output_debounce_ms: int = 500
    output_max_buffer: int = 2000
    silence_warning_minutes: int = 10


@dataclass
class ClaudeConfig:
    command: str = "claude"
    default_args: list[str] = field(default_factory=list)
    update_command: str = "claude update"


@dataclass
class DatabaseConfig:
    path: str = "data/sessions.db"


@dataclass
class AppConfig:
    telegram: TelegramConfig
    projects: ProjectsConfig
    sessions: SessionsConfig
    claude: ClaudeConfig
    database: DatabaseConfig

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self.telegram.authorized_users


def load_config(path: str) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    telegram_raw = raw.get("telegram", {})
    if not telegram_raw.get("bot_token"):
        raise ConfigError("telegram.bot_token is required")
    if not telegram_raw.get("authorized_users"):
        raise ConfigError("telegram.authorized_users must not be empty")

    projects_raw = raw.get("projects", {})
    if not projects_raw.get("root"):
        raise ConfigError("projects.root is required")

    sessions_raw = raw.get("sessions", {}) or {}
    claude_raw = raw.get("claude", {}) or {}
    database_raw = raw.get("database", {}) or {}

    return AppConfig(
        telegram=TelegramConfig(
            bot_token=telegram_raw["bot_token"],
            authorized_users=telegram_raw["authorized_users"],
        ),
        projects=ProjectsConfig(
            root=projects_raw["root"],
            scan_depth=projects_raw.get("scan_depth", 1),
        ),
        sessions=SessionsConfig(
            max_per_user=sessions_raw.get("max_per_user", 3),
            output_debounce_ms=sessions_raw.get("output_debounce_ms", 500),
            output_max_buffer=sessions_raw.get("output_max_buffer", 2000),
            silence_warning_minutes=sessions_raw.get("silence_warning_minutes", 10),
        ),
        claude=ClaudeConfig(
            command=claude_raw.get("command", "claude"),
            default_args=claude_raw.get("default_args", []),
            update_command=claude_raw.get("update_command", "claude update"),
        ),
        database=DatabaseConfig(
            path=database_raw.get("path", "data/sessions.db"),
        ),
    )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_config.py --cov=src.config --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config loading with validation and defaults"
```

---

## Phase 3: Project Scanner

### Task 3.1: Directory scanning for projects

**Files:**
- Create: `src/project_scanner.py`
- Create: `tests/test_project_scanner.py`

**Step 1: Write failing tests**

```python
# tests/test_project_scanner.py
from src.project_scanner import scan_projects, Project


class TestScanProjects:
    def test_finds_git_project(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert "project-alpha" in names

    def test_finds_claude_project(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert "project-beta" in names

    def test_ignores_non_project(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert "not-a-project" not in names

    def test_returns_absolute_paths(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        for p in projects:
            assert p.path.startswith("/")

    def test_returns_sorted_by_name(self, tmp_projects):
        projects = scan_projects(str(tmp_projects))
        names = [p.name for p in projects]
        assert names == sorted(names)

    def test_empty_directory(self, tmp_path):
        projects = scan_projects(str(tmp_path))
        assert projects == []

    def test_nonexistent_directory(self):
        projects = scan_projects("/nonexistent/path")
        assert projects == []

    def test_ignores_hidden_directories(self, tmp_path):
        hidden = tmp_path / ".hidden-project"
        hidden.mkdir()
        (hidden / ".git").mkdir()
        projects = scan_projects(str(tmp_path))
        assert len(projects) == 0

    def test_scan_depth_one(self, tmp_path):
        nested = tmp_path / "parent" / "child"
        nested.mkdir(parents=True)
        (nested / ".git").mkdir()
        projects = scan_projects(str(tmp_path), depth=1)
        names = [p.name for p in projects]
        assert "child" not in names


class TestProject:
    def test_project_equality(self):
        p1 = Project(name="foo", path="/a/foo")
        p2 = Project(name="foo", path="/a/foo")
        assert p1 == p2

    def test_project_repr(self):
        p = Project(name="foo", path="/a/foo")
        assert "foo" in repr(p)
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_project_scanner.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement `src/project_scanner.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    name: str
    path: str


def scan_projects(root: str, depth: int = 1) -> list[Project]:
    root_path = Path(root)
    if not root_path.is_dir():
        return []

    projects = []
    for entry in root_path.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if (entry / ".git").exists() or (entry / ".claude").exists():
            projects.append(Project(name=entry.name, path=str(entry.resolve())))

    projects.sort(key=lambda p: p.name)
    return projects
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_project_scanner.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_project_scanner.py --cov=src.project_scanner --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/project_scanner.py tests/test_project_scanner.py
git commit -m "feat: add project scanner with directory discovery"
```

---

## Phase 4: Database Layer

### Task 4.1: SQLite session persistence

**Files:**
- Create: `src/database.py`
- Create: `tests/test_database.py`

**Step 1: Write failing tests**

```python
# tests/test_database.py
import pytest
from datetime import datetime, timezone

from src.database import Database


@pytest.fixture
async def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


class TestDatabase:
    async def test_initialize_creates_table(self, db):
        sessions = await db.list_sessions(user_id=1)
        assert sessions == []

    async def test_create_session(self, db):
        session_id = await db.create_session(
            user_id=111,
            project="my-project",
            project_path="/home/user/dev/my-project",
        )
        assert isinstance(session_id, int)
        assert session_id > 0

    async def test_get_session(self, db):
        sid = await db.create_session(
            user_id=111, project="proj", project_path="/a/proj"
        )
        session = await db.get_session(sid)
        assert session["user_id"] == 111
        assert session["project"] == "proj"
        assert session["status"] == "active"
        assert session["ended_at"] is None

    async def test_end_session(self, db):
        sid = await db.create_session(
            user_id=111, project="proj", project_path="/a/proj"
        )
        await db.end_session(sid, exit_code=0, status="ended")
        session = await db.get_session(sid)
        assert session["status"] == "ended"
        assert session["exit_code"] == 0
        assert session["ended_at"] is not None

    async def test_end_session_crashed(self, db):
        sid = await db.create_session(
            user_id=111, project="proj", project_path="/a/proj"
        )
        await db.end_session(sid, exit_code=1, status="crashed")
        session = await db.get_session(sid)
        assert session["status"] == "crashed"
        assert session["exit_code"] == 1

    async def test_list_sessions_filters_by_user(self, db):
        await db.create_session(user_id=111, project="a", project_path="/a")
        await db.create_session(user_id=222, project="b", project_path="/b")
        sessions = await db.list_sessions(user_id=111)
        assert len(sessions) == 1
        assert sessions[0]["project"] == "a"

    async def test_list_sessions_ordered_by_most_recent(self, db):
        await db.create_session(user_id=111, project="first", project_path="/a")
        await db.create_session(user_id=111, project="second", project_path="/b")
        sessions = await db.list_sessions(user_id=111)
        assert sessions[0]["project"] == "second"
        assert sessions[1]["project"] == "first"

    async def test_get_nonexistent_session_returns_none(self, db):
        session = await db.get_session(999)
        assert session is None

    async def test_mark_active_sessions_lost(self, db):
        sid1 = await db.create_session(user_id=111, project="a", project_path="/a")
        sid2 = await db.create_session(user_id=111, project="b", project_path="/b")
        await db.end_session(sid1, exit_code=0, status="ended")
        lost = await db.mark_active_sessions_lost()
        assert len(lost) == 1
        assert lost[0]["id"] == sid2
        session = await db.get_session(sid2)
        assert session["status"] == "lost"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement `src/database.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    project      TEXT NOT NULL,
    project_path TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    exit_code    INTEGER,
    status       TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
"""


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def create_session(
        self, user_id: int, project: str, project_path: str
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._db.execute(
            "INSERT INTO sessions (user_id, project, project_path, started_at, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (user_id, project, project_path, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_session(self, session_id: int) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def end_session(
        self, session_id: int, exit_code: int | None, status: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE sessions SET ended_at = ?, exit_code = ?, status = ? WHERE id = ?",
            (now, exit_code, status, session_id),
        )
        await self._db.commit()

    async def list_sessions(self, user_id: int) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def mark_active_sessions_lost(self) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE status = 'active'"
        )
        rows = await cursor.fetchall()
        lost = [dict(r) for r in rows]
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE sessions SET status = 'lost', ended_at = ? WHERE status = 'active'",
            (now,),
        )
        await self._db.commit()
        return lost
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_database.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_database.py --cov=src.database --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/database.py tests/test_database.py
git commit -m "feat: add SQLite database layer for session persistence"
```

---

## Phase 5: Output Parser

This is the most complex and most testable module. Split into sub-tasks.

### Task 5.1: ANSI stripping

**Files:**
- Create: `src/output_parser.py`
- Create: `tests/test_output_parser.py`

**Step 1: Write failing tests**

```python
# tests/test_output_parser.py
from src.output_parser import strip_ansi


class TestStripAnsi:
    def test_strips_color_codes(self):
        assert strip_ansi("\x1b[31mred text\x1b[0m") == "red text"

    def test_strips_bold(self):
        assert strip_ansi("\x1b[1mbold\x1b[0m") == "bold"

    def test_strips_cursor_movement(self):
        assert strip_ansi("\x1b[2J\x1b[H hello") == " hello"

    def test_strips_multiple_codes(self):
        assert strip_ansi("\x1b[1;32mgreen bold\x1b[0m normal") == "green bold normal"

    def test_preserves_plain_text(self):
        assert strip_ansi("hello world") == "hello world"

    def test_strips_256_color(self):
        assert strip_ansi("\x1b[38;5;196mred\x1b[0m") == "red"

    def test_strips_rgb_color(self):
        assert strip_ansi("\x1b[38;2;255;0;0mred\x1b[0m") == "red"

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_strips_erase_line(self):
        assert strip_ansi("\x1b[2Ksome text") == "some text"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestStripAnsi -v`
Expected: FAIL

**Step 3: Implement `strip_ansi` in `src/output_parser.py`**

```python
from __future__ import annotations

import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\x1b\[[\d;]*m")
# More comprehensive: covers CSI sequences, OSC sequences
_ANSI_FULL_RE = re.compile(
    r"\x1b"          # ESC
    r"(?:"
    r"\[[0-9;]*[a-zA-Z]"   # CSI sequences: ESC [ ... letter
    r"|\][^\x07]*\x07"     # OSC sequences: ESC ] ... BEL
    r"|\[[0-9;]*m"         # SGR (color) sequences
    r")"
)


def strip_ansi(text: str) -> str:
    return _ANSI_FULL_RE.sub("", text)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestStripAnsi -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add ANSI escape code stripping"
```

### Task 5.2: Spinner/progress filter

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**Step 1: Append failing tests to `tests/test_output_parser.py`**

```python
from src.output_parser import strip_ansi, filter_spinners


class TestFilterSpinners:
    def test_collapses_braille_spinners(self):
        text = "⠋ Working...\n⠙ Working...\n⠹ Working...\n⠸ Working..."
        result = filter_spinners(text)
        assert result == "Working..."

    def test_preserves_non_spinner_text(self):
        text = "Hello world\nThis is normal text"
        assert filter_spinners(text) == text

    def test_collapses_dots_spinner(self):
        text = "Loading.\nLoading..\nLoading..."
        result = filter_spinners(text)
        assert result == "Loading..."

    def test_empty_string(self):
        assert filter_spinners("") == ""

    def test_mixed_content(self):
        text = "Starting\n⠋ Thinking...\n⠙ Thinking...\nDone!"
        result = filter_spinners(text)
        assert "Done!" in result
        assert result.count("Thinking") == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestFilterSpinners -v`
Expected: FAIL

**Step 3: Implement `filter_spinners`**

Add to `src/output_parser.py`:

```python
_BRAILLE_SPINNER = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*")
_DOTS_SPINNER = re.compile(r"^(.+?)\.{1,3}$", re.MULTILINE)


def filter_spinners(text: str) -> str:
    lines = text.split("\n")
    seen_spinners: dict[str, str] = {}
    result_lines = []

    for line in lines:
        stripped = _BRAILLE_SPINNER.sub("", line).strip()
        if stripped != line.strip() and stripped:
            seen_spinners[stripped] = stripped
            continue
        result_lines.append(line)

    for spinner_text in seen_spinners.values():
        result_lines.append(spinner_text)

    # Collapse progressive dots (Loading. -> Loading.. -> Loading...)
    final_text = "\n".join(result_lines)
    dot_groups: dict[str, int] = {}
    for match in _DOTS_SPINNER.finditer(final_text):
        base = match.group(1).rstrip(".")
        dot_groups[base] = max(dot_groups.get(base, 0), len(match.group(0)) - len(base))

    for base, dot_count in dot_groups.items():
        if dot_count > 1:
            for i in range(1, dot_count):
                final_text = final_text.replace(f"{base}{'.' * i}\n", "")
            # Keep only the last variant
            final_text = final_text.strip()

    return final_text.strip() if final_text.strip() else ""
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestFilterSpinners -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add spinner/progress filter for terminal output"
```

### Task 5.3: Prompt detector

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**Step 1: Append failing tests**

```python
from src.output_parser import detect_prompt, PromptType, DetectedPrompt


class TestDetectPrompt:
    def test_detects_yes_no_uppercase_default(self):
        result = detect_prompt("Allow Read tool? [Y/n]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO
        assert result.options == ["Yes", "No"]
        assert result.default == "Yes"

    def test_detects_yes_no_lowercase_default(self):
        result = detect_prompt("Continue? [y/N]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO
        assert result.default == "No"

    def test_detects_multiple_choice(self):
        text = "Choose an option:\n  1. Option A\n  2. Option B\n  3. Option C\n> "
        result = detect_prompt(text)
        assert result is not None
        assert result.prompt_type == PromptType.MULTIPLE_CHOICE
        assert len(result.options) == 3

    def test_detects_tool_approval(self):
        result = detect_prompt("Allow Bash tool? [Y/n]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO

    def test_no_prompt_in_regular_text(self):
        result = detect_prompt("Hello, this is normal output from Claude.")
        assert result is None

    def test_empty_string(self):
        result = detect_prompt("")
        assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestDetectPrompt -v`
Expected: FAIL

**Step 3: Implement prompt detection**

Add to `src/output_parser.py`:

```python
from dataclasses import dataclass
from enum import Enum


class PromptType(Enum):
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"


@dataclass
class DetectedPrompt:
    prompt_type: PromptType
    options: list[str]
    default: str | None = None
    raw_text: str = ""


_YES_NO_RE = re.compile(r"\[([Yy])/([Nn])\]|\[([Nn])/([Yy])\]")
_MULTI_CHOICE_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)


def detect_prompt(text: str) -> DetectedPrompt | None:
    if not text.strip():
        return None

    # Check yes/no pattern
    match = _YES_NO_RE.search(text)
    if match:
        if match.group(1) and match.group(1).isupper():
            default = "Yes"
        elif match.group(4) and match.group(4).isupper():
            default = "Yes"
        elif match.group(2) and match.group(2).isupper():
            default = "No"
        elif match.group(3) and match.group(3).isupper():
            default = "No"
        else:
            default = None
        return DetectedPrompt(
            prompt_type=PromptType.YES_NO,
            options=["Yes", "No"],
            default=default,
            raw_text=text,
        )

    # Check multiple choice pattern
    choices = _MULTI_CHOICE_RE.findall(text)
    if len(choices) >= 2:
        options = [label.strip() for _, label in choices]
        return DetectedPrompt(
            prompt_type=PromptType.MULTIPLE_CHOICE,
            options=options,
            raw_text=text,
        )

    return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestDetectPrompt -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add interactive prompt detection (yes/no, multiple choice)"
```

### Task 5.4: Context usage detector

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**Step 1: Append failing tests**

```python
from src.output_parser import detect_context_usage, ContextUsage


class TestDetectContextUsage:
    def test_detects_percentage(self):
        result = detect_context_usage("Context: 75% used")
        assert result is not None
        assert result.percentage == 75

    def test_detects_compact_suggestion(self):
        result = detect_context_usage("Context window is almost full. Consider using /compact")
        assert result is not None
        assert result.needs_compact is True

    def test_no_context_info(self):
        result = detect_context_usage("Hello world, just some normal output")
        assert result is None

    def test_empty_string(self):
        result = detect_context_usage("")
        assert result is None

    def test_detects_token_count(self):
        result = detect_context_usage("Context: 150k/200k tokens used")
        assert result is not None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestDetectContextUsage -v`
Expected: FAIL

**Step 3: Implement context usage detection**

Add to `src/output_parser.py`:

```python
@dataclass
class ContextUsage:
    percentage: int | None = None
    needs_compact: bool = False
    raw_text: str = ""


_CONTEXT_PCT_RE = re.compile(r"(?:context|ctx)[:\s]*(\d+)\s*%", re.IGNORECASE)
_CONTEXT_TOKENS_RE = re.compile(r"(\d+)k\s*/\s*(\d+)k\s*tokens", re.IGNORECASE)
_COMPACT_RE = re.compile(r"compact|context.*(?:full|almost|running out)", re.IGNORECASE)


def detect_context_usage(text: str) -> ContextUsage | None:
    if not text.strip():
        return None

    pct_match = _CONTEXT_PCT_RE.search(text)
    token_match = _CONTEXT_TOKENS_RE.search(text)
    compact_match = _COMPACT_RE.search(text)

    if not any([pct_match, token_match, compact_match]):
        return None

    percentage = None
    if pct_match:
        percentage = int(pct_match.group(1))
    elif token_match:
        used = int(token_match.group(1))
        total = int(token_match.group(2))
        percentage = round(used / total * 100) if total > 0 else None

    return ContextUsage(
        percentage=percentage,
        needs_compact=compact_match is not None,
        raw_text=text,
    )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestDetectContextUsage -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add context usage detection with compact alerts"
```

### Task 5.5: File path detector

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**Step 1: Append failing tests**

```python
from src.output_parser import detect_file_paths


class TestDetectFilePaths:
    def test_detects_wrote_to(self):
        paths = detect_file_paths("Wrote to /home/user/output.png")
        assert "/home/user/output.png" in paths

    def test_detects_saved(self):
        paths = detect_file_paths("File saved /tmp/result.pdf")
        assert "/tmp/result.pdf" in paths

    def test_detects_created(self):
        paths = detect_file_paths("Created /home/user/project/new_file.py")
        assert "/home/user/project/new_file.py" in paths

    def test_no_paths_in_regular_text(self):
        paths = detect_file_paths("Hello world, just some text")
        assert paths == []

    def test_multiple_paths(self):
        text = "Wrote to /a/file1.txt and saved /b/file2.txt"
        paths = detect_file_paths(text)
        assert len(paths) == 2

    def test_empty_string(self):
        assert detect_file_paths("") == []

    def test_ignores_short_paths(self):
        paths = detect_file_paths("Wrote to /tmp")
        assert paths == []
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestDetectFilePaths -v`
Expected: FAIL

**Step 3: Implement file path detection**

Add to `src/output_parser.py`:

```python
_FILE_PATH_RE = re.compile(
    r"(?:wrote to|saved|created|generated|output)\s+"
    r"(\/[\w./\-]+\.\w+)",
    re.IGNORECASE,
)


def detect_file_paths(text: str) -> list[str]:
    if not text.strip():
        return []
    matches = _FILE_PATH_RE.findall(text)
    return [m for m in matches if len(m) > 5]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestDetectFilePaths -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add file path detection in Claude output"
```

### Task 5.6: Telegram markdown formatter

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**Ref:** `docs/telegram/api/bots/messages/formatting.md` — MarkdownV2 requires escaping: `_*[]()~>#+\-=|{}.!`

**Step 1: Append failing tests**

```python
from src.output_parser import format_telegram


class TestFormatTelegram:
    def test_escapes_special_chars(self):
        result = format_telegram("Hello! How are you?")
        assert "\\!" in result

    def test_preserves_code_blocks(self):
        text = "Here is code:\n```python\nprint('hello')\n```"
        result = format_telegram(text)
        assert "```python" in result
        assert "print('hello')" in result

    def test_preserves_inline_code(self):
        text = "Use the `print()` function"
        result = format_telegram(text)
        assert "`print()`" in result

    def test_converts_bold(self):
        text = "This is **bold** text"
        result = format_telegram(text)
        assert "*bold*" in result

    def test_converts_italic(self):
        text = "This is *italic* text"
        result = format_telegram(text)
        assert "_italic_" in result

    def test_empty_string(self):
        assert format_telegram("") == ""

    def test_plain_text_with_dots(self):
        result = format_telegram("version 1.2.3 is out")
        assert "\\." in result
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestFormatTelegram -v`
Expected: FAIL

**Step 3: Implement Telegram formatter**

Add to `src/output_parser.py`:

```python
_TG_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!\\"
_TG_ESCAPE_RE = re.compile(r"([" + re.escape(_TG_ESCAPE_CHARS) + r"])")

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _escape_telegram(text: str) -> str:
    return _TG_ESCAPE_RE.sub(r"\\\1", text)


def format_telegram(text: str) -> str:
    if not text:
        return ""

    # Extract code blocks and inline code to protect them
    code_blocks: list[tuple[str, str]] = []
    inline_codes: list[str] = []

    def _save_block(match: re.Match) -> str:
        idx = len(code_blocks)
        code_blocks.append((match.group(1), match.group(2)))
        return f"\x00CODEBLOCK{idx}\x00"

    def _save_inline(match: re.Match) -> str:
        idx = len(inline_codes)
        inline_codes.append(match.group(1))
        return f"\x00INLINE{idx}\x00"

    result = _CODE_BLOCK_RE.sub(_save_block, text)
    result = _INLINE_CODE_RE.sub(_save_inline, result)

    # Convert markdown bold/italic before escaping
    result = _BOLD_RE.sub(r"\x00BOLD_START\1\x00BOLD_END", result)
    result = _ITALIC_RE.sub(r"\x00ITALIC_START\1\x00ITALIC_END", result)

    # Escape remaining special chars
    result = _escape_telegram(result)

    # Restore formatting
    result = result.replace("\x00BOLD_START", "*").replace("\x00BOLD_END", "*")
    result = result.replace("\x00ITALIC_START", "_").replace("\x00ITALIC_END", "_")

    # Restore code blocks
    for idx, (lang, code) in enumerate(code_blocks):
        placeholder = _escape_telegram(f"\x00CODEBLOCK{idx}\x00")
        result = result.replace(placeholder, f"```{lang}\n{code}```")

    # Restore inline code
    for idx, code in enumerate(inline_codes):
        placeholder = _escape_telegram(f"\x00INLINE{idx}\x00")
        result = result.replace(placeholder, f"`{code}`")

    return result
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestFormatTelegram -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add Telegram MarkdownV2 formatter"
```

### Task 5.7: Message splitter

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**Step 1: Append failing tests**

```python
from src.output_parser import split_message, TELEGRAM_MAX_LENGTH


class TestSplitMessage:
    def test_short_message_unchanged(self):
        result = split_message("Hello world")
        assert result == ["Hello world"]

    def test_splits_at_paragraph_boundary(self):
        text = "A" * 2000 + "\n\n" + "B" * 2000
        result = split_message(text)
        assert len(result) == 2
        assert result[0].strip().endswith("A" * 2000)
        assert result[1].strip().startswith("B" * 2000)

    def test_splits_long_message(self):
        text = "A" * 5000
        result = split_message(text)
        assert len(result) >= 2
        assert all(len(chunk) <= TELEGRAM_MAX_LENGTH for chunk in result)

    def test_preserves_code_blocks(self):
        text = "before\n```python\n" + "x = 1\n" * 500 + "```\nafter"
        result = split_message(text)
        # Code block should not be split in the middle
        for chunk in result:
            if "```python" in chunk:
                assert "```" in chunk[chunk.index("```python") + 10 :]

    def test_empty_string(self):
        assert split_message("") == [""]

    def test_exactly_max_length(self):
        text = "A" * TELEGRAM_MAX_LENGTH
        result = split_message(text)
        assert len(result) == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_output_parser.py::TestSplitMessage -v`
Expected: FAIL

**Step 3: Implement message splitter**

Add to `src/output_parser.py`:

```python
TELEGRAM_MAX_LENGTH = 4096


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    if not text or len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try to split at paragraph boundary
        split_at = remaining.rfind("\n\n", 0, max_length)

        # Try newline boundary
        if split_at == -1:
            split_at = remaining.rfind("\n", 0, max_length)

        # Try space boundary
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_length)

        # Hard split as last resort
        if split_at == -1:
            split_at = max_length

        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    return chunks if chunks else [""]
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py::TestSplitMessage -v`
Expected: all PASS

**Step 5: Check full output_parser coverage**

Run: `pytest tests/test_output_parser.py --cov=src.output_parser --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add message splitter for Telegram 4096-char limit"
```

---

## Phase 6: Git Info

### Task 6.1: Git branch and PR detection

**Files:**
- Create: `src/git_info.py`
- Create: `tests/test_git_info.py`

**Step 1: Write failing tests**

```python
# tests/test_git_info.py
from unittest.mock import AsyncMock, patch

import pytest

from src.git_info import get_git_info, GitInfo


class TestGetGitInfo:
    async def test_returns_branch_name(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                "feature/my-branch",  # git branch
                "",                    # gh pr view (no PR)
            ]
            info = await get_git_info("/some/project")
            assert info.branch == "feature/my-branch"

    async def test_returns_pr_info(self):
        import json
        pr_json = json.dumps({
            "url": "https://github.com/user/repo/pull/42",
            "title": "My PR title",
            "state": "OPEN",
        })
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = [
                "feature/branch",
                pr_json,
            ]
            info = await get_git_info("/some/project")
            assert info.pr_url == "https://github.com/user/repo/pull/42"
            assert info.pr_title == "My PR title"

    async def test_no_pr(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = ["main", ""]
            info = await get_git_info("/some/project")
            assert info.pr_url is None
            assert info.pr_title is None

    async def test_git_command_fails(self):
        with patch("src.git_info._run_command", new_callable=AsyncMock) as mock_run:
            mock_run.side_effect = Exception("git not found")
            info = await get_git_info("/some/project")
            assert info.branch is None
            assert info.pr_url is None

    async def test_formats_with_pr(self):
        info = GitInfo(
            branch="feature/foo",
            pr_url="https://github.com/u/r/pull/1",
            pr_title="Fix bug",
        )
        text = info.format()
        assert "feature/foo" in text
        assert "Fix bug" in text

    async def test_formats_without_pr(self):
        info = GitInfo(branch="main", pr_url=None, pr_title=None)
        text = info.format()
        assert "main" in text
        assert "No open PR" in text

    async def test_formats_no_git(self):
        info = GitInfo(branch=None, pr_url=None, pr_title=None)
        text = info.format()
        assert "not a git repository" in text.lower() or "no git info" in text.lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_git_info.py -v`
Expected: FAIL

**Step 3: Implement `src/git_info.py`**

```python
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass


@dataclass
class GitInfo:
    branch: str | None = None
    pr_url: str | None = None
    pr_title: str | None = None
    pr_state: str | None = None

    def format(self) -> str:
        if not self.branch:
            return "No git info available"
        parts = [f"Branch: `{self.branch}`"]
        if self.pr_url and self.pr_title:
            parts.append(f"PR: [{self.pr_title}]({self.pr_url})")
        else:
            parts.append("No open PR")
        return " | ".join(parts)


async def _run_command(cmd: list[str], cwd: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()


async def get_git_info(project_path: str) -> GitInfo:
    try:
        branch = await _run_command(
            ["git", "branch", "--show-current"], cwd=project_path
        )
    except Exception:
        return GitInfo()

    pr_url = None
    pr_title = None
    pr_state = None

    try:
        pr_raw = await _run_command(
            ["gh", "pr", "view", "--json", "url,title,state"], cwd=project_path
        )
        if pr_raw:
            pr_data = json.loads(pr_raw)
            pr_url = pr_data.get("url")
            pr_title = pr_data.get("title")
            pr_state = pr_data.get("state")
    except Exception:
        pass

    return GitInfo(
        branch=branch or None,
        pr_url=pr_url,
        pr_title=pr_title,
        pr_state=pr_state,
    )
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_git_info.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_git_info.py --cov=src.git_info --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/git_info.py tests/test_git_info.py
git commit -m "feat: add git branch and PR info detection"
```

---

## Phase 7: File Handler

### Task 7.1: File upload/download paths and cleanup

**Files:**
- Create: `src/file_handler.py`
- Create: `tests/test_file_handler.py`

**Step 1: Write failing tests**

```python
# tests/test_file_handler.py
import os

import pytest

from src.file_handler import FileHandler


class TestFileHandler:
    def test_get_upload_dir_creates_directory(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        upload_dir = handler.get_upload_dir("my-project", 1)
        assert os.path.isdir(upload_dir)
        assert "my-project" in upload_dir
        assert "1" in upload_dir

    def test_get_upload_path(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        path = handler.get_upload_path("my-project", 1, "photo.jpg")
        assert path.endswith("photo.jpg")
        assert os.path.isdir(os.path.dirname(path))

    def test_cleanup_session_files(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        upload_dir = handler.get_upload_dir("proj", 1)
        test_file = os.path.join(upload_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        assert os.path.exists(test_file)
        handler.cleanup_session(project_name="proj", session_id=1)
        assert not os.path.exists(upload_dir)

    def test_cleanup_nonexistent_session(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        # Should not raise
        handler.cleanup_session(project_name="nope", session_id=99)

    def test_unique_filenames(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        path1 = handler.get_upload_path("proj", 1, "file.txt")
        with open(path1, "w") as f:
            f.write("first")
        path2 = handler.get_upload_path("proj", 1, "file.txt")
        assert path1 != path2

    def test_file_exists_check(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        assert handler.file_exists("/nonexistent/file.txt") is False
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")
        assert handler.file_exists(str(real_file)) is True

    def test_get_file_size(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        f = tmp_path / "sized.txt"
        f.write_text("hello")
        assert handler.get_file_size(str(f)) == 5
        assert handler.get_file_size("/nonexistent") is None
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_file_handler.py -v`
Expected: FAIL

**Step 3: Implement `src/file_handler.py`**

```python
from __future__ import annotations

import os
import shutil
from pathlib import Path


class FileHandler:
    def __init__(self, base_dir: str = "/tmp/claude") -> None:
        self._base_dir = base_dir

    def _session_dir(self, project_name: str, session_id: int) -> str:
        return os.path.join(self._base_dir, f"{project_name}_{session_id}")

    def get_upload_dir(self, project_name: str, session_id: int) -> str:
        d = self._session_dir(project_name, session_id)
        os.makedirs(d, exist_ok=True)
        return d

    def get_upload_path(
        self, project_name: str, session_id: int, filename: str
    ) -> str:
        upload_dir = self.get_upload_dir(project_name, session_id)
        path = os.path.join(upload_dir, filename)
        if os.path.exists(path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(path):
                path = os.path.join(upload_dir, f"{base}_{counter}{ext}")
                counter += 1
        return path

    def cleanup_session(self, project_name: str, session_id: int) -> None:
        d = self._session_dir(project_name, session_id)
        if os.path.isdir(d):
            shutil.rmtree(d)

    def file_exists(self, path: str) -> bool:
        return os.path.isfile(path)

    def get_file_size(self, path: str) -> int | None:
        try:
            return os.path.getsize(path)
        except OSError:
            return None
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_file_handler.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_file_handler.py --cov=src.file_handler --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/file_handler.py tests/test_file_handler.py
git commit -m "feat: add file handler for upload/download with session cleanup"
```

---

## Phase 8: Claude Process Layer

### Task 8.1: PTY process spawning, reading, and writing

**Files:**
- Create: `src/claude_process.py`
- Create: `tests/test_claude_process.py`

**Note:** This module interacts with real PTY processes. Tests use a mock command (`cat` or `echo`) instead of the real `claude` binary.

**Step 1: Write failing tests**

```python
# tests/test_claude_process.py
import asyncio

import pytest

from src.claude_process import ClaudeProcess


class TestClaudeProcess:
    async def test_spawn_and_read(self):
        # Use 'cat' as a simple PTY process that echoes input
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        assert proc.is_alive()
        await proc.write("hello\n")
        # Give cat time to echo
        await asyncio.sleep(0.2)
        output = proc.read_available()
        assert "hello" in output
        await proc.terminate()

    async def test_terminate(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        assert proc.is_alive()
        await proc.terminate()
        assert not proc.is_alive()

    async def test_exit_code_after_terminate(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        await proc.terminate()
        exit_code = proc.exit_code()
        assert exit_code is not None

    async def test_write_to_terminated_process(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        await proc.terminate()
        # Should not raise, just silently fail
        await proc.write("hello\n")

    async def test_read_from_empty_buffer(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        output = proc.read_available()
        # Might have a prompt or be empty
        assert isinstance(output, str)
        await proc.terminate()

    async def test_cwd_is_set(self, tmp_path):
        proc = ClaudeProcess(command="pwd", args=[], cwd=str(tmp_path))
        await proc.spawn()
        await asyncio.sleep(0.3)
        output = proc.read_available()
        assert str(tmp_path) in output or "tmp" in output
        # pwd exits immediately, so process may already be dead
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_claude_process.py -v`
Expected: FAIL

**Step 3: Implement `src/claude_process.py`**

```python
from __future__ import annotations

import asyncio
import pexpect
import pexpect.popen_spawn


class ClaudeProcess:
    def __init__(self, command: str, args: list[str], cwd: str) -> None:
        self._command = command
        self._args = args
        self._cwd = cwd
        self._process: pexpect.spawn | None = None
        self._buffer: str = ""

    async def spawn(self) -> None:
        cmd = self._command
        if self._args:
            cmd = f"{self._command} {' '.join(self._args)}"
        loop = asyncio.get_event_loop()
        self._process = await loop.run_in_executor(
            None,
            lambda: pexpect.spawn(
                cmd,
                cwd=self._cwd,
                encoding="utf-8",
                timeout=5,
                maxread=4096,
            ),
        )

    def is_alive(self) -> bool:
        if self._process is None:
            return False
        return self._process.isalive()

    async def write(self, text: str) -> None:
        if not self.is_alive():
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._process.send, text)

    def read_available(self) -> str:
        if self._process is None:
            return ""
        try:
            # Non-blocking read
            while True:
                try:
                    chunk = self._process.read_nonblocking(size=4096, timeout=0)
                    self._buffer += chunk
                except pexpect.TIMEOUT:
                    break
                except pexpect.EOF:
                    break
        except Exception:
            pass
        result = self._buffer
        self._buffer = ""
        return result

    async def terminate(self) -> None:
        if self._process is None:
            return
        loop = asyncio.get_event_loop()
        if self._process.isalive():
            await loop.run_in_executor(None, self._process.close, True)

    def exit_code(self) -> int | None:
        if self._process is None:
            return None
        return self._process.exitstatus
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_claude_process.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_claude_process.py --cov=src.claude_process --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/claude_process.py tests/test_claude_process.py
git commit -m "feat: add Claude process layer with PTY spawn, read, write, terminate"
```

---

## Phase 9: Session Manager

### Task 9.1: Session lifecycle, routing, and limits

**Files:**
- Create: `src/session_manager.py`
- Create: `tests/test_session_manager.py`

**Step 1: Write failing tests**

```python
# tests/test_session_manager.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.session_manager import SessionManager, ClaudeSession, SessionError


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.create_session = AsyncMock(return_value=1)
    db.end_session = AsyncMock()
    return db


@pytest.fixture
def mock_file_handler():
    return MagicMock()


@pytest.fixture
def manager(mock_db, mock_file_handler):
    return SessionManager(
        claude_command="cat",
        claude_args=[],
        max_per_user=3,
        db=mock_db,
        file_handler=mock_file_handler,
    )


class TestSessionManager:
    async def test_create_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            session = await manager.create_session(
                user_id=111, project_name="proj", project_path="/a/proj"
            )
            assert session.user_id == 111
            assert session.project_name == "proj"
            assert session.status == "active"

    async def test_session_limit_enforced(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            await manager.create_session(111, "p1", "/a/p1")
            await manager.create_session(111, "p2", "/a/p2")
            await manager.create_session(111, "p3", "/a/p3")
            with pytest.raises(SessionError, match="limit"):
                await manager.create_session(111, "p4", "/a/p4")

    async def test_get_active_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            session = await manager.create_session(111, "proj", "/a/proj")
            active = manager.get_active_session(111)
            assert active is not None
            assert active.session_id == session.session_id

    async def test_switch_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            s1 = await manager.create_session(111, "p1", "/a/p1")
            s2 = await manager.create_session(111, "p2", "/a/p2")
            manager.switch_session(111, s1.session_id)
            assert manager.get_active_session(111).session_id == s1.session_id

    async def test_list_sessions(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            await manager.create_session(111, "p1", "/a/p1")
            await manager.create_session(111, "p2", "/a/p2")
            sessions = manager.list_sessions(111)
            assert len(sessions) == 2

    async def test_kill_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            mock_proc.terminate = AsyncMock()
            mock_proc.exit_code.return_value = 0
            MockProc.return_value = mock_proc
            session = await manager.create_session(111, "proj", "/a/proj")
            await manager.kill_session(111, session.session_id)
            assert len(manager.list_sessions(111)) == 0

    async def test_different_users_independent(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            await manager.create_session(111, "p1", "/a/p1")
            await manager.create_session(222, "p2", "/a/p2")
            assert len(manager.list_sessions(111)) == 1
            assert len(manager.list_sessions(222)) == 1

    async def test_has_active_sessions(self, manager):
        assert manager.has_active_sessions() is False
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            await manager.create_session(111, "proj", "/a/proj")
            assert manager.has_active_sessions() is True

    async def test_active_session_count(self, manager):
        assert manager.active_session_count() == 0
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            mock_proc = AsyncMock()
            mock_proc.is_alive.return_value = True
            mock_proc.spawn = AsyncMock()
            MockProc.return_value = mock_proc
            await manager.create_session(111, "p1", "/a/p1")
            await manager.create_session(222, "p2", "/a/p2")
            assert manager.active_session_count() == 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_session_manager.py -v`
Expected: FAIL

**Step 3: Implement `src/session_manager.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.claude_process import ClaudeProcess
from src.database import Database
from src.file_handler import FileHandler


class SessionError(Exception):
    pass


@dataclass
class ClaudeSession:
    session_id: int
    user_id: int
    project_name: str
    project_path: str
    process: ClaudeProcess
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    db_session_id: int = 0


class SessionManager:
    def __init__(
        self,
        claude_command: str,
        claude_args: list[str],
        max_per_user: int,
        db: Database,
        file_handler: FileHandler,
    ) -> None:
        self._command = claude_command
        self._args = claude_args
        self._max_per_user = max_per_user
        self._db = db
        self._file_handler = file_handler
        # {user_id: {session_id: ClaudeSession}}
        self._sessions: dict[int, dict[int, ClaudeSession]] = {}
        # {user_id: active_session_id}
        self._active: dict[int, int] = {}
        self._next_id: dict[int, int] = {}

    async def create_session(
        self, user_id: int, project_name: str, project_path: str
    ) -> ClaudeSession:
        user_sessions = self._sessions.get(user_id, {})
        if len(user_sessions) >= self._max_per_user:
            raise SessionError(
                f"Session limit reached ({self._max_per_user}). "
                f"Kill a session first."
            )

        session_id = self._next_id.get(user_id, 1)
        self._next_id[user_id] = session_id + 1

        process = ClaudeProcess(
            command=self._command, args=self._args, cwd=project_path
        )
        await process.spawn()

        db_id = await self._db.create_session(
            user_id=user_id, project=project_name, project_path=project_path
        )

        session = ClaudeSession(
            session_id=session_id,
            user_id=user_id,
            project_name=project_name,
            project_path=project_path,
            process=process,
            db_session_id=db_id,
        )

        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        self._sessions[user_id][session_id] = session
        self._active[user_id] = session_id

        return session

    def get_active_session(self, user_id: int) -> ClaudeSession | None:
        active_id = self._active.get(user_id)
        if active_id is None:
            return None
        return self._sessions.get(user_id, {}).get(active_id)

    def switch_session(self, user_id: int, session_id: int) -> None:
        if session_id not in self._sessions.get(user_id, {}):
            raise SessionError(f"Session {session_id} not found")
        self._active[user_id] = session_id

    def list_sessions(self, user_id: int) -> list[ClaudeSession]:
        return list(self._sessions.get(user_id, {}).values())

    async def kill_session(self, user_id: int, session_id: int) -> None:
        session = self._sessions.get(user_id, {}).get(session_id)
        if session is None:
            raise SessionError(f"Session {session_id} not found")

        await session.process.terminate()
        exit_code = session.process.exit_code()
        session.status = "dead"

        await self._db.end_session(
            session.db_session_id, exit_code=exit_code, status="ended"
        )
        self._file_handler.cleanup_session(session.project_name, session_id)
        del self._sessions[user_id][session_id]

        # Switch to another session if available
        remaining = self._sessions.get(user_id, {})
        if remaining:
            self._active[user_id] = next(iter(remaining))
        else:
            self._active.pop(user_id, None)

    def has_active_sessions(self) -> bool:
        return any(len(s) > 0 for s in self._sessions.values())

    def active_session_count(self) -> int:
        return sum(len(s) for s in self._sessions.values())
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_session_manager.py --cov=src.session_manager --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/session_manager.py tests/test_session_manager.py
git commit -m "feat: add session manager with lifecycle, routing, and limits"
```

---

## Phase 10: Telegram Bot Layer

### Task 10.1: Auth middleware and basic command handlers

**Files:**
- Create: `src/bot.py`
- Create: `tests/test_bot.py`

**Ref:** `docs/telegram/python-telegram-bot/handlers/command-handler.md`, `docs/telegram/python-telegram-bot/types/keyboards.md`

**Step 1: Write failing tests**

```python
# tests/test_bot.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot import (
    is_authorized,
    build_project_keyboard,
    build_sessions_keyboard,
    format_session_started,
    format_session_ended,
    format_history_entry,
)
from src.project_scanner import Project


class TestIsAuthorized:
    def test_authorized_user(self):
        assert is_authorized(111, [111, 222]) is True

    def test_unauthorized_user(self):
        assert is_authorized(999, [111, 222]) is False

    def test_empty_allowlist(self):
        assert is_authorized(111, []) is False


class TestBuildProjectKeyboard:
    def test_creates_keyboard_from_projects(self):
        projects = [
            Project(name="alpha", path="/a/alpha"),
            Project(name="beta", path="/a/beta"),
        ]
        keyboard = build_project_keyboard(projects)
        assert len(keyboard) == 2
        assert keyboard[0][0]["text"] == "alpha"
        assert keyboard[0][0]["callback_data"] == "project:/a/alpha"

    def test_empty_projects(self):
        keyboard = build_project_keyboard([])
        assert keyboard == []

    def test_pagination_over_8_projects(self):
        projects = [Project(name=f"p{i}", path=f"/a/p{i}") for i in range(12)]
        keyboard = build_project_keyboard(projects, page=0, page_size=8)
        # 8 project buttons + 1 row with "Next >" button
        project_rows = [row for row in keyboard if any("project:" in btn.get("callback_data", "") for btn in row)]
        nav_rows = [row for row in keyboard if any("page:" in btn.get("callback_data", "") for btn in row)]
        assert len(project_rows) == 8
        assert len(nav_rows) == 1


class TestBuildSessionsKeyboard:
    def test_creates_session_buttons(self):
        sessions = [
            MagicMock(session_id=1, project_name="alpha"),
            MagicMock(session_id=2, project_name="beta"),
        ]
        keyboard = build_sessions_keyboard(sessions, active_id=1)
        assert len(keyboard) >= 2

    def test_marks_active_session(self):
        sessions = [MagicMock(session_id=1, project_name="alpha")]
        keyboard = build_sessions_keyboard(sessions, active_id=1)
        # First row should have the active marker
        first_row_text = keyboard[0][0]["text"]
        assert "alpha" in first_row_text

    def test_empty_sessions(self):
        keyboard = build_sessions_keyboard([], active_id=None)
        assert keyboard == []


class TestFormatMessages:
    def test_session_started(self):
        msg = format_session_started("my-project", 1)
        assert "my-project" in msg
        assert "1" in msg

    def test_session_ended(self):
        msg = format_session_ended("my-project", 1)
        assert "my-project" in msg
        assert "ended" in msg.lower()

    def test_history_entry(self):
        entry = {
            "project": "my-proj",
            "started_at": "2026-02-09T10:00:00",
            "ended_at": "2026-02-09T11:00:00",
            "status": "ended",
            "exit_code": 0,
        }
        msg = format_history_entry(entry)
        assert "my-proj" in msg
        assert "ended" in msg.lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bot.py -v`
Expected: FAIL

**Step 3: Implement `src/bot.py` — helper functions first**

```python
from __future__ import annotations

from src.project_scanner import Project


def is_authorized(user_id: int, authorized_users: list[int]) -> bool:
    return user_id in authorized_users


def build_project_keyboard(
    projects: list[Project], page: int = 0, page_size: int = 8
) -> list[list[dict]]:
    if not projects:
        return []

    start = page * page_size
    end = start + page_size
    page_projects = projects[start:end]

    rows = []
    for proj in page_projects:
        rows.append([{"text": proj.name, "callback_data": f"project:{proj.path}"}])

    # Pagination buttons
    nav = []
    if page > 0:
        nav.append({"text": "< Prev", "callback_data": f"page:{page - 1}"})
    if end < len(projects):
        nav.append({"text": "Next >", "callback_data": f"page:{page + 1}"})
    if nav:
        rows.append(nav)

    return rows


def build_sessions_keyboard(
    sessions: list, active_id: int | None
) -> list[list[dict]]:
    if not sessions:
        return []

    rows = []
    for s in sessions:
        marker = " *" if s.session_id == active_id else ""
        rows.append([
            {"text": f"#{s.session_id} {s.project_name}{marker}", "callback_data": f"switch:{s.session_id}"},
            {"text": "Kill", "callback_data": f"kill:{s.session_id}"},
        ])
    return rows


def format_session_started(project_name: str, session_id: int) -> str:
    return f"Session started on *{project_name}*. Session #{session_id}"


def format_session_ended(project_name: str, session_id: int) -> str:
    return f"Session #{session_id} on *{project_name}* ended."


def format_history_entry(entry: dict) -> str:
    parts = [
        f"*{entry['project']}*",
        f"Started: {entry['started_at']}",
    ]
    if entry.get("ended_at"):
        parts.append(f"Ended: {entry['ended_at']}")
    parts.append(f"Status: {entry['status']}")
    if entry.get("exit_code") is not None:
        parts.append(f"Exit code: {entry['exit_code']}")
    return "\n".join(parts)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bot.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/bot.py tests/test_bot.py
git commit -m "feat: add bot helper functions (auth, keyboards, formatting)"
```

### Task 10.2: Telegram bot application wiring with handlers

**Files:**
- Modify: `src/bot.py`
- Modify: `tests/test_bot.py`

**Step 1: Append handler tests to `tests/test_bot.py`**

These test the handler logic by mocking the Telegram update/context objects.

```python
from src.bot import handle_start, handle_sessions, handle_exit, handle_text_message


class TestHandleStart:
    async def test_unauthorized_user_rejected(self):
        update = MagicMock()
        update.effective_user.id = 999
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {"config": MagicMock(telegram=MagicMock(authorized_users=[111]))}
        await handle_start(update, context)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "not authorized" in call_text.lower()

    async def test_authorized_user_sees_projects(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        config.projects.root = "/tmp"
        config.projects.scan_depth = 1
        context.bot_data = {"config": config}
        with patch("src.bot.scan_projects") as mock_scan:
            mock_scan.return_value = [Project(name="proj", path="/a/proj")]
            await handle_start(update, context)
            update.message.reply_text.assert_called_once()


class TestHandleTextMessage:
    async def test_no_active_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.text = "hello"
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        context.bot_data = {
            "config": MagicMock(telegram=MagicMock(authorized_users=[111])),
            "session_manager": MagicMock(get_active_session=MagicMock(return_value=None)),
        }
        await handle_text_message(update, context)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "no active session" in call_text.lower()
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bot.py::TestHandleStart -v && pytest tests/test_bot.py::TestHandleTextMessage -v`
Expected: FAIL

**Step 3: Add handler functions to `src/bot.py`**

Append to `src/bot.py`:

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.project_scanner import scan_projects


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    projects = scan_projects(config.projects.root, depth=config.projects.scan_depth)
    if not projects:
        await update.message.reply_text("No projects found.")
        return

    keyboard_data = build_project_keyboard(projects)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]) for btn in row]
        for row in keyboard_data
    ])
    await update.message.reply_text("Choose a project:", reply_markup=keyboard)


async def handle_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    sessions = session_manager.list_sessions(user_id)
    if not sessions:
        await update.message.reply_text("No active sessions.")
        return

    active = session_manager.get_active_session(user_id)
    active_id = active.session_id if active else None
    keyboard_data = build_sessions_keyboard(sessions, active_id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]) for btn in row]
        for row in keyboard_data
    ])
    await update.message.reply_text("Active sessions:", reply_markup=keyboard)


async def handle_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session to exit.")
        return

    await session_manager.kill_session(user_id, active.session_id)
    msg = format_session_ended(active.project_name, active.session_id)

    new_active = session_manager.get_active_session(user_id)
    if new_active:
        msg += f"\nSwitched to *{new_active.project_name}* (session #{new_active.session_id})"

    await update.message.reply_text(msg)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session. Use /start to begin one.")
        return

    await active.process.write(update.message.text + "\n")
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bot.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_bot.py --cov=src.bot --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/bot.py tests/test_bot.py
git commit -m "feat: add Telegram bot handlers (start, sessions, exit, text)"
```

### Task 10.3: Callback query handlers and remaining commands

**Files:**
- Modify: `src/bot.py`
- Modify: `tests/test_bot.py`

**Step 1: Append failing tests for callback handlers and remaining commands**

```python
from src.bot import (
    handle_callback_query,
    handle_history,
    handle_git,
    handle_context,
    handle_download,
    handle_update_claude,
    handle_file_upload,
)


class TestHandleCallbackQuery:
    async def test_project_selection_creates_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "project:/a/my-project"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = AsyncMock()
        session = MagicMock(session_id=1, project_name="my-project")
        sm.create_session = AsyncMock(return_value=session)
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.bot.get_git_info", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = MagicMock(format=MagicMock(return_value="Branch: main"))
            await handle_callback_query(update, context)
            sm.create_session.assert_called_once()

    async def test_switch_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "switch:2"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = MagicMock()
        sm.switch_session = MagicMock()
        session = MagicMock(session_id=2, project_name="proj")
        sm.get_active_session = MagicMock(return_value=session)
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        sm.switch_session.assert_called_once_with(111, 2)

    async def test_kill_session(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.callback_query.data = "kill:1"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        context = MagicMock()
        config = MagicMock()
        config.telegram.authorized_users = [111]
        sm = AsyncMock()
        killed_session = MagicMock(session_id=1, project_name="proj")
        sm._sessions = {111: {1: killed_session}}
        sm.kill_session = AsyncMock()
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_callback_query(update, context)
        sm.kill_session.assert_called_once_with(111, 1)


class TestHandleHistory:
    async def test_shows_history(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        db = AsyncMock()
        db.list_sessions = AsyncMock(return_value=[
            {"project": "p1", "started_at": "2026-01-01", "ended_at": "2026-01-02", "status": "ended", "exit_code": 0}
        ])
        context.bot_data = {"config": config, "db": db}
        await handle_history(update, context)
        update.message.reply_text.assert_called_once()

    async def test_empty_history(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        db = AsyncMock()
        db.list_sessions = AsyncMock(return_value=[])
        context.bot_data = {"config": config, "db": db}
        await handle_history(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "no" in call_text.lower()


class TestHandleGit:
    async def test_shows_git_info(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        session = MagicMock(project_path="/a/proj")
        sm = MagicMock(get_active_session=MagicMock(return_value=session))
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.bot.get_git_info", new_callable=AsyncMock) as mock_git:
            mock_git.return_value = MagicMock(format=MagicMock(return_value="Branch: main | No open PR"))
            await handle_git(update, context)
            update.message.reply_text.assert_called_once()
            assert "main" in update.message.reply_text.call_args[0][0]


class TestHandleUpdateClaude:
    async def test_no_active_sessions_updates_directly(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(
            telegram=MagicMock(authorized_users=[111]),
            claude=MagicMock(update_command="echo updated"),
        )
        sm = MagicMock(has_active_sessions=MagicMock(return_value=False))
        context.bot_data = {"config": config, "session_manager": sm}
        with patch("src.bot._run_update_command", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "Updated to v2.0"
            await handle_update_claude(update, context)
            mock_run.assert_called_once()

    async def test_with_active_sessions_warns(self):
        update = MagicMock()
        update.effective_user.id = 111
        update.message.reply_text = AsyncMock()
        context = MagicMock()
        config = MagicMock(telegram=MagicMock(authorized_users=[111]))
        sm = MagicMock(
            has_active_sessions=MagicMock(return_value=True),
            active_session_count=MagicMock(return_value=2),
        )
        context.bot_data = {"config": config, "session_manager": sm}
        await handle_update_claude(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        assert "2" in call_text
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_bot.py -v`
Expected: FAIL for new tests

**Step 3: Implement remaining handlers in `src/bot.py`**

Append to `src/bot.py`:

```python
import asyncio
from src.git_info import get_git_info


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await query.answer("Not authorized")
        return

    data = query.data
    session_manager = context.bot_data["session_manager"]

    if data.startswith("project:"):
        project_path = data[len("project:"):]
        project_name = project_path.rstrip("/").split("/")[-1]
        session = await session_manager.create_session(user_id, project_name, project_path)
        git_info = await get_git_info(project_path)
        msg = format_session_started(project_name, session.session_id)
        msg += f"\n{git_info.format()}"
        await query.answer()
        await query.edit_message_text(msg)

    elif data.startswith("switch:"):
        session_id = int(data[len("switch:"):])
        session_manager.switch_session(user_id, session_id)
        active = session_manager.get_active_session(user_id)
        await query.answer()
        await query.edit_message_text(f"Switched to *{active.project_name}* (session #{active.session_id})")

    elif data.startswith("kill:"):
        session_id = int(data[len("kill:"):])
        await session_manager.kill_session(user_id, session_id)
        await query.answer()
        await query.edit_message_text(f"Session #{session_id} killed.")

    elif data.startswith("page:"):
        page = int(data[len("page:"):])
        projects = scan_projects(config.projects.root, depth=config.projects.scan_depth)
        keyboard_data = build_project_keyboard(projects, page=page)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]) for btn in row]
            for row in keyboard_data
        ])
        await query.answer()
        await query.edit_message_text("Choose a project:", reply_markup=keyboard)

    elif data == "compact:yes":
        active = session_manager.get_active_session(user_id)
        if active:
            await active.process.write("/compact\n")
            await query.answer("Compacting...")
        else:
            await query.answer("No active session")
        await query.edit_message_text("Compact command sent.")

    elif data == "compact:dismiss":
        await query.answer()
        await query.edit_message_text("Alert dismissed.")

    elif data == "update:confirm":
        update_cmd = config.claude.update_command
        result = await _run_update_command(update_cmd)
        await query.answer()
        await query.edit_message_text(f"Update result:\n{result}")

    elif data == "update:cancel":
        await query.answer()
        await query.edit_message_text("Update cancelled.")


async def handle_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    db = context.bot_data["db"]
    sessions = await db.list_sessions(user_id)
    if not sessions:
        await update.message.reply_text("No session history.")
        return

    lines = [format_history_entry(s) for s in sessions[:20]]
    await update.message.reply_text("\n\n".join(lines))


async def handle_git(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session.")
        return

    git_info = await get_git_info(active.project_path)
    await update.message.reply_text(git_info.format())


async def handle_context(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session.")
        return

    await active.process.write("/context\n")
    await update.message.reply_text("Context info requested. Output will follow.")


async def handle_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    file_handler = context.bot_data["file_handler"]
    text = update.message.text
    # /download /path/to/file
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /download /path/to/file")
        return

    file_path = parts[1].strip()
    if not file_handler.file_exists(file_path):
        await update.message.reply_text(f"File not found: {file_path}")
        return

    await update.message.reply_document(document=open(file_path, "rb"), filename=file_path.split("/")[-1])


async def handle_update_claude(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    if session_manager.has_active_sessions():
        count = session_manager.active_session_count()
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Yes, update", callback_data="update:confirm"),
                InlineKeyboardButton("Cancel", callback_data="update:cancel"),
            ]
        ])
        await update.message.reply_text(
            f"{count} active session(s) running. Update anyway?",
            reply_markup=keyboard,
        )
        return

    result = await _run_update_command(config.claude.update_command)
    await update.message.reply_text(f"Update result:\n{result}")


async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session. Upload ignored.")
        return

    file_handler = context.bot_data["file_handler"]
    document = update.message.document or update.message.photo[-1] if update.message.photo else None
    if document is None:
        return

    file_obj = await context.bot.get_file(document.file_id)
    filename = getattr(document, "file_name", None) or f"{document.file_id}.bin"
    save_path = file_handler.get_upload_path(active.project_name, active.session_id, filename)
    await file_obj.download_to_drive(save_path)

    await active.process.write(f"User uploaded a file: {save_path}\n")
    await update.message.reply_text(f"File uploaded: `{save_path}`")


async def _run_update_command(command: str) -> str:
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bot.py -v`
Expected: all PASS

**Step 5: Check coverage**

Run: `pytest tests/test_bot.py --cov=src.bot --cov-report=term-missing`
Expected: 90%+

**Step 6: Commit**

```bash
git add src/bot.py tests/test_bot.py
git commit -m "feat: add all Telegram bot handlers (callbacks, history, git, context, download, update, upload)"
```

---

## Phase 11: Main Entry Point & Output Loop

### Task 11.1: Wire everything together in main.py

**Files:**
- Create: `src/main.py`
- Modify: `tests/test_bot.py` (add app builder test)

**Step 1: Write failing test**

Append to `tests/test_bot.py`:

```python
from src.main import build_app


class TestBuildApp:
    def test_builds_app_with_handlers(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        import yaml
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "fake-token", "authorized_users": [111]},
            "projects": {"root": "/tmp"},
        }))
        app = build_app(str(config_file))
        assert app is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot.py::TestBuildApp -v`
Expected: FAIL

**Step 3: Implement `src/main.py`**

```python
from __future__ import annotations

import asyncio
import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from src.bot import (
    handle_start,
    handle_sessions,
    handle_exit,
    handle_text_message,
    handle_callback_query,
    handle_history,
    handle_git,
    handle_context,
    handle_download,
    handle_update_claude,
    handle_file_upload,
)
from src.config import load_config
from src.database import Database
from src.file_handler import FileHandler
from src.session_manager import SessionManager

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_app(config_path: str) -> Application:
    config = load_config(config_path)

    app = Application.builder().token(config.telegram.bot_token).build()

    db = Database(config.database.path)
    file_handler = FileHandler()
    session_manager = SessionManager(
        claude_command=config.claude.command,
        claude_args=config.claude.default_args,
        max_per_user=config.sessions.max_per_user,
        db=db,
        file_handler=file_handler,
    )

    app.bot_data["config"] = config
    app.bot_data["db"] = db
    app.bot_data["session_manager"] = session_manager
    app.bot_data["file_handler"] = file_handler

    # Command handlers
    app.add_handler(CommandHandler(["start", "new"], handle_start))
    app.add_handler(CommandHandler("sessions", handle_sessions))
    app.add_handler(CommandHandler("exit", handle_exit))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(CommandHandler("git", handle_git))
    app.add_handler(CommandHandler("context", handle_context))
    app.add_handler(CommandHandler("download", handle_download))
    app.add_handler(CommandHandler("update_claude", handle_update_claude))

    # Callback query handler
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # File uploads
    app.add_handler(MessageHandler(
        filters.ATTACHMENT & ~filters.COMMAND,
        handle_file_upload,
    ))

    # Text messages (must be last)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message,
    ))

    return app


async def _on_startup(app: Application) -> None:
    db: Database = app.bot_data["db"]
    await db.initialize()
    lost = await db.mark_active_sessions_lost()
    if lost:
        logger.info(f"Marked {len(lost)} stale sessions as lost on startup")


async def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.yaml"
    app = build_app(config_path)
    app.post_init = _on_startup

    logger.info("Starting ClaudeInstanceManager bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Run until stopped
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bot.py::TestBuildApp -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/main.py tests/test_bot.py
git commit -m "feat: add main entry point wiring all components together"
```

### Task 11.2: Output reader loop with debouncing

**Files:**
- Modify: `src/session_manager.py`
- Modify: `tests/test_session_manager.py`

**Step 1: Append failing tests**

```python
from src.session_manager import OutputBuffer


class TestOutputBuffer:
    async def test_buffer_accumulates(self):
        buf = OutputBuffer(debounce_ms=100, max_buffer=2000)
        buf.append("hello ")
        buf.append("world")
        text = buf.flush()
        assert text == "hello world"

    async def test_flush_clears_buffer(self):
        buf = OutputBuffer(debounce_ms=100, max_buffer=2000)
        buf.append("hello")
        buf.flush()
        assert buf.flush() == ""

    async def test_is_ready_after_debounce(self):
        import time
        buf = OutputBuffer(debounce_ms=50, max_buffer=2000)
        buf.append("data")
        assert buf.is_ready() is False
        time.sleep(0.06)
        assert buf.is_ready() is True

    async def test_is_ready_when_max_buffer_exceeded(self):
        buf = OutputBuffer(debounce_ms=5000, max_buffer=10)
        buf.append("A" * 15)
        assert buf.is_ready() is True

    async def test_empty_buffer_not_ready(self):
        buf = OutputBuffer(debounce_ms=100, max_buffer=2000)
        assert buf.is_ready() is False
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_session_manager.py::TestOutputBuffer -v`
Expected: FAIL

**Step 3: Implement `OutputBuffer` in `src/session_manager.py`**

Add to `src/session_manager.py`:

```python
import time


class OutputBuffer:
    def __init__(self, debounce_ms: int, max_buffer: int) -> None:
        self._debounce_s = debounce_ms / 1000.0
        self._max_buffer = max_buffer
        self._buffer: str = ""
        self._last_append: float = 0

    def append(self, text: str) -> None:
        self._buffer += text
        self._last_append = time.monotonic()

    def flush(self) -> str:
        result = self._buffer
        self._buffer = ""
        self._last_append = 0
        return result

    def is_ready(self) -> bool:
        if not self._buffer:
            return False
        if len(self._buffer) >= self._max_buffer:
            return True
        if self._last_append and (time.monotonic() - self._last_append) >= self._debounce_s:
            return True
        return False
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: all PASS

**Step 5: Commit**

```bash
git add src/session_manager.py tests/test_session_manager.py
git commit -m "feat: add output buffer with debounce and max-buffer flush"
```

---

## Phase 12: Systemd & Deployment Config

### Task 12.1: Systemd unit file and config example

**Files:**
- Create: `systemd/claude-bot.service`

**Step 1: Create the systemd unit file**

```ini
[Unit]
Description=Claude Instance Manager Telegram Bot
After=network.target

[Service]
Type=simple
User=lounis
WorkingDirectory=/opt/claude-instance-manager
ExecStart=/opt/claude-instance-manager/.venv/bin/python -m src.main /opt/claude-instance-manager/config.yaml
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

**Step 2: Commit**

```bash
git add systemd/claude-bot.service
git commit -m "feat: add systemd service unit for deployment"
```

---

## Phase 13: Full Coverage Check & Cleanup

### Task 13.1: Run full test suite and reach 90%+ coverage

**Step 1: Run full test suite with coverage**

Run: `pytest --cov=src --cov-report=term-missing --cov-fail-under=90 -v`

**Step 2: Identify uncovered lines**

Review the `term-missing` output. Add targeted tests for any uncovered branches.

**Step 3: Fix any coverage gaps**

Write additional tests for uncovered lines. Common gaps:
- Error branches in `bot.py` (unauthorized access, missing sessions)
- Edge cases in `output_parser.py`
- Exception handling in `claude_process.py`

**Step 4: Verify 90%+ coverage**

Run: `pytest --cov=src --cov-report=term-missing --cov-fail-under=90 -v`
Expected: all PASS, coverage >= 90%

**Step 5: Final commit**

```bash
git add -A
git commit -m "test: achieve 90%+ test coverage across all modules"
```

---

## Summary

| Phase | What | Key files |
|-------|------|-----------|
| 1 | Project scaffolding | `pyproject.toml`, `requirements.txt`, `conftest.py` |
| 2 | Config module | `src/config.py` |
| 3 | Project scanner | `src/project_scanner.py` |
| 4 | Database layer | `src/database.py` |
| 5 | Output parser (7 sub-tasks) | `src/output_parser.py` |
| 6 | Git info | `src/git_info.py` |
| 7 | File handler | `src/file_handler.py` |
| 8 | Claude process layer | `src/claude_process.py` |
| 9 | Session manager | `src/session_manager.py` |
| 10 | Telegram bot (3 sub-tasks) | `src/bot.py` |
| 11 | Main entry + output loop | `src/main.py`, `OutputBuffer` |
| 12 | Deployment | `systemd/claude-bot.service` |
| 13 | Coverage check & cleanup | Tests gap-filling |
