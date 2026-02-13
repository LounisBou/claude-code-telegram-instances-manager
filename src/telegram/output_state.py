"""Per-session output state and content deduplication.

Replaces the module-level dicts in ``output.py`` with cohesive classes:

- :class:`ContentDeduplicator` — dedup/snapshot logic for filtering already-sent
  lines and subtracting pre-existing chrome from fast THINKING→IDLE extraction.
- :class:`SessionOutputState` — all per-session state (emulator, streaming
  message, dedup, previous state, tool-acted flag) in one object.

A module-level registry (``get_or_create`` / ``cleanup``) manages the
lifecycle keyed by ``(user_id, session_id)`` tuples.
"""

from __future__ import annotations

import logging
import textwrap
from typing import TYPE_CHECKING

from src.parsing.models import ScreenState
from src.parsing.ui_patterns import CHROME_CATEGORIES, classify_text_line

if TYPE_CHECKING:
    from telegram import Bot

    from src.parsing.terminal_emulator import TerminalEmulator
    from src.telegram.streaming_message import StreamingMessage

logger = logging.getLogger(__name__)


class ContentDeduplicator:
    """Content deduplication for the output streaming pipeline.

    Tracks lines already sent to Telegram to prevent re-sending when the pyte
    terminal scrolls (``get_changes()`` re-reports shifted lines).

    Also captures a UI chrome snapshot on THINKING entry so that fast
    THINKING→IDLE extraction can subtract pre-existing artifacts (separators,
    status bar, prompt echo) from the full display.
    """

    def __init__(self) -> None:
        self.sent_lines: set[str] = set()
        self.thinking_snapshot: set[str] = set()

    def seed_from_display(self, display: list[str]) -> None:
        """Pre-seed dedup set with all visible non-blank lines.

        Called during STARTUP (banner persists in pyte buffer) and on
        IDLE transitions (re-seed to prevent previous response lines
        from leaking into the next extraction).

        Args:
            display: Full terminal display lines.
        """
        for line in display:
            stripped = line.strip()
            if stripped:
                self.sent_lines.add(stripped)

    def snapshot_chrome(self, display: list[str]) -> None:
        """Capture UI chrome lines visible on the display.

        Only lines classified as chrome (separators, status bar, thinking
        indicators, etc.) are captured — content/response/tool lines are
        excluded because a previous response may still be visible and
        would incorrectly dedup identical patterns from a new response.

        Called on THINKING entry.

        Args:
            display: Full terminal display lines.
        """
        snap: set[str] = set()
        for line in display:
            stripped = line.strip()
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
                snap.add(stripped)
        self.thinking_snapshot = snap

    def clear(self) -> None:
        """Clear dedup state for a fresh response cycle.

        Called on USER_MESSAGE transitions.
        """
        self.sent_lines.clear()
        self.thinking_snapshot.clear()

    def filter_new(
        self, content: str, *, use_snapshot: bool = False,
    ) -> str:
        """Filter content to only new (unsent) lines.

        Preserves blank lines.  Repeated lines *within* the same response
        (e.g. multiple ``return False`` in code) are preserved — only lines
        already in the sent set from a *previous* extraction are filtered out.
        After filtering, all content lines are recorded as sent.

        Args:
            content: Newline-separated content string.
            use_snapshot: If True, also subtract the THINKING chrome snapshot.

        Returns:
            Filtered and dedented content string, or empty string.
        """
        snap = self.thinking_snapshot if use_snapshot else set()
        new_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
            elif stripped not in self.sent_lines and stripped not in snap:
                new_lines.append(line)
        # Record all content lines as sent AFTER the full batch
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped:
                self.sent_lines.add(stripped)
        if not new_lines:
            return ""
        return textwrap.dedent("\n".join(new_lines)).strip()


class SessionOutputState:
    """All per-session state for the output processing pipeline.

    Composes the terminal emulator, streaming message manager,
    content deduplicator, previous screen state, and tool-acted flag
    into a single cohesive object.
    """

    def __init__(
        self,
        emulator: TerminalEmulator,
        streaming: StreamingMessage,
    ) -> None:
        self.emulator = emulator
        self.streaming = streaming
        self.prev_state: ScreenState = ScreenState.STARTUP
        self.dedup = ContentDeduplicator()
        self.tool_acted: bool = False


# ---------------------------------------------------------------------------
# Registry: (user_id, session_id) -> SessionOutputState
# ---------------------------------------------------------------------------

_states: dict[tuple[int, int], SessionOutputState] = {}


def get_or_create(
    user_id: int,
    session_id: int,
    bot: Bot,
    edit_rate_limit: int = 3,
) -> SessionOutputState:
    """Get or lazily create a SessionOutputState for the given session.

    Args:
        user_id: Telegram user (chat) ID.
        session_id: Claude session ID.
        bot: Telegram Bot instance for StreamingMessage.
        edit_rate_limit: Max edit_message calls per second.

    Returns:
        The (possibly new) SessionOutputState.
    """
    key = (user_id, session_id)
    if key not in _states:
        from src.parsing.terminal_emulator import TerminalEmulator
        from src.telegram.streaming_message import StreamingMessage

        _states[key] = SessionOutputState(
            emulator=TerminalEmulator(),
            streaming=StreamingMessage(
                bot=bot, chat_id=user_id, edit_rate_limit=edit_rate_limit,
            ),
        )
    return _states[key]


def cleanup(user_id: int, session_id: int) -> None:
    """Remove session state, freeing resources.

    Called when a session terminates.

    Args:
        user_id: Telegram user (chat) ID.
        session_id: Claude session ID.
    """
    _states.pop((user_id, session_id), None)


def mark_tool_acted(user_id: int, session_id: int) -> None:
    """Signal that a tool approval callback was processed for this session."""
    key = (user_id, session_id)
    state = _states.get(key)
    if state:
        state.tool_acted = True


def is_tool_request_pending(user_id: int, session_id: int) -> bool:
    """Check whether the session is currently showing a tool approval menu."""
    key = (user_id, session_id)
    state = _states.get(key)
    if not state:
        return False
    if state.tool_acted:
        return False
    return state.prev_state == ScreenState.TOOL_REQUEST
