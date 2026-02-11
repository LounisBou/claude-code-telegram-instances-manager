# Project Restructure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize flat `src/` into sub-packages (`parsing/`, `telegram/`, `core/`), split large test files to mirror source, add CLAUDE.md and documentation.

**Architecture:** Move 12 source files into 3 sub-packages via `git mv`, update all import paths across source, tests, and scripts. Split 2 large test files into 9 smaller ones. Add project-level navigation docs.

**Tech Stack:** Python 3, pytest, python-telegram-bot, pyte, git

---

## Phase A: Create Sub-packages (Source)

### Task 1: Create parsing sub-package and move files

**Files:**
- Create: `src/parsing/__init__.py`
- Move: `src/terminal_emulator.py` → `src/parsing/terminal_emulator.py`
- Move: `src/ui_patterns.py` → `src/parsing/ui_patterns.py`
- Move: `src/detectors.py` → `src/parsing/detectors.py`
- Move: `src/screen_classifier.py` → `src/parsing/screen_classifier.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p src/parsing
```

Write `src/parsing/__init__.py`:
```python
"""Terminal output parsing pipeline: emulator → patterns → detectors → classifier."""
```

**Step 2: Move files with git mv**

```bash
git mv src/terminal_emulator.py src/parsing/terminal_emulator.py
git mv src/ui_patterns.py src/parsing/ui_patterns.py
git mv src/detectors.py src/parsing/detectors.py
git mv src/screen_classifier.py src/parsing/screen_classifier.py
```

**Step 3: Update internal imports within parsing package**

In `src/parsing/detectors.py`, change:
```python
# OLD:
from src.ui_patterns import (
# NEW:
from src.parsing.ui_patterns import (
```

In `src/parsing/screen_classifier.py`, change:
```python
# OLD:
from src.detectors import (
...
from src.log_setup import TRACE
from src.ui_patterns import (
# NEW:
from src.parsing.detectors import (
...
from src.core.log_setup import TRACE
from src.parsing.ui_patterns import (
```

**Note:** `src/core/` doesn't exist yet. Do NOT update `log_setup` imports here — we'll do all core imports in Task 3 after core/ is created. Instead, keep `from src.log_setup import TRACE` temporarily.

Actually — to avoid a broken intermediate state, update only the intra-parsing imports now:

In `src/parsing/detectors.py`:
```python
from src.ui_patterns import (  →  from src.parsing.ui_patterns import (
```

In `src/parsing/screen_classifier.py`:
```python
from src.detectors import (  →  from src.parsing.detectors import (
from src.ui_patterns import (  →  from src.parsing.ui_patterns import (
```

Leave `from src.log_setup` unchanged for now (it still resolves because log_setup.py is still in src/).

### Task 2: Create telegram sub-package and move files

**Files:**
- Create: `src/telegram/__init__.py`
- Move: `src/telegram_format.py` → `src/telegram/formatter.py`
- Move: `src/bot_keyboards.py` → `src/telegram/keyboards.py`
- Move: `src/bot_handlers.py` → `src/telegram/handlers.py`
- Move: `src/bot_commands.py` → `src/telegram/commands.py`
- Move: `src/bot_output.py` → `src/telegram/output.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p src/telegram
```

Write `src/telegram/__init__.py`:
```python
"""Telegram bot layer: keyboards, handlers, commands, output streaming, formatting."""
```

**Step 2: Move files with git mv**

```bash
git mv src/telegram_format.py src/telegram/formatter.py
git mv src/bot_keyboards.py src/telegram/keyboards.py
git mv src/bot_handlers.py src/telegram/handlers.py
git mv src/bot_commands.py src/telegram/commands.py
git mv src/bot_output.py src/telegram/output.py
```

**Step 3: Update intra-telegram imports**

In `src/telegram/commands.py`, change:
```python
from src.bot_keyboards import format_history_entry, is_authorized
→
from src.telegram.keyboards import format_history_entry, is_authorized
```

Also change:
```python
from src.git_info import get_git_info
```
This stays the same (git_info.py stays in src/).

In `src/telegram/handlers.py`, change:
```python
from src.bot_commands import _run_update_command
→
from src.telegram.commands import _run_update_command

from src.bot_keyboards import (
→
from src.telegram.keyboards import (

from src.git_info import get_git_info        # stays same
from src.project_scanner import scan_projects  # stays same
```

