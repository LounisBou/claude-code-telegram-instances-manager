# Pipeline Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify the output pipeline's three state machines (ScreenState, StreamingState, ExtractionMode) into a single PipelinePhase with an explicit transition table, drop the heuristic rendering pipeline in favor of ANSI-only, eliminate ContentDeduplicator in favor of emulator-native change tracking, and move session state ownership into ClaudeSession.

**Architecture:** A `PipelineRunner` class processes `(current_phase, terminal_observation) → (next_phase, actions)` transitions via a lookup table. The terminal classifier stays pure (lines in → observation out) but its output type is renamed from `ScreenState` to `TerminalView` to clarify it's an observation, not behavioral state. All rendering uses the ANSI attribute-based pipeline. Per-session state moves from a module-level global registry into `ClaudeSession`.

**Tech Stack:** Python 3.11+, pytest with asyncio_mode="auto", python-telegram-bot, pyte terminal emulator

**Design doc:** `docs/plans/2026-02-13-pipeline-unification-design.md`

---

## Pre-flight

Before starting, verify the baseline:

```bash
python -m pytest --tb=short -q
```

Expected: 805 tests, with known failures:
- 13 PTY allocation failures (sandbox)
- 2 TestBuildApp failures (SOCKS proxy)

All other tests must pass. If additional tests fail, investigate before proceeding.

---

## Phase 1: Rename ScreenState → TerminalView

Pure rename across the codebase. No logic changes. This establishes the conceptual separation between "observation" and "state."

### Task 1.1: Rename the enum in models.py

**Files:**
- Modify: `src/parsing/models.py`

**Step 1: Rename the class**

In `src/parsing/models.py`, rename `class ScreenState(Enum)` → `class TerminalView(Enum)`. Keep `ScreenEvent` unchanged but update its `state` field type annotation to `TerminalView`.

```python
class TerminalView(Enum):
    """Possible observations of the Claude Code terminal screen."""
    STARTUP = "startup"
    IDLE = "idle"
    THINKING = "thinking"
    STREAMING = "streaming"
    USER_MESSAGE = "user_message"
    TOOL_REQUEST = "tool_request"
    TOOL_RUNNING = "tool_running"
    TOOL_RESULT = "tool_result"
    BACKGROUND_TASK = "background_task"
    PARALLEL_AGENTS = "parallel_agents"
    TODO_LIST = "todo_list"
    AUTH_REQUIRED = "auth_required"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ScreenEvent:
    """Classified screen observation with extracted payload and raw lines."""
    state: TerminalView
    payload: dict = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)
```

Also add a backward-compatible alias at the bottom of the file:

```python
# Backward-compatible alias — will be removed at end of migration
ScreenState = TerminalView
```

**Step 2: Run tests**

```bash
python -m pytest --tb=short -q
```

Expected: All tests pass (alias keeps backward compat).

**Step 3: Commit**

```bash
git add src/parsing/models.py
git commit -m 'refactor: rename ScreenState → TerminalView in models.py (with alias)'
```

### Task 1.2: Update all consumers to use TerminalView

**Files:**
- Modify: `src/parsing/ui_patterns.py` (re-export)
- Modify: `src/parsing/__init__.py` (re-export)
- Modify: `src/parsing/screen_classifier.py` (imports + all ScreenState.X references)
- Modify: `src/telegram/output_state.py`
- Modify: `src/telegram/output_processor.py`
- Modify: `scripts/validate_classifier.py`
- Modify: All test files that import ScreenState

**Step 1: Update all imports and references**

Use find-and-replace across all `.py` files (not docs):
1. `ScreenState` → `TerminalView` in all import statements
2. `ScreenState.` → `TerminalView.` in all enum member access
3. Keep `ScreenEvent` unchanged

Key files to update (each has `ScreenState` references):
- `src/parsing/ui_patterns.py:6` — re-export line
- `src/parsing/__init__.py:3` — re-export line
- `src/parsing/screen_classifier.py` — 17 occurrences of `ScreenState.`
- `src/telegram/output_state.py` — 2 occurrences
- `src/telegram/output_processor.py` — 25 occurrences
- `scripts/validate_classifier.py` — 1 occurrence
- `tests/parsing/test_screen_classifier.py` — 32 occurrences
- `tests/parsing/test_ui_patterns.py` — 17 occurrences
- `tests/telegram/test_output_state.py` — 4 occurrences
- `tests/telegram/test_output_processor.py` — 44 occurrences
- `tests/telegram/test_output.py` — many occurrences

