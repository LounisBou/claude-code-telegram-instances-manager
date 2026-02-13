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
