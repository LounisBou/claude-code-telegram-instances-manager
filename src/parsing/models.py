"""Shared data types for the terminal parsing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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
    """Classified screen state with extracted payload and raw lines."""

    state: TerminalView
    payload: dict = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)


# Backward-compatible alias
ScreenState = TerminalView
