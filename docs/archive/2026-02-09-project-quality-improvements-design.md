# Project Quality Improvements — Design Document

**Date:** 2026-02-09
**Status:** Approved

## Overview

Improve the Claude Instance Manager project with documentation, developer experience, and CI tooling. No behavioral changes to existing code — all changes are additive.

The project is already fully typed (all functions annotated, `from __future__ import annotations` everywhere). This design covers the remaining 7 improvement areas.

## Phase A: MIT License

Create `LICENSE` file in project root with MIT license text, copyright 2026 Lounis Bou.

**Files:** `LICENSE`

---

## Phase B: Google-style Docstrings

Add Google-style docstrings to every function, method, and class across all 11 source files (~90 docstrings total).

### Rules

1. **Every function/method** gets full Args and Returns sections, including private helpers and bot handlers.
2. **Dataclasses** get a one-line class docstring (fields are self-documenting with type annotations). Regular classes with explicit `__init__` get full Args on `__init__`.
3. **Enums** get a class docstring describing purpose.
4. **Raises** section only when the function explicitly raises exceptions.

### Format

```python
def build_project_keyboard(
    projects: list[Project], page: int = 0, page_size: int = 8
) -> list[list[dict]]:
    """Build an inline keyboard layout for project selection.

    Args:
        projects: List of available projects to display.
        page: Zero-based page index for pagination.
        page_size: Maximum number of projects per page.

    Returns:
        List of keyboard rows, each row a list of button dicts
        with 'text' and 'callback_data' keys. Includes pagination
        buttons when projects exceed page_size.
    """
```

### Files

| File | Functions/methods | Classes |
|------|-------------------|---------|
| `src/output_parser.py` | ~29 functions | 7 classes (ScreenState, ScreenEvent, StatusBar, TerminalEmulator, etc.) |
| `src/bot.py` | ~16 functions | 0 |
| `src/session_manager.py` | ~10 methods | 4 classes (SessionError, ClaudeSession, SessionManager, OutputBuffer) |
| `src/main.py` | 3 functions | 0 |
| `src/config.py` | 2 functions | 7 dataclasses |
| `src/database.py` | 8 methods | 1 class |
| `src/claude_process.py` | 6 methods | 1 class |
| `src/git_info.py` | 2 functions | 1 dataclass |
| `src/file_handler.py` | 7 methods | 1 class |
| `src/project_scanner.py` | 1 function | 1 dataclass |
| `src/__init__.py` | 0 | 0 |

---

## Phase C: Inline Comments

Add ~30-40 comment lines explaining *why*, not *what*.

### Where to add

- Complex regex patterns (verify `output_parser.py` completeness)
- Non-obvious control flow (3-pass classifier, IDLE gap tolerance loop)
- Business logic reasoning (session limit check before spawn, text/\r send separation)
- Error handling rationale (signalstatus fallback, exception swallowing)

### Where NOT to add

- Self-documenting code (`if not projects: return []`)
- Anything the docstring already explains
- Type-annotated function signatures
- Simple getters/setters

### Style

```python
# pexpect sets signalstatus (not exitstatus) when process is killed by signal
if self._process.exitstatus is not None:
    return self._process.exitstatus
return self._process.signalstatus
```

---

## Phase D: Debug Mode with PyDevMate

### Configuration

Add `DebugConfig` dataclass to `src/config.py`:

```python
@dataclass
class DebugConfig:
    enabled: bool = False
```

Add to `AppConfig` and `load_config`. Config YAML:

```yaml
debug:
  enabled: false
```

### CLI Flag

Update `src/main.py` with `argparse`:

```python
parser = argparse.ArgumentParser(description="Claude Instance Manager Bot")
parser.add_argument("config", nargs="?", default="config.yaml")
parser.add_argument("--debug", action="store_true", help="Enable debug mode")
```

`--debug` overrides `config.debug.enabled`.

### Logging with LogIt

Replace `logging.basicConfig` with PyDevMate's `LogIt`:

- Create logger in `main.py`, pass via `bot_data["logger"]`
- `level=DEBUG` when debug mode on, `level=INFO` otherwise
- Console output always on, file logging off (systemd captures stdout)
- Each module creates its own logger: `LogIt(name="session_manager", ...)`

