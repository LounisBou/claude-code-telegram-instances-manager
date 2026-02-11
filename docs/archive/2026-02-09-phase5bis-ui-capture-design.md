# Phase 5-bis: Real-world Claude Code UI Capture & Parser Hardening

## Problem

The output parser (Phase 5) was built on assumptions and limited test data. We verified pyte+pexpect works for a simple Q&A, but the Telegram bot needs to handle **every** Claude Code UI state to provide rich mirroring of the Claude Code experience.

The parser currently classifies individual **lines** but cannot answer: "What is Claude doing right now?"

## Goal

1. Capture real Claude Code interactive output for every UI state
2. Build a **screen state classifier** that detects what Claude is doing at any moment
3. Harden all existing parsers with real-world data
4. Enable rich Telegram mirroring: streaming text, tool approval as buttons, background task progress, todo lists, parallel agent tracking

## Design Decisions

- **Rich mirroring** in Telegram (not just clean text)
- **Tool approvals always forwarded** to Telegram user (never auto-approved)
- **ScreenState enum** classifies the full screen, not just individual lines
- **Capture-driven development**: every parser change validated against real captured data

## Screen State Model

| State | Screen Pattern | Telegram Output |
|---|---|---|
| `STARTUP` | Welcome box, logo, model info | "Session started (Opus 4.6)" |
| `TRUST_PROMPT` | "Trust this folder?" selection | Auto-handled internally |
| `IDLE` | `❯` prompt with cursor, status bar | Nothing / "Ready" |
| `THINKING` | Spinner, no content yet | "Claude is thinking..." |
| `STREAMING` | Text appearing progressively | Message edited with streaming text |
| `TOOL_REQUEST` | "Allow Read/Write/Bash? [Y/n]" | Message + Yes/No buttons |
| `TOOL_RUNNING` | Spinner + "Running..." | "Running: `command`..." |
| `TOOL_RESULT` | Output block from tool | Formatted tool output |
| `BACKGROUND_TASK` | Subagent/parallel task running | "Background: Searching..." |
| `TODO_LIST` | TaskCreate/TaskList output | Formatted checklist |
| `PARALLEL_AGENTS` | Multiple agents running | Multi-agent status updates |
| `SELECTION_MENU` | `❯ 1. Option / 2. Option` | Inline keyboard buttons |
| `FREE_TEXT_PROMPT` | Choice menu with "Other" option | Keyboard + text input |
| `ERROR` | Error/crash message | Error forwarded to user |
| `CONTEXT_WARNING` | "Context almost full" | Warning message |

## Data Structures

```python
class ScreenState(Enum):
    STARTUP = "startup"
    TRUST_PROMPT = "trust_prompt"
    IDLE = "idle"
    THINKING = "thinking"
    STREAMING = "streaming"
    TOOL_REQUEST = "tool_request"
    TOOL_RUNNING = "tool_running"
    TOOL_RESULT = "tool_result"
    BACKGROUND_TASK = "background_task"
    TODO_LIST = "todo_list"
    PARALLEL_AGENTS = "parallel_agents"
    SELECTION_MENU = "selection_menu"
    FREE_TEXT_PROMPT = "free_text_prompt"
    ERROR = "error"
    CONTEXT_WARNING = "context_warning"

@dataclass
class ScreenEvent:
    state: ScreenState
    payload: dict  # state-specific data
    raw_lines: list[str]
    timestamp: float
```

## Capture Script Design

`scripts/capture_claude_ui.py` — run from a separate terminal.

**Automated scenario:**
1. Spawn Claude Code with CLAUDE_CONFIG_DIR
2. Capture startup (trust prompt, welcome box, status bar)
3. Send simple question → capture streaming response
4. Send request that triggers file read → capture tool approval + spinner + result
5. Send request that triggers bash command → capture approval + execution + output
6. Send multi-turn follow-up → capture prompt reappearance
7. Capture status bar with context usage

**Manual mode:**
After automated scenario, drop into interactive mode where user can:
- Type commands to send to Claude
- Type `/snap` to force a screen snapshot
- Type `/quit` to save and exit
- Every screen change is automatically captured

**Output:** `scripts/captures/<session_name>/` containing:
- `raw_pty.bin` — all raw PTY bytes
- `snapshots.json` — timestamped screen states
- `events.json` — event timeline
- `report.txt` — human-readable summary