In `src/telegram/output.py`, change:
```python
from src.log_setup import TRACE               # stays same for now
from src.screen_classifier import classify_screen_state
→
from src.parsing.screen_classifier import classify_screen_state

from src.telegram_format import split_message
→
from src.telegram.formatter import split_message

from src.terminal_emulator import TerminalEmulator
→
from src.parsing.terminal_emulator import TerminalEmulator

from src.ui_patterns import ScreenEvent, ScreenState, extract_content
→
from src.parsing.ui_patterns import ScreenEvent, ScreenState, extract_content

from src.session_manager import OutputBuffer   # stays same
```

### Task 3: Create core sub-package and move files

**Files:**
- Create: `src/core/__init__.py`
- Move: `src/config.py` → `src/core/config.py`
- Move: `src/database.py` → `src/core/database.py`
- Move: `src/log_setup.py` → `src/core/log_setup.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p src/core
```

Write `src/core/__init__.py`:
```python
"""Core infrastructure: configuration, database, logging."""
```

**Step 2: Move files with git mv**

```bash
git mv src/config.py src/core/config.py
git mv src/database.py src/core/database.py
git mv src/log_setup.py src/core/log_setup.py
```

**Step 3: Update ALL remaining log_setup/config/database imports across the entire project**

Files that import `from src.log_setup`:
- `src/parsing/screen_classifier.py`: `from src.log_setup import TRACE` → `from src.core.log_setup import TRACE`
- `src/telegram/output.py`: `from src.log_setup import TRACE` → `from src.core.log_setup import TRACE`
- `src/project_scanner.py`: `from src.log_setup import TRACE` → `from src.core.log_setup import TRACE`
- `src/claude_process.py`: `from src.log_setup import TRACE` → `from src.core.log_setup import TRACE`
- `src/session_manager.py`: `from src.log_setup import TRACE` → `from src.core.log_setup import TRACE`

Files that import `from src.database`:
- `src/session_manager.py`: `from src.database import Database` → `from src.core.database import Database`

Files that import `from src.config`:
- `src/main.py` (handled in Task 4)

### Task 4: Update src/main.py imports

**File:** `src/main.py`

Replace the import block (lines 17-39) with:

```python
from src.telegram.commands import (
    handle_context,
    handle_download,
    handle_file_upload,
    handle_git,
    handle_history,
    handle_update_claude,
)
from src.telegram.handlers import (
    handle_callback_query,
    handle_exit,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_unknown_command,
)
from src.telegram.keyboards import BOT_COMMANDS
from src.telegram.output import poll_output
from src.core.config import load_config
from src.core.database import Database
from src.file_handler import FileHandler
from src.core.log_setup import setup_logging
from src.session_manager import SessionManager
```

### Task 5: Update scripts/validate_classifier.py imports

**File:** `scripts/validate_classifier.py`

Change:
```python
from src.screen_classifier import classify_screen_state
from src.ui_patterns import ScreenState
```
To:
```python
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import ScreenState
```

### Task 6: Update test imports and verify

**Files to update:**
- `tests/test_output_parser.py`
- `tests/test_bot.py`
- `tests/test_main.py`
- `tests/test_config.py`
- `tests/test_database.py`
- `tests/test_log_setup.py`
- `tests/test_session_manager.py`
- `tests/test_claude_process.py`
- `tests/test_project_scanner.py`

**test_output_parser.py** — replace import block (lines 4-28):
```python
from src.parsing.detectors import (
    ContextUsage,
    DetectedPrompt,
    PromptType,
    StatusBar,
    detect_background_task,
    detect_context_usage,
    detect_file_paths,
    detect_parallel_agents,
    detect_prompt,
    detect_thinking,
    detect_todo_list,
    detect_tool_request,
    parse_extra_status,
    parse_status_bar,
)
from src.parsing.screen_classifier import classify_screen_state
from src.telegram.formatter import TELEGRAM_MAX_LENGTH, format_telegram, split_message
from src.parsing.terminal_emulator import (
    TerminalEmulator,
    clean_terminal_output,
    filter_spinners,
    strip_ansi,
)
from src.parsing.ui_patterns import ScreenEvent, ScreenState, classify_line, extract_content
```

Also update inline imports:
- Line 1300, 1312: `from src.log_setup import TRACE, setup_logging` → `from src.core.log_setup import TRACE, setup_logging`
- Line 1306: `logger="src.screen_classifier"` → `logger="src.parsing.screen_classifier"` (logger name changes because `__name__` changes)

