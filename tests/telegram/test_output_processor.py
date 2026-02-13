"""Tests for SessionProcessor and ExtractionMode."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.parsing.models import ScreenEvent, ScreenState
from src.telegram.output_processor import (
    ExtractionMode,
    SessionProcessor,
    _CONTENT_STATES,
)
from src.telegram.output_state import ContentDeduplicator, SessionOutputState
from src.telegram.streaming_message import StreamingState


def _make_state(
    prev: ScreenState = ScreenState.STARTUP,
) -> SessionOutputState:
    """Create a SessionOutputState with mocked components."""
    emu = MagicMock()
    emu.get_display.return_value = ["" for _ in range(36)]
    emu.get_changes.return_value = []
    emu.get_full_display.return_value = ["" for _ in range(36)]
    emu.get_full_attributed_lines.return_value = [[] for _ in range(36)]
    streaming = AsyncMock()
    streaming.state = StreamingState.IDLE
    streaming.accumulated = ""
    state = SessionOutputState(emulator=emu, streaming=streaming)
    state.prev_state = prev
    return state


def _make_processor(
    state: SessionOutputState | None = None,
    user_id: int = 1,
    session_id: int = 2,
) -> SessionProcessor:
    bot = AsyncMock()
    sm = AsyncMock()
    if state is None:
        state = _make_state()
    return SessionProcessor(
        state=state,
        user_id=user_id,
        session_id=session_id,
        bot=bot,
        session_manager=sm,
    )


class TestExtractionMode:
    """ExtractionMode enum has all required values."""

    def test_none_exists(self):
        assert ExtractionMode.NONE.value == "none"

    def test_streaming_exists(self):
        assert ExtractionMode.STREAMING.value == "streaming"

    def test_fast_idle_exists(self):
        assert ExtractionMode.FAST_IDLE.value == "fast_idle"

    def test_ultra_fast_exists(self):
        assert ExtractionMode.ULTRA_FAST.value == "ultra_fast"


class TestContentStates:
    """_CONTENT_STATES has the right members."""

    def test_streaming_included(self):
        assert ScreenState.STREAMING in _CONTENT_STATES

    def test_idle_excluded(self):
        assert ScreenState.IDLE not in _CONTENT_STATES

    def test_startup_excluded(self):
        assert ScreenState.STARTUP not in _CONTENT_STATES

    def test_thinking_excluded(self):
        assert ScreenState.THINKING not in _CONTENT_STATES


class TestApplyOverrides:
    """_apply_overrides handles STARTUP lockout and tool-acted suppression."""

    def test_startup_after_non_startup_becomes_unknown(self):
        proc = _make_processor()
        event = ScreenEvent(state=ScreenState.STARTUP)
        result = proc._apply_overrides(event, ScreenState.IDLE)
        assert result.state == ScreenState.UNKNOWN

    def test_startup_from_startup_stays(self):
        proc = _make_processor()
        event = ScreenEvent(state=ScreenState.STARTUP)
        result = proc._apply_overrides(event, ScreenState.STARTUP)
        assert result.state == ScreenState.STARTUP

    def test_tool_request_suppressed_when_acted(self):
        state = _make_state()
        state.tool_acted = True
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.TOOL_REQUEST)
        result = proc._apply_overrides(event, ScreenState.STREAMING)
        assert result.state == ScreenState.UNKNOWN

    def test_non_tool_request_clears_acted(self):
        state = _make_state()
        state.tool_acted = True
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.STREAMING)
        proc._apply_overrides(event, ScreenState.TOOL_REQUEST)
        assert state.tool_acted is False


class TestExtractionModeLogic:
    """_extraction_mode determines the right extraction strategy."""

    def test_streaming_state_returns_streaming(self):
        streaming = MagicMock()
        streaming.state = StreamingState.STREAMING
        event = ScreenEvent(state=ScreenState.STREAMING)
        mode = SessionProcessor._extraction_mode(
            event, ScreenState.THINKING, ["line"], streaming,
        )
        assert mode == ExtractionMode.STREAMING

    def test_idle_from_thinking_returns_fast_idle(self):
        streaming = MagicMock()
        streaming.state = StreamingState.THINKING
        event = ScreenEvent(state=ScreenState.IDLE)
        mode = SessionProcessor._extraction_mode(
            event, ScreenState.THINKING, [], streaming,
        )
        assert mode == ExtractionMode.FAST_IDLE

    def test_idle_with_changes_no_thinking_returns_ultra_fast(self):
        streaming = MagicMock()
        streaming.state = StreamingState.IDLE
        event = ScreenEvent(state=ScreenState.IDLE)
        mode = SessionProcessor._extraction_mode(
            event, ScreenState.UNKNOWN, ["changed"], streaming,
        )
        assert mode == ExtractionMode.ULTRA_FAST

    def test_idle_from_idle_returns_none(self):
        streaming = MagicMock()
        streaming.state = StreamingState.IDLE
        event = ScreenEvent(state=ScreenState.IDLE)
        mode = SessionProcessor._extraction_mode(
            event, ScreenState.IDLE, [], streaming,
        )
        assert mode == ExtractionMode.NONE

    def test_thinking_returns_none(self):
        streaming = MagicMock()
        streaming.state = StreamingState.THINKING
        event = ScreenEvent(state=ScreenState.THINKING)
        mode = SessionProcessor._extraction_mode(
            event, ScreenState.STARTUP, [], streaming,
        )
        assert mode == ExtractionMode.NONE


class TestHandleStateEntry:
    """_handle_state_entry runs pre-extraction side effects."""

    @pytest.mark.asyncio
    async def test_startup_seeds_dedup(self):
        state = _make_state(prev=ScreenState.STARTUP)
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.STARTUP)
        display = ["Banner line", ""]
        await proc._handle_state_entry(event, ScreenState.STARTUP, display)
        assert "Banner line" in state.dedup.sent_lines

    @pytest.mark.asyncio
    async def test_user_message_clears_dedup(self):
        state = _make_state()
        state.dedup.sent_lines.add("old")
        state.dedup.thinking_snapshot.add("snap")
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.USER_MESSAGE)
        await proc._handle_state_entry(event, ScreenState.IDLE, [])
        assert len(state.dedup.sent_lines) == 0
        assert len(state.dedup.thinking_snapshot) == 0

    @pytest.mark.asyncio
    async def test_thinking_entry_starts_typing(self):
        state = _make_state(prev=ScreenState.IDLE)
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.THINKING)
        await proc._handle_state_entry(
            event, ScreenState.IDLE, ["────────────────────"],
        )
        state.streaming.start_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_thinking_entry_snapshots_chrome(self):
        state = _make_state(prev=ScreenState.IDLE)
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.THINKING)
        await proc._handle_state_entry(
            event, ScreenState.IDLE, ["────────────────────"],
        )
        assert "────────────────────" in state.dedup.thinking_snapshot

    @pytest.mark.asyncio
    async def test_auth_required_kills_session(self):
        state = _make_state()
        proc = _make_processor(state=state)
        event = ScreenEvent(state=ScreenState.AUTH_REQUIRED)
        result = await proc._handle_state_entry(
            event, ScreenState.IDLE, [],
        )
        assert result is True
        proc.session_manager.kill_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_request_sends_keyboard(self):
        state = _make_state()
        proc = _make_processor(state=state)
        event = ScreenEvent(
            state=ScreenState.TOOL_REQUEST,
            payload={
                "question": "Allow?",
                "options": ["Yes", "No"],
                "selected": 0,
            },
        )
        await proc._handle_state_entry(
            event, ScreenState.STREAMING, [],
        )
        state.streaming.finalize.assert_called()
        proc.bot.send_message.assert_called_once()


class TestFinalizeResponse:
    """_finalize_response runs post-extraction finalization."""

    @pytest.mark.asyncio
    async def test_reseeds_dedup(self):
        state = _make_state()
        proc = _make_processor(state=state)
        emu = state.emulator
        streaming = state.streaming
        streaming.state = StreamingState.IDLE
        streaming.accumulated = ""
        display = ["Some content"]
        await proc._finalize_response(False, display, emu, streaming)
        assert "Some content" in state.dedup.sent_lines

    @pytest.mark.asyncio
    async def test_clears_history_and_finalizes(self):
        state = _make_state()
        proc = _make_processor(state=state)
        emu = state.emulator
        streaming = state.streaming
        streaming.state = StreamingState.IDLE
        streaming.accumulated = ""
        await proc._finalize_response(False, [], emu, streaming)
        emu.clear_history.assert_called_once()
        streaming.finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_rerender_after_fast_idle(self):
        state = _make_state()
        proc = _make_processor(state=state)
        emu = state.emulator
        streaming = state.streaming
        streaming.state = StreamingState.STREAMING
        streaming.accumulated = "content"
        await proc._finalize_response(True, [], emu, streaming)
        # Should NOT call get_full_display (re-render skipped)
        emu.get_full_display.assert_not_called()

    @pytest.mark.asyncio
    async def test_ansi_rerender_when_not_fast_idle(self):
        state = _make_state()
        proc = _make_processor(state=state)
        emu = state.emulator
        emu.get_full_display.return_value = ["❯ hello", "⏺ Response"]
        emu.get_full_attributed_lines.return_value = [
            [MagicMock(text="❯ hello", fg="default", bold=False, italic=False)],
            [MagicMock(text="⏺ Response", fg="default", bold=False, italic=False)],
        ]
        streaming = state.streaming
        streaming.state = StreamingState.STREAMING
        streaming.accumulated = "old heuristic"
        await proc._finalize_response(False, [], emu, streaming)
        # get_full_display should have been called for re-render
        emu.get_full_display.assert_called()


class TestExtractAndSend:
    """_extract_and_send covers all extraction branches."""

    @pytest.mark.asyncio
    async def test_fast_idle_with_prompt_found(self):
        """FAST_IDLE with find_last_prompt returning an index slices source."""
        state = _make_state()
        proc = _make_processor(state=state)
        emu = state.emulator
        streaming = state.streaming
        streaming.state = StreamingState.STREAMING
        emu.get_full_display.return_value = [
            "❯ Previous prompt", "⏺ Response text", ""
        ]
        emu.get_full_attributed_lines.return_value = [
            [MagicMock(text="❯ Previous prompt", fg="default", bold=False, italic=False)],
            [MagicMock(text="⏺ Response text", fg="default", bold=False, italic=False)],
            [MagicMock(text="", fg="default", bold=False, italic=False)],
        ]
        with patch(
            "src.telegram.output_processor.find_last_prompt", return_value=0,
        ), patch(
            "src.telegram.output_processor.extract_content",
            return_value="Response text",
        ), patch(
            "src.telegram.output_processor.render_ansi",
            return_value="<b>Response text</b>",
        ):
            await proc._extract_and_send(
                ExtractionMode.FAST_IDLE, [], [], emu, streaming,
            )
        streaming.append_content.assert_called_once()
        emu.clear_history.assert_called()

    @pytest.mark.asyncio
    async def test_extract_returns_empty_content(self):
        """Early return when extract_content produces nothing."""
        state = _make_state()
        proc = _make_processor(state=state)
        streaming = state.streaming
        streaming.state = StreamingState.STREAMING
        with patch(
            "src.telegram.output_processor.extract_content", return_value="",
        ):
            await proc._extract_and_send(
                ExtractionMode.STREAMING, ["changed"], [], MagicMock(), streaming,
            )
        streaming.append_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_dedup_returns_empty(self):
        """Early return when dedup filters everything out."""
        state = _make_state()
        state.dedup.sent_lines.add("already seen")
        proc = _make_processor(state=state)
        streaming = state.streaming
        streaming.state = StreamingState.STREAMING
        with patch(
            "src.telegram.output_processor.extract_content",
            return_value="already seen",
        ):
            await proc._extract_and_send(
                ExtractionMode.STREAMING, ["changed"], [], MagicMock(), streaming,
            )
        streaming.append_content.assert_not_called()


class TestProcessCycle:
    """Integration test for process_cycle."""

    @pytest.mark.asyncio
    async def test_processes_raw_bytes(self):
        state = _make_state(prev=ScreenState.IDLE)
        proc = _make_processor(state=state)
        emu = state.emulator
        emu.get_display.return_value = ["" for _ in range(36)]
        emu.get_changes.return_value = []
        with patch(
            "src.telegram.output_processor.classify_screen_state"
        ) as mock_classify:
            mock_classify.return_value = ScreenEvent(
                state=ScreenState.IDLE,
            )
            await proc.process_cycle(b"raw data")
        emu.feed.assert_called_once_with(b"raw data")
