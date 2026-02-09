# Phase 5-bis: Real-world UI Capture & Parser Hardening — Implementation Plan

> Inserts between Phase 5 (Output parser) and Phase 6 (Git info) in the main plan.
> Design doc: `docs/plans/2026-02-09-phase5bis-ui-capture-design.md`

---

## Task 5-bis.1: Build capture script

**Files:**
- Create: `scripts/capture_claude_ui.py`

**What:** A comprehensive capture tool that spawns Claude Code, runs an automated scenario triggering all major UI states, then drops into manual interactive mode. Saves raw PTY bytes, pyte screen snapshots, and event timelines.

**Automated scenario steps:**
1. Spawn with `CLAUDE_CONFIG_DIR=~/.claude-work`
2. Wait for startup → snapshot startup screen (logo, welcome box, model info)
3. Handle trust prompt if present → snapshot before/after
4. Snapshot idle state (prompt `❯`, status bar)
5. Send `"What is 2+2? Reply just the number"` → snapshot streaming changes → snapshot final response
6. Send `"Read pyproject.toml and tell me the project name"` → snapshot tool approval prompt → approve → snapshot spinner/loading → snapshot result
7. Send `"Run echo hello"` → snapshot bash approval → approve → snapshot execution → snapshot output
8. Send `"Say done"` → snapshot prompt reappearance + updated status bar
9. Drop into manual mode

**Manual mode commands:**
- Any text → sent to Claude, screen changes captured
- `/snap` → force snapshot
- `/dump` → print current screen
- `/quit` → save captures and exit

**Output:** `scripts/captures/<timestamp>/` with `raw_pty.bin`, `snapshots.json`, `events.json`, `report.txt`

**Acceptance:** User runs script from separate terminal, captures are saved to disk.

---

## Task 5-bis.2: Analyze captures & document UI patterns

**Files:**
- Create: `docs/claude-ui-patterns.md`

**What:** Read the capture data from 5-bis.1 (user shares report.txt or pastes screen output). Document every UI pattern:
- Exact screen layout for each state (which rows, what characters)
- Line patterns that identify each state
- Transition sequences (e.g., IDLE → THINKING → STREAMING → IDLE)
- Edge cases (overlapping patterns, ambiguous states)

**Depends on:** 5-bis.1 output (user runs script and shares results)

**Acceptance:** Comprehensive pattern document that serves as spec for parser implementation.

---

## Task 5-bis.3: Implement ScreenState classifier

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**What:** Add the screen state classification system:

1. `ScreenState` enum (15 states from design doc)
2. `ScreenEvent` dataclass (state + payload + raw_lines + timestamp)
3. `classify_screen_state(lines: list[str], prev_state: ScreenState | None = None) -> ScreenEvent`
   - Takes full screen lines from pyte
   - Optionally takes previous state for transition context
   - Returns classified state with extracted payload

**Payload examples by state:**
- `STREAMING`: `{"text": "The answer is 4", "is_complete": False}`
- `TOOL_REQUEST`: `{"tool": "Read", "target": "pyproject.toml", "approval_type": "Y/n"}`
- `TOOL_RUNNING`: `{"tool": "Bash", "command": "echo hello"}`
- `BACKGROUND_TASK`: `{"description": "Searching codebase...", "progress": None}`
- `TODO_LIST`: `{"items": [{"id": 1, "text": "...", "status": "pending"}, ...]}`
- `SELECTION_MENU`: `{"options": ["Yes, I trust", "No"], "selected": 0, "has_free_text": False}`
- `FREE_TEXT_PROMPT`: `{"options": [...], "has_free_text": True}`

**TDD:** Tests use real captured screen data from 5-bis.2 as fixtures.

**Acceptance:** All captured states correctly classified. 100% coverage on new code.

---

## Task 5-bis.4: Harden existing parsers with real data

**Files:**
- Modify: `src/output_parser.py`
- Modify: `tests/test_output_parser.py`

**What:** Fix and extend existing functions based on real captured patterns:

1. **`classify_line()`** — add patterns for:
   - Tool approval lines ("Allow Claude to..." / "Read file..." / "[Y/n]")
   - Spinner/loading indicator lines
   - Background task status lines
   - Todo list lines
   - Error message lines (red text patterns)

2. **`detect_prompt()`** — handle:
   - Real Claude Code tool approval format (not just generic Y/n)
   - Selection menu with "Other" / free text option
   - The exact Ink/React TUI prompt rendering

3. **`parse_status_bar()`** — handle:
   - All real status bar variations captured
   - Progress bar characters (█▎░)
   - Timer display (↻ 5:00)

4. **New functions:**
   - `detect_tool_request(text) -> ToolRequest | None` — extracts tool name, target, type
   - `detect_background_task(text) -> BackgroundTask | None` — extracts description, progress
   - `detect_todo_list(text) -> list[TodoItem] | None` — extracts todo items with status
   - `detect_error(text) -> ErrorInfo | None` — extracts error type and message

**TDD:** Every new test uses real captured data. No invented test data.

**Acceptance:** All functions pass against real captured patterns. 100% coverage.

---

## Task 5-bis.5: Validation round (capture → verify → fix)

**Files:**
- Modify: `src/output_parser.py` (if fixes needed)
- Modify: `tests/test_output_parser.py` (if new tests needed)

**What:** Run the capture script again after parser improvements. Verify every UI state is correctly classified by the new `classify_screen_state()`. Fix any remaining issues.

**Process:**
1. User runs `scripts/capture_claude_ui.py` again
2. I analyze new captures against parser
3. Fix any misclassifications
4. Repeat if needed

**Acceptance:** All 15 screen states correctly detected in real captures. User confirms parser output matches their expectations.
