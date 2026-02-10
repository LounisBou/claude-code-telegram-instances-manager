# Debug & Trace Logging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the sparse pydevmate-based debug setup with a tiered logging system: `--debug` for high-level events (terminal), `--trace` for deep output parser/PTY diagnostics (session-based file + optional terminal).

**Architecture:** Custom TRACE level (5) below DEBUG (10). New `src/log_setup.py` module handles all logging configuration. Console handler at DEBUG by default, file handler writes to `debug/trace-<timestamp>.log` when `--trace` is active. `--trace --verbose` bumps terminal to TRACE too. Removes pydevmate DebugIt/LogIt dependency.

**Tech Stack:** Python stdlib `logging`, no new dependencies.

---

### Task 1: Create `src/log_setup.py` with TRACE level and `setup_logging()`

**Files:**
- Create: `src/log_setup.py`
- Test: `tests/test_log_setup.py`

**Step 1: Write the failing tests**

```python
# tests/test_log_setup.py
from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from src.log_setup import TRACE, setup_logging


class TestTraceLevel:
    def test_trace_level_value(self):
        assert TRACE == 5

    def test_trace_level_name(self):
        assert logging.getLevelName(TRACE) == "TRACE"

    def test_logger_has_trace_method(self):
        setup_logging(debug=False, trace=False, verbose=False)
        logger = logging.getLogger("test.trace")
        assert hasattr(logger, "trace")
        assert callable(logger.trace)


class TestSetupLogging:
    def test_default_console_info(self):
        root = setup_logging(debug=False, trace=False, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert len(console) == 1
        assert console[0].level == logging.INFO

    def test_debug_console_debug(self):
        root = setup_logging(debug=True, trace=False, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert console[0].level == logging.DEBUG

    def test_trace_creates_file_handler(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            root = setup_logging(debug=False, trace=True, verbose=False)
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 1
        assert file_handlers[0].level == TRACE

    def test_trace_console_stays_debug(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            root = setup_logging(debug=False, trace=True, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert console[0].level == logging.DEBUG

    def test_trace_verbose_console_at_trace(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            root = setup_logging(debug=False, trace=True, verbose=True)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert console[0].level == TRACE

    def test_trace_file_naming(self, tmp_path):
        with patch("src.log_setup.TRACE_DIR", str(tmp_path)):
            setup_logging(debug=False, trace=True, verbose=False)
        log_files = list(tmp_path.iterdir())
        assert len(log_files) == 1
        assert log_files[0].name.startswith("trace-")
        assert log_files[0].suffix == ".log"

    def test_no_file_without_trace(self):
        root = setup_logging(debug=True, trace=False, verbose=False)
        file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) == 0

    def test_idempotent_clears_old_handlers(self):
        setup_logging(debug=True, trace=False, verbose=False)
        root = setup_logging(debug=False, trace=False, verbose=False)
        console = [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert len(console) == 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_log_setup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.log_setup'`

**Step 3: Write minimal implementation**

```python
# src/log_setup.py
from __future__ import annotations

import logging
import os
from datetime import datetime

TRACE = 5
TRACE_DIR = "debug"

logging.addLevelName(TRACE, "TRACE")


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = _trace

_CONSOLE_FMT = "%(levelname)s %(name)s: %(message)s"
_FILE_FMT = "%(asctime)s.%(msecs)03d %(levelname)s %(name)s:%(funcName)s:%(lineno)d %(message)s"
_FILE_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    *, debug: bool, trace: bool, verbose: bool
) -> logging.Logger:
    root = logging.getLogger("claude-bot")
    root.handlers.clear()
    root.setLevel(TRACE)

    # Console handler
    console = logging.StreamHandler()
    if trace and verbose:
        console.setLevel(TRACE)
    elif debug or trace:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_CONSOLE_FMT))
    root.addHandler(console)

    # File handler (trace only)
    if trace:
        os.makedirs(TRACE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filepath = os.path.join(TRACE_DIR, f"trace-{timestamp}.log")
        fh = logging.FileHandler(filepath)
        fh.setLevel(TRACE)
        fh.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_FILE_DATEFMT))
        root.addHandler(fh)

    return root
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_log_setup.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/log_setup.py tests/test_log_setup.py
git commit -m "feat: add log_setup module with TRACE level and tiered logging"
```

