# ClaudeInstanceManager — Design Document

**Date:** 2026-02-09
**Status:** Approved

## Overview

ClaudeInstanceManager is a Python application that acts as a proxy between Telegram and Claude Code CLI instances running on a remote server (IznoServer). Users interact with Claude Code through a Telegram bot (ClaudeBot), managing sessions, viewing output, and providing input — all from their phone or desktop Telegram client.

## Architecture

```
┌─────────────────────────────────────┐
│         Telegram Bot Layer          │
│  (python-telegram-bot, async)       │
│  Handles: messages, callbacks,      │
│  inline keyboards, user auth,       │
│  file upload/download               │
├─────────────────────────────────────┤
│        Session Manager Layer        │
│  Manages multiple Claude sessions   │
│  per user. Routes input/output      │
│  to the correct session.            │
│  Persists session metadata to DB.   │
├─────────────────────────────────────┤
│       Claude Process Layer          │
│  (pexpect + asyncio)                │
│  Spawns Claude Code CLI in PTY,     │
│  reads output stream, writes input  │
├─────────────────────────────────────┤
│       Storage Layer                 │
│  (SQLite via aiosqlite)             │
│  Session history (metadata only)    │
└─────────────────────────────────────┘
         │              │
    ┌────┴────┐   ┌─────┴─────┐
    │Project A│   │ Project B │
    │ claude  │   │  claude   │
    └─────────┘   └───────────┘
```

### Data Flow

1. User sends a message in Telegram
2. Bot Layer authenticates user (allowlist check), routes to Session Manager
3. Session Manager identifies which Claude session is "active" for that user and forwards input
4. Claude Process Layer writes to the PTY stdin
5. PTY output is read asynchronously, parsed, formatted, and sent back through the layers to Telegram
6. Session metadata is persisted to SQLite

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python | Best for PTY interaction (pexpect), text parsing, and Telegram integration (python-telegram-bot docs already gathered) |
| Project discovery | Directory scan | Scan `projects_root` one level deep for dirs containing `.git` or `.claude` |
| Access control | Allowlist | List of authorized Telegram user IDs in config |
| Concurrency | Multiple sessions per user | Max configurable (default 3). Users switch via inline keyboards |
| Output rendering | Formatted best-effort | Strip ANSI, convert markdown to Telegram MarkdownV2, detect prompts → inline keyboards |
| Deployment | Systemd service | Auto-restart on crash, starts on boot |
| Storage | SQLite via aiosqlite | Metadata-only session history. Zero-config, file-based, async |
| Testing | pytest + TDD | 90%+ coverage enforced. pytest-asyncio for async tests, pytest-cov for coverage |
| File transfer | Temp folder per session | `/tmp/claude/{project_name}_{session_id}/` — cleaned on session end |

## Telegram Bot — User Interaction

### Commands

| Command | Description |
|---------|-------------|
| `/start`, `/new` | Start a new Claude session (shows project picker) |
| `/sessions` | List active sessions with `[Switch to]` `[Kill]` buttons |
| `/to:N text` | Send text to session N without switching |
| `/exit` | Exit the active Claude session |
| `/context` | Show context usage for active session |
| `/git` | Show current branch and PR for active session's project |
| `/history` | List past sessions (project, date, duration, status) |
| `/history N` | Show details for session N |
| `/download /path` | Download a file from IznoServer to Telegram |
| `/update-claude` | Update Claude Code CLI on the server |

### Starting a Session

1. User sends `/start` or `/new`
2. Bot scans `projects_root` for project directories (dirs containing `.git` or `.claude`)
3. Bot displays inline keyboard with project names, paginated if many
4. User taps a project → bot spawns Claude Code in that folder
5. Bot shows git info: branch name and PR link (if any)
6. Bot confirms: "Session started on **my-project**. Session #1"
7. Session metadata is written to SQLite

### Managing Multiple Sessions

- `/sessions` — lists all active sessions with project name and session ID
- Inline keyboard buttons: `[Switch to]` `[Kill]`
- The active session receives all text input by default
- `/to:N text` — send to specific session without switching
- Switching shows: "Switched to **my-project** (session #2)"

### Claude Prompts

When Claude presents interactive prompts (yes/no, multiple choice, tool approval), the output parser detects them and renders Telegram inline keyboards. User taps a button → the corresponding keystroke is sent to the PTY.

### Exiting

- `/exit` or typing `exit` sends exit to Claude, waits for termination
- Bot confirms: "Session #1 on **my-project** ended."
- Session end time and exit code written to SQLite
- If other sessions exist, auto-switches to the next one

## File Upload/Download

