"""SessionProcessor: 3-phase event processing for Claude output.

Replaces the monolithic ``poll_output`` body with a structured processor
that separates concerns into three phases per poll cycle:

1. **Pre-extraction** — state entry side effects (start typing, snapshot
   chrome, clear dedup, send tool approval keyboard, handle auth).
2. **Extraction** — read content, dedup, render via heuristic or ANSI
   pipeline, send to Telegram.
3. **Finalization** — ANSI re-render, clear emulator history, finalize
   streaming message.  Only runs on IDLE transitions.

The ordering constraint is critical: ``_on_enter_thinking`` must run
*before* extraction (it starts the typing indicator), while
``_finalize_response`` must run *after* extraction (it finalizes the
accumulated streaming content).
"""

from __future__ import annotations

import html as html_mod
import logging
from enum import Enum
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.core.log_setup import TRACE
from src.parsing.models import ScreenEvent, ScreenState
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import extract_content
from src.telegram.keyboards import build_tool_approval_keyboard
from src.telegram.output_pipeline import (
    find_last_prompt,
    render_ansi,
    render_heuristic,
)
from src.telegram.streaming_message import StreamingState

if TYPE_CHECKING:
    from telegram import Bot

    from src.telegram.output_state import SessionOutputState

logger = logging.getLogger(__name__)


class ExtractionMode(Enum):
    """How to extract content from the terminal for this cycle.

    Values:
        NONE: No extraction (UI chrome, transient states).
        STREAMING: Changed lines + heuristic pipeline.
        FAST_IDLE: Full display + ANSI pipeline (THINKING→IDLE).
        ULTRA_FAST: Changed lines + heuristic pipeline (no THINKING detected).
    """

    NONE = "none"
    STREAMING = "streaming"
    FAST_IDLE = "fast_idle"
    ULTRA_FAST = "ultra_fast"


# States that produce user-visible output sent to Telegram.
_CONTENT_STATES = {
    ScreenState.STREAMING,
    ScreenState.TOOL_RUNNING,
    ScreenState.TOOL_RESULT,
    ScreenState.ERROR,
    ScreenState.TODO_LIST,
    ScreenState.PARALLEL_AGENTS,
    ScreenState.BACKGROUND_TASK,
}


