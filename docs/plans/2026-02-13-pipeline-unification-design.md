# Pipeline Unification Design

**Date**: 2026-02-13
**Status**: Proposed
**Scope**: Unify the output pipeline's three state machines, rendering paths, and dedup mechanism

## Problem

The output pipeline has three interacting state representations that compound complexity:

1. **ScreenState** (14 values in `parsing/models.py`) — classifies what the terminal looks like
2. **StreamingState** (3 values in `streaming_message.py`) — tracks Telegram message lifecycle
3. **ExtractionMode** (4 values in `output_processor.py`) — determines how content is extracted

These interact in `SessionProcessor._extraction_mode()` which consults all three plus the `changed` lines list to pick a strategy. This is the most fragile point in the codebase — a change to any of the three enums can break the extraction logic without obvious symptoms.

Additional tensions:

- **Dual rendering pipeline**: Heuristic (keyword-based) during streaming, ANSI (attribute-based) on finalization. Same response renders differently at different times. The heuristic pipeline exists as legacy — it was the first approach before ANSI rendering was added.
- **Line-based string dedup**: `ContentDeduplicator` tracks `set[str]` of sent line text. Identical lines across responses get falsely deduped. Lifecycle (seed/clear/snapshot/re-seed) is spread across multiple transition handlers.
- **Module-level global state**: `_states` dict in `output_state.py` with `get_or_create()`/`cleanup()` creates hidden coupling between handlers and the output pipeline.

## Design

### Core Separation: Observation vs. State

The terminal classifier produces an **observation** (what the screen looks like right now). The pipeline maintains **state** (what the bot is doing). These are currently conflated — `ScreenState` is used as both.

Rename `ScreenState` → `TerminalView`. Keep the classifier identical (14 values, same detection logic). The classifier is a pure function: terminal lines in, observation out.

Create `PipelinePhase` — the actual behavioral state:

```python
class PipelinePhase(Enum):
    DORMANT       = "dormant"        # Idle, no pending message
    THINKING      = "thinking"       # "Thinking..." sent, typing indicator active
    STREAMING     = "streaming"      # Content flowing, editing message in place
    TOOL_PENDING  = "tool_pending"   # Tool approval keyboard sent, waiting for user
```

### Transition Table

Every behavior is an explicit `(current_phase, observation) → (next_phase, actions)` rule:

```
DORMANT + thinking          → THINKING       send_thinking, start_typing, snapshot_chrome
DORMANT + response_content  → STREAMING      send_new_message (ultra-fast, no thinking)
DORMANT + tool_menu         → TOOL_PENDING   send_keyboard
DORMANT + auth_required     → DORMANT        send_auth_warning, kill_session
DORMANT + *                 → DORMANT        (no-op)

THINKING + response_content → STREAMING      cancel_typing, extract_changes, edit_message
THINKING + idle_prompt      → DORMANT        cancel_typing, extract_full, finalize
THINKING + tool_menu        → TOOL_PENDING   cancel_typing, finalize, send_keyboard
THINKING + thinking         → THINKING       (no-op, already thinking)
THINKING + *                → THINKING       (no-op)

STREAMING + response_content → STREAMING     extract_changes, edit_message (throttled)
STREAMING + idle_prompt      → DORMANT       finalize (optional ANSI re-render)
STREAMING + tool_menu        → TOOL_PENDING  finalize, send_keyboard
STREAMING + thinking         → THINKING      finalize, send_thinking, start_typing
STREAMING + tool_running     → STREAMING     extract_changes, edit_message
STREAMING + tool_result      → STREAMING     extract_changes, edit_message
STREAMING + error            → STREAMING     extract_changes, edit_message
STREAMING + *                → STREAMING     (no-op)

TOOL_PENDING + tool_running       → STREAMING      (tool approved, resume flow)
TOOL_PENDING + response_content   → STREAMING      extract_changes, edit_or_new_message
TOOL_PENDING + thinking           → THINKING       send_thinking, start_typing
TOOL_PENDING + idle_prompt        → DORMANT        (tool completed without content)
TOOL_PENDING + tool_menu          → TOOL_PENDING   (stale detection — replaces tool_acted flag)
TOOL_PENDING + *                  → TOOL_PENDING   (no-op)
```

