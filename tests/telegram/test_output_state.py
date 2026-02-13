"""Tests for SessionOutputState and registry functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from src.parsing.models import TerminalView
from src.telegram.output_state import (
    SessionOutputState,
    _states,
    cleanup,
    get_or_create,
    is_tool_request_pending,
    mark_tool_acted,
)


class TestSessionOutputStateInit:
    """SessionOutputState must compose all session components."""

    def test_has_emulator(self):
        emu = MagicMock()
        sm = MagicMock()
        state = SessionOutputState(emulator=emu, streaming=sm)
        assert state.emulator is emu

    def test_has_streaming(self):
        emu = MagicMock()
        sm = MagicMock()
        state = SessionOutputState(emulator=emu, streaming=sm)
        assert state.streaming is sm

    def test_default_prev_state_is_startup(self):
        state = SessionOutputState(emulator=MagicMock(), streaming=MagicMock())
        assert state.prev_state == TerminalView.STARTUP

    def test_has_dedup(self):
        state = SessionOutputState(emulator=MagicMock(), streaming=MagicMock())
        assert state.dedup is not None
        assert state.dedup.sent_lines == set()

    def test_tool_acted_defaults_false(self):
        state = SessionOutputState(emulator=MagicMock(), streaming=MagicMock())
        assert state.tool_acted is False


class TestRegistry:
    """get_or_create / cleanup manage session state lifecycle."""

    def setup_method(self):
        _states.clear()

    def teardown_method(self):
        _states.clear()

    def test_get_or_create_creates_new(self):
        bot = AsyncMock()
        state = get_or_create(user_id=1, session_id=2, bot=bot)
        assert state is not None
        assert (1, 2) in _states

    def test_get_or_create_returns_same_instance(self):
        bot = AsyncMock()
        s1 = get_or_create(user_id=1, session_id=2, bot=bot)
        s2 = get_or_create(user_id=1, session_id=2, bot=bot)
        assert s1 is s2

    def test_cleanup_removes_state(self):
        bot = AsyncMock()
        get_or_create(user_id=1, session_id=2, bot=bot)
        cleanup(user_id=1, session_id=2)
        assert (1, 2) not in _states

    def test_cleanup_noop_when_missing(self):
        cleanup(user_id=99, session_id=99)  # Should not raise


class TestToolActedFunctions:
    """mark_tool_acted / is_tool_request_pending delegate to state."""

    def setup_method(self):
        _states.clear()

    def teardown_method(self):
        _states.clear()

    def test_mark_tool_acted_sets_flag(self):
        bot = AsyncMock()
        state = get_or_create(user_id=1, session_id=2, bot=bot)
        mark_tool_acted(user_id=1, session_id=2)
        assert state.tool_acted is True

    def test_mark_tool_acted_noop_when_missing(self):
        mark_tool_acted(user_id=99, session_id=99)  # Should not raise

    def test_is_tool_request_pending_true(self):
        bot = AsyncMock()
        state = get_or_create(user_id=1, session_id=2, bot=bot)
        state.prev_state = TerminalView.TOOL_REQUEST
        assert is_tool_request_pending(user_id=1, session_id=2) is True

    def test_is_tool_request_pending_false_after_acted(self):
        bot = AsyncMock()
        state = get_or_create(user_id=1, session_id=2, bot=bot)
        state.prev_state = TerminalView.TOOL_REQUEST
        mark_tool_acted(user_id=1, session_id=2)
        assert is_tool_request_pending(user_id=1, session_id=2) is False

    def test_is_tool_request_pending_false_when_different_state(self):
        bot = AsyncMock()
        state = get_or_create(user_id=1, session_id=2, bot=bot)
        state.prev_state = TerminalView.STREAMING
        assert is_tool_request_pending(user_id=1, session_id=2) is False

    def test_is_tool_request_pending_false_when_missing(self):
        assert is_tool_request_pending(user_id=99, session_id=99) is False
