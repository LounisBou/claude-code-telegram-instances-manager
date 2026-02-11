from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from src.core.log_setup import TRACE
from src.parsing.screen_classifier import classify_screen_state
from src.telegram.formatter import reflow_text, split_message
from src.parsing.terminal_emulator import TerminalEmulator
from src.parsing.ui_patterns import ScreenEvent, ScreenState, extract_content
from src.session_manager import OutputBuffer

logger = logging.getLogger(__name__)


# States that produce user-visible output sent to Telegram.
# STARTUP, IDLE, USER_MESSAGE, UNKNOWN, and THINKING are suppressed:
# they are UI chrome or transient states with no extractable content.
# THINKING gets a one-time "_Thinking..._" notification instead.
_CONTENT_STATES = {
    ScreenState.STREAMING,
    ScreenState.TOOL_REQUEST,
    ScreenState.TOOL_RUNNING,
    ScreenState.TOOL_RESULT,
    ScreenState.ERROR,
    ScreenState.TODO_LIST,
    ScreenState.PARALLEL_AGENTS,
    ScreenState.BACKGROUND_TASK,
}

# Per-session state for the output loop (keyed by (user_id, session_id))
_session_emulators: dict[tuple[int, int], TerminalEmulator] = {}
_session_buffers: dict[tuple[int, int], OutputBuffer] = {}
_session_prev_state: dict[tuple[int, int], ScreenState] = {}


async def poll_output(bot: Bot, session_manager) -> None:
    """Background loop that reads Claude output and sends it to Telegram.

    Pipeline per cycle (300ms):
      1. read_available() drains raw PTY bytes
      2. TerminalEmulator.feed() updates the pyte virtual screen
      3. get_display() returns full screen → classify_screen_state()
      4. get_changes() returns only changed lines → extract_content()
      5. OutputBuffer accumulates text, flushes after debounce

    Two separate reads from the emulator: get_display() gives the classifier
    full context (screen-wide patterns like tool menus), while get_changes()
    gives content extraction only the delta (avoids re-sending all visible
    text every cycle).
    """
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
                key = (user_id, sid)

                # Lazy-init emulator and buffer per session
                if key not in _session_emulators:
                    _session_emulators[key] = TerminalEmulator()
                    _session_buffers[key] = OutputBuffer(
                        debounce_ms=500, max_buffer=2000
                    )
                    _session_prev_state[key] = ScreenState.STARTUP

                raw = session.process.read_available()
                if not raw:
                    # Still check buffer readiness even without new data
                    buf = _session_buffers[key]
                    if buf.is_ready():
                        await _flush_buffer(bot, user_id, buf)
                    continue

                emu = _session_emulators[key]
                buf = _session_buffers[key]

                emu.feed(raw)
                # Full display for classification (needs screen-wide context)
                display = emu.get_display()
                # Changed lines only for content extraction (incremental delta)
                changed = emu.get_changes()
                event = classify_screen_state(display, _session_prev_state.get(key))
                prev = _session_prev_state.get(key)

                # Once we've left STARTUP, never go back — the banner
                # persists in pyte's screen buffer and tricks the classifier
                if event.state == ScreenState.STARTUP and prev not in (
                    ScreenState.STARTUP, None,
                ):
                    event = event.__class__(
                        state=ScreenState.UNKNOWN,
                        payload=event.payload,
                        raw_lines=event.raw_lines,
                    )

                _session_prev_state[key] = event.state

                if event.state != prev:
                    logger.debug(
                        "poll_output user=%d sid=%d state=%s prev=%s",
                        user_id, sid, event.state.name, prev.name if prev else "None",
                    )
                else:
                    logger.log(
                        TRACE,
                        "poll_output user=%d sid=%d state=%s (unchanged)",
                        user_id, sid, event.state.name,
                    )

                # Dump screen on state transitions for debugging
                if event.state != prev:
                    non_empty = [l for l in display if l.strip()]
                    for i, line in enumerate(non_empty[-10:]):
                        logger.log(TRACE, "  screen[%d]: %s", i, line)

                # Notify on state transitions to THINKING
                if event.state == ScreenState.THINKING and prev != ScreenState.THINKING:
                    buf.append("_Thinking..._\n")

                # Extract content for states that produce output
                if event.state in _CONTENT_STATES:
                    content = extract_content(changed)
                    if content:
                        buf.append(reflow_text(content) + "\n")

                # Flush on transition to idle (response complete)
                if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
                    if buf.is_ready():
                        await _flush_buffer(bot, user_id, buf)
                elif buf.is_ready():
                    await _flush_buffer(bot, user_id, buf)


async def _flush_buffer(bot: Bot, user_id: int, buf: OutputBuffer) -> None:
    """Send buffered output to the user's Telegram chat."""
    text = buf.flush()
    if not text.strip():
        return
    for chunk in split_message(text):
        try:
            await bot.send_message(chat_id=user_id, text=chunk)
        except Exception as exc:
            logger.error("Failed to send output to user %d: %s", user_id, exc)