---

### Task 2: Update `DebugConfig`, CLI args, and `main.py` wiring

**Files:**
- Modify: `src/config.py:58-63` (DebugConfig)
- Modify: `src/main.py:1-47,49-95,142-164` (imports, _setup_logging removal, build_app, _parse_args, main)
- Test: `tests/test_main.py` (update existing)
- Test: `tests/test_config.py` (add trace/verbose fields)

**Step 1: Write/update failing tests**

Add to `tests/test_config.py`:
```python
class TestDebugConfig:
    def test_debug_config_defaults(self):
        from src.config import DebugConfig
        dc = DebugConfig()
        assert dc.enabled is False
        assert dc.trace is False
        assert dc.verbose is False
```

Update `tests/test_main.py`:
```python
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.main import _on_startup, _parse_args


class TestOnStartup:
    @pytest.mark.asyncio
    async def test_initializes_db_and_marks_lost(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(
            return_value=[{"id": 1, "project": "p1"}]
        )
        app = MagicMock()
        app.bot_data = {"db": db}
        await _on_startup(app)
        db.initialize.assert_called_once()
        db.mark_active_sessions_lost.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_lost_sessions(self):
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app = MagicMock()
        app.bot_data = {"db": db}
        await _on_startup(app)
        db.initialize.assert_called_once()


class TestParseArgs:
    def test_default_config_path(self):
        with patch.object(sys, "argv", ["main"]):
            args = _parse_args()
            assert args.config == "config.yaml"
            assert args.debug is False
            assert args.trace is False
            assert args.verbose is False

    def test_custom_config_and_debug(self):
        with patch.object(sys, "argv", ["main", "my.yaml", "--debug"]):
            args = _parse_args()
            assert args.config == "my.yaml"
            assert args.debug is True

    def test_trace_flag(self):
        with patch.object(sys, "argv", ["main", "--trace"]):
            args = _parse_args()
            assert args.trace is True
            assert args.verbose is False

    def test_trace_verbose_flags(self):
        with patch.object(sys, "argv", ["main", "--trace", "--verbose"]):
            args = _parse_args()
            assert args.trace is True
            assert args.verbose is True
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_main.py tests/test_config.py -v`
Expected: FAIL — removed `_setup_logging` import, missing `trace`/`verbose` args

**Step 3: Implement changes**

`src/config.py` — expand DebugConfig:
```python
@dataclass
class DebugConfig:
    """Debug mode settings."""

    enabled: bool = False
    trace: bool = False
    verbose: bool = False
```