**Step 2: Remove the backward-compat alias from models.py**

Delete the `ScreenState = TerminalView` line from `src/parsing/models.py`.

**Step 3: Run tests**

```bash
python -m pytest --tb=short -q
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add -u
git commit -m 'refactor: update all consumers to TerminalView, remove ScreenState alias'
```

---

## Phase 2: Create PipelinePhase and PipelineState

New types that will become the core of the unified state machine.

### Task 2.1: Create pipeline_state.py with tests

**Files:**
- Create: `src/telegram/pipeline_state.py`
- Create: `tests/telegram/test_pipeline_state.py`

**Step 1: Write the failing tests**

```python
# tests/telegram/test_pipeline_state.py
"""Tests for PipelinePhase and PipelineState."""

from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock

from src.telegram.pipeline_state import PipelinePhase, PipelineState


class TestPipelinePhase:
    def test_dormant_exists(self):
        assert PipelinePhase.DORMANT.value == "dormant"

    def test_thinking_exists(self):
        assert PipelinePhase.THINKING.value == "thinking"

    def test_streaming_exists(self):
        assert PipelinePhase.STREAMING.value == "streaming"

    def test_tool_pending_exists(self):
        assert PipelinePhase.TOOL_PENDING.value == "tool_pending"


class TestPipelineState:
    def test_initial_phase_is_dormant(self):
        emu = MagicMock()
        streaming = MagicMock()
        ps = PipelineState(emulator=emu, streaming=streaming)
        assert ps.phase == PipelinePhase.DORMANT

    def test_has_emulator(self):
        emu = MagicMock()
        ps = PipelineState(emulator=emu, streaming=MagicMock())
        assert ps.emulator is emu

    def test_has_streaming(self):
        sm = MagicMock()
        ps = PipelineState(emulator=MagicMock(), streaming=sm)
        assert ps.streaming is sm

    def test_prev_view_is_none(self):
        ps = PipelineState(emulator=MagicMock(), streaming=MagicMock())
        assert ps.prev_view is None
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/telegram/test_pipeline_state.py -v
```

Expected: ImportError — module does not exist.

**Step 3: Write the implementation**

```python
# src/telegram/pipeline_state.py
"""Pipeline phase and per-session state for the output pipeline.

- :class:`PipelinePhase` — the behavioral state of the bot for one session.
- :class:`PipelineState` — all per-session state: emulator, streaming
  message, current phase, and previous terminal view.
"""

from __future__ import annotations
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.parsing.terminal_emulator import TerminalEmulator
    from src.parsing.models import TerminalView
    from src.telegram.streaming_message import StreamingMessage


class PipelinePhase(Enum):
    """Behavioral state of the output pipeline for one session.

    Values:
        DORMANT: Idle, no pending Telegram message.
        THINKING: "Thinking..." placeholder sent, typing indicator active.
        STREAMING: Content flowing, editing message in place.
        TOOL_PENDING: Tool approval keyboard sent, waiting for user action.
    """
    DORMANT = "dormant"
    THINKING = "thinking"
    STREAMING = "streaming"
    TOOL_PENDING = "tool_pending"


class PipelineState:
    """All per-session state for the output processing pipeline."""

    def __init__(
        self,
        emulator: TerminalEmulator,
        streaming: StreamingMessage,
    ) -> None:
        self.emulator = emulator
        self.streaming = streaming
        self.phase: PipelinePhase = PipelinePhase.DORMANT
        self.prev_view: TerminalView | None = None
```

**Step 4: Run tests to verify they pass**

```bash
python -m pytest tests/telegram/test_pipeline_state.py -v
```

Expected: All pass.

**Step 5: Commit**

```bash
git add src/telegram/pipeline_state.py tests/telegram/test_pipeline_state.py
git commit -m 'feat: add PipelinePhase enum and PipelineState class'
```

---

