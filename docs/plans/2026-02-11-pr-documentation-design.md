# PR Documentation & Regression Tests Design

**Date:** 2026-02-11
**Branch:** fix-first-launch
**Audience:** Future self, contributors, operators

## Goal

Improve documentation and test coverage for the fix-first-launch PR (20 commits).
Three deliverables:

1. Mermaid diagrams in `docs/architecture.md` showing Telegram↔Claude communication
2. Inline code comments on all PR-changed critical sections
3. Full regression test suite covering all 20 commits' bug fixes

## Deliverable 1: Mermaid Diagrams in architecture.md

### Diagram 1 — User Message Flow (input path)

`sequenceDiagram` showing:
- User → Telegram API → bot.py `handle_message` → session.process.submit()
- submit() internals: send(text) + sleep(0.15) + send(\r)
- Annotation: why text and Enter must be separate (paste mode detection)

### Diagram 2 — Output Pipeline (output path)

`sequenceDiagram` showing the poll_output loop:
- Claude PTY → process.read_available()
- → TerminalEmulator.feed(raw) → get_display() for classification
- → classify_screen_state(display) → ScreenState decision
- → get_changes() for incremental delta
- → extract_content(changed) filters UI chrome
- → OutputBuffer.append() → debounce → bot.send_message()
- Annotations: which states are content vs suppressed, why get_changes not get_display

### Diagram 3 — Screen State Machine

`stateDiagram-v2` showing:
- STARTUP → IDLE → USER_MESSAGE → THINKING → STREAMING → IDLE
- STREAMING → TOOL_REQUEST → TOOL_RUNNING → TOOL_RESULT → STREAMING
- Side states: TODO_LIST, PARALLEL_AGENTS, BACKGROUND_TASK, ERROR
- Color/note annotations: _CONTENT_STATES (sent to Telegram) vs suppressed (STARTUP, IDLE, UNKNOWN)

## Deliverable 2: Inline Code Comments

Concise 2-3 line block comments explaining the **why** at each critical point:

### src/bot.py — poll_output()
- Pipeline overview comment at function top
- `get_changes()`: why incremental extraction (not full display re-send)
- STARTUP→UNKNOWN guard: why banner persists in pyte
- `_CONTENT_STATES`: why these specific states

### src/output_parser.py — classify_screen_state()
- Step 9: why scan all lines for ⏺ (content appears below marker)
- Step 11: why guarded by has_response (pyte never clears banner)

### src/output_parser.py — extract_content()
- Why response (⏺) and tool_connector (⎿) lines are now included

### src/claude_process.py
- `_build_env()`: pexpect treats env-in-command as executable name
- `submit()`: paste mode detection requires 0.15s delay

### src/main.py
- `_on_startup()`: post_init doesn't fire with manual startup
- Signal handlers: removed after first SIGINT for clean second Ctrl+C

## Deliverable 3: Regression Tests

### Existing (32 tests)
- TestBuildEnv (5) — pexpect env var handling
- TestSubmit (2) — text+CR separation
- TestDatabaseInitialize (2) — parent dir creation
- TestSessionManagerShutdown (3) — terminate all + clear state
- test_log_setup src logger (2) — module logger inheritance
- TestSpawnErrorReporting (2) — Telegram error messages
- TestHandleUnknownCommand (3) — forwarding + fallback
- TestOutputStateFiltering (8) — content state filtering
- Classifier streaming/startup (2) — ⏺ scan + STARTUP guard
- extract_content response/connector (3) — inclusion with prefix strip

### New Tests (~10)
1. poll_output incremental extraction — get_changes not get_display
2. STARTUP→UNKNOWN guard — no re-enter after leaving STARTUP
3. THINKING notification — `_Thinking..._` buffered on transition
4. Flush on IDLE transition — buffer sends on state change
5. Command menu registration — set_my_commands called on startup
6. Graceful shutdown sequence — sessions terminated, db closed
7. Config env threading — claude_env flows config → SessionManager → ClaudeProcess
8. extract_content mixed lines — realistic screen with all line types
9. classify long response — ⏺ far above, content fills bottom
10. OutputBuffer no duplicate sends — flush clears correctly

### Test locations
- Classifier/extract tests → `tests/test_output_parser.py`
- poll_output/bot tests → `tests/test_bot.py`
- Shutdown/env tests → `tests/test_session_manager.py`, `tests/test_main.py`

## Non-goals
- No changes to `docs/usage.md` or `docs/installation.md` (PR doesn't change user commands or deployment)
- No new doc files beyond updating architecture.md
- No refactoring of existing code — comments only