### What the Transition Table Eliminates

- **ExtractionMode enum** — extraction strategy is implicit in the action list per transition
- **`_apply_overrides()`** — STARTUP lockout: DORMANT doesn't react to startup observations. `tool_acted` flag: TOOL_PENDING ignores repeated tool_menu observations
- **Scattered `if prev != current` checks** — every transition is explicit
- **StreamingMessage safety nets** — states like "append_content without start_thinking" become unreachable

### ANSI-Only Rendering

Drop the heuristic pipeline. Always render via ANSI attribute-based pipeline.

**Current (two pipelines):**
```
Streaming:  get_changes() → extract_content() → wrap_code_blocks() → reflow_text() → format_html()
Finalize:   get_full_attributed_lines() → filter_response_attr() → classify_regions() → render_regions() → format_html()
```

**Proposed (single pipeline):**
```
Streaming:  get_attributed_changes() → strip_markers() → classify_regions() → render_regions() → format_html()
Finalize:   get_full_attributed_lines() → filter_response_attr() → classify_regions() → render_regions() → format_html()
```

Split `filter_response_attr()` into two functions:
1. **`strip_response_markers()`** — strips ⏺/⎿ markers from attributed spans. Used during streaming on per-line changes.
2. **`filter_response_attr()`** — full prompt-aware filtering for finalization. Calls `strip_response_markers()` internally.

**Why keep a finalization re-render:** During streaming, content arrives line-by-line. `classify_regions()` detects multi-line code blocks by looking at color patterns across adjacent lines. Line-by-line classification may fragment a single code block into multiple regions. The finalization re-render sees the full response at once and produces cleaner region boundaries. But now it's the same pipeline producing a better version, not a different pipeline producing a different representation. Visual change on finalization becomes minor formatting corrections.

**Deleted code:**
- `wrap_code_blocks()` in `formatter.py`
- `render_heuristic()` in `output_pipeline.py`
- `extract_content()` in `ui_patterns.py`
- `ExtractionMode.FAST_IDLE` / `ULTRA_FAST` distinction

### Emulator-Native Dedup (ContentDeduplicator Deletion)

With ANSI-only rendering, change detection shifts to the emulator layer:

1. **During STREAMING:** `get_attributed_changes()` compares current screen against `_prev_display` and returns only lines that changed. No external dedup needed.

2. **On THINKING → DORMANT (fast response):** Extract from `get_full_attributed_lines()` using `filter_response_attr()` which structurally filters out chrome (separators, status bar, prompt). Replaces `snapshot_chrome()` + string-based subtraction.

3. **On STREAMING → DORMANT (finalization):** Re-render from `get_full_attributed_lines()`. Complete replacement of accumulated content. No dedup needed.

4. **On session start:** No pre-seeding needed. The emulator's `_prev_display` starts empty; the first `get_attributed_changes()` will report the startup banner as changes, but `strip_response_markers()` will filter them as non-response content.

**Scroll awareness:** When the terminal scrolls, `get_attributed_changes()` reports shifted lines as "changed" because their row index changed. Fix: in `get_attributed_changes()`, detect scroll events (pyte tracks dirty lines and scroll offset) and exclude lines that merely shifted position without content change.

**Deleted:**
- `ContentDeduplicator` class
- `seed_from_display()`, `snapshot_chrome()`, `clear()`, `filter_new()` calls
- `thinking_snapshot` mechanism

### Global State → Session-Owned State

Move `PipelineState` (renamed from `SessionOutputState`) into `ClaudeSession`:

```python
@dataclass
class ClaudeSession:
    session_id: int
    user_id: int
    project_name: str
    project_path: str
    process: ClaudeProcess
    pipeline: PipelineState     # Formerly in module-level _states registry
    status: str = "active"
    created_at: datetime = field(default_factory=...)
    db_session_id: int = 0
```

`PipelineState` contains: emulator, streaming message, current phase, and any per-session flags.

**Changes:**
- `SessionManager.create_session()` receives `bot` and `edit_rate_limit`, creates `PipelineState` inline
- `cleanup()` → automatic when session is killed (garbage collected)
- `mark_tool_acted()` → phase check (`pipeline.phase == PipelinePhase.TOOL_PENDING`)
- `is_tool_request_pending()` → `session.pipeline.phase == PipelinePhase.TOOL_PENDING`
- `poll_output()` reads pipeline from session object