### Upload (Telegram → Claude)

1. User sends a file (image, document, video, audio) in Telegram
2. Bot downloads it via Telegram Bot API
3. Saves to `/tmp/claude/{project_name}_{session_id}/filename.ext`
4. Sends a message to Claude's PTY: `"User uploaded a file: /tmp/claude/{project_name}_{session_id}/filename.ext"`
5. On session end, the temp folder is deleted

### Download (Claude → Telegram)

1. Output parser scans for file path patterns in Claude's output (e.g. `wrote to /path/file.png`, `saved /path/file.pdf`)
2. When detected, bot appends a `[Download]` inline keyboard button to the message
3. User taps → bot reads the file and sends it via Telegram
4. Fallback: `/download /path/to/file` command for manual download

### Limits

Telegram's own limits apply: 20MB download from Telegram servers, 50MB upload to Telegram. No additional limits enforced.

## Context Usage & Compact Alerts

- Output parser watches for context usage patterns in Claude's terminal output (percentage indicators, "compact" suggestions)
- **Auto-alert**: when "need to compact" is detected, bot sends: "Context usage is high. Claude suggests compacting." with inline keyboard `[Compact now]` `[Dismiss]`
- **`/context` command**: shows current context usage for the active session on demand
- "Compact now" sends the `/compact` command to Claude's PTY

## Git Branch & PR Info

- **On session start**: bot runs `git -C {project_path} branch --show-current` and `gh pr view --json url,title,state -C {project_path}` as subprocesses
- Displays: "Branch: `feature/foo` | PR: [#42 - My PR title](url)" or "Branch: `main` | No open PR"
- **`/git` command**: re-runs the same checks on demand for the active session

## Claude Update Command

- `/update-claude` triggers the update process
- If active sessions exist: bot warns "N active sessions are running. Update anyway?" with `[Yes, update]` `[Cancel]` buttons
- On confirm: runs `claude update` (or configured update command), streams output to user
- On completion: reports success/failure and new version
- Available to any authorized user

## Claude Process Layer

### Spawning

Each session spawns Claude Code via pexpect. The process runs in a PTY for interactive terminal behavior.

### Output Processing Pipeline

Raw PTY bytes go through a sequential pipeline:

1. **ANSI stripper** — remove color codes, cursor movement, clear-screen sequences
2. **Spinner/progress filter** — detect and collapse repeated spinner frames (⠋⠙⠹...) into "Working..." or suppress entirely
3. **Prompt detector** — regex patterns to identify interactive prompts:
   - Yes/No: `[Y/n]`, `[y/N]`
   - Multiple choice: numbered lists followed by `>`
   - Tool approval: `Allow tool X? [Y/n]`
   - Text input: open-ended prompt waiting for user input
4. **Context usage detector** — parse context usage indicators and "need to compact" warnings
5. **File path detector** — detect output file references for download buttons
6. **Markdown formatter** — convert to Telegram MarkdownV2 (escape special chars, code blocks, bold, italic)
7. **Message splitter** — split at 4096-char Telegram limit at logical boundaries (paragraph breaks, code block boundaries)

### Output Buffering

- **Debounce window**: accumulate output for 500ms of silence before sending
- **Max buffer size**: 2000 chars triggers immediate send
- **Rate limiting**: respect Telegram's ~30 msg/sec limit, queue if needed

### Input Handling

- Regular text: write to PTY stdin + `\n`
- Prompt responses: send the appropriate keystroke (`y\n`, `1\n`, arrow keys + enter for selection menus)
- File uploads: save file, then write file path notification to PTY stdin

## Session Manager

### Session Object

```
ClaudeSession:
  session_id    int          # Incrementing per user (1, 2, 3...)
  user_id       int          # Telegram user ID
  project_name  str          # Directory name
  project_path  str          # Absolute path
  process       PtyProcess   # pexpect PTY process
  reader_task   asyncio.Task # Async PTY output reader
  status        str          # starting | active | exiting | dead
  created_at    datetime
  db_session_id int          # SQLite row ID
```

### Lifecycle

1. **Starting**: PTY spawned, reader task created, DB row inserted with status `active`
2. **Active**: input/output flowing, user interacting
3. **Exiting**: exit command sent, waiting for process termination
4. **Dead**: process terminated, DB row updated with `ended_at` and `exit_code`, temp files cleaned, session removed from memory

### Constraints

- `max_sessions_per_user` (default 3) — rejects new session with a message if limit reached
- Tracks active session per user for message routing
- Cleans up dead sessions automatically

### Error Handling

