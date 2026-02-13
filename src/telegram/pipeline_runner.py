"""PipelineRunner: transition-table-driven output processing.

Replaces the SessionProcessor's three interacting state machines with
a single (phase, observation) -> (next_phase, actions) lookup table.
"""

from __future__ import annotations

import html as html_mod
import logging
from typing import TYPE_CHECKING

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import Forbidden

from src.parsing.models import ScreenEvent, TerminalView
from src.telegram.keyboards import build_tool_approval_keyboard
from src.parsing.content_classifier import classify_regions
from src.telegram.formatter import format_html, reflow_text, render_regions
from src.telegram.output_pipeline import render_ansi, strip_response_markers
from src.telegram.pipeline_state import PipelinePhase, PipelineState

if TYPE_CHECKING:
    from telegram import Bot
    from src.session_manager import SessionManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------
# Key:   (current_phase, observed_terminal_view)
# Value: (next_phase, tuple_of_action_names)
#
# Actions are method name suffixes: "send_thinking" -> _send_thinking(event).
# The process() method dispatches them in order.

_TRANSITIONS: dict[
    tuple[PipelinePhase, TerminalView],
    tuple[PipelinePhase, tuple[str, ...]],
] = {
    # --- DORMANT ---
    (PipelinePhase.DORMANT, TerminalView.THINKING): (
        PipelinePhase.THINKING, ("send_thinking",),
    ),
    (PipelinePhase.DORMANT, TerminalView.STREAMING): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.DORMANT, TerminalView.TOOL_REQUEST): (
        PipelinePhase.TOOL_PENDING, ("send_keyboard",),
    ),
    (PipelinePhase.DORMANT, TerminalView.AUTH_REQUIRED): (
        PipelinePhase.DORMANT, ("send_auth_warning",),
    ),
    (PipelinePhase.DORMANT, TerminalView.ERROR): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.DORMANT, TerminalView.TODO_LIST): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.DORMANT, TerminalView.PARALLEL_AGENTS): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.DORMANT, TerminalView.BACKGROUND_TASK): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),

    # --- THINKING ---
    (PipelinePhase.THINKING, TerminalView.STREAMING): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.THINKING, TerminalView.IDLE): (
        PipelinePhase.DORMANT, ("extract_and_send", "finalize"),
    ),
    (PipelinePhase.THINKING, TerminalView.TOOL_REQUEST): (
        PipelinePhase.TOOL_PENDING, ("finalize", "send_keyboard"),
    ),
    (PipelinePhase.THINKING, TerminalView.AUTH_REQUIRED): (
        PipelinePhase.DORMANT, ("finalize", "send_auth_warning"),
    ),
    (PipelinePhase.THINKING, TerminalView.ERROR): (
        PipelinePhase.DORMANT, ("extract_and_send", "finalize"),
    ),
    (PipelinePhase.THINKING, TerminalView.TODO_LIST): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.THINKING, TerminalView.PARALLEL_AGENTS): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.THINKING, TerminalView.BACKGROUND_TASK): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),

    # --- STREAMING ---
    (PipelinePhase.STREAMING, TerminalView.STREAMING): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.STREAMING, TerminalView.IDLE): (
        PipelinePhase.DORMANT, ("finalize",),
    ),
    (PipelinePhase.STREAMING, TerminalView.TOOL_REQUEST): (
        PipelinePhase.TOOL_PENDING, ("finalize", "send_keyboard"),
    ),
    (PipelinePhase.STREAMING, TerminalView.THINKING): (
        PipelinePhase.THINKING, ("finalize", "send_thinking"),
    ),
    (PipelinePhase.STREAMING, TerminalView.TOOL_RUNNING): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.STREAMING, TerminalView.TOOL_RESULT): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.STREAMING, TerminalView.ERROR): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.STREAMING, TerminalView.AUTH_REQUIRED): (
        PipelinePhase.DORMANT, ("finalize", "send_auth_warning"),
    ),
    (PipelinePhase.STREAMING, TerminalView.TODO_LIST): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.STREAMING, TerminalView.PARALLEL_AGENTS): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.STREAMING, TerminalView.BACKGROUND_TASK): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),

    # --- TOOL_PENDING ---
    (PipelinePhase.TOOL_PENDING, TerminalView.TOOL_RUNNING): (
        PipelinePhase.STREAMING, (),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.STREAMING): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.THINKING): (
        PipelinePhase.THINKING, ("send_thinking",),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.IDLE): (
        PipelinePhase.DORMANT, (),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.TOOL_REQUEST): (
        PipelinePhase.TOOL_PENDING, (),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.AUTH_REQUIRED): (
        PipelinePhase.DORMANT, ("send_auth_warning",),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.ERROR): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.TODO_LIST): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.PARALLEL_AGENTS): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
    (PipelinePhase.TOOL_PENDING, TerminalView.BACKGROUND_TASK): (
        PipelinePhase.STREAMING, ("extract_and_send",),
    ),
}

