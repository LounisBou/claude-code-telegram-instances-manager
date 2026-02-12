from __future__ import annotations

import asyncio
import logging
import textwrap
import time
from enum import Enum

import html as html_mod

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from src.core.log_setup import TRACE
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.content_classifier import classify_regions
from src.telegram.formatter import (
    format_html, reflow_text, render_regions, wrap_code_blocks,
)
from src.telegram.keyboards import build_tool_approval_keyboard
from src.parsing.terminal_emulator import CharSpan, TerminalEmulator
from src.parsing.ui_patterns import (
    ScreenEvent, ScreenState, classify_line, extract_content,
)

logger = logging.getLogger(__name__)


def _strip_marker_from_spans(
    spans: list[CharSpan], marker: str,
) -> list[CharSpan]:
    """Remove a leading Unicode marker (⏺ or ⎿) from attributed spans.

    Strips the marker character and any following space from the first
    non-whitespace span.  Returns a new span list; original is not modified.

    Args:
        spans: Attributed spans for a terminal line.
        marker: The marker character to strip (e.g. '⏺' or '⎿').

    Returns:
        Span list with the marker removed from the leading span.
    """
    result: list[CharSpan] = []
    stripped = False
    for span in spans:
        if not stripped and marker in span.text:
            # Remove the marker and optional trailing space
            new_text = span.text.replace(marker, "", 1)
            if new_text.startswith(" "):
                new_text = new_text[1:]
            stripped = True
            if new_text:
                result.append(CharSpan(
                    text=new_text, fg=span.fg,
                    bold=span.bold, italic=span.italic,
                ))
        else:
            result.append(span)
    return result


def _lstrip_n_chars(spans: list[CharSpan], n: int) -> list[CharSpan]:
    """Strip *n* leading characters from the start of a span list.

    Removes exactly *n* characters from the beginning of the combined
    span text, splitting spans if necessary.  Used by
    :func:`_dedent_attr_lines` to remove common terminal margin.

    Args:
        spans: Attributed spans for one line.
        n: Number of leading characters to strip.

    Returns:
        New span list with *n* characters removed from the front.
    """
    remaining = n
    result: list[CharSpan] = []
    for span in spans:
        if remaining <= 0:
            result.append(span)
            continue
        if len(span.text) <= remaining:
            remaining -= len(span.text)
            continue
        result.append(CharSpan(
            text=span.text[remaining:],
            fg=span.fg, bold=span.bold, italic=span.italic,
        ))
        remaining = 0
    return result


def _dedent_attr_lines(
    lines: list[list[CharSpan]],
) -> list[list[CharSpan]]:
    """Remove common leading whitespace from attributed lines.

    Computes the minimum indent (leading spaces) across all non-empty
    lines, then strips that many characters from each line's spans.
    This removes the 2-space terminal margin that Claude Code adds
    to content below the ``⏺`` marker.

    Args:
        lines: Filtered attributed span lists (one per line).

    Returns:
        Dedented span lists with common leading whitespace removed.
    """
    min_indent = float("inf")
    for spans in lines:
        text = "".join(s.text for s in spans)
        lstripped = text.lstrip()
        if lstripped:
            indent = len(text) - len(lstripped)
            min_indent = min(min_indent, indent)
    if min_indent in (0, float("inf")):
        return lines
    return [_lstrip_n_chars(spans, min_indent) for spans in lines]