**test_bot.py** — replace import block (lines 8-38):
```python
from src.telegram.commands import (
    _run_update_command,
    handle_context,
    handle_download,
    handle_file_upload,
    handle_git,
    handle_history,
    handle_update_claude,
)
from src.telegram.handlers import (
    handle_callback_query,
    handle_exit,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_unknown_command,
)
from src.telegram.keyboards import (
    build_project_keyboard,
    build_sessions_keyboard,
    format_history_entry,
    format_session_ended,
    format_session_started,
    is_authorized,
)
from src.telegram.output import _CONTENT_STATES
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.terminal_emulator import TerminalEmulator
from src.parsing.ui_patterns import ScreenState, extract_content
from src.project_scanner import Project
from src.session_manager import OutputBuffer
```

Also update all `patch()` targets:
- `"src.bot_handlers.scan_projects"` → `"src.telegram.handlers.scan_projects"`
- `"src.bot_handlers.get_git_info"` → `"src.telegram.handlers.get_git_info"`
- `"src.bot_handlers._run_update_command"` → `"src.telegram.handlers._run_update_command"`
- `"src.bot_commands.get_git_info"` → `"src.telegram.commands.get_git_info"`
- `"src.bot_commands._run_update_command"` → `"src.telegram.commands._run_update_command"`

Also update inline imports:
- Line 928: `from src.log_setup import setup_logging` → `from src.core.log_setup import setup_logging`
- Line 932: `logger="src.bot_handlers"` → `logger="src.telegram.handlers"`
- Line 1076: `from src.bot_output import _session_prev_state` → `from src.telegram.output import _session_prev_state`
- Line 1077: `from src.ui_patterns import ScreenEvent` → `from src.parsing.ui_patterns import ScreenEvent`

**test_main.py** — line 8:
```python
from src.main import _on_startup, _parse_args  # stays same
```
Line 102 (inline): `from src.bot_keyboards import BOT_COMMANDS` → `from src.telegram.keyboards import BOT_COMMANDS`
Line 94 (inline): `from src.main import build_app` — stays same.

**test_config.py**:
```python
from src.config import AppConfig, load_config, ConfigError
→
from src.core.config import AppConfig, load_config, ConfigError
```
And inline (line 114): `from src.config import DebugConfig` → `from src.core.config import DebugConfig`

**test_database.py**:
```python
from src.database import Database
→
from src.core.database import Database
```

**test_log_setup.py**:
```python
from src.log_setup import TRACE, setup_logging
→
from src.core.log_setup import TRACE, setup_logging
```

**test_session_manager.py**: update inline import:
- `from src.log_setup import setup_logging` → `from src.core.log_setup import setup_logging`

Top-level import `from src.session_manager import ...` stays same.

**test_claude_process.py**: update inline import:
- `from src.log_setup import setup_logging` → `from src.core.log_setup import setup_logging`

Top-level import `from src.claude_process import ClaudeProcess` stays same.

**test_project_scanner.py**: update inline imports:
- `from src.log_setup import setup_logging` → `from src.core.log_setup import setup_logging`
- `from src.log_setup import TRACE, setup_logging` → `from src.core.log_setup import TRACE, setup_logging`

### Task 7: Run full test suite and commit Phase A

**Step 1: Run tests**

```bash
python -m pytest --tb=short -q
```

Expected: All 401+ tests pass.

**Step 2: Verify no old import paths remain**

```bash
grep -r "from src\.bot_keyboards\|from src\.bot_handlers\|from src\.bot_commands\|from src\.bot_output\|from src\.telegram_format\|from src\.terminal_emulator\|from src\.ui_patterns\|from src\.detectors\|from src\.screen_classifier\|from src\.config\b\|from src\.database\b\|from src\.log_setup\b" src/ tests/ scripts/ --include="*.py"
```