## Phase 3: Create PipelineRunner with transition table

The core of the refactoring. This creates the unified state machine that will replace `SessionProcessor`.

### Task 3.1: Write transition table tests

**Files:**
- Create: `tests/telegram/test_pipeline_runner.py`

**Step 1: Write tests for every transition row from the design doc**

Write one test per transition from the design doc's transition table. Each test creates a `PipelineRunner` at a given phase, feeds it a `ScreenEvent` with a specific `TerminalView`, and asserts:
1. The new phase is correct
2. The expected actions were called on the mocked bot/streaming/emulator

The test file should use a helper to create a runner with mocked dependencies:

```python
# tests/telegram/test_pipeline_runner.py
"""Tests for PipelineRunner transition table."""

from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.parsing.models import ScreenEvent, TerminalView
from src.telegram.pipeline_state import PipelinePhase, PipelineState
from src.telegram.pipeline_runner import PipelineRunner


def _make_pipeline_state(phase: PipelinePhase = PipelinePhase.DORMANT):
    emu = MagicMock()
    emu.get_display.return_value = [""] * 40
    emu.get_attributed_changes.return_value = []
    emu.get_full_display.return_value = [""] * 40
    emu.get_full_attributed_lines.return_value = [[] for _ in range(40)]
    streaming = AsyncMock()
    streaming.accumulated = ""
    ps = PipelineState(emulator=emu, streaming=streaming)
    ps.phase = phase
    return ps


def _make_runner(
    phase: PipelinePhase = PipelinePhase.DORMANT,
    user_id: int = 1,
    session_id: int = 2,
):
    ps = _make_pipeline_state(phase)
    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=42)
    sm = AsyncMock()
    runner = PipelineRunner(
        state=ps, user_id=user_id, session_id=session_id,
        bot=bot, session_manager=sm,
    )
    return runner, ps, bot, sm


def _event(view: TerminalView, **payload) -> ScreenEvent:
    return ScreenEvent(state=view, payload=payload, raw_lines=[])


class TestDormantTransitions:
    @pytest.mark.asyncio
    async def test_dormant_thinking_goes_to_thinking(self):
        runner, ps, bot, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.THINKING, text="Thinking..."))
        assert ps.phase == PipelinePhase.THINKING

    @pytest.mark.asyncio
    async def test_dormant_thinking_sends_thinking_message(self):
        runner, ps, bot, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.THINKING, text="Thinking..."))
        ps.streaming.start_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_streaming_goes_to_streaming(self):
        runner, ps, bot, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.STREAMING, text="Hello"))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_dormant_tool_menu_goes_to_tool_pending(self):
        runner, ps, bot, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(
            TerminalView.TOOL_REQUEST,
            question="Allow?", options=["Yes", "No"], selected=0,
        ))
        assert ps.phase == PipelinePhase.TOOL_PENDING

    @pytest.mark.asyncio
    async def test_dormant_tool_menu_sends_keyboard(self):
        runner, ps, bot, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(
            TerminalView.TOOL_REQUEST,
            question="Allow?", options=["Yes", "No"], selected=0,
        ))
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_auth_required_kills_session(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.AUTH_REQUIRED, url="https://..."))
        sm.kill_session.assert_called_once_with(1, 2)
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_idle_stays_dormant(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.IDLE, placeholder=""))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_unknown_stays_dormant(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.UNKNOWN))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_startup_stays_dormant(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.STARTUP))
        assert ps.phase == PipelinePhase.DORMANT


class TestThinkingTransitions:
    @pytest.mark.asyncio
    async def test_thinking_streaming_goes_to_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.STREAMING, text="Content"))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_thinking_idle_goes_to_dormant(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.IDLE, placeholder=""))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_thinking_idle_finalizes(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.IDLE, placeholder=""))
        ps.streaming.finalize.assert_called()

    @pytest.mark.asyncio
    async def test_thinking_tool_menu_goes_to_tool_pending(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(
            TerminalView.TOOL_REQUEST,
            question="Allow?", options=["Yes", "No"], selected=0,
        ))
        assert ps.phase == PipelinePhase.TOOL_PENDING

    @pytest.mark.asyncio
    async def test_thinking_thinking_stays_thinking(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.THINKING, text="Still..."))
        assert ps.phase == PipelinePhase.THINKING


class TestStreamingTransitions:
    @pytest.mark.asyncio
    async def test_streaming_streaming_stays_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.STREAMING, text="More"))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_idle_goes_to_dormant(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.IDLE, placeholder=""))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_streaming_idle_finalizes(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.IDLE, placeholder=""))
        ps.streaming.finalize.assert_called()

    @pytest.mark.asyncio
    async def test_streaming_tool_menu_goes_to_tool_pending(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(
            TerminalView.TOOL_REQUEST,
            question="Allow?", options=["Yes", "No"], selected=0,
        ))
        assert ps.phase == PipelinePhase.TOOL_PENDING

    @pytest.mark.asyncio
    async def test_streaming_thinking_goes_to_thinking(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.THINKING, text="Rethinking..."))
        assert ps.phase == PipelinePhase.THINKING

    @pytest.mark.asyncio
    async def test_streaming_tool_running_stays_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.TOOL_RUNNING, tool="Bash"))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_tool_result_stays_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.TOOL_RESULT, added=4, removed=1))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_error_stays_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.ERROR, text="MCP failed"))
        assert ps.phase == PipelinePhase.STREAMING


class TestToolPendingTransitions:
    @pytest.mark.asyncio
    async def test_tool_pending_tool_running_goes_to_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.TOOL_RUNNING, tool="Bash"))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_tool_pending_streaming_goes_to_streaming(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.STREAMING, text="Result"))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_tool_pending_thinking_goes_to_thinking(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.THINKING, text="Processing..."))
        assert ps.phase == PipelinePhase.THINKING

    @pytest.mark.asyncio
    async def test_tool_pending_idle_goes_to_dormant(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.IDLE, placeholder=""))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_tool_pending_tool_menu_stays_tool_pending(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(
            TerminalView.TOOL_REQUEST,
            question="Allow?", options=["Yes", "No"], selected=0,
        ))
        assert ps.phase == PipelinePhase.TOOL_PENDING

    @pytest.mark.asyncio
    async def test_tool_pending_unknown_stays_tool_pending(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.UNKNOWN))
        assert ps.phase == PipelinePhase.TOOL_PENDING
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/telegram/test_pipeline_runner.py -v
```