# Fallback: when (phase, view) is not in _TRANSITIONS, phase stays the same
# and no actions fire.


class PipelineRunner:
    """Transition-table-driven output event processor.

    Each call to :meth:`process` looks up the (current_phase, terminal_view)
    pair in the transition table, executes the associated actions in order,
    then advances the phase.
    """

    def __init__(
        self,
        state: PipelineState,
        user_id: int,
        session_id: int,
        bot: Bot,
        session_manager: SessionManager,
    ) -> None:
        self.state = state
        self.user_id = user_id
        self.session_id = session_id
        self.bot = bot
        self.session_manager = session_manager

    async def process(self, event: ScreenEvent) -> None:
        """Process a single screen event through the transition table."""
        key = (self.state.phase, event.state)
        if key in _TRANSITIONS:
            next_phase, actions = _TRANSITIONS[key]
        else:
            next_phase = self.state.phase
            actions = ()
            if event.state not in (
                TerminalView.UNKNOWN,
                TerminalView.STARTUP,
                TerminalView.USER_MESSAGE,
            ):
                logger.warning(
                    "No transition for (%s, %s) -- staying in %s",
                    self.state.phase.name, event.state.name, next_phase.name,
                )

        for action in actions:
            method = getattr(self, f"_{action}")
            try:
                await method(event)
            except Forbidden:
                logger.warning(
                    "User %d blocked the bot — killing session %d",
                    self.user_id, self.session_id,
                )
                try:
                    await self.session_manager.kill_session(
                        self.user_id, self.session_id,
                    )
                except Exception:
                    pass
                return
            except Exception:
                logger.exception(
                    "Action %s failed during (%s, %s) for user=%d sid=%d",
                    action, self.state.phase.name, event.state.name,
                    self.user_id, self.session_id,
                )

        self.state.phase = next_phase
        self.state.prev_view = event.state

    # ------------------------------------------------------------------
    # Action methods
    # ------------------------------------------------------------------

    async def _send_thinking(self, event: ScreenEvent) -> None:
        """Start typing indicator and send thinking placeholder."""
        await self.state.streaming.start_thinking()

    async def _send_keyboard(self, event: ScreenEvent) -> None:
        """Send tool approval inline keyboard."""
        self.state.tool_acted = False
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

    async def _send_auth_warning(self, event: ScreenEvent) -> None:
        """Send authentication warning and kill the session (one-shot)."""
        if self.state.auth_warned:
            return
        self.state.auth_warned = True
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
            "Auth required for user=%d sid=%d -- killing session",
            self.user_id, self.session_id,
        )
        await self.session_manager.kill_session(
            self.user_id, self.session_id,
        )

    async def _extract_and_send(self, event: ScreenEvent) -> None:
        """Extract content changes via ANSI pipeline and send to Telegram."""
        emu = self.state.emulator

        # Get attributed delta lines (changed since last check)
        attr_changes = emu.get_attributed_changes()
        if not attr_changes:
            return

        # Filter chrome and strip markers
        filtered = strip_response_markers(attr_changes)
        if not filtered:
            return

        # Render through ANSI pipeline
        regions = classify_regions(filtered)
        rendered = render_regions(regions)
        html = format_html(reflow_text(rendered))

        if not html.strip():
            return

        await self.state.streaming.append_content(html)

    async def _finalize(self, event: ScreenEvent) -> None:
        """Finalize: optionally re-render via full ANSI pipeline, then finalize message."""
        emu = self.state.emulator
        streaming = self.state.streaming

        # Only re-render if we have accumulated streaming content
        if streaming.accumulated:
            source = emu.get_full_display()
            attr = emu.get_full_attributed_lines()
            html = render_ansi(source, attr)
            if html.strip():
                streaming.replace_content(html)

        await streaming.finalize()
        emu.clear_history()


# ---------------------------------------------------------------------------
# Import-time validation: every action string in the table must have a method
# ---------------------------------------------------------------------------
for (_ph, _tv), (_next, _acts) in _TRANSITIONS.items():
    for _a in _acts:
        if not hasattr(PipelineRunner, f"_{_a}"):
            raise AssertionError(
                f"Transition ({_ph.name}, {_tv.name}) references "
                f"unknown action {_a!r}"
            )