Expected: No matches (all old flat import paths replaced).

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: reorganize src/ into parsing/, telegram/, core/ sub-packages"
```

---

## Phase B: Split Test Files

### Task 8: Create tests/parsing/ and split test_output_parser.py

**Files:**
- Create: `tests/parsing/__init__.py`
- Create: `tests/parsing/conftest.py`
- Create: `tests/parsing/test_terminal_emulator.py`
- Create: `tests/parsing/test_ui_patterns.py`
- Create: `tests/parsing/test_detectors.py`
- Create: `tests/parsing/test_screen_classifier.py`
- Create: `tests/parsing/test_formatter.py`
- Delete: `tests/test_output_parser.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p tests/parsing
touch tests/parsing/__init__.py
```

**Step 2: Create conftest.py with shared test data**

Move the real captured ANSI data constants and real screen data (lines 31-213 of test_output_parser.py) into `tests/parsing/conftest.py`. These are used across multiple test files.

The conftest should contain:
- All `REAL_*_ANSI` constants (REAL_STATUS_BAR_ANSI, REAL_TRUST_PROMPT_ANSI, REAL_EXIT_ANSI, REAL_ERROR_ANSI, REAL_STARTUP_ANSI, REAL_BOX_ANSI)
- All `REAL_*_SCREEN` constants (REAL_IDLE_SCREEN, REAL_THINKING_SCREEN, REAL_STREAMING_SCREEN, REAL_TOOL_REQUEST_SCREEN, REAL_TOOL_RUNNING_SCREEN, REAL_TOOL_RESULT_SCREEN, REAL_TODO_LIST_SCREEN, REAL_PARALLEL_AGENTS_SCREEN, REAL_BACKGROUND_SCREEN, REAL_STARTUP_SCREEN, REAL_USER_MESSAGE_SCREEN, REAL_ERROR_SCREEN)

Each test file imports what it needs from conftest.

**Step 3: Create test files**

Split classes from test_output_parser.py into their target files:

`tests/parsing/test_terminal_emulator.py`:
- TestTerminalEmulator (lines 215-326)
- TestStripAnsi (lines 551-602)
- TestCleanTerminalOutput (lines 603-625)
- TestFilterSpinners (lines 627-650)

Imports:
```python
from src.parsing.terminal_emulator import (
    TerminalEmulator, clean_terminal_output, filter_spinners, strip_ansi,
)
from tests.parsing.conftest import (
    REAL_STATUS_BAR_ANSI, REAL_STARTUP_ANSI, REAL_BOX_ANSI,
)
```

`tests/parsing/test_ui_patterns.py`:
- TestScreenState (lines 328-347)
- TestScreenEvent (lines 348-366)
- TestClassifyLine (lines 368-458)
- TestExtractContent (lines 460-549)

Imports:
```python
from src.parsing.ui_patterns import ScreenEvent, ScreenState, classify_line, extract_content
```

`tests/parsing/test_detectors.py`:
- TestDetectPrompt (lines 652-695)
- TestDetectContextUsage (lines 696-732)
- TestParseStatusBar (lines 733-801)
- TestParseExtraStatus (lines 803-828)
- TestDetectFilePaths (lines 829-858)
- TestDetectThinking (lines 859-910)
- TestDetectToolRequest (lines 911-955)
- TestDetectTodoList (lines 956-1009)
- TestDetectBackgroundTask (lines 1011-1030)
- TestDetectParallelAgents (lines 1031-1062)

Imports:
```python
from src.parsing.detectors import (
    ContextUsage, DetectedPrompt, PromptType, StatusBar,
    detect_background_task, detect_context_usage, detect_file_paths,
    detect_parallel_agents, detect_prompt, detect_thinking,
    detect_todo_list, detect_tool_request, parse_extra_status, parse_status_bar,
)
```

`tests/parsing/test_screen_classifier.py`:
- TestClassifyScreenState (lines 1063-1229)
- TestClassifyScreenStateLogging (lines 1298-1318)

Imports:
```python
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import ScreenEvent, ScreenState
from tests.parsing.conftest import (
    REAL_IDLE_SCREEN, REAL_THINKING_SCREEN, REAL_STREAMING_SCREEN,
    REAL_TOOL_REQUEST_SCREEN, REAL_TOOL_RUNNING_SCREEN, REAL_TOOL_RESULT_SCREEN,
    REAL_TODO_LIST_SCREEN, REAL_PARALLEL_AGENTS_SCREEN, REAL_BACKGROUND_SCREEN,
    REAL_STARTUP_SCREEN, REAL_USER_MESSAGE_SCREEN, REAL_ERROR_SCREEN,
)
```

`tests/parsing/test_formatter.py`:
- TestFormatTelegram (lines 1230-1263)
- TestSplitMessage (lines 1264-1297)

Imports:
```python
from src.telegram.formatter import TELEGRAM_MAX_LENGTH, format_telegram, split_message
```

**Step 4: Delete old file**

```bash
git rm tests/test_output_parser.py
```

### Task 9: Create tests/telegram/ and split test_bot.py

**Files:**
- Create: `tests/telegram/__init__.py`
- Create: `tests/telegram/conftest.py`
- Create: `tests/telegram/test_keyboards.py`
- Create: `tests/telegram/test_handlers.py`
- Create: `tests/telegram/test_commands.py`
- Create: `tests/telegram/test_output.py`
- Delete: `tests/test_bot.py`

**Step 1: Create directory and __init__.py**

```bash
mkdir -p tests/telegram
touch tests/telegram/__init__.py
```

**Step 2: Create conftest.py**

The root `tests/conftest.py` already has `mock_update` and `mock_context` fixtures — these are shared across all tests. No need to duplicate. The `tests/telegram/conftest.py` can be minimal or empty initially. Add any telegram-specific shared helpers as needed.

```python
"""Shared fixtures for telegram test package."""
```

**Step 3: Create test files**

`tests/telegram/test_keyboards.py`:
- TestIsAuthorized (lines 44-53)
- TestBuildProjectKeyboard (lines 55-97)
- TestBuildSessionsKeyboard (lines 98-117)
- TestFormatMessages (lines 118-155)

Imports:
```python
from unittest.mock import MagicMock
from src.telegram.keyboards import (
    build_project_keyboard, build_sessions_keyboard,
    format_history_entry, format_session_ended, format_session_started,
    is_authorized,
)
from src.project_scanner import Project
```

`tests/telegram/test_handlers.py`:
- TestHandleStart (lines 157-204)
- TestHandleSessions (lines 206-235)
- TestHandleExit (lines 237-283)
- TestHandleTextMessage (lines 285-337)
- TestHandleSessionsAuth (lines 338-366)
- TestHandleExitAuth (lines 353-366)
- TestHandleCallbackQuery (lines 368-490)
- TestHandlerLogging (lines 925-935)
- TestSpawnErrorReporting (lines 937-977)
- TestHandleUnknownCommand (lines 979-1023)

Imports:
```python
from __future__ import annotations
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.telegram.handlers import (
    handle_callback_query, handle_exit, handle_sessions,
    handle_start, handle_text_message, handle_unknown_command,
)
from src.project_scanner import Project
```

Patch targets in this file:
- `"src.telegram.handlers.scan_projects"`
- `"src.telegram.handlers.get_git_info"`
- `"src.telegram.handlers._run_update_command"`

Logger reference: `logger="src.telegram.handlers"`

`tests/telegram/test_commands.py`:
- TestHandleHistoryAuth (lines 492-520)
- TestHandleGitAuth (lines 507-535)
- TestHandleUpdateAuth (lines 522-535)
- TestHandleHistory (lines 537-574)
- TestHandleGit (lines 576-607)
- TestHandleUpdateClaude (lines 609-644)
- TestHandleContext (lines 646-674)
- TestHandleDownload (lines 676-754)
- TestHandleFileUpload (lines 756-843)
- TestRunUpdateCommand (lines 845-851)
- The parametrized `test_unauthorized_rejected` function (lines 856-877)

Imports:
```python
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.telegram.commands import (
    _run_update_command, handle_context, handle_download,
    handle_file_upload, handle_git, handle_history, handle_update_claude,
)
from src.telegram.handlers import (
    handle_callback_query, handle_exit, handle_sessions,
    handle_start, handle_text_message,
)
```

Note: the parametrized test imports handlers from both modules.

Patch targets:
- `"src.telegram.commands.get_git_info"`
- `"src.telegram.commands._run_update_command"`

`tests/telegram/test_output.py`:
- TestOutputStateFiltering (lines 1026-1122)
- TestBuildApp (lines 880-923)

Imports:
```python
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock
import pytest
from src.telegram.output import _CONTENT_STATES
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import ScreenEvent, ScreenState, extract_content
from src.session_manager import OutputBuffer
```

Inline imports to update:
- `from src.telegram.output import _session_prev_state`
- `from src.parsing.ui_patterns import ScreenEvent`
- `from src.core.log_setup import setup_logging`

TestBuildApp uses `from src.main import build_app` — stays same.

**Step 4: Update tests/test_main.py**

Update inline import at line 102:
```python
from src.bot_keyboards import BOT_COMMANDS → from src.telegram.keyboards import BOT_COMMANDS
```

**Step 5: Delete old file**

```bash
git rm tests/test_bot.py
```

### Task 10: Run full test suite and commit Phase B

**Step 1: Run tests**

```bash
python -m pytest --tb=short -q
```

Expected: All 401+ tests pass.

**Step 2: Verify no old test files remain**

```bash
ls tests/test_output_parser.py tests/test_bot.py 2>&1
```

Expected: "No such file or directory" for both.

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: split test files to mirror source sub-package structure"
```

