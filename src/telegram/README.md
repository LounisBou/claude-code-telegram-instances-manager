# src/telegram/ -- Telegram Bot Layer

User interaction, output streaming, and message formatting for the Telegram interface. All handlers gate on `is_authorized()` before processing.

## Modules

| Module | Purpose |
|---|---|
| `keyboards.py` | `is_authorized()` gate, `BOT_COMMANDS` list, inline keyboard builders for projects/sessions/tools, history formatting helpers |
| `handlers.py` | Core Telegram handlers: `/start`, `/sessions`, `/exit`, text messages, callback queries, unknown commands |
| `commands.py` | Extended command handlers: `/history`, `/git`, `/context`, `/download`, `/update_claude`, file uploads |
| `formatter.py` | Telegram MarkdownV2 escaping (`format_telegram`), HTML formatting (`format_html`), message splitting for the 4096-char limit, text reflowing (`reflow_text`) |
| `output.py` | `poll_output()` async loop -- polls sessions every 300ms, classifies screen state, extracts content, formats via `format_html()`, and streams to Telegram via `StreamingMessage` edit-in-place. Also provides `StreamingMessage` and `StreamingState` for edit-in-place streaming with throttled edits and overflow handling |

## Dependency Diagram

```mermaid
graph LR
    keyboards["keyboards.py<br/>(leaf)"]
    formatter["formatter.py<br/>(leaf)"]
    handlers["handlers.py"] --> keyboards
    handlers --> commands
    commands["commands.py"] --> keyboards
    output["output.py"] --> formatter
```

`keyboards` and `formatter` are leaf modules. `handlers` imports from both `keyboards` and `commands`. `commands` imports from `keyboards`. `output` imports from `formatter` and the parsing sub-package.

## Key Patterns

- **`is_authorized()` gate:** Every handler checks the user against `config.telegram.authorized_users` before processing. Unauthorized users receive a rejection message.
- **`poll_output()` async loop:** Runs as a background `asyncio.Task`. Each cycle reads from all active sessions, classifies the screen state, extracts content via `_CONTENT_STATES` filtering, converts to HTML via `format_html()`, and streams to Telegram via `StreamingMessage` (edit-in-place).
- **`_CONTENT_STATES` filtering:** Only screen states that produce user-visible output (STREAMING, TOOL_REQUEST, TOOL_RUNNING, TOOL_RESULT, ERROR, TODO_LIST, PARALLEL_AGENTS, BACKGROUND_TASK) are forwarded to Telegram. UI chrome states (STARTUP, IDLE, USER_MESSAGE, UNKNOWN) are suppressed.
- **`StreamingMessage` edit-in-place:** Manages a single Telegram message that is edited in-place as Claude streams output. State machine: IDLE -> THINKING (typing indicator) -> STREAMING (throttled edits) -> IDLE. Handles overflow by splitting at 4096 chars and starting a new message. Falls back to plain text on HTML parse errors.