### DebugIt Decorators

Applied conditionally on key functions when debug mode is enabled:

- `get_git_info`, `create_session`, `kill_session`, `classify_screen_state`
- NOT on hot-path functions (`read_available`, `classify_line`, `read_nonblocking`)

### Dependency

Add `pydevmate>=0.0.3` to `pyproject.toml` dependencies.

---

## Phase E: Test Improvements

### Coverage Gaps (92% -> 95%+)

**`src/bot.py` (77% -> 95%+):**
- `handle_context`: test sends `/context\n` to process, test no active session
- `handle_download`: test file found (reply_document called), test file not found, test missing path arg
- `handle_file_upload`: test document upload, test photo upload, test no active session, test no document
- `_run_update_command`: test with mocked subprocess

**`src/main.py` (67% -> 85%+):**
- `_on_startup`: test DB initialization and stale session marking with mocked DB

### Structural Improvements

**Shared fixtures in `conftest.py`:**

```python
@pytest.fixture
def mock_update():
    """Create a mock Telegram Update with common attributes."""
    update = MagicMock()
    update.effective_user.id = 111
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    return update

@pytest.fixture
def mock_context():
    """Create a mock context with config authorizing user 111."""
    context = MagicMock()
    config = MagicMock()
    config.telegram.authorized_users = [111]
    context.bot_data = {"config": config}
    return context
```

**Parametrize auth tests:**

All handlers have near-identical "unauthorized user rejected" tests. Consolidate into a single parametrized test:

```python
@pytest.mark.parametrize("handler", [
    handle_start, handle_sessions, handle_exit,
    handle_history, handle_git, handle_update_claude,
])
async def test_unauthorized_rejected(handler, mock_update, mock_context):
    mock_update.effective_user.id = 999
    await handler(mock_update, mock_context)
    call_text = mock_update.message.reply_text.call_args[0][0]
    assert "not authorized" in call_text.lower()
```

---

## Phase F: CI with GitHub Actions

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src --cov-fail-under=90 -q
```

Update `pyproject.toml` to define `[project.optional-dependencies] dev` group so CI can use `pip install -e ".[dev]"`.

---

## Phase G: Documentation

### `README.md` (project root)

- Project title and one-line description
- Features list (bullet points)
- Quick start (clone, venv, config, run)
- Links to detailed docs (architecture, installation, usage)
- Available commands table
- License mention (MIT)

### `docs/architecture.md`

- High-level text diagram: Telegram <-> Bot handlers <-> Session Manager <-> Claude Process (pexpect/pyte)
- Module responsibilities table (each `src/*.py` with one-line purpose)
- Data flow: user message -> PTY write -> screen read/parse -> Telegram response
- Key design decisions: ScreenState classifier, capture-driven parsing, tool approval forwarding

### `docs/installation.md`

- Prerequisites (Python 3.11+, Claude Code CLI, Telegram bot token via BotFather)
- Clone, create venv, install dependencies
- Config file setup (`config.yaml` with all fields documented including debug)
- Systemd deployment (reference to `systemd/claude-bot.service`)
- Debug mode activation (`--debug` flag)

### `docs/usage.md`

- Available Telegram commands with descriptions
- Session lifecycle (select project -> chat -> exit)
- File uploads (documents, photos)
- Multi-session management (switch, kill, list)
- Git info and context commands

---

## Phase Order

| Phase | Area | Commit message |
|-------|------|----------------|
| A | MIT License | `chore: add MIT license` |
| B | Google-style docstrings | `docs: add Google-style docstrings to all source files` |
| C | Inline comments | `docs: add inline comments for non-obvious logic` |
| D | Debug mode (PyDevMate) | `feat: add debug mode with PyDevMate LogIt/DebugIt` |
| E | Test improvements | `test: improve coverage to 95%+ and refactor fixtures` |
| F | CI with GitHub Actions | `ci: add GitHub Actions workflow with test matrix` |
| G | Documentation | `docs: add README, architecture, installation, and usage docs` |

Each phase is one commit. Phase G goes last because docs reference the final state of the code.
