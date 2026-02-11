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
| `src/main.py`        | Application wiring, startup, signal handling, and entry point        |
| `src/bot.py`         | Telegram command/callback/message handlers, keyboard builders, output polling loop |
| `src/session_manager.py` | Per-user session lifecycle management and output buffering       |
| `src/claude_process.py`  | Async wrapper around pexpect-managed Claude Code CLI subprocess  |
| `src/output_parser.py`   | pyte-based terminal emulator, screen state classifier, and Telegram formatter |
| `src/config.py`      | YAML config loading and validation with typed dataclasses            |
| `src/database.py`    | Async SQLite wrapper for persisting session records                  |
| `src/project_scanner.py` | Project discovery by scanning for `.git`/`.claude` directories   |
| `src/git_info.py`    | Git branch and GitHub PR metadata retrieval                          |
| `src/file_handler.py`| File upload directory management and cleanup                         |
| `src/log_setup.py`   | Custom TRACE level (5), console/file handler setup                   |

## Input Path: Telegram to Claude

When a user sends a message, it flows through three layers before reaching Claude Code's PTY:

```mermaid
sequenceDiagram
    participant U as Telegram User
    participant T as Telegram API
    participant B as bot.py
    participant SM as SessionManager
    participant CP as ClaudeProcess
    participant PTY as Claude Code PTY

    U->>T: Send text message
    T->>B: Update (handle_text_message)
    B->>B: Check authorization
    B->>SM: get_active_session(user_id)
    SM-->>B: ClaudeSession
    B->>CP: session.process.submit(text)

    Note over CP,PTY: submit() sends text and Enter separately<br/>to avoid triggering Claude Code paste mode
    CP->>PTY: send(text)
    CP->>CP: await asyncio.sleep(0.15)
    CP->>PTY: send("\r")
```

**Key implementation detail:** Claude Code's TUI detects text + Enter arriving
together as a clipboard paste. The `submit()` method sends them separately with
a 0.15 second delay so the TUI treats it as typed input followed by submit.

## Output Path: Claude to Telegram

Claude Code's responses follow an asynchronous pipeline from PTY bytes to
Telegram messages. A background loop (`poll_output`) polls every 300ms:

```mermaid
sequenceDiagram
    participant PTY as Claude Code PTY
    participant CP as ClaudeProcess
    participant EMU as TerminalEmulator (pyte)
    participant CLS as classify_screen_state
    participant EXT as extract_content
    participant BUF as OutputBuffer
    participant T as Telegram API

    loop Every 300ms
        CP->>CP: read_available()
        alt Has new data
            CP-->>EMU: raw bytes
            EMU->>EMU: feed(raw) — update pyte screen
            EMU-->>CLS: get_display() — full 40x120 grid
            CLS->>CLS: 3-pass priority detection
            CLS-->>BUF: ScreenState + payload

            EMU-->>EXT: get_changes() — only changed lines
            EXT->>EXT: Filter UI chrome, keep content
            EXT-->>BUF: Extracted text

            Note over EXT,BUF: Only _CONTENT_STATES produce output:<br/>STREAMING, TOOL_REQUEST, TOOL_RUNNING,<br/>TOOL_RESULT, ERROR, TODO_LIST,<br/>PARALLEL_AGENTS, BACKGROUND_TASK

            alt Buffer ready (debounce expired or max size)
                BUF->>T: send_message(text)
            end
        end
    end
```

**Two separate reads from the emulator per cycle:**
1. `get_display()` returns the full screen for state classification (needs full context)
2. `get_changes()` returns only lines that changed since last read (incremental delta for content extraction, avoids re-sending the entire screen every cycle)

## Screen State Machine

The classifier recognizes 13 distinct screen states. States in green produce
content sent to Telegram; states in grey are suppressed (UI chrome, transient).

```mermaid
stateDiagram-v2
    direction LR

    [*] --> STARTUP: Process spawned

    STARTUP --> IDLE: Prompt appears<br/>(❯ between separators)

    IDLE --> USER_MESSAGE: User types text
    USER_MESSAGE --> THINKING: Claude starts processing

    THINKING --> STREAMING: Response begins<br/>(⏺ marker appears)

    STREAMING --> IDLE: Response complete<br/>(prompt returns)
    STREAMING --> TOOL_REQUEST: Needs approval<br/>(selection menu)
    STREAMING --> THINKING: Pauses to think

    TOOL_REQUEST --> TOOL_RUNNING: User approves
    TOOL_RUNNING --> TOOL_RESULT: Tool completes
    TOOL_RESULT --> STREAMING: Continues response
    TOOL_RESULT --> THINKING: Thinks about result

    STREAMING --> TODO_LIST: Shows task list
    STREAMING --> PARALLEL_AGENTS: Launches agents
    STREAMING --> BACKGROUND_TASK: Background work

    state "Sent to Telegram (_CONTENT_STATES)" as content {
        STREAMING
        TOOL_REQUEST
        TOOL_RUNNING
        TOOL_RESULT
        ERROR
        TODO_LIST
        PARALLEL_AGENTS
        BACKGROUND_TASK
    }

    state "Suppressed (UI chrome)" as suppressed {
        STARTUP
        IDLE
        USER_MESSAGE
        UNKNOWN
    }

    note right of THINKING
        Sends "_Thinking..._" once
        on transition, then suppressed
    end note
```