- **Process crash**: reader task catches EOF/exit, notifies user "Session #N crashed. Exit code: X", cleans up, persists to DB
- **Process hangs**: no output timeout (configurable, default 10 min) — bot warns "Session #N has been silent for 10 minutes. Still running." Not killed automatically.
- **Bot restart**: PTY processes die with parent. On startup, no sessions exist. If user chat IDs are known from DB, they are notified that sessions were lost.

## Persistent Storage (SQLite)

### Schema

```sql
CREATE TABLE sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    project      TEXT NOT NULL,
    project_path TEXT NOT NULL,
    started_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at     TIMESTAMP,
    exit_code    INTEGER,
    status       TEXT NOT NULL DEFAULT 'active'
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);
```

### What's Stored

Metadata only — no message content, no file references. Lightweight.

### Access

- Via `aiosqlite` for non-blocking async queries
- Database file at `data/sessions.db` (gitignored)

## Project Scanner

- Scans `projects_root` one level deep (configurable depth)
- A directory qualifies as a project if it contains `.git` or `.claude`
- Returns `list[Project]` with `name` (dir name) and `path` (absolute)
- Called on-demand when user requests `/start` or `/new`

## Configuration

```yaml
telegram:
  bot_token: "YOUR_TOKEN"
  authorized_users:
    - 123456789
    - 987654321

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

## Project Structure

```
claude-instance-manager/
├── config.yaml.example
├── config.yaml                # gitignored
├── requirements.txt
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── main.py                # Entry point, wires everything together
│   ├── config.py              # Config loading and validation
│   ├── bot.py                 # Telegram bot handlers, keyboards, commands
│   ├── session_manager.py     # Session lifecycle, routing, active tracking
│   ├── claude_process.py      # PTY spawning, async reading, writing
│   ├── output_parser.py       # ANSI stripping, prompt detection, formatting
│   ├── project_scanner.py     # Directory scanning for projects
│   ├── database.py            # SQLite persistence layer (aiosqlite)
│   ├── file_handler.py        # File upload/download between Telegram and server
│   └── git_info.py            # Git branch and PR detection
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_output_parser.py
│   ├── test_session_manager.py
│   ├── test_project_scanner.py
│   ├── test_bot.py
│   ├── test_database.py
│   ├── test_file_handler.py
│   ├── test_git_info.py
│   └── test_config.py
├── systemd/
│   └── claude-bot.service
├── data/                      # SQLite DB (gitignored)
└── docs/
    └── ...
```

## Deployment

- **Runtime**: Python 3.11+ with venv
- **Service**: systemd unit with `Restart=on-failure`
- **Dependencies**:
  - `python-telegram-bot[ext]` — async Telegram bot framework
  - `pexpect` — PTY process management
  - `pyyaml` — config parsing
  - `aiosqlite` — async SQLite access
  - `pytest` + `pytest-asyncio` + `pytest-cov` — testing (dev)

### Systemd Unit

```ini
[Unit]
Description=Claude Instance Manager Telegram Bot
After=network.target

[Service]
Type=simple
User=lounis
WorkingDirectory=/path/to/claude-instance-manager
ExecStart=/path/to/venv/bin/python -m src.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Testing Strategy (TDD, 90%+ Coverage)

**Framework:** pytest + pytest-asyncio + pytest-cov

**Approach:** Write tests first for each module (red → green → refactor).

| Module | Test focus | Technique |
|--------|-----------|-----------|
| `output_parser.py` | ANSI stripping, spinner collapsing, prompt detection, markdown conversion, message splitting, context detection, file path detection | Unit tests with captured terminal output samples |
| `database.py` | CRUD operations, schema creation, query correctness | In-memory SQLite |
| `file_handler.py` | Upload path generation, cleanup, path detection regex | Unit tests with temp dirs |
| `project_scanner.py` | Directory scanning, project qualification | Temp directories with `.git`/`.claude` markers |
| `session_manager.py` | Routing, session limits, lifecycle, cleanup on crash | Mocked ClaudeProcess |
| `config.py` | Validation, defaults, missing keys, type checking | Unit tests with sample configs |
| `git_info.py` | Branch detection, PR parsing, error cases | Mocked subprocess calls |
| `bot.py` | Handler logic, auth rejection, keyboard generation | Mocked Telegram updates |

**Coverage enforcement:** `pytest --cov=src --cov-fail-under=90`

## Out of Scope

- Web dashboard or admin panel
- Multi-server support
- Claude API usage (strictly CLI wrapper)
- Session resumption after bot restart (PTY processes die with parent)
- Message content persistence (metadata only)
- Auto-update mechanism for ClaudeInstanceManager itself