---

## Phase C: Documentation

### Task 11: Create CLAUDE.md

**File:** Create `CLAUDE.md` at project root.

Content should include:
- Project overview (Python Telegram bot proxying Claude Code CLI via pyte/pexpect)
- Mermaid architecture diagram showing 3 sub-packages and top-level modules
- Key conventions table (naming, imports, test patterns)
- "Where to find X" quick reference table
- Directives: keep docs, docstrings, comments up to date after every change

### Task 12: Create per-package READMEs

**Files:**
- Create: `src/parsing/README.md`
- Create: `src/telegram/README.md`
- Create: `src/core/README.md`

Each should include:
- Package purpose (1 sentence)
- Module inventory table with one-line descriptions
- Internal dependency mermaid diagram
- Key patterns and conventions specific to the package

### Task 13: Create docs/index.md

**File:** Create `docs/index.md`

Content:
- Links to all documentation files
- Full system mermaid diagram (Telegram → bot handlers → session manager → Claude process → pyte → classifier → formatter → Telegram)
- Quick-start for contributors

### Task 14: Update docs/architecture.md

**File:** Modify `docs/architecture.md`

Updates needed:
- Replace ASCII art diagram at top with mermaid
- Update module table: remove `bot.py` and `output_parser.py`, add all new sub-package modules
- Update all references from old module paths to new paths
- Update `bot.py` references in sequence diagrams to use specific module names (handlers.py, commands.py, etc.)
- Replace any remaining ASCII art with mermaid diagrams

