# Architecture

## High-Level Overview

```
Telegram Cloud API
       |
       v
+--------------+       +------------------+       +------------------+
|   bot.py     | <---> | session_manager  | <---> | claude_process   |
|              |       |                  |       |                  |
| Commands     |       | Per-user session |       | pexpect PTY      |
| Callbacks    |       | lifecycle,       |       | subprocess       |
| Messages     |       | output buffering |       | management       |
+--------------+       +------------------+       +------------------+
                              |                          |
                              v                          v
                       +-------------+           +---------------+
                       | database.py |           | output_parser |
                       | (SQLite)    |           | (pyte screen) |
                       +-------------+           +---------------+
```

User messages flow left to right: Telegram -> bot handlers -> session manager -> Claude CLI process.
Responses flow right to left: PTY output -> pyte terminal -> parser/classifier -> Telegram message.

## Module Responsibilities

| Module               | Purpose                                                              |
|----------------------|----------------------------------------------------------------------|
| `src/main.py`        | Application wiring, startup, and entry point                         |
| `src/bot.py`         | Telegram command/callback/message handlers and keyboard builders     |
| `src/session_manager.py` | Per-user session lifecycle management and output buffering       |
| `src/claude_process.py`  | Async wrapper around pexpect-managed Claude Code CLI subprocess  |
| `src/output_parser.py`   | pyte-based terminal emulator, screen state classifier, and Telegram formatter |
| `src/config.py`      | YAML config loading and validation with typed dataclasses            |
| `src/database.py`    | Async SQLite wrapper for persisting session records                  |
| `src/project_scanner.py` | Project discovery by scanning for `.git`/`.claude` directories   |
| `src/git_info.py`    | Git branch and GitHub PR metadata retrieval                          |
| `src/file_handler.py`| File upload directory management and cleanup                         |

## Data Flow

```
1. User sends message via Telegram
2. bot.py receives update, resolves active session via session_manager
3. session_manager writes user text to the PTY fd (send + \r, separated by 0.15s delay)
4. claude_process reads raw bytes from the PTY
5. Raw bytes are fed into pyte virtual terminal (Screen object)
6. output_parser reads the pyte screen buffer:
   a. classify_screen_state() determines one of 13 ScreenState values
   b. classify_line() tags each line (one of 14 line types)
   c. Formatter builds Telegram-ready HTML from classified lines
7. session_manager buffers output, detects stable state, sends to Telegram
8. If ScreenState is TOOL_APPROVAL, an inline keyboard is sent for user confirmation
```

## Key Design Decisions

### 1. ScreenState Classifier

The parser uses a 13-state enum (`ScreenState`) to classify the full terminal screen rather than reacting to individual lines. Classification runs a 3-pass priority detection:

- **Pass 1 (high priority):** error banners, permission prompts, tool approval dialogs.
- **Pass 2 (structural):** cost/token status bars, streaming output indicators.
- **Pass 3 (fallback):** idle prompt, compact prompt, unknown.

Five dedicated detector functions feed into `classify_screen_state()`, which returns a single authoritative state used by downstream formatting and control logic.

### 2. Capture-Driven Parsing

Every parser change is validated against 161 real terminal snapshots captured from live Claude Code sessions using `scripts/capture_claude_ui.py`. This ensures:

- Zero UNKNOWN classifications across all captured states.
- Regressions from pyte rendering artifacts (e.g., trailing U+FFFD on separator lines) are caught immediately.
- New Claude Code UI patterns are added to the test corpus before parser code is modified.

### 3. Tool Approval Forwarding

All tool approval prompts detected by the screen state classifier are forwarded to the Telegram user as interactive inline keyboards. The bot never auto-approves any tool use. This gives the human operator full control over file writes, command execution, and other side-effecting actions initiated by Claude Code.

### 4. pyte Terminal Emulator

Instead of regex-stripping ANSI escape sequences from raw PTY output, the parser feeds bytes into a real virtual terminal emulator (`pyte.Screen`). This approach:

- Correctly handles cursor movement, screen redraws, and partial overwrites that Claude Code's TUI produces.
- Provides a stable 2D character grid to read from, eliminating an entire class of escape-sequence parsing bugs.
- Trades some performance for correctness -- the pyte screen is the single source of truth for what the user would see in a real terminal.