Expected: ImportError — `pipeline_runner` module does not exist.

### Task 3.2: Implement PipelineRunner

**Files:**
- Create: `src/telegram/pipeline_runner.py`

**Step 1: Implement the runner**

Create `src/telegram/pipeline_runner.py` implementing the `PipelineRunner` class with:
- A `process(event: ScreenEvent)` method that looks up `(self.state.phase, event.state)` in the transition table
- Action methods: `_send_thinking()`, `_send_keyboard()`, `_extract_and_send()`, `_finalize()`, `_send_auth_warning()`
- Logging of transitions at DEBUG level
- Logging of unexpected (phase, view) pairs at WARNING level (falling back to no-op)

The runner receives: `PipelineState`, `user_id`, `session_id`, `bot`, `session_manager`.

For the initial implementation, action methods can be stubs or thin wrappers that call `StreamingMessage` methods. The rendering pipeline integration (ANSI extraction) comes in Phase 5.

**Step 2: Run tests**

```bash
python -m pytest tests/telegram/test_pipeline_runner.py -v
```

Expected: All pass.

**Step 3: Commit**

```bash
git add src/telegram/pipeline_runner.py tests/telegram/test_pipeline_runner.py
git commit -m 'feat: add PipelineRunner with transition table and tests'
```

---

## Phase 4: Move PipelineState into ClaudeSession

Eliminate the global `_states` registry.

### Task 4.1: Add pipeline field to ClaudeSession

**Files:**
- Modify: `src/session_manager.py`
- Modify: `tests/test_session_manager.py`

**Step 1: Write test for pipeline attribute on ClaudeSession**

Add to `tests/test_session_manager.py`:

```python
class TestClaudeSessionPipeline:
    def test_session_has_pipeline_attribute(self):
        from src.telegram.pipeline_state import PipelinePhase, PipelineState
        ps = MagicMock(spec=PipelineState)
        session = ClaudeSession(
            session_id=1, user_id=111, project_name="proj",
            project_path="/a", process=MagicMock(), pipeline=ps,
        )
        assert session.pipeline is ps
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_session_manager.py::TestClaudeSessionPipeline -v
```

Expected: TypeError — `pipeline` is not a recognized field.

**Step 3: Add pipeline field to ClaudeSession**

In `src/session_manager.py`, add `pipeline` to `ClaudeSession` dataclass:

```python
@dataclass
class ClaudeSession:
    session_id: int
    user_id: int
    project_name: str
    project_path: str
    process: ClaudeProcess
    pipeline: PipelineState | None = None  # None during transition period
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    db_session_id: int = 0
```

Add import: `from src.telegram.pipeline_state import PipelineState`

**Step 4: Update SessionManager.create_session() to accept bot and create PipelineState**

Add `bot` and `edit_rate_limit` parameters to `SessionManager.__init__()`:

```python
def __init__(self, ..., bot=None, edit_rate_limit: int = 3) -> None:
    ...
    self._bot = bot
    self._edit_rate_limit = edit_rate_limit
```

In `create_session()`, create and assign `PipelineState`:

```python
from src.parsing.terminal_emulator import TerminalEmulator
from src.telegram.streaming_message import StreamingMessage

pipeline = PipelineState(
    emulator=TerminalEmulator(),
    streaming=StreamingMessage(bot=self._bot, chat_id=user_id, edit_rate_limit=self._edit_rate_limit),
) if self._bot else None
session = ClaudeSession(..., pipeline=pipeline)
```

**Step 5: Update main.py to pass bot to SessionManager**

In `src/main.py`, the `build_app()` function creates `SessionManager` before `app` is fully built, so `app.bot` isn't available yet. Instead, defer pipeline creation: set `bot=None` at construction and pass `bot` via a setter or parameter later.

Alternative: Pass `bot` in `_on_startup()` after `app.initialize()`:

```python
async def _on_startup(app: Application) -> None:
    ...
    session_manager = app.bot_data["session_manager"]
    session_manager.set_bot(app.bot, config.telegram.edit_rate_limit)
```

Add `set_bot()` method to `SessionManager`.

**Step 6: Run all tests**

```bash
python -m pytest --tb=short -q
```

Expected: All pass. Existing tests don't pass `bot` to `SessionManager`, so `pipeline` will be `None` in test fixtures — that's fine for now.

**Step 7: Commit**

```bash
git add src/session_manager.py src/main.py tests/test_session_manager.py
git commit -m 'feat: add PipelineState to ClaudeSession, pass bot via set_bot()'
```

### Task 4.2: Wire poll_output to use session.pipeline instead of _states registry

**Files:**
- Modify: `src/telegram/output.py`
- Modify: `tests/telegram/test_output.py`

**Step 1: Update poll_output() to read pipeline from session**

In `src/telegram/output.py`, replace `get_or_create()` with `session.pipeline`:

```python
async def poll_output(bot, session_manager, *, edit_rate_limit=3):
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
                try:
                    if session.pipeline is None:
                        continue
                    # ... use session.pipeline instead of get_or_create()
```

For now, keep the old `SessionProcessor` path working alongside the new pipeline. The actual switchover to `PipelineRunner` happens in a later phase.

**Step 2: Update handlers that use is_tool_request_pending and mark_tool_acted**

In `src/telegram/handlers.py` and `src/telegram/callbacks.py`, replace:
- `is_tool_request_pending(user_id, session_id)` → check `session.pipeline.phase == PipelinePhase.TOOL_PENDING`
- `mark_tool_acted(user_id, session_id)` → no longer needed (TOOL_PENDING phase handles stale detection)

**Step 3: Run all tests**

```bash
python -m pytest --tb=short -q
```

Expected: All pass.

**Step 4: Commit**

```bash
git add -u
git commit -m 'refactor: wire poll_output and handlers to session.pipeline'
```

### Task 4.3: Remove the _states global registry

**Files:**
- Modify: `src/telegram/output_state.py` — delete `_states`, `get_or_create()`, `cleanup()`, `mark_tool_acted()`, `is_tool_request_pending()`
- Modify: `src/session_manager.py` — remove `_cleanup_output_state` import and call
- Update: Tests that used the registry functions