### Classifier Priority Order

The classifier uses a 3-pass priority system to resolve ambiguity when multiple
patterns are present on screen simultaneously:

| Pass | Step | State | Detection Method |
|------|------|-------|-----------------|
| 1 (screen-wide) | 1 | TOOL_REQUEST | Selection menu with ❯ cursor + numbered options |
| 1 | 2 | TODO_LIST | Task count header + checkbox items |
| 1 | 3 | PARALLEL_AGENTS | Agent launch count + tree items |
| 2 (bottom-up) | 4 | THINKING | Star character + ellipsis in bottom 8 lines |
| 2 | 5 | TOOL_RUNNING | "Running..." or "Waiting..." status |
| 2 | 6 | TOOL_RESULT | "Added N lines, removed M lines" diff summary |
| 2 | 7 | BACKGROUND_TASK | "in the background" text |
| 3 (last line) | 8 | IDLE | ❯ between separator lines (3-line gap tolerance) |
| 3 | 9 | STREAMING | ⏺ response marker anywhere on screen |
| 3 | 10 | USER_MESSAGE | ❯ with text, not between separators |
| fallback | 11 | STARTUP | Logo/version in first 10 lines (only if no ⏺ visible) |
| fallback | 12 | ERROR | Error keywords (MCP, ENOENT, etc.) |
| fallback | 13 | UNKNOWN | Nothing matched |

**pyte banner persistence:** The Claude Code startup banner (logo + version)
stays at the top of pyte's screen buffer permanently because the TUI redraws
in-place rather than scrolling. Step 11 guards against this by skipping STARTUP
when a `⏺` response marker exists anywhere on screen. The poll loop has an
additional guard that converts STARTUP to UNKNOWN once the session has left
the STARTUP state.

## Content Extraction

`extract_content()` filters display lines through `classify_line()` which
recognizes 14 line types:

| Kept (sent to user) | Stripped (UI chrome) |
|---------------------|---------------------|
| `content` — plain text | `separator` — ─━═ lines |
| `response` — ⏺ prefix stripped | `status_bar` — project/branch/usage |
| `tool_connector` — ⎿ prefix stripped | `thinking` — star + ellipsis |
| | `tool_header` — Bash()/Write()/Read() |
| | `prompt` — ❯ input line |
| | `box` — ╭╮╰╯ box-drawing |
| | `logo` — ▐▛▜▌ block elements |
| | `empty` — blank lines |
| | `diff_delimiter` — ╌ lines |
| | `todo_item` — ◻◼✔ checkboxes |
| | `agent_tree` — ├└─ tree items |

## Startup & Shutdown

```mermaid
sequenceDiagram
    participant M as main.py
    participant A as Application
    participant DB as Database
    participant SM as SessionManager
    participant PO as poll_output

    Note over M: Startup sequence
    M->>A: build_app(config)
    M->>A: app.initialize()
    M->>DB: db.initialize()
    M->>DB: mark_active_sessions_lost()
    M->>A: set_my_commands(BOT_COMMANDS)
    M->>A: app.start() + updater.start_polling()
    M->>PO: asyncio.create_task(poll_output)
    M->>M: await stop_event (SIGINT/SIGTERM)

    Note over M: Shutdown sequence (first Ctrl+C)
    M->>PO: poll_task.cancel()
    M->>M: Remove signal handlers<br/>(second Ctrl+C → force exit)
    M->>A: updater.stop()
    M->>A: app.stop()
    M->>SM: session_manager.shutdown()<br/>(terminates all PTY processes)
    M->>DB: db.close()
    M->>A: app.shutdown()
```

**Why `_on_startup()` is called directly:** The python-telegram-bot `post_init`
callback only fires with `run_polling()` or `run_webhook()`. This application
uses manual startup (`initialize()` + `start()` + `updater.start_polling()`)
for signal handling control, so `_on_startup()` must be called explicitly.

## Key Design Decisions

### 1. ScreenState Classifier

The parser uses a 13-state enum (`ScreenState`) to classify the full terminal screen rather than reacting to individual lines. Classification runs a 3-pass priority detection:

- **Pass 1 (screen-wide):** tool approval menus, TODO lists, parallel agents.
- **Pass 2 (bottom-up):** thinking indicators, running tools, tool results, background tasks.
- **Pass 3 (last line):** idle prompt, streaming, user message, startup, error, unknown.

Five dedicated detector functions feed into `classify_screen_state()`, which returns a single authoritative state used by downstream formatting and control logic.

### 2. Capture-Driven Parsing

Every parser change is validated against a corpus of real terminal snapshots captured from live Claude Code sessions using `scripts/capture_claude_ui.py`. This ensures:

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

### 5. Incremental Content Extraction

The output pipeline uses two separate reads from the terminal emulator each cycle:

- `get_display()` returns the full 40x120 screen for state classification (the classifier needs full context to detect screen-wide patterns like tool approval menus).
- `get_changes()` returns only lines that changed since the last read, used for content extraction. This prevents re-sending the entire visible screen every 300ms.

This separation is critical: classification needs the full picture, but content extraction must be incremental to avoid duplicate messages in Telegram.