def _filter_response_attr(
    source: list[str],
    attr: list[list[CharSpan]],
) -> list[list[CharSpan]]:
    """Filter attributed lines to response content only.

    Uses :func:`~src.parsing.ui_patterns.classify_line` on the plain text
    version of each line to identify terminal chrome (prompts, status bars,
    separators, etc.) and returns only the attributed lines that correspond
    to Claude's actual response content.

    After filtering, applies :func:`_dedent_attr_lines` to remove the
    common terminal margin (typically 2 spaces from the ``⏺`` marker
    column).

    Mirrors the filtering logic of
    :func:`~src.parsing.ui_patterns.extract_content` but operates on
    attributed spans instead of plain text.

    Args:
        source: Plain text lines (parallel to *attr*).
        attr: Attributed span lists (one per line, same length as *source*).

    Returns:
        Filtered and dedented list of attributed span lists.
    """
    result: list[list[CharSpan]] = []
    in_prompt = False
    for plain, spans in zip(source, attr):
        cls = classify_line(plain)
        # Start skipping after a ❯ prompt line
        if cls == "prompt":
            in_prompt = True
            continue
        # End prompt continuation on response marker / structured element
        if in_prompt:
            if cls in (
                "response", "tool_connector", "tool_header",
                "thinking", "separator",
            ):
                in_prompt = False
            else:
                continue
        if cls == "content":
            result.append(spans)
        elif cls == "response":
            result.append(_strip_marker_from_spans(spans, "⏺"))
        elif cls == "tool_connector":
            result.append(_strip_marker_from_spans(spans, "⎿"))
    return _dedent_attr_lines(result)


# States that produce user-visible output sent to Telegram.
# STARTUP, IDLE, USER_MESSAGE, UNKNOWN, and THINKING are suppressed:
# they are UI chrome or transient states with no extractable content.
# THINKING gets a one-time "_Thinking..._" notification instead.
# TOOL_REQUEST is handled separately with an inline keyboard (not
# extracted as plain content), so it is excluded from _CONTENT_STATES.
_CONTENT_STATES = {
    ScreenState.STREAMING,
    ScreenState.TOOL_RUNNING,
    ScreenState.TOOL_RESULT,
    ScreenState.ERROR,
    ScreenState.TODO_LIST,
    ScreenState.PARALLEL_AGENTS,
    ScreenState.BACKGROUND_TASK,
}

# Line categories that are pure UI chrome — never part of Claude's actual
# response content.  Used when building the THINKING snapshot so that
# content from a *previous* response (still visible on the pyte screen)
# doesn't accidentally dedup identical patterns from a *new* response.
_CHROME_CATEGORIES = frozenset({
    "separator", "diff_delimiter", "status_bar", "prompt",
    "thinking", "startup", "logo", "box", "empty",
})

# Per-session state for the output loop (keyed by (user_id, session_id))
_session_emulators: dict[tuple[int, int], TerminalEmulator] = {}
_session_streaming: dict[tuple[int, int], StreamingMessage] = {}
_session_prev_state: dict[tuple[int, int], ScreenState] = {}
# Content dedup: tracks lines already sent to avoid re-sending when
# pyte redraws the screen (e.g. terminal scroll shifts all line positions,
# making get_changes() report previously-sent content as "changed").
# Cleared on IDLE transitions (response boundary).
_session_sent_lines: dict[tuple[int, int], set[str]] = {}
# Display snapshot captured on THINKING entry.  Used to subtract
# pre-existing content (banner artifacts, user echo, status bar)
# from the full display during fast THINKING→IDLE extraction.
_session_thinking_snapshot: dict[tuple[int, int], set[str]] = {}