### Task 15: Move old plans to docs/archive/

**Step 1: Create archive directory**

```bash
mkdir -p docs/archive
```

**Step 2: Move old plan files**

```bash
git mv docs/plans/2026-02-09-* docs/archive/
```

Keep recent plans (2026-02-10+) in docs/plans/.

### Task 16: Create run.py launcher

**File:** Create `run.py` at project root.

```python
#!/usr/bin/env python3
"""Launch the Claude Instance Manager bot.

Usage:
    python run.py [config.yaml] [--debug] [--trace] [--verbose]
"""
import asyncio
import sys

from src.main import main

if __name__ == "__main__":
    asyncio.run(main())
```

Make executable:
```bash
chmod +x run.py
```

### Task 17: Final verification and commit Phase C

**Step 1: Run tests**

```bash
python -m pytest --tb=short -q
```

Expected: All tests still pass (docs changes shouldn't break anything, but run.py import might).

**Step 2: Verify all files under 500 lines**

```bash
find src -name "*.py" -exec wc -l {} + | sort -n
```

**Step 3: Commit**

```bash
git add -A
git commit -m "docs: add CLAUDE.md, package READMEs, docs/index.md, update architecture, add run.py launcher"
```

---

## Verification Checklist

After all tasks complete:
- [ ] `python -m pytest` — all 401+ tests pass
- [ ] `wc -l src/**/*.py` — all files under 500 lines
- [ ] `grep -r "from src\.output_parser\|from src\.bot import" src/ tests/ scripts/` — no matches
- [ ] `grep -r "from src\.bot_keyboards\|from src\.bot_handlers\|from src\.bot_commands\|from src\.bot_output\|from src\.telegram_format\|from src\.terminal_emulator\b\|from src\.ui_patterns\b\|from src\.detectors\b\|from src\.screen_classifier\b\|from src\.config\b\|from src\.database\b\|from src\.log_setup\b" src/ tests/ scripts/` — no matches (all old flat paths gone)
- [ ] CLAUDE.md exists at project root with mermaid diagrams
- [ ] docs/index.md exists with full system diagram
- [ ] Per-package READMEs exist in src/parsing/, src/telegram/, src/core/
- [ ] docs/architecture.md updated with new module paths and mermaid diagrams
- [ ] run.py exists and is executable
- [ ] Old plans moved to docs/archive/
