"""Tests for PipelineRunner transition table."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import Forbidden

from src.parsing.models import ScreenEvent, TerminalView
from src.telegram.pipeline_state import PipelinePhase, PipelineState
from src.telegram.pipeline_runner import PipelineRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline_state(phase: PipelinePhase = PipelinePhase.DORMANT):
    emu = MagicMock()
    emu.get_display.return_value = [""] * 40
    emu.get_attributed_changes.return_value = []
    emu.get_full_display.return_value = [""] * 40
    emu.get_full_attributed_lines.return_value = [[] for _ in range(40)]
    streaming = AsyncMock()
    streaming.accumulated = ""
    # replace_content is sync on the real StreamingMessage
    streaming.replace_content = MagicMock()
    ps = PipelineState(emulator=emu, streaming=streaming)
    ps.phase = phase
    return ps


def _make_runner(
    phase: PipelinePhase = PipelinePhase.DORMANT,
    user_id: int = 1,
    session_id: int = 2,
):
    ps = _make_pipeline_state(phase)
    bot = AsyncMock()
    bot.send_message.return_value = MagicMock(message_id=42)
    sm = AsyncMock()
    runner = PipelineRunner(
        state=ps,
        user_id=user_id,
        session_id=session_id,
        bot=bot,
        session_manager=sm,
    )
    return runner, ps, bot, sm


def _event(view: TerminalView, **payload) -> ScreenEvent:
    return ScreenEvent(state=view, payload=payload, raw_lines=[])


# ===================================================================
# DORMANT transitions
# ===================================================================


class TestDormantTransitions:
    """Transitions from DORMANT phase."""

    @pytest.mark.asyncio
    async def test_dormant_thinking(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.THINKING))
        assert ps.phase == PipelinePhase.THINKING
        ps.streaming.start_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_streaming(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.STREAMING))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_dormant_tool_request(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Run tool?", options=["Yes", "No"])
        )
        assert ps.phase == PipelinePhase.TOOL_PENDING
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_auth_required(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        assert ps.phase == PipelinePhase.DORMANT
        bot.send_message.assert_called_once()
        sm.kill_session.assert_called_once_with(1, 2)

    @pytest.mark.asyncio
    async def test_dormant_idle_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.IDLE))
        assert ps.phase == PipelinePhase.DORMANT
        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_dormant_unknown_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.UNKNOWN))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_startup_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.STARTUP))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_user_message_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.USER_MESSAGE))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_error_starts_streaming(self):
        """ERROR during DORMANT extracts content and enters STREAMING."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.ERROR))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_todo_list_starts_streaming(self):
        """TODO_LIST during DORMANT extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.TODO_LIST))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_parallel_agents_starts_streaming(self):
        """PARALLEL_AGENTS during DORMANT extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.PARALLEL_AGENTS))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_background_task_starts_streaming(self):
        """BACKGROUND_TASK during DORMANT extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.BACKGROUND_TASK))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_dormant_tool_running_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.TOOL_RUNNING))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_dormant_tool_result_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.TOOL_RESULT))
        assert ps.phase == PipelinePhase.DORMANT


# ===================================================================
# THINKING transitions
# ===================================================================


class TestThinkingTransitions:
    """Transitions from THINKING phase."""

    @pytest.mark.asyncio
    async def test_thinking_streaming(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.STREAMING))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_thinking_idle_extracts_then_finalizes(self):
        """THINKING -> IDLE (fast response): extract content then finalize."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.IDLE))
            assert ps.phase == PipelinePhase.DORMANT
            mock_extract.assert_called_once()
        ps.streaming.finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_thinking_tool_request(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Allow?", options=["Yes"])
        )
        assert ps.phase == PipelinePhase.TOOL_PENDING
        ps.streaming.finalize.assert_called_once()
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_thinking_thinking_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.THINKING))
        assert ps.phase == PipelinePhase.THINKING
        ps.streaming.start_thinking.assert_not_called()

    @pytest.mark.asyncio
    async def test_thinking_unknown_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.UNKNOWN))
        assert ps.phase == PipelinePhase.THINKING

    @pytest.mark.asyncio
    async def test_thinking_startup_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.STARTUP))
        assert ps.phase == PipelinePhase.THINKING

    @pytest.mark.asyncio
    async def test_thinking_user_message_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.USER_MESSAGE))
        assert ps.phase == PipelinePhase.THINKING

    @pytest.mark.asyncio
    async def test_thinking_auth_required_finalizes_and_kills(self):
        """AUTH_REQUIRED during THINKING finalizes, warns, and kills session."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        assert ps.phase == PipelinePhase.DORMANT
        ps.streaming.finalize.assert_called_once()
        bot.send_message.assert_called_once()
        sm.kill_session.assert_called_once_with(1, 2)

    @pytest.mark.asyncio
    async def test_thinking_error_extracts_and_finalizes(self):
        """ERROR during THINKING extracts content, finalizes, goes DORMANT."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.ERROR))
            assert ps.phase == PipelinePhase.DORMANT
            mock_extract.assert_called_once()
        ps.streaming.finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_thinking_todo_list_starts_streaming(self):
        """TODO_LIST during THINKING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.TODO_LIST))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_thinking_parallel_agents_starts_streaming(self):
        """PARALLEL_AGENTS during THINKING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.PARALLEL_AGENTS))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_thinking_background_task_starts_streaming(self):
        """BACKGROUND_TASK during THINKING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.BACKGROUND_TASK))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()


# ===================================================================
# STREAMING transitions
# ===================================================================


class TestStreamingTransitions:
    """Transitions from STREAMING phase."""

    @pytest.mark.asyncio
    async def test_streaming_streaming(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.STREAMING))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_idle(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.IDLE))
        assert ps.phase == PipelinePhase.DORMANT
        ps.streaming.finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_tool_request(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Write file?", options=["Yes", "No"])
        )
        assert ps.phase == PipelinePhase.TOOL_PENDING
        ps.streaming.finalize.assert_called_once()
        bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_thinking(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.THINKING))
        assert ps.phase == PipelinePhase.THINKING
        ps.streaming.finalize.assert_called_once()
        ps.streaming.start_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_tool_running(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.TOOL_RUNNING))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_tool_result(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.TOOL_RESULT))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_error(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.ERROR))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_unknown_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.UNKNOWN))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_startup_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.STARTUP))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_user_message_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.USER_MESSAGE))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_streaming_todo_list(self):
        """TODO_LIST during STREAMING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.TODO_LIST))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_parallel_agents(self):
        """PARALLEL_AGENTS during STREAMING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.PARALLEL_AGENTS))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_background_task(self):
        """BACKGROUND_TASK during STREAMING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.BACKGROUND_TASK))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_auth_required_finalizes_and_kills(self):
        """AUTH_REQUIRED during STREAMING finalizes, warns, and kills session."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        assert ps.phase == PipelinePhase.DORMANT
        ps.streaming.finalize.assert_called_once()
        bot.send_message.assert_called_once()
        sm.kill_session.assert_called_once_with(1, 2)


# ===================================================================
# TOOL_PENDING transitions
# ===================================================================


class TestToolPendingTransitions:
    """Transitions from TOOL_PENDING phase."""

    @pytest.mark.asyncio
    async def test_tool_pending_tool_running(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.TOOL_RUNNING))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_tool_pending_streaming(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.STREAMING))
        assert ps.phase == PipelinePhase.STREAMING

    @pytest.mark.asyncio
    async def test_tool_pending_thinking(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.THINKING))
        assert ps.phase == PipelinePhase.THINKING
        ps.streaming.start_thinking.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_pending_idle(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.IDLE))
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_tool_pending_tool_request_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Stale?")
        )
        assert ps.phase == PipelinePhase.TOOL_PENDING
        # Stale re-detection -- no new keyboard sent
        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_tool_pending_unknown_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.UNKNOWN))
        assert ps.phase == PipelinePhase.TOOL_PENDING

    @pytest.mark.asyncio
    async def test_tool_pending_auth_required_kills(self):
        """AUTH_REQUIRED during TOOL_PENDING warns and kills session."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        assert ps.phase == PipelinePhase.DORMANT
        bot.send_message.assert_called_once()
        sm.kill_session.assert_called_once_with(1, 2)

    @pytest.mark.asyncio
    async def test_tool_pending_error_extracts(self):
        """ERROR during TOOL_PENDING extracts content and enters STREAMING."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.ERROR))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_pending_todo_list(self):
        """TODO_LIST during TOOL_PENDING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.TODO_LIST))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_pending_parallel_agents(self):
        """PARALLEL_AGENTS during TOOL_PENDING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.PARALLEL_AGENTS))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_pending_background_task(self):
        """BACKGROUND_TASK during TOOL_PENDING extracts content."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.BACKGROUND_TASK))
            assert ps.phase == PipelinePhase.STREAMING
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_pending_startup_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.STARTUP))
        assert ps.phase == PipelinePhase.TOOL_PENDING

    @pytest.mark.asyncio
    async def test_tool_pending_user_message_noop(self):
        runner, ps, bot, sm = _make_runner(PipelinePhase.TOOL_PENDING)
        await runner.process(_event(TerminalView.USER_MESSAGE))
        assert ps.phase == PipelinePhase.TOOL_PENDING


