"""Background loop that reads Claude output and streams it to Telegram.

Thin orchestration loop using :class:`~src.telegram.output_processor.SessionProcessor`
for the actual event processing.  Each poll cycle (300ms) reads raw PTY bytes
from all active sessions and delegates to the processor's 3-phase pipeline:

1. Pre-extraction — state entry side effects (typing indicator, dedup, auth)
2. Extraction — content dedup, render, send to Telegram
3. Finalization — ANSI re-render, clear history, finalize message (IDLE only)
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from src.telegram.output_processor import SessionProcessor
from src.telegram.output_state import (
    cleanup,  # noqa: F401 — re-exported for session cleanup
    get_or_create,
    is_tool_request_pending as _is_pending_impl,
    mark_tool_acted as _mark_tool_acted_impl,
)

# Re-exports consumed only by test_output.py (will be removed in Phase 7b).
from src.parsing.models import ScreenEvent, ScreenState  # noqa: F401
from src.parsing.ui_patterns import CHROME_CATEGORIES as _CHROME_CATEGORIES  # noqa: F401
from src.telegram.output_pipeline import (  # noqa: F401
    dedent_attr_lines as _dedent_attr_lines,
    filter_response_attr as _filter_response_attr,
    find_last_prompt as _find_last_prompt,
    lstrip_n_chars as _lstrip_n_chars,
    strip_marker_from_spans as _strip_marker_from_spans,
)
from src.telegram.streaming_message import StreamingMessage, StreamingState  # noqa: F401

logger = logging.getLogger(__name__)

# Backward-compat: _CONTENT_STATES used by test_output.py as ScreenState set
_CONTENT_STATES = {
    ScreenState.STREAMING,
    ScreenState.TOOL_RUNNING,
    ScreenState.TOOL_RESULT,
    ScreenState.ERROR,
    ScreenState.TODO_LIST,
    ScreenState.PARALLEL_AGENTS,
    ScreenState.BACKGROUND_TASK,
}

# Backward-compat: module-level dicts for test_output.py direct manipulation.
# The real state lives in output_state._states; these dicts are populated
# from SessionOutputState on each poll cycle for test compatibility.
from src.parsing.terminal_emulator import TerminalEmulator  # noqa: F401, E402
_session_emulators: dict[tuple[int, int], TerminalEmulator] = {}
_session_streaming: dict[tuple[int, int], StreamingMessage] = {}
_session_prev_state: dict[tuple[int, int], ScreenState] = {}
_session_sent_lines: dict[tuple[int, int], set[str]] = {}
_session_thinking_snapshot: dict[tuple[int, int], set[str]] = {}
_session_tool_acted: dict[tuple[int, int], bool] = {}


def is_tool_request_pending(user_id: int, session_id: int) -> bool:
    """Check whether the session is currently showing a tool approval menu.

    Checks real SessionOutputState first.  Falls back to compat dicts
    for tests that set ``_session_prev_state`` / ``_session_tool_acted``
    directly (without a real state entry in output_state._states).
    The two paths cannot contradict because :func:`mark_tool_acted`
    updates both atomically.
    """
    if _is_pending_impl(user_id, session_id):
        return True
    # Fallback for tests that bypass real state
    key = (user_id, session_id)
    if _session_tool_acted.get(key):
        return False
    return _session_prev_state.get(key) == ScreenState.TOOL_REQUEST


def mark_tool_acted(user_id: int, session_id: int) -> None:
    """Signal that a tool approval callback was processed.

    Wrapper that updates both the real SessionOutputState and the
    backward-compat module-level dict.
    """
    _mark_tool_acted_impl(user_id, session_id)
    _session_tool_acted[(user_id, session_id)] = True


def _sync_compat_dicts(
    user_id: int, session_id: int, state,
) -> None:
    """Sync backward-compat module-level dicts from SessionOutputState.

    This allows test_output.py to manipulate session state directly
    via the module-level dicts while the real state lives in output_state.
    Will be removed after test migration (Phase 7b).
    """
    key = (user_id, session_id)
    _session_emulators[key] = state.emulator
    _session_streaming[key] = state.streaming
    _session_prev_state[key] = state.prev_state
    _session_sent_lines[key] = state.dedup.sent_lines
    _session_thinking_snapshot[key] = state.dedup.thinking_snapshot
    _session_tool_acted[key] = state.tool_acted


def _read_compat_dicts(
    user_id: int, session_id: int, state,
) -> None:
    """Read backward-compat dicts back into SessionOutputState.

    Tests may mutate the module-level dicts; propagate changes back.
    """
    key = (user_id, session_id)
    if key in _session_emulators:
        state.emulator = _session_emulators[key]
    if key in _session_streaming:
        state.streaming = _session_streaming[key]
    if key in _session_prev_state:
        state.prev_state = _session_prev_state[key]
    if key in _session_sent_lines:
        state.dedup.sent_lines = _session_sent_lines[key]
    if key in _session_thinking_snapshot:
        state.dedup.thinking_snapshot = _session_thinking_snapshot[key]
    if key in _session_tool_acted:
        state.tool_acted = _session_tool_acted[key]


async def poll_output(
    bot: Bot, session_manager, *, edit_rate_limit: int = 3,
) -> None:
    """Background loop that reads Claude output and streams it to Telegram.

    Creates a :class:`SessionProcessor` per session and delegates each
    poll cycle to its ``process_cycle`` method.

    Args:
        bot: Telegram Bot instance for sending messages.
        session_manager: SessionManager with active sessions.
        edit_rate_limit: Maximum Telegram edit_message calls per second.
    """
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
              try:
                state = get_or_create(
                    user_id, sid, bot, edit_rate_limit,
                )

                # Sync compat dicts so tests that mutate them are respected
                _read_compat_dicts(user_id, sid, state)

                raw = session.process.read_available()
                if not raw:
                    # Still sync state for tests even with no data
                    _sync_compat_dicts(user_id, sid, state)
                    continue

                processor = SessionProcessor(
                    state=state,
                    user_id=user_id,
                    session_id=sid,
                    bot=bot,
                    session_manager=session_manager,
                )
                await processor.process_cycle(raw)

                # Sync back to compat dicts after processing
                _sync_compat_dicts(user_id, sid, state)

              except asyncio.CancelledError:
                raise
              except Exception:
                logger.exception(
                    "poll_output crash for user=%d sid=%d — will retry next cycle",
                    user_id, sid,
                )
