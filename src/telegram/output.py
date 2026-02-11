from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum

from telegram import Bot

from src.core.log_setup import TRACE
from src.parsing.screen_classifier import classify_screen_state
from src.telegram.formatter import format_html, reflow_text
from src.parsing.terminal_emulator import TerminalEmulator
from src.parsing.ui_patterns import ScreenEvent, ScreenState, extract_content

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
_session_streaming: dict[tuple[int, int], StreamingMessage] = {}
_session_prev_state: dict[tuple[int, int], ScreenState] = {}
# Content dedup: tracks lines already sent to avoid re-sending when
# pyte redraws the screen (e.g. terminal scroll shifts all line positions,
# making get_changes() report previously-sent content as "changed").
# Cleared on IDLE transitions (response boundary).
_session_sent_lines: dict[tuple[int, int], set[str]] = {}


async def poll_output(
    bot: Bot, session_manager, *, edit_rate_limit: int = 3
) -> None:
    """Background loop that reads Claude output and streams it to Telegram.

    Uses StreamingMessage for edit-in-place streaming: a single Telegram
    message is created on THINKING, edited in-place as content arrives,
    and finalized when the response completes (IDLE transition).

    Pipeline per cycle (300ms):
      1. read_available() drains raw PTY bytes
      2. TerminalEmulator.feed() updates the pyte virtual screen
      3. get_display() returns full screen -> classify_screen_state()
      4. get_changes() returns only changed lines -> extract_content()
      5. format_html() converts to Telegram HTML
      6. StreamingMessage.append_content() edits message in-place

    Two separate reads from the emulator: get_display() gives the classifier
    full context (screen-wide patterns like tool menus), while get_changes()
    gives content extraction only the delta (avoids re-sending all visible
    text every cycle).

    Special case: THINKING→IDLE fast responses. When Claude responds within
    one poll cycle, response content arrives with the thinking indicator and
    is consumed by get_changes() during THINKING (not a content state). By
    the IDLE cycle, get_changes() only has UI chrome. The fix: use the full
    display for content extraction on THINKING→IDLE, with the dedup set
    preventing old content from leaking.

    Args:
        bot: Telegram Bot instance for sending messages.
        session_manager: SessionManager with active sessions.
        edit_rate_limit: Maximum Telegram edit_message calls per second.
            Passed to StreamingMessage on creation.
    """
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
                key = (user_id, sid)

                # Lazy-init emulator and streaming message per session
                if key not in _session_emulators:
                    _session_emulators[key] = TerminalEmulator()
                    _session_streaming[key] = StreamingMessage(
                        bot=bot, chat_id=user_id,
                        edit_rate_limit=edit_rate_limit,
                    )
                    _session_prev_state[key] = ScreenState.STARTUP
                    _session_sent_lines[key] = set()

                raw = session.process.read_available()
                if not raw:
                    continue

                emu = _session_emulators[key]
                streaming = _session_streaming[key]

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

                # Pre-seed dedup set during STARTUP: add all visible content
                # lines so they don't leak into the first response when pyte
                # redraws the screen (the banner persists in the buffer).
                if event.state == ScreenState.STARTUP:
                    sent = _session_sent_lines.get(key, set())
                    for line in display:
                        stripped = line.strip()
                        if stripped:
                            sent.add(stripped)

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
                    await streaming.start_thinking()

                # Extract content for states that produce output.
                # Also extract on IDLE transition from THINKING/STREAMING:
                # fast responses may complete within a single poll cycle,
                # going THINKING→IDLE without ever entering STREAMING.
                _should_extract = event.state in _CONTENT_STATES or (
                    event.state == ScreenState.IDLE
                    and prev in (ScreenState.THINKING, ScreenState.STREAMING)
                )
                if _should_extract:
                    # For THINKING→IDLE fast responses, response content
                    # arrived in the same PTY read as the thinking indicator.
                    # get_changes() consumed it during the THINKING cycle
                    # (which doesn't extract content), so by IDLE only UI
                    # chrome remains in changed. Use full display instead —
                    # the dedup set prevents re-sending old content.
                    _fast_idle = (
                        event.state == ScreenState.IDLE
                        and prev == ScreenState.THINKING
                    )
                    source = display if _fast_idle else changed
                    if source:
                        for ci, cl in enumerate(source):
                            if cl.strip():
                                logger.debug(
                                    "poll_output RAW %s[%d]: %r",
                                    "display" if _fast_idle else "changed",
                                    ci, cl.strip(),
                                )
                    content = extract_content(source)
                    if content:
                        # Dedup: filter out lines already sent (screen scroll
                        # causes get_changes() to re-report shifted lines)
                        sent = _session_sent_lines.get(key, set())
                        new_lines = []
                        for line in content.split("\n"):
                            stripped = line.strip()
                            if stripped and stripped not in sent:
                                new_lines.append(line)
                                sent.add(stripped)
                        if new_lines:
                            deduped = "\n".join(new_lines)
                            logger.debug(
                                "poll_output CONTENT lines=%r changed_count=%d",
                                new_lines, len(changed),
                            )
                            html = format_html(reflow_text(deduped))
                            await streaming.append_content(html)

                # Finalize on transition to idle (response complete)
                if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
                    # Clear dedup set at response boundary so future
                    # responses can reuse the same phrases
                    _session_sent_lines[key] = set()
                    await streaming.finalize()