**Wiring:** `SessionManager.__init__()` receives `bot` (available from `app.bot` in `main.py`). Alternatively, `create_session()` accepts `bot` as parameter.

## Target Module Structure

```
src/
├── parsing/
│   ├── models.py              (~40)   # TerminalView (renamed), ScreenEvent
│   ├── ui_patterns.py         (~200)  # Regex constants + classify_text_line()
│   ├── screen_classifier.py   (~290)  # classify_screen() → ScreenEvent with TerminalView
│   ├── content_classifier.py  (~285)  # classify_regions() + classify_attr_line()
│   ├── terminal_emulator.py   (~400)  # TerminalEmulator (with scroll-aware changes)
│   └── detectors.py           (~480)  # detect_tool_request, etc. (unchanged)
│
├── telegram/
│   ├── pipeline.py            (~300)  # PipelinePhase, transition table, PipelineRunner
│   ├── pipeline_state.py      (~100)  # PipelineState (emulator + streaming + phase)
│   ├── output.py              (~50)   # poll_output() thin loop
│   ├── output_pipeline.py     (~250)  # strip_response_markers(), filter_response_attr(), render_ansi()
│   ├── streaming_message.py   (~200)  # StreamingMessage (simplified, no safety nets)
│   ├── handlers.py            (~170)  # Command handlers
│   ├── callbacks.py           (~220)  # Callback dispatch
│   ├── keyboards.py           (~250)  # Keyboard builders (unchanged)
│   ├── commands.py            (~315)  # Bot commands (unchanged)
│   └── formatter.py           (~400)  # format_html, reflow_text, render_regions
│
├── session_manager.py                  # ClaudeSession now owns PipelineState
├── claude_process.py                   # Unchanged
└── ...
```

**Deleted files:**
- `src/telegram/output_processor.py` → replaced by `pipeline.py`
- `src/telegram/output_state.py` → `ContentDeduplicator` deleted, `SessionOutputState` → `PipelineState` in `pipeline_state.py`

## Data Flow

```
PTY bytes
  → TerminalEmulator.feed()
  → get_display() → classify_screen() → ScreenEvent(view=TerminalView.xxx)
  → PipelineRunner.process(event)
      → lookup transition: (current_phase, event.view) → (next_phase, actions)
      → execute actions:
          extract: get_attributed_changes() → strip_response_markers() → classify_regions() → render → HTML
          send:    StreamingMessage.append_content(html) or .finalize()
      → update phase
  → Telegram Bot API
```

## Migration Strategy

Each step is independently testable and committable:

1. Rename `ScreenState` → `TerminalView` in `parsing/models.py` and all consumers. Pure rename, no logic change.
2. Create `PipelinePhase` enum and `PipelineState` class in `pipeline_state.py`.
3. Create `PipelineRunner` with transition table in `pipeline.py`. Initially wraps existing `SessionProcessor` logic.
4. Move `PipelineState` into `ClaudeSession`, remove `_states` registry.
5. Implement ANSI-only streaming extraction (`get_attributed_changes()` → `strip_response_markers()`).
6. Add scroll-aware change detection to `TerminalEmulator`.
7. Delete `ContentDeduplicator`, `render_heuristic()`, `wrap_code_blocks()`, `extract_content()`.
8. Simplify `StreamingMessage` (remove safety nets).
9. Delete `output_processor.py` and `output_state.py`.
10. Validate against terminal capture test corpus.

## Risks

- **ANSI pipeline coverage**: The ANSI pipeline may not handle all edge cases the heuristic pipeline covers (e.g., content without syntax highlighting). Mitigation: validate against full capture corpus before deleting heuristic fallback.
- **Scroll detection**: pyte's scroll tracking may have edge cases. Mitigation: add scroll-specific test cases with captured terminal sequences.
- **Transition table completeness**: The table may miss edge cases discovered in production. Mitigation: log unexpected (phase, view) pairs at WARNING level; fall back to no-op rather than crashing.
- **Large refactor scope**: Touching ~15 files. Mitigation: each migration step is independently testable and committable; no step depends on a later step.