`src/main.py` — full replacement:
```python
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot import (
    handle_callback_query,
    handle_context,
    handle_download,
    handle_exit,
    handle_file_upload,
    handle_git,
    handle_history,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_update_claude,
)
from src.config import load_config
from src.database import Database
from src.file_handler import FileHandler
from src.log_setup import setup_logging
from src.session_manager import SessionManager


def build_app(config_path: str, debug: bool = False, trace: bool = False, verbose: bool = False) -> Application:
    """Build and configure the Telegram bot application."""
    config = load_config(config_path)

    if debug:
        config.debug.enabled = True
    if trace:
        config.debug.trace = True
    if verbose:
        config.debug.verbose = True

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
    app.add_handler(
        MessageHandler(filters.ATTACHMENT & ~filters.COMMAND, handle_file_upload)
    )

    # Text handler registered last so commands and callbacks take priority
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    return app


async def _on_startup(app: Application) -> None:
    """Run one-time initialization tasks after the application starts."""
    logger = logging.getLogger(__name__)
    db = app.bot_data["db"]
    await db.initialize()
    lost = await db.mark_active_sessions_lost()
    if lost:
        logger.info("Marked %d stale sessions as lost on startup", len(lost))


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Claude Instance Manager Bot")
    parser.add_argument("config", nargs="?", default="config.yaml",
                        help="Path to YAML config file (default: config.yaml)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode (verbose logging)")
    parser.add_argument("--trace", action="store_true",
                        help="Enable trace mode (writes trace file to debug/)")
    parser.add_argument("--verbose", action="store_true",
                        help="With --trace, also send trace output to terminal")
    return parser.parse_args()


async def main() -> None:
    """Entry point for the ClaudeInstanceManager Telegram bot."""
    args = _parse_args()
    logger = setup_logging(
        debug=args.debug, trace=args.trace, verbose=args.verbose
    )

    app = build_app(args.config, debug=args.debug, trace=args.trace, verbose=args.verbose)
    app.post_init = _on_startup

    logger.info("Starting ClaudeInstanceManager bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

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

Run: `pytest tests/test_main.py tests/test_config.py tests/test_log_setup.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/config.py src/main.py tests/test_main.py tests/test_config.py
git commit -m "feat: replace pydevmate logging with tiered debug/trace setup"
```

---

### Task 3: Add DEBUG logging to startup modules (`config.py`, `project_scanner.py`, `main.py`)

**Files:**
- Modify: `src/config.py:81-147` (add logger calls in load_config)
- Modify: `src/project_scanner.py:1-43` (add logger + trace calls)
- Modify: `src/main.py` (add debug log in build_app)
- Test: `tests/test_project_scanner.py` (add logging assertions)

**Step 1: Write failing tests**

Add to `tests/test_project_scanner.py`:
```python
class TestScanProjectsLogging:
    def test_logs_root_and_count(self, tmp_projects, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        with caplog.at_level(logging.DEBUG, logger="claude-bot.src.project_scanner"):
            projects = scan_projects(str(tmp_projects))
        assert any("Scanning" in r.message for r in caplog.records)
        assert any("Found 2 projects" in r.message for r in caplog.records)

    def test_trace_logs_each_entry(self, tmp_projects, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        with caplog.at_level(TRACE, logger="claude-bot.src.project_scanner"):
            projects = scan_projects(str(tmp_projects))
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        # Should have trace entries for examined dirs
        assert len(trace_records) >= 2
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_project_scanner.py::TestScanProjectsLogging -v`
Expected: FAIL — no logging calls in scan_projects yet

**Step 3: Implement logging**

`src/project_scanner.py`:
```python
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.log_setup import TRACE

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """A discovered project with its display name and absolute path."""

    name: str
    path: str


def scan_projects(root: str, depth: int = 1) -> list[Project]:
    """Scan a directory for projects containing .git or .claude markers."""
    root_path = Path(root)
    logger.debug("Scanning projects root=%s depth=%d", root, depth)
    if not root_path.is_dir():
        logger.debug("Root path does not exist: %s", root)
        return []

    projects = []
    for entry in root_path.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            logger.log(TRACE, "Skipping %s (not dir or hidden)", entry.name)
            continue
        if (entry / ".git").exists() or (entry / ".claude").exists():
            resolved = str(entry.resolve())
            logger.log(TRACE, "Found project %s at %s", entry.name, resolved)
            projects.append(Project(name=entry.name, path=resolved))
        else:
            logger.log(TRACE, "Skipping %s (no .git or .claude)", entry.name)

    projects.sort(key=lambda p: p.name)
    logger.debug("Found %d projects in %s", len(projects), root)
    return projects
```

`src/config.py` — add logger calls in `load_config`:
```python
logger = logging.getLogger(__name__)
```
At top of module, and inside `load_config` after parsing:
```python
    logger.debug("Loaded config from %s", path)
    logger.debug("Projects root=%s scan_depth=%d", projects_raw["root"], projects_raw.get("scan_depth", 1))
```

`src/main.py` — add in `build_app` after building app:
```python
    logger.debug("Built app: %d handlers registered", len(app.handlers[0].handlers) if app.handlers else 0)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_project_scanner.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/project_scanner.py src/config.py src/main.py tests/test_project_scanner.py
git commit -m "feat: add debug/trace logging to startup modules"
```

---

### Task 4: Add DEBUG logging to `bot.py` handlers

**Files:**
- Modify: `src/bot.py` (add logger.debug in each handler entry, auth check, outcome)

**Step 1: Write failing test**

Add to `tests/test_bot.py`:
```python
class TestHandlerLogging:
    @pytest.mark.asyncio
    async def test_handle_start_logs_handler_entry(self, mock_update, mock_context, caplog):
        from src.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        mock_context.bot_data["config"].projects.root = "/nonexistent"
        mock_context.bot_data["config"].projects.scan_depth = 1
        with caplog.at_level(logging.DEBUG, logger="claude-bot.src.bot"):
            await handle_start(mock_update, mock_context)
        assert any("handle_start" in r.message for r in caplog.records)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_bot.py::TestHandlerLogging -v`
Expected: FAIL — no "handle_start" in log output

**Step 3: Implement logging**

Add `logger.debug` at entry of each handler in `src/bot.py`. Pattern:

```python
async def handle_start(update, context):
    user_id = update.effective_user.id
    logger.debug("handle_start user_id=%d", user_id)
    ...
```

For `handle_callback_query`, log the dispatch action:
```python
    logger.debug("handle_callback_query user_id=%d action=%s", user_id, data.split(":")[0])
```

For `handle_text_message`, log that text was forwarded:
```python
    logger.debug("handle_text_message user_id=%d len=%d", user_id, len(update.message.text))
```

Remove the two `logger.debug` lines we added earlier in `handle_start` (lines 183-185) — they'll be replaced by the project_scanner's own logging plus the handler entry log.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_bot.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/bot.py tests/test_bot.py
git commit -m "feat: add debug logging to all bot handlers"
```

---

### Task 5: Add DEBUG + TRACE logging to `session_manager.py`

**Files:**
- Modify: `src/session_manager.py` (add logger calls)
- Test: `tests/test_session_manager.py` (add logging assertions)

**Step 1: Write failing test**

Add to `tests/test_session_manager.py`:
```python
class TestSessionManagerLogging:
    @pytest.mark.asyncio
    async def test_create_session_logs(self, caplog):
        from src.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        db = AsyncMock()
        db.create_session = AsyncMock(return_value=1)
        fh = MagicMock()
        sm = SessionManager(
            claude_command="echo", claude_args=[], max_per_user=3, db=db, file_handler=fh
        )
        with patch("src.session_manager.ClaudeProcess") as mock_cp:
            mock_cp.return_value.spawn = AsyncMock()
            with caplog.at_level(logging.DEBUG, logger="claude-bot.src.session_manager"):
                await sm.create_session(111, "test-project", "/tmp/test")
        assert any("create_session" in r.message for r in caplog.records)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_session_manager.py::TestSessionManagerLogging -v`
Expected: FAIL

**Step 3: Implement logging**

Add to `src/session_manager.py`:
```python
import logging
from src.log_setup import TRACE

logger = logging.getLogger(__name__)
```

Then in key methods:
- `create_session`: `logger.debug("create_session user_id=%d project=%s", user_id, project_name)` at entry, `logger.debug("Session #%d created for user %d (pid pending)", session_id, user_id)` after spawn
- `kill_session`: `logger.debug("kill_session user_id=%d session_id=%d", user_id, session_id)` at entry
- `switch_session`: `logger.debug("switch_session user_id=%d -> session_id=%d", user_id, session_id)`

In `OutputBuffer`:
- `append`: `logger.log(TRACE, "OutputBuffer append len=%d total=%d", len(text), len(self._buffer))`
- `flush`: `logger.debug("OutputBuffer flush len=%d", len(result))`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_session_manager.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/session_manager.py tests/test_session_manager.py
git commit -m "feat: add debug/trace logging to session manager"
```

---

### Task 6: Add DEBUG + TRACE logging to `claude_process.py`

**Files:**
- Modify: `src/claude_process.py` (add logger calls)

**Step 1: Write failing test**

Add to `tests/test_claude_process.py`:
```python
class TestClaudeProcessLogging:
    @pytest.mark.asyncio
    async def test_spawn_logs_command(self, caplog):
        from src.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        proc = ClaudeProcess(command="echo", args=["hello"], cwd="/tmp")
        with caplog.at_level(logging.DEBUG, logger="claude-bot.src.claude_process"):
            await proc.spawn()
        assert any("spawn" in r.message.lower() for r in caplog.records)
        await proc.terminate()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_claude_process.py::TestClaudeProcessLogging -v`
Expected: FAIL

**Step 3: Implement logging**

Add to `src/claude_process.py`:
```python
from src.log_setup import TRACE
```

Then in key methods:
- `spawn`: `logger.debug("Spawning process: cmd=%s cwd=%s", cmd, self._cwd)` before spawn, `logger.debug("Process spawned pid=%d", self._process.pid)` after
- `write`: `logger.debug("PTY write: %r", text[:200])`
- `read_available`: `logger.log(TRACE, "PTY read chunk len=%d", len(chunk))` inside the drain loop, and `logger.log(TRACE, "PTY read_available total=%d", len(result))` before return
- `terminate`: `logger.debug("Terminating process pid=%s", self._process.pid if self._process else None)`

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_claude_process.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/claude_process.py tests/test_claude_process.py
git commit -m "feat: add debug/trace logging to claude process"
```

---

### Task 7: Add TRACE logging to `output_parser.py` (replaces DebugIt)

**Files:**
- Modify: `src/output_parser.py:812-976` (classify_screen_state — add trace calls)

**Step 1: Write failing test**

Add to `tests/test_output_parser.py`:
```python
class TestClassifyScreenStateLogging:
    def test_classify_logs_result_at_trace(self, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        lines = [""] * 40
        lines[18] = "❯"
        lines[17] = "─" * 20
        lines[19] = "─" * 20
        with caplog.at_level(TRACE, logger="claude-bot.src.output_parser"):
            result = classify_screen_state(lines)
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert any("IDLE" in r.message for r in trace_records)

    def test_classify_logs_line_count_at_trace(self, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        lines = ["content line"] * 5 + [""] * 35
        with caplog.at_level(TRACE, logger="claude-bot.src.output_parser"):
            classify_screen_state(lines)
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert any("non_empty=5" in r.message for r in trace_records)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_output_parser.py::TestClassifyScreenStateLogging -v`
Expected: FAIL

**Step 3: Implement trace logging**

Add to top of `src/output_parser.py`:
```python
import logging
from src.log_setup import TRACE

logger = logging.getLogger(__name__)
```

Add trace calls inside `classify_screen_state`:
- At entry: `logger.log(TRACE, "classify_screen_state lines=%d non_empty=%d", len(lines), len(non_empty))`
- At each return point, before returning: `logger.log(TRACE, "classify_screen_state -> %s payload_keys=%s", event.state.name, list(event.payload.keys()))`

This replaces the DebugIt wrapper with targeted trace output that shows inputs and result without flooding.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_output_parser.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/output_parser.py tests/test_output_parser.py
git commit -m "feat: add trace logging to classify_screen_state (replaces DebugIt)"
```

---

### Task 8: Add `debug/` to `.gitignore` and run full test suite

**Files:**
- Modify: `.gitignore` (add `debug/`)

**Step 1: Update .gitignore**

Add line: `debug/`

**Step 2: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 3: Verify no pydevmate imports remain**

Run: `grep -r "pydevmate\|DebugIt\|LogIt" src/`
Expected: No output

**Step 4: Commit**

```bash
git add .gitignore
git commit -m "chore: add debug/ to gitignore and remove pydevmate dependency"
```

---

## Summary

| Flag combo | Terminal | File | Use case |
|---|---|---|---|
| (none) | INFO | no | Production |
| `--debug` | DEBUG | no | Day-to-day troubleshooting |
| `--trace` | DEBUG | `debug/trace-*.log` | Parser/PTY investigation |
| `--trace --verbose` | TRACE | `debug/trace-*.log` | Live deep debugging |

**8 tasks, ~35 test additions, 7 files modified, 1 file created, 1 dependency removed (pydevmate).**
