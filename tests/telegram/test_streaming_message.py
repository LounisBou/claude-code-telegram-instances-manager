"""Tests for StreamingMessage and StreamingState classes in output.py."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.streaming_message import StreamingMessage, StreamingState


class TestStreamingMessageInit:
    """StreamingMessage must initialize in IDLE state."""

    def test_initial_state_is_idle(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        assert sm.state == StreamingState.IDLE
        assert sm.message_id is None
        assert sm.accumulated == ""


class TestStreamingMessageThinking:
    """start_thinking() must send typing action and placeholder."""

    @pytest.mark.asyncio
    async def test_sends_typing_action(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        bot.send_chat_action.assert_called_once_with(chat_id=123, action="typing")

    @pytest.mark.asyncio
    async def test_sends_placeholder_message(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        bot.send_message.assert_called_once_with(
            chat_id=123, text="<i>Thinking...</i>", parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_stores_message_id(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        assert sm.message_id == 42
        assert sm.state == StreamingState.THINKING

    @pytest.mark.asyncio
    async def test_starts_typing_loop(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        assert sm._typing_task is not None
        assert not sm._typing_task.done()
        sm._typing_task.cancel()
        try:
            await sm._typing_task
        except asyncio.CancelledError:
            pass


class TestStreamingMessageAppendContent:
    """append_content() must edit message with accumulated HTML."""

    @pytest.mark.asyncio
    async def test_first_content_cancels_typing(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        typing_task = sm._typing_task
        await sm.append_content("Hello")
        assert sm._typing_task is None
        # Allow the cancellation to propagate through the event loop
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        assert typing_task.cancelled()

    @pytest.mark.asyncio
    async def test_accumulates_content(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        sm.last_edit_time = 0
        await sm.append_content("Hello ")
        await sm.append_content("World")
        assert sm.accumulated == "Hello World"

    @pytest.mark.asyncio
    async def test_edits_message_when_throttle_allows(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        sm.last_edit_time = 0
        await sm.append_content("Hello")
        bot.edit_message_text.assert_called_with(
            chat_id=123, message_id=42, text="Hello", parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_throttles_edits(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        sm.last_edit_time = time.monotonic()
        await sm.append_content("Hello")
        bot.edit_message_text.assert_not_called()
        assert sm.accumulated == "Hello"

    @pytest.mark.asyncio
    async def test_state_transitions_to_streaming(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        sm.last_edit_time = 0
        await sm.append_content("Hello")
        assert sm.state == StreamingState.STREAMING


class TestStreamingMessageOverflow:
    """Content exceeding 4096 chars must trigger overflow."""

    @pytest.mark.asyncio
    async def test_overflow_splits_at_newline(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=99)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0
        content = "A" * 4000 + "\n" + "B" * 200
        await sm.append_content(content)
        bot.edit_message_text.assert_called()
        assert bot.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_overflow_continues_with_remainder(self):
        bot = AsyncMock()
        new_msg = MagicMock(message_id=99)
        bot.send_message.return_value = new_msg
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0
        content = "A" * 4000 + "\n" + "B" * 200
        await sm.append_content(content)
        assert sm.message_id == 99


class TestStreamingMessageFinalize:
    """finalize() must send final edit and reset state."""

    @pytest.mark.asyncio
    async def test_finalize_sends_final_edit(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.accumulated = "Final content"
        sm.state = StreamingState.STREAMING
        await sm.finalize()
        bot.edit_message_text.assert_called_with(
            chat_id=123, message_id=42, text="Final content", parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_finalize_resets_state(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.accumulated = "Content"
        sm.state = StreamingState.STREAMING
        await sm.finalize()
        assert sm.state == StreamingState.IDLE
        assert sm.message_id is None
        assert sm.accumulated == ""

    @pytest.mark.asyncio
    async def test_finalize_cancels_typing_task(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.start_thinking()
        typing_task = sm._typing_task
        await sm.finalize()
        # Allow the cancellation to propagate through the event loop
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        assert typing_task.cancelled()

    @pytest.mark.asyncio
    async def test_finalize_noop_when_empty(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        await sm.finalize()
        bot.edit_message_text.assert_not_called()


class TestStreamingMessageEdgeErrors:
    """Error handling in StreamingMessage."""

    @pytest.mark.asyncio
    async def test_edit_failure_logged_not_raised(self):
        bot = AsyncMock()
        bot.edit_message_text.side_effect = Exception("Bad request")
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0
        await sm.append_content("Hello")
        assert sm.accumulated == "Hello"

    @pytest.mark.asyncio
    async def test_html_fallback_on_parse_error(self):
        from telegram.error import BadRequest

        bot = AsyncMock()
        bot.edit_message_text.side_effect = [
            BadRequest("Can't parse entities"),
            None,
        ]
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0
        await sm.append_content("Hello <bad")
        assert bot.edit_message_text.call_count == 2
        second_call = bot.edit_message_text.call_args_list[1]
        assert second_call.kwargs.get("parse_mode") is None


    @pytest.mark.asyncio
    async def test_message_not_modified_suppressed(self):
        """'Message is not modified' error must be silently suppressed."""
        bot = AsyncMock()
        bot.edit_message_text.side_effect = Exception(
            "Message is not modified: specified new message content and reply "
            "markup are exactly the same as a current content and reply markup "
            "of the message"
        )
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.accumulated = "Same content"
        sm.state = StreamingState.STREAMING
        # Should not raise and should not log a warning
        await sm._edit()


class TestStreamingMessageSafetyNets:
    """Safety nets: auto-finalize on re-entry and auto-create on missing thinking."""

    @pytest.mark.asyncio
    async def test_start_thinking_auto_finalizes_if_streaming(self):
        """start_thinking() while still STREAMING must finalize previous response."""
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 10
        sm.accumulated = "Previous response"
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0

        await sm.start_thinking()

        # Previous response was finalized (edit with final content)
        bot.edit_message_text.assert_called_with(
            chat_id=123, message_id=10, text="Previous response", parse_mode="HTML"
        )
        # New thinking message was sent
        assert sm.message_id == 42
        assert sm.state == StreamingState.THINKING

    @pytest.mark.asyncio
    async def test_append_content_creates_message_if_idle(self):
        """append_content() while IDLE (no start_thinking) must send a new message."""
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=55)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        assert sm.state == StreamingState.IDLE
        assert sm.message_id is None

        await sm.append_content("Direct content")

        bot.send_message.assert_called_once_with(
            chat_id=123, text="Direct content", parse_mode="HTML"
        )
        assert sm.message_id == 55
        assert sm.state == StreamingState.STREAMING
        assert sm.accumulated == "Direct content"

    @pytest.mark.asyncio
    async def test_append_content_creates_message_if_message_id_none(self):
        """append_content() with None message_id must send a new message."""
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=66)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.state = StreamingState.STREAMING
        sm.message_id = None

        await sm.append_content("Orphaned content")

        bot.send_message.assert_called_once()
        assert sm.message_id == 66

    @pytest.mark.asyncio
    async def test_start_thinking_from_idle_no_finalize(self):
        """start_thinking() from IDLE should NOT call finalize (nothing to finalize)."""
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        assert sm.state == StreamingState.IDLE

        await sm.start_thinking()

        # No edit_message_text called (nothing to finalize)
        bot.edit_message_text.assert_not_called()
        assert sm.state == StreamingState.THINKING