class StreamingState(Enum):
    """State of a StreamingMessage lifecycle.

    Values:
        IDLE: No active response. Ready to begin a new cycle.
        THINKING: Placeholder message sent, typing indicator active.
        STREAMING: Content is being appended and edited in-place.
    """

    IDLE = "idle"
    THINKING = "thinking"
    STREAMING = "streaming"


class StreamingMessage:
    """Manages edit-in-place streaming for a single Claude response.

    State machine: IDLE -> start_thinking() -> THINKING -> first content -> STREAMING -> finalize() -> IDLE

    In THINKING state, sends typing action every 4s.
    In STREAMING state, edits message in-place at throttled rate.
    On overflow (>4096 chars), finalizes current message and starts a new one.
    """

    def __init__(self, bot: Bot, chat_id: int, edit_rate_limit: int = 3) -> None:
        """Initialize streaming message manager.

        Args:
            bot: Telegram Bot instance for API calls.
            chat_id: Telegram chat ID to send messages to.
            edit_rate_limit: Maximum edit_message calls per second.
        """
        self.bot = bot
        self.chat_id = chat_id
        self.edit_rate_limit = edit_rate_limit
        self.message_id: int | None = None
        self.accumulated: str = ""
        self.last_edit_time: float = 0
        self.state: StreamingState = StreamingState.IDLE
        self._typing_task: asyncio.Task | None = None

    async def start_thinking(self) -> None:
        """Send typing action and placeholder message.

        Transitions: IDLE -> THINKING.
        If still in STREAMING state (previous response not finalized),
        auto-finalizes the previous response first.
        Starts a background task that resends typing action every 4 seconds.
        """
        # Safety net: if previous response was not finalized (IDLE missed),
        # finalize it now before starting a new response cycle.
        if self.state == StreamingState.STREAMING:
            logger.warning(
                "start_thinking called while still STREAMING — "
                "auto-finalizing previous response"
            )
            await self.finalize()

        await self.bot.send_chat_action(chat_id=self.chat_id, action="typing")
        msg = await self.bot.send_message(
            chat_id=self.chat_id,
            text="<i>Thinking...</i>",
            parse_mode="HTML",
        )
        self.message_id = msg.message_id
        self.state = StreamingState.THINKING
        self._typing_task = asyncio.create_task(self._typing_loop())

    async def append_content(self, html: str) -> None:
        """Add content and edit message if throttle allows.

        On first call, cancels typing indicator and transitions to STREAMING.
        Handles overflow when accumulated content exceeds 4096 chars.

        Safety net: if called while IDLE (start_thinking was never called,
        e.g. classifier skipped THINKING state), sends a new message first
        so there is a message_id to edit.

        Args:
            html: HTML-formatted content to append.
        """
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None

        # Safety net: create a message if start_thinking() was never called
        if self.state == StreamingState.IDLE or self.message_id is None:
            logger.warning(
                "append_content called without start_thinking — "
                "sending new message (state=%s)",
                self.state.value,
            )
            msg = await self.bot.send_message(
                chat_id=self.chat_id, text=html, parse_mode="HTML"
            )
            self.message_id = msg.message_id
            self.accumulated = html
            self.last_edit_time = time.monotonic()
            self.state = StreamingState.STREAMING
            return

        self.state = StreamingState.STREAMING
        self.accumulated += html

        if len(self.accumulated) > 4096:
            await self._overflow()
            return

        now = time.monotonic()
        min_interval = 1.0 / self.edit_rate_limit
        if now - self.last_edit_time < min_interval:
            return

        await self._edit()

    async def finalize(self) -> None:
        """Final edit to ensure all content is sent, then reset.

        Transitions: any -> IDLE.
        """
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None
        if self.accumulated and self.message_id:
            await self._edit()
        self.reset()

    async def _edit(self) -> None:
        """Edit the current message with accumulated content."""
        if not self.message_id or not self.accumulated:
            return
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=self.accumulated,
                parse_mode="HTML",
            )
            self.last_edit_time = time.monotonic()
        except Exception as exc:
            exc_str = str(exc)
            if "parse entities" in exc_str.lower():
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        text=self.accumulated,
                        parse_mode=None,
                    )
                    self.last_edit_time = time.monotonic()
                except Exception as inner_exc:
                    logger.warning(
                        "edit_message plain-text fallback failed: %s", inner_exc
                    )
            else:
                logger.warning("edit_message failed: %s", exc)

    async def _overflow(self) -> None:
        """Content exceeds 4096: finalize current message, start new one."""
        split_at = self.accumulated.rfind("\n", 0, 4096)
        if split_at == -1:
            split_at = 4000
        current = self.accumulated[:split_at]
        remainder = self.accumulated[split_at:].lstrip()
        self.accumulated = current
        await self._edit()
        if remainder:
            msg = await self.bot.send_message(
                chat_id=self.chat_id, text=remainder, parse_mode="HTML"
            )
            self.message_id = msg.message_id
            self.accumulated = remainder
            self.last_edit_time = time.monotonic()

    async def _typing_loop(self) -> None:
        """Resend typing action every 4 seconds."""
        try:
            while True:
                await asyncio.sleep(4)
                await self.bot.send_chat_action(
                    chat_id=self.chat_id, action="typing"
                )
        except asyncio.CancelledError:
            pass

    def reset(self) -> None:
        """Reset to IDLE for next response."""
        self.message_id = None
        self.accumulated = ""
        self.last_edit_time = 0
        self.state = StreamingState.IDLE