class SessionProcessor:
    """Processes screen events for one session.

    Three-phase cycle per poll iteration:
      1. Pre-extraction: state entry side effects
      2. Extraction: read content, dedup, render, send to Telegram
      3. Finalization: ANSI re-render, clear history, finalize (IDLE only)
    """

    def __init__(
        self,
        state: SessionOutputState,
        user_id: int,
        session_id: int,
        bot: Bot,
        session_manager,
    ) -> None:
        self.s = state
        self.user_id = user_id
        self.session_id = session_id
        self.bot = bot
        self.session_manager = session_manager

    async def process_cycle(self, raw: bytes) -> None:
        """Run one full processing cycle on new PTY data.

        Feeds raw bytes to the emulator, classifies the screen state,
        applies overrides, then runs the 3-phase pipeline.

        Args:
            raw: Raw bytes from the PTY read.
        """
        emu = self.s.emulator
        streaming = self.s.streaming

        emu.feed(raw)
        display = emu.get_display()
        changed = emu.get_changes()
        event = classify_screen_state(display, self.s.prev_state)
        prev = self.s.prev_state

        # --- State overrides ---
        event = self._apply_overrides(event, prev)

        self.s.prev_state = event.state
        self._log_state(event, prev, display)

        # === Phase 1: Pre-extraction ===
        should_break = await self._handle_state_entry(
            event, prev, display,
        )
        if should_break:
            return

        # === Phase 2: Extraction ===
        mode = self._extraction_mode(event, prev, changed, streaming)
        was_fast_idle = mode == ExtractionMode.FAST_IDLE
        if mode != ExtractionMode.NONE:
            await self._extract_and_send(
                mode, changed, display, emu, streaming,
            )

        # === Phase 3: Finalization (IDLE only, after extraction) ===
        if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
            await self._finalize_response(
                was_fast_idle, display, emu, streaming,
            )

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def _apply_overrides(
        self, event: ScreenEvent, prev: ScreenState,
    ) -> ScreenEvent:
        """Apply state overrides (STARTUP lockout, tool-acted suppression)."""
        # Once we've left STARTUP, never go back — the banner persists
        if event.state == ScreenState.STARTUP and prev not in (
            ScreenState.STARTUP, None,
        ):
            event = ScreenEvent(
                state=ScreenState.UNKNOWN,
                payload=event.payload,
                raw_lines=event.raw_lines,
            )

        # After tool callback, suppress stale TOOL_REQUEST detections
        if (
            event.state == ScreenState.TOOL_REQUEST
            and self.s.tool_acted
        ):
            event = ScreenEvent(
                state=ScreenState.UNKNOWN,
                payload=event.payload,
                raw_lines=event.raw_lines,
            )
        elif event.state != ScreenState.TOOL_REQUEST:
            self.s.tool_acted = False

        return event

    # ------------------------------------------------------------------
    # Phase 1: Pre-extraction state entry
    # ------------------------------------------------------------------

    async def _handle_state_entry(
        self,
        event: ScreenEvent,
        prev: ScreenState,
        display: list[str],
    ) -> bool:
        """Handle state entry side effects.

        Returns True if the caller should break (session killed).
        """
        # Pre-seed dedup during STARTUP
        if event.state == ScreenState.STARTUP:
            self.s.dedup.seed_from_display(display)

        # Reset dedup on new user interaction
        if event.state == ScreenState.USER_MESSAGE:
            self.s.dedup.clear()

        # Auth screen: notify user and kill session
        if (
            event.state == ScreenState.AUTH_REQUIRED
            and prev != ScreenState.AUTH_REQUIRED
        ):
            await self.s.streaming.finalize()
            await self.bot.send_message(
                chat_id=self.user_id,
                text=(
                    "Claude Code requires authentication.\n"
                    "Run <code>claude</code> in a terminal on the "
                    "host to complete the login flow, then try again."
                ),
                parse_mode="HTML",
            )
            logger.warning(
                "Auth required for user=%d sid=%d — killing session",
                self.user_id, self.session_id,
            )
            await self.session_manager.kill_session(
                self.user_id, self.session_id,
            )
            return True

        # THINKING entry: snapshot chrome and start typing
        if (
            event.state == ScreenState.THINKING
            and prev != ScreenState.THINKING
        ):
            self.s.dedup.snapshot_chrome(display)
            await self.s.streaming.start_thinking()

        # TOOL_REQUEST entry: send inline keyboard
        if (
            event.state == ScreenState.TOOL_REQUEST
            and prev != ScreenState.TOOL_REQUEST
        ):
            await self._send_tool_approval(event)

        return False

    async def _send_tool_approval(self, event: ScreenEvent) -> None:
        """Send tool approval inline keyboard message."""
        await self.s.streaming.finalize()
        question = event.payload.get("question") or "Tool approval requested"
        options = event.payload.get("options", [])
        safe_q = html_mod.escape(question)
        parts = [f"<b>{safe_q}</b>"]
        for i, opt in enumerate(options):
            parts.append(f"  {i + 1}. {html_mod.escape(opt)}")
        text = "\n".join(parts)
        kb_data = build_tool_approval_keyboard(
            self.session_id,
            options=options,
            selected=event.payload.get("selected", 0),
        )
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
        await self.bot.send_message(
            chat_id=self.user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )

    # ------------------------------------------------------------------
    # Phase 2: Extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extraction_mode(
        event: ScreenEvent,
        prev: ScreenState,
        changed: list[str],
        streaming,
    ) -> ExtractionMode:
        """Determine how to extract content for this cycle."""
        incomplete_cycle = streaming.state in (
            StreamingState.THINKING, StreamingState.STREAMING,
        )
        ultra_fast = (
            not incomplete_cycle
            and changed
            and prev not in (ScreenState.IDLE, ScreenState.STARTUP, None)
        )
        should_extract = event.state in _CONTENT_STATES or (
            event.state == ScreenState.IDLE
            and (incomplete_cycle or ultra_fast)
        )
        if not should_extract:
            return ExtractionMode.NONE

        fast_idle = (
            event.state == ScreenState.IDLE
            and streaming.state == StreamingState.THINKING
        )
        if fast_idle:
            return ExtractionMode.FAST_IDLE
        if ultra_fast:
            return ExtractionMode.ULTRA_FAST
        return ExtractionMode.STREAMING

    async def _extract_and_send(
        self,
        mode: ExtractionMode,
        changed: list[str],
        display: list[str],
        emu,
        streaming,
    ) -> None:
        """Extract content and send to Telegram."""
        fast_idle_attr = None
        if mode == ExtractionMode.FAST_IDLE:
            full = emu.get_full_display()
            full_attr = emu.get_full_attributed_lines()
            prompt_idx = find_last_prompt(full)
            if prompt_idx is not None:
                source = full[prompt_idx:]
                fast_idle_attr = full_attr[prompt_idx:]
            else:
                source = full
                fast_idle_attr = full_attr
            emu.clear_history()
        else:
            source = changed

        content = extract_content(source)
        if not content:
            return

        use_snapshot = mode == ExtractionMode.FAST_IDLE
        deduped = self.s.dedup.filter_new(
            content, use_snapshot=use_snapshot,
        )
        if not deduped:
            return

        if fast_idle_attr is not None:
            html = render_ansi(source, fast_idle_attr)
        else:
            html = render_heuristic(deduped)
        await streaming.append_content(html)

    # ------------------------------------------------------------------
    # Phase 3: Finalization
    # ------------------------------------------------------------------

    async def _finalize_response(
        self,
        was_fast_idle: bool,
        display: list[str],
        emu,
        streaming,
    ) -> None:
        """Finalize response on IDLE transition.

        Re-seeds dedup, optionally re-renders with ANSI pipeline,
        clears emulator history, and finalizes the streaming message.
        """
        # Re-seed dedup with all visible content
        self.s.dedup.seed_from_display(display)

        # ANSI re-render: when streamed with heuristic pipeline,
        # re-render final message using ANSI-aware pipeline.
        # MUST NOT fire after FAST_IDLE (emulator history already cleared).
        if (
            streaming.state == StreamingState.STREAMING
            and streaming.accumulated
            and not was_fast_idle
        ):
            full = emu.get_full_display()
            full_attr = emu.get_full_attributed_lines()
            prompt_idx = find_last_prompt(full)
            if prompt_idx is not None:
                re_source = full[prompt_idx:]
                re_attr = full_attr[prompt_idx:]
            else:
                re_source = full
                re_attr = full_attr
            re_html = render_ansi(re_source, re_attr)
            if re_html.strip():
                streaming.accumulated = re_html

        emu.clear_history()
        await streaming.finalize()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_state(
        self,
        event: ScreenEvent,
        prev: ScreenState,
        display: list[str],
    ) -> None:
        """Log state transitions."""
        if event.state != prev:
            logger.debug(
                "poll_output user=%d sid=%d state=%s prev=%s",
                self.user_id, self.session_id,
                event.state.name,
                prev.name if prev else "None",
            )
            non_empty = [line for line in display if line.strip()]
            for i, line in enumerate(non_empty[-10:]):
                logger.log(TRACE, "  screen[%d]: %s", i, line)
        else:
            logger.log(
                TRACE,
                "poll_output user=%d sid=%d state=%s (unchanged)",
                self.user_id, self.session_id, event.state.name,
            )