**Step 1: Remove registry functions and update tests**

Delete `_states`, `get_or_create`, `cleanup`, `mark_tool_acted`, `is_tool_request_pending` from `output_state.py`. Update or delete the corresponding tests in `test_output_state.py`.

**Step 2: Run all tests**

```bash
python -m pytest --tb=short -q
```

Expected: All pass.

**Step 3: Commit**

```bash
git add -u
git commit -m 'refactor: remove _states global registry, session owns pipeline state'
```

---

## Phase 5: ANSI-only streaming extraction

Replace the heuristic rendering pipeline with ANSI attribute-based rendering everywhere.

### Task 5.1: Create strip_response_markers() function

**Files:**
- Modify: `src/telegram/output_pipeline.py`
- Modify: `tests/telegram/test_output_pipeline.py`

**Step 1: Write tests for strip_response_markers()**

`strip_response_markers()` takes a list of attributed lines (each line is `list[CharSpan]`) and strips ⏺/⎿ markers, similar to `filter_response_attr()` but without prompt-aware filtering. It's used during streaming on per-line changes.

```python
class TestStripResponseMarkers:
    def test_strips_response_marker(self):
        lines = [[_span("⏺ Hello", fg="default")]]
        result = strip_response_markers(lines)
        text = "".join(s.text for s in result[0])
        assert "⏺" not in text
        assert "Hello" in text

    def test_strips_tool_connector(self):
        lines = [[_span("  ⎿ Output", fg="default")]]
        result = strip_response_markers(lines)
        text = "".join(s.text for s in result[0])
        assert "⎿" not in text

    def test_preserves_plain_content(self):
        lines = [[_span("Just text", fg="default")]]
        result = strip_response_markers(lines)
        assert result[0][0].text == "Just text"

    def test_filters_chrome_lines(self):
        lines = [
            [_span("─" * 60)],                      # separator — chrome
            [_span("⏺ Real content", fg="default")], # response — kept
            [_span("─" * 60)],                       # separator — chrome
        ]
        result = strip_response_markers(lines)
        assert len(result) == 1  # only the content line
```

**Step 2: Implement strip_response_markers()**

In `src/telegram/output_pipeline.py`, add a function that:
1. Iterates attributed lines
2. Classifies the plain-text version via `classify_text_line()`
3. Keeps only `content`, `response`, `tool_connector` lines
4. Strips markers from response/tool_connector lines via existing `strip_marker_from_spans()`
5. Returns filtered, marker-stripped attributed lines

**Step 3: Run tests**

```bash
python -m pytest tests/telegram/test_output_pipeline.py -v
```

Expected: All pass.

**Step 4: Commit**

```bash
git add src/telegram/output_pipeline.py tests/telegram/test_output_pipeline.py
git commit -m 'feat: add strip_response_markers() for streaming ANSI extraction'
```

### Task 5.2: Wire ANSI rendering into PipelineRunner actions

**Files:**
- Modify: `src/telegram/pipeline_runner.py`
- Modify: `tests/telegram/test_pipeline_runner.py`

**Step 1: Implement extraction actions in PipelineRunner**

The `_extract_and_send()` action in `PipelineRunner` should:
1. Call `emu.get_attributed_changes()` to get delta lines with attributes
2. Call `strip_response_markers()` to filter and clean
3. Call `classify_regions()` → `render_regions()` → `format_html()` → `reflow_text()`
4. Call `streaming.append_content(html)`

The `_finalize()` action should:
1. Call `emu.get_full_attributed_lines()` + `filter_response_attr()` for full re-render
2. Call `streaming.replace_content(html)` then `streaming.finalize()`
3. Call `emu.clear_history()`

**Step 2: Run tests**

```bash
python -m pytest tests/telegram/test_pipeline_runner.py -v
```

Expected: All pass.

**Step 3: Commit**

```bash
git add -u
git commit -m 'feat: wire ANSI rendering into PipelineRunner extraction actions'
```

---

## Phase 6: Scroll-aware change detection

Prevent false "changed" reports when terminal content scrolls.