def _find_last_prompt(display: list[str]) -> int | None:
    """Find index of the last user prompt line on the display.

    Looks for ``❯`` lines with text longer than 2 chars (to skip bare
    prompts that are just the cursor marker ``❯``).  The previous
    threshold of 5 incorrectly skipped short user inputs like a
    3-emoji message (``❯ 🤖💬🔥`` = 5 chars, which failed ``> 5``).

    Args:
        display: Terminal display lines from the emulator.

    Returns:
        Line index of the last prompt, or ``None`` if no prompt is visible
        (e.g. it scrolled off the 36-row pyte screen).
    """
    result = None
    for i, line in enumerate(display):
        s = line.strip()
        if s.startswith("❯") and len(s) > 2:
            result = i
    return result


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

    Ultra-fast case: UNKNOWN→IDLE (no THINKING detected). When the entire
    response cycle completes within a single poll interval (<300ms), the
    classifier never sees THINKING — it jumps from UNKNOWN/USER_MESSAGE
    straight to IDLE. We detect this via non-empty changed lines on a
    non-trivial IDLE transition, and extract from ``changed``. The
    StreamingMessage safety net creates a new message since start_thinking
    was never called.

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

                # Reset dedup state on new user interaction so stale
                # data from a previous response cycle never bleeds in.
                if event.state == ScreenState.USER_MESSAGE:
                    _session_sent_lines[key] = set()
                    _session_thinking_snapshot.pop(key, None)

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
                    # Snapshot UI chrome visible on the display so fast
                    # THINKING→IDLE can subtract non-content artifacts
                    # (separators, status bar, prompt echo, thinking stars).
                    #
                    # ONLY chrome lines are captured (via classify_line).
                    # Content/response/tool lines are excluded because a
                    # previous response may still be visible on the pyte
                    # screen and common patterns like "Args:", "Returns:"
                    # would incorrectly dedup from the *new* response.
                    snap: set[str] = set()
                    for line in display:
                        stripped = line.strip()
                        if stripped and classify_line(line) in _CHROME_CATEGORIES:
                            snap.add(stripped)
                    _session_thinking_snapshot[key] = snap
                    await streaming.start_thinking()

                # --- Tool approval: send inline keyboard instead of text ---
                if (
                    event.state == ScreenState.TOOL_REQUEST
                    and prev != ScreenState.TOOL_REQUEST
                ):
                    # Finalize any in-progress streaming message first
                    await streaming.finalize()
                    # Build the approval message from the classifier payload
                    question = event.payload.get("question", "Tool approval requested")
                    options = event.payload.get("options", [])
                    safe_q = html_mod.escape(question)
                    parts = [f"<b>{safe_q}</b>"]
                    for i, opt in enumerate(options):
                        parts.append(f"  {i + 1}. {html_mod.escape(opt)}")
                    text = "\n".join(parts)
                    kb_data = build_tool_approval_keyboard(sid)
                    keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    text=btn["text"],
                                    callback_data=btn["callback_data"],
                                )
                                for btn in row
                            ]
                            for row in kb_data
                        ]
                    )
                    await bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )

                # Extract content for states that produce output.
                # Also extract on IDLE when a response cycle is incomplete
                # (streaming is THINKING or STREAMING but not yet finalized).
                # This handles both direct (THINKING→IDLE) and indirect
                # (THINKING→UNKNOWN→IDLE) fast-response transitions where
                # intermediate states don't trigger extraction.
                #
                # Ultra-fast path: when Claude responds within a single poll
                # cycle (<300ms), THINKING is never detected — the classifier
                # jumps from UNKNOWN/USER_MESSAGE straight to IDLE. In this
                # case streaming.state is still IDLE (start_thinking never
                # called). We detect this by checking for non-empty changed
                # lines on a non-trivial IDLE transition (prev != IDLE/STARTUP).
                _incomplete_cycle = streaming.state in (
                    StreamingState.THINKING, StreamingState.STREAMING,
                )
                _ultra_fast = (
                    not _incomplete_cycle
                    and changed
                    and prev not in (ScreenState.IDLE, ScreenState.STARTUP, None)
                )
                _should_extract = event.state in _CONTENT_STATES or (
                    event.state == ScreenState.IDLE
                    and (_incomplete_cycle or _ultra_fast)
                )
                if _should_extract:
                    # When streaming is still in THINKING, response content
                    # hasn't been extracted via get_changes() yet (THINKING
                    # and UNKNOWN don't extract). Use the display trimmed
                    # to the last user prompt — this excludes old responses
                    # that would otherwise need aggressive snapshot dedup
                    # (which incorrectly eats common patterns like "Args:").
                    # When no prompt is found (scrolled off), use the full
                    # display — the empty snapshot ensures no content dedup.
                    # For ultra-fast responses (no THINKING detected), use
                    # changed lines — they contain the fresh response delta.
                    _fast_idle = (
                        event.state == ScreenState.IDLE
                        and streaming.state == StreamingState.THINKING
                    )
                    # Attributed lines for ANSI-aware pipeline (must be
                    # captured BEFORE clear_history so scrollback is intact)
                    fast_idle_attr = None
                    if _fast_idle:
                        # Use full display including scrollback history so
                        # that long responses aren't truncated to the last
                        # screen-full.  The pyte HistoryScreen preserves
                        # lines that scrolled off the visible area.
                        full = emu.get_full_display()
                        full_attr = emu.get_full_attributed_lines()
                        prompt_idx = _find_last_prompt(full)
                        if prompt_idx is not None:
                            source = full[prompt_idx:]
                            fast_idle_attr = full_attr[prompt_idx:]
                        else:
                            source = full
                            fast_idle_attr = full_attr
                        # Clear history after extraction to avoid re-reading
                        # the same scrollback on subsequent poll cycles.
                        emu.clear_history()
                    else:
                        source = changed
                    content = extract_content(source)
                    if content:
                        # Dedup: filter out lines already sent (screen scroll
                        # causes get_changes() to re-report shifted lines)
                        sent = _session_sent_lines.get(key, set())
                        # For fast-IDLE, also subtract lines that existed
                        # before THINKING (banner artifacts, user echo, etc.)
                        snap = (
                            _session_thinking_snapshot.get(key, set())
                            if _fast_idle else set()
                        )
                        # Check against pre-existing sent set, but do NOT
                        # add to sent during iteration — repeated lines
                        # within the same response (e.g. multiple "return
                        # False" in code) must be preserved.  Only record
                        # lines as sent AFTER the full batch is extracted.
                        new_lines = []
                        for line in content.split("\n"):
                            stripped = line.strip()
                            if stripped and stripped not in sent and stripped not in snap:
                                new_lines.append(line)
                        for line in content.split("\n"):
                            stripped = line.strip()
                            if stripped:
                                sent.add(stripped)
                        if new_lines:
                            deduped = textwrap.dedent(
                                "\n".join(new_lines)
                            ).strip()
                            # ANSI-aware pipeline: use attributed lines from
                            # pyte buffer to classify code vs prose via syntax
                            # highlighting colors.  Falls back to the old
                            # heuristic pipeline when no attributed data is
                            # available (e.g. streaming with only changed text).
                            if fast_idle_attr is not None:
                                # Fast-IDLE: filter attributed lines to
                                # response content (strip prompt echo,
                                # status bar, progress bar, ⏺ markers)
                                filtered = _filter_response_attr(
                                    source, fast_idle_attr,
                                )
                                regions = classify_regions(filtered)
                                rendered = render_regions(regions)
                                html = format_html(reflow_text(rendered))
                            else:
                                # Streaming / ultra-fast: use old pipeline
                                # with heuristic code block detection
                                html = format_html(
                                    reflow_text(wrap_code_blocks(deduped))
                                )
                            await streaming.append_content(html)

                # Finalize on transition to idle (response complete)
                if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
                    # Re-seed dedup with all visible content instead of
                    # clearing.  When pyte scrolls, get_changes() re-reports
                    # shifted lines from a *previous* response.  Keeping
                    # those lines in the dedup set prevents them from leaking
                    # into the next extraction (e.g. TOOL_REQUEST right after
                    # a text response).  The dedup set is properly cleared on
                    # USER_MESSAGE (line ~184) for a fresh start when the
                    # user sends a new message.
                    sent = _session_sent_lines.setdefault(key, set())
                    for line in display:
                        stripped = line.strip()
                        if stripped:
                            sent.add(stripped)
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
            elif "message is not modified" in exc_str.lower():
                # Harmless: finalize() re-editing with same content
                pass
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
