# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Telegram bot that proxies Claude Code CLI sessions over PTY. Users interact with Claude Code through Telegram messages and inline keyboards. The bot parses the terminal screen via a pyte virtual terminal emulator, classifies the screen state, and streams formatted output to Telegram in real time.

## Commands

### Run the bot
```bash
python -m src.main config.yaml --debug
```

### Run the bot via runner script (for testing)
```bash
./scripts/bot-runner.sh
```
Manages the bot process externally with file-based control (restart/stop via `.claude/heuristic-loop-state/bot.control`). See [docs/bot-runner.md](docs/bot-runner.md) for details.

**When starting a heuristic-loop test session**, tell the user to run this script first if `bot.status` is not `running`.

### Run all tests
```bash
python -m pytest
```

### Run a single test file or test
```bash
python -m pytest tests/test_config.py
python -m pytest tests/test_config.py::TestLoadConfig::test_minimal_config
```

### Run tests with coverage
```bash
python -m pytest --cov=src --cov-report=term-missing
```
Coverage threshold is 90% (configured in `pyproject.toml`).

### Install for development
```bash
pip install -e ".[dev]"
```

## Architecture

The system has three layers connected by an async pipeline:

**Telegram layer** (`src/telegram/`) — Handlers receive user messages, forward them to sessions, and stream output back to Telegram via edit-in-place HTML messages.

**Session layer** (`src/session_manager.py`, `src/claude_process.py`) — Manages per-user session lifecycles. `ClaudeProcess` wraps a pexpect-managed PTY subprocess. Text is sent via `submit()` which separates text and Enter with a 150ms delay to avoid triggering Claude Code's paste detection.

**Parsing layer** (`src/parsing/`) — A pyte virtual terminal (`terminal_emulator.py`) feeds a 3-pass priority screen classifier (`screen_classifier.py`) that returns one of 14 `ScreenState` values. Content is extracted via `ui_patterns.py` line classification and `content_classifier.py` ANSI-attribute-based region detection.

### Output pipeline (the critical path)

`poll_output()` in `src/telegram/output.py` runs a 300ms async loop across all sessions. Each cycle:
1. Reads raw PTY bytes via `ClaudeProcess.read_available()`
2. Feeds bytes into the pyte terminal emulator
3. Reads the full screen (`get_display()`) for state classification — classifier needs full context
4. Reads only changed lines (`get_changes()`) for content extraction — avoids re-sending the entire screen
5. Delegates to `SessionProcessor` (`output_processor.py`) which runs a 3-phase pipeline: pre-extraction (side effects), extraction (dedup + render + send), finalization (ANSI re-render on IDLE)

The output module is decomposed into 5 files:
- `output.py` — orchestration loop
- `output_processor.py` — 3-phase per-session event processor
- `output_state.py` — per-session state registry and content deduplication
- `output_pipeline.py` — span manipulation and rendering helpers (heuristic + ANSI pipelines)
- `streaming_message.py` — edit-in-place Telegram message with rate limiting

### Screen state classifier

`classify_screen_state()` in `src/parsing/screen_classifier.py` uses a 3-pass priority system:
- **Pass 1 (screen-wide):** tool approval menus, TODO lists, parallel agents
- **Pass 2 (bottom-up):** thinking, running tools, tool results, background tasks
- **Pass 3 (last line + fallback):** idle prompt, streaming, user message, startup, error

The 14 states are defined in `ScreenState` enum (`src/parsing/models.py`). Only `_CONTENT_STATES` produce output sent to Telegram; others (STARTUP, IDLE, USER_MESSAGE, UNKNOWN) are suppressed.

### Callback query dispatch

`src/telegram/callbacks.py` dispatches inline keyboard callbacks by prefix: `project:`, `switch:`, `kill:`, `update:`, `tool:`, `page:`.

## Key Conventions

- **Config:** Typed dataclasses in `src/core/config.py`, loaded from YAML. See `config.yaml.example` for all options.
- **Tests:** pytest with `asyncio_mode = "auto"`. Tests use `MagicMock`/`AsyncMock`. Root `conftest.py` provides `mock_update` (user 111), `mock_context` (authorizes user 111). Handlers under test need `session_manager` in `bot_data`.
- **Telegram HTML:** The bot uses `parse_mode="HTML"`. File paths in messages use `<code>` tags to prevent Telegram from parsing `/path/to/file` as command links.
- **No-session messages:** Standardized to "No active session. Use /start to begin one." (singular) or "No active sessions." (plural).
- **Authorization:** Every handler checks `is_authorized(user_id, config.telegram.authorized_users)` from `keyboards.py` before proceeding.
- **Logging:** Custom TRACE level (5) defined in `src/core/log_setup.py`, used for high-frequency PTY I/O logs.
- **Python:** Requires 3.11+. Uses `from __future__ import annotations` throughout.