# ===================================================================
# Action verification tests (detailed behavior checks)
# ===================================================================


class TestActionDetails:
    """Verify specific action side effects beyond phase transitions."""

    @pytest.mark.asyncio
    async def test_send_keyboard_includes_markup(self):
        """send_keyboard sends InlineKeyboardMarkup with tool approval buttons."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Run cmd?", options=["Yes, allow", "No"])
        )
        call_kwargs = bot.send_message.call_args
        assert call_kwargs is not None
        assert "reply_markup" in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_send_auth_warning_message_content(self):
        """Auth warning sends message with authentication text."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        call_kwargs = bot.send_message.call_args
        assert call_kwargs is not None
        text = call_kwargs.kwargs.get("text", call_kwargs.args[0] if call_kwargs.args else "")
        assert "auth" in text.lower() or "Auth" in text

    @pytest.mark.asyncio
    async def test_auth_warned_guard_prevents_repeated_warning(self):
        """Auth warning only fires once even if AUTH_REQUIRED persists."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        assert ps.auth_warned is True
        assert bot.send_message.call_count == 1
        runner.session_manager.kill_session.assert_called_once()

        # Second AUTH_REQUIRED should be a no-op
        bot.send_message.reset_mock()
        runner.session_manager.kill_session.reset_mock()
        ps.phase = PipelinePhase.DORMANT  # back to dormant
        await runner.process(_event(TerminalView.AUTH_REQUIRED))
        bot.send_message.assert_not_called()
        runner.session_manager.kill_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_finalize_clears_emulator_history(self):
        """Finalize calls emulator.clear_history()."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        await runner.process(_event(TerminalView.IDLE))
        ps.emulator.clear_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_idle_finalize_clears_history(self):
        """STREAMING -> IDLE finalize also clears emulator history."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        await runner.process(_event(TerminalView.IDLE))
        ps.emulator.clear_history.assert_called_once()
        ps.streaming.finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_thinking_finalize_then_think(self):
        """STREAMING -> THINKING: finalize first, then start_thinking."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        call_order = []
        ps.streaming.finalize.side_effect = lambda: call_order.append("finalize")
        ps.streaming.start_thinking.side_effect = lambda: call_order.append("start_thinking")
        await runner.process(_event(TerminalView.THINKING))
        assert call_order == ["finalize", "start_thinking"]

    @pytest.mark.asyncio
    async def test_thinking_tool_request_finalize_then_keyboard(self):
        """THINKING -> TOOL_REQUEST: finalize first, then send keyboard."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.THINKING)
        call_order = []
        ps.streaming.finalize.side_effect = lambda: call_order.append("finalize")
        bot.send_message.side_effect = lambda **kw: (
            call_order.append("send_message"),
            MagicMock(message_id=42),
        )[1]
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Allow?", options=["Yes"])
        )
        assert "finalize" in call_order
        assert "send_message" in call_order
        assert call_order.index("finalize") < call_order.index("send_message")

    @pytest.mark.asyncio
    async def test_send_keyboard_resets_tool_acted(self):
        """_send_keyboard sets tool_acted = False."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        ps.tool_acted = True
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Run?", options=["Yes"])
        )
        assert ps.tool_acted is False

    @pytest.mark.asyncio
    async def test_partial_action_failure_still_advances_phase(self):
        """If one action fails in a multi-action transition, phase still advances."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        # Make finalize succeed but send_message (used by _send_keyboard) raise
        bot.send_message.side_effect = RuntimeError("Telegram API error")
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Run?", options=["Yes"])
        )
        # Phase should still advance to TOOL_PENDING despite _send_keyboard failure
        assert ps.phase == PipelinePhase.TOOL_PENDING
        ps.streaming.finalize.assert_called_once()

    @pytest.mark.asyncio
    async def test_forbidden_kills_session_and_stops(self):
        """Forbidden from Telegram API kills session and stops processing."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        bot.send_message.side_effect = Forbidden("Forbidden: bot was blocked by the user")
        await runner.process(
            _event(TerminalView.TOOL_REQUEST, question="Run?", options=["Yes"])
        )
        runner.session_manager.kill_session.assert_called_once_with(
            runner.user_id, runner.session_id,
        )
        # Phase should NOT advance (early return)
        assert ps.phase == PipelinePhase.DORMANT

    @pytest.mark.asyncio
    async def test_forbidden_during_streaming_kills_session(self):
        """Forbidden during extract_and_send kills session."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        ps.streaming.append_content = AsyncMock(
            side_effect=Forbidden("Forbidden: bot was blocked by the user"),
        )
        ps.emulator.get_attributed_changes.return_value = [
            [MagicMock(text="⏺ hello", fg="default", bold=False, italic=False)],
        ]
        await runner.process(_event(TerminalView.STREAMING))
        runner.session_manager.kill_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_prev_view_updated_after_process(self):
        """prev_view should be updated to the event's view after processing."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.DORMANT)
        assert ps.prev_view is None
        await runner.process(_event(TerminalView.THINKING))
        assert ps.prev_view == TerminalView.THINKING

    @pytest.mark.asyncio
    async def test_streaming_streaming_extract_and_send(self):
        """STREAMING + STREAMING should call extract_and_send."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.STREAMING))
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_tool_running_extract_and_send(self):
        """STREAMING + TOOL_RUNNING should call extract_and_send."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.TOOL_RUNNING))
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_tool_result_extract_and_send(self):
        """STREAMING + TOOL_RESULT should call extract_and_send."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.TOOL_RESULT))
            mock_extract.assert_called_once()

    @pytest.mark.asyncio
    async def test_streaming_error_extract_and_send(self):
        """STREAMING + ERROR should call extract_and_send."""
        runner, ps, bot, sm = _make_runner(PipelinePhase.STREAMING)
        with patch.object(runner, "_extract_and_send", new_callable=AsyncMock) as mock_extract:
            await runner.process(_event(TerminalView.ERROR))
            mock_extract.assert_called_once()


# ===================================================================
# Integration tests: real extraction & finalization
# ===================================================================


class TestExtractAndSendIntegration:
    """Test _extract_and_send with real rendering."""

    @pytest.mark.asyncio
    async def test_no_changes_skips_send(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        ps.emulator.get_attributed_changes.return_value = []
        await runner._extract_and_send(_event(TerminalView.STREAMING))
        ps.streaming.append_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_chrome_only_skips_send(self):
        """Changes that are all chrome (separators) produce no output."""
        from src.parsing.terminal_emulator import CharSpan
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        ps.emulator.get_attributed_changes.return_value = [
            [CharSpan(text="─" * 60, fg="default", bold=False, italic=False)]
        ]
        await runner._extract_and_send(_event(TerminalView.STREAMING))
        ps.streaming.append_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_content_changes_sent(self):
        """Real content changes produce output."""
        from src.parsing.terminal_emulator import CharSpan
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        ps.emulator.get_attributed_changes.return_value = [
            [CharSpan(text="Hello world", fg="default", bold=False, italic=False)]
        ]
        await runner._extract_and_send(_event(TerminalView.STREAMING))
        ps.streaming.append_content.assert_called_once()
        html_arg = ps.streaming.append_content.call_args[0][0]
        assert "Hello" in html_arg


class TestFinalizeIntegration:
    """Test _finalize with real ANSI re-render."""

    @pytest.mark.asyncio
    async def test_finalize_clears_history(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        ps.streaming.accumulated = ""
        await runner._finalize(_event(TerminalView.IDLE))
        ps.streaming.finalize.assert_called_once()
        ps.emulator.clear_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_rerenders_when_has_content(self):
        from src.parsing.terminal_emulator import CharSpan
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        ps.streaming.accumulated = "previous content"
        ps.emulator.get_full_display.return_value = ["❯ hello", "⏺ Response text", ""]
        ps.emulator.get_full_attributed_lines.return_value = [
            [CharSpan(text="❯ hello", fg="default", bold=False, italic=False)],
            [CharSpan(text="⏺ Response text", fg="default", bold=False, italic=False)],
            [CharSpan(text="", fg="default", bold=False, italic=False)],
        ]
        await runner._finalize(_event(TerminalView.IDLE))
        ps.streaming.replace_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_finalize_skips_rerender_when_no_accumulated(self):
        runner, ps, _, _ = _make_runner(PipelinePhase.STREAMING)
        ps.streaming.accumulated = ""
        await runner._finalize(_event(TerminalView.IDLE))
        ps.streaming.replace_content.assert_not_called()
        ps.streaming.finalize.assert_called_once()
        ps.emulator.clear_history.assert_called_once()