### Task 6.1: Add scroll-aware logic to get_attributed_changes()

**Files:**
- Modify: `src/parsing/terminal_emulator.py`
- Modify: `tests/parsing/test_terminal_emulator.py`

**Step 1: Write test for scroll detection**

```python
class TestScrollAwareChanges:
    def test_scroll_does_not_report_shifted_lines_as_changed(self):
        emu = TerminalEmulator(rows=5, cols=20)
        # Fill screen
        emu.feed("line1\r\nline2\r\nline3\r\nline4\r\nline5\r\n")
        _ = emu.get_changes()  # snapshot current state

        # Add a new line that pushes content up (scroll)
        emu.feed("line6\r\n")
        changes = emu.get_changes()

        # Only "line6" is new — the shifted lines should not appear
        assert any("line6" in c for c in changes)
        # Shifted lines that just moved up should ideally be filtered
        # (This is the behavior we want to achieve)
```

**Step 2: Implement scroll-aware change detection**

In `TerminalEmulator.get_changes()` and `get_attributed_changes()`, track scroll offset:
- After comparing current vs previous display, check if a "changed" line's content matches a line that was at `row - scroll_offset` in the previous display
- If so, exclude it from changes (it's just shifted, not new)

pyte's `HistoryScreen` has a `dirty` set that tracks which rows were actually modified. Use this as a hint for scroll detection.

**Step 3: Run tests**

```bash
python -m pytest tests/parsing/test_terminal_emulator.py -v
```

Expected: All pass.

**Step 4: Commit**

```bash
git add src/parsing/terminal_emulator.py tests/parsing/test_terminal_emulator.py
git commit -m 'feat: scroll-aware change detection in TerminalEmulator'
```

---

## Phase 7: Switch poll_output to PipelineRunner

Replace `SessionProcessor` with `PipelineRunner` in the main loop.

### Task 7.1: Update poll_output to use PipelineRunner

**Files:**
- Modify: `src/telegram/output.py`
- Modify: `tests/telegram/test_output.py`

**Step 1: Replace SessionProcessor with PipelineRunner in poll_output()**

```python
from src.telegram.pipeline_runner import PipelineRunner
from src.parsing.screen_classifier import classify_screen_state

async def poll_output(bot, session_manager, *, edit_rate_limit=3):
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
                try:
                    pipeline = session.pipeline
                    if pipeline is None:
                        continue

                    raw = session.process.read_available()
                    if not raw:
                        continue

                    pipeline.emulator.feed(raw)
                    display = pipeline.emulator.get_display()
                    event = classify_screen_state(display, pipeline.prev_view)

                    runner = PipelineRunner(
                        state=pipeline, user_id=user_id, session_id=sid,
                        bot=bot, session_manager=session_manager,
                    )
                    await runner.process(event)

                    pipeline.prev_view = event.state

                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("poll_output crash user=%d sid=%d", user_id, sid)
```

**Step 2: Update tests to match new flow**

Update `tests/telegram/test_output.py` to use `PipelineRunner` patterns.

**Step 3: Run all tests**

```bash
python -m pytest --tb=short -q
```

Expected: All pass.

**Step 4: Commit**

```bash
git add -u
git commit -m 'refactor: switch poll_output from SessionProcessor to PipelineRunner'
```

---

## Phase 8: Delete dead code

Remove all the old code that's been replaced.

### Task 8.1: Delete ContentDeduplicator

**Files:**
- Modify: `src/telegram/output_state.py` — delete `ContentDeduplicator` class
- Delete: `tests/telegram/test_content_deduplicator.py`

**Step 1: Remove the class and tests**

Remove `ContentDeduplicator` from `output_state.py`. Delete the entire test file. Update any remaining imports.

**Step 2: Run all tests**

```bash
python -m pytest --tb=short -q
```

**Step 3: Commit**

```bash
git add -u
git commit -m 'refactor: delete ContentDeduplicator (replaced by emulator change tracking)'
```

### Task 8.2: Delete heuristic rendering pipeline

**Files:**
- Modify: `src/telegram/output_pipeline.py` — delete `render_heuristic()`
- Modify: `src/telegram/formatter.py` — delete `wrap_code_blocks()`, `_CODE_FIRST_LINE_RE`
- Modify: `src/parsing/ui_patterns.py` — delete `extract_content()`
- Update: Test files that reference deleted functions

**Step 1: Remove the functions**

Delete `render_heuristic()` from `output_pipeline.py`. Delete `wrap_code_blocks()` and `_CODE_FIRST_LINE_RE` from `formatter.py`. Delete `extract_content()` from `ui_patterns.py`. Update or delete corresponding test cases.

**Step 2: Run all tests**

```bash
python -m pytest --tb=short -q
```

**Step 3: Commit**

```bash
git add -u
git commit -m 'refactor: delete heuristic rendering pipeline (ANSI-only now)'
```

### Task 8.3: Delete SessionProcessor and ExtractionMode

**Files:**
- Delete: `src/telegram/output_processor.py`
- Delete: `tests/telegram/test_output_processor.py`
- Modify: `src/telegram/output_state.py` — if only `SessionOutputState` remains, delete the file entirely (replaced by `pipeline_state.py`)

**Step 1: Remove the files**

Delete `output_processor.py` and its test file. If `output_state.py` has no remaining useful code, delete it too. Update any remaining imports.

**Step 2: Run all tests**

```bash
python -m pytest --tb=short -q
```

**Step 3: Commit**

```bash
git add -u
git commit -m 'refactor: delete SessionProcessor, ExtractionMode, output_state.py'
```

### Task 8.4: Simplify StreamingMessage

**Files:**
- Modify: `src/telegram/streaming_message.py`
- Modify: `tests/telegram/test_streaming_message.py`

**Step 1: Remove safety nets that are now unreachable**

In `streaming_message.py`:
- In `start_thinking()`: Remove the `if self.state == StreamingState.STREAMING` safety net (PipelineRunner handles phase correctly)
- In `append_content()`: Remove the `if self.state == StreamingState.IDLE or self.message_id is None` safety net

Keep `StreamingState` enum for internal use by `StreamingMessage` but it's no longer consulted by external code.

**Step 2: Update tests that tested safety net behavior**

Remove or update tests that tested the safety net paths.

**Step 3: Run all tests**

```bash
python -m pytest --tb=short -q
```

**Step 4: Commit**

```bash
git add -u
git commit -m 'refactor: simplify StreamingMessage, remove safety nets'
```

---

## Phase 9: Update handlers for PipelinePhase

### Task 9.1: Update is_tool_request_pending checks

**Files:**
- Modify: `src/telegram/handlers.py`
- Modify: `src/telegram/callbacks.py`
- Modify: `tests/telegram/test_handlers.py`

**Step 1: Replace is_tool_request_pending with phase check**

In `handlers.py`, replace:
```python
if is_tool_request_pending(user_id, active.session_id):
```
with:
```python
if active.pipeline and active.pipeline.phase == PipelinePhase.TOOL_PENDING:
```

Do the same in `callbacks.py`.

**Step 2: Run all tests**

```bash
python -m pytest --tb=short -q
```

**Step 3: Commit**

```bash
git add -u
git commit -m 'refactor: replace is_tool_request_pending with PipelinePhase check'
```

---

## Phase 10: Validate and clean up

### Task 10.1: Run full test suite

```bash
python -m pytest --tb=short -q
python -m pytest --cov=src --cov-report=term-missing
```

Verify:
- No new test failures beyond the known 13 PTY + 2 SOCKS proxy failures
- Coverage stays at or above 90%

### Task 10.2: Validate against terminal capture corpus

```bash
python scripts/validate_classifier.py
```

Verify: Zero UNKNOWN classifications across all captured states.

### Task 10.3: Update CLAUDE.md architecture description

**Files:**
- Modify: `CLAUDE.md`

Update the architecture section to reflect:
- `PipelinePhase` replaces `ScreenState` + `StreamingState` + `ExtractionMode`
- `TerminalView` is the observation type (pure classifier output)
- ANSI-only rendering pipeline
- Session-owned `PipelineState` (no global registry)

### Task 10.4: Final commit

```bash
git add -u
git commit -m 'docs: update CLAUDE.md for pipeline unification architecture'
```
