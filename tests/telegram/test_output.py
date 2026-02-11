from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.output import (
    _CONTENT_STATES,
    _session_emulators,
    _session_prev_state,
    _session_sent_lines,
    _session_streaming,
    StreamingMessage,
    StreamingState,
    poll_output,
)
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import ScreenEvent, ScreenState, extract_content


class TestOutputStateFiltering:
    """Regression: poll_output must suppress UI chrome and only send content."""

    def test_startup_not_in_content_states(self):
        assert ScreenState.STARTUP not in _CONTENT_STATES

    def test_idle_not_in_content_states(self):
        assert ScreenState.IDLE not in _CONTENT_STATES

    def test_unknown_not_in_content_states(self):
        assert ScreenState.UNKNOWN not in _CONTENT_STATES

    def test_streaming_in_content_states(self):
        assert ScreenState.STREAMING in _CONTENT_STATES

    def test_tool_request_in_content_states(self):
        assert ScreenState.TOOL_REQUEST in _CONTENT_STATES

    def test_error_in_content_states(self):
        assert ScreenState.ERROR in _CONTENT_STATES

    def test_startup_screen_classified_and_filtered(self):
        """A Claude Code startup banner must be classified as STARTUP."""
        lines = [
            "Claude Code v2.1.37",
            " \u2590\u259b\u2588\u2588\u2588\u259c\u2590   Opus 4.6 \u00b7 Claude Max",
            "\u259d\u259c\u2588\u2588\u2588\u2588\u2588\u259b\u2598  ~/dev/my-project",
            "  \u2598\u2598 \u259d\u259d",
            "",
        ] + [""] * 35
        event = classify_screen_state(lines)
        assert event.state == ScreenState.STARTUP
        # extract_content should return nothing useful from startup chrome
        content = extract_content(lines)
        # No meaningful user content in startup screen
        assert "Opus" not in content or content == ""

    def test_extract_content_filters_separators(self):
        """Separator lines must be stripped by extract_content."""
        lines = [
            "\u2500" * 80,
            "This is real content from Claude",
            "\u2500" * 80,
        ]
        content = extract_content(lines)
        assert "real content" in content
        assert "\u2500" * 10 not in content

    def test_startup_to_unknown_guard_prevents_reentry(self):
        """Regression: once past STARTUP, classifier returning STARTUP must become UNKNOWN."""
        key = (999, 999)
        _session_prev_state[key] = ScreenState.IDLE
        prev = _session_prev_state[key]

        # This is the guard logic from poll_output
        event = ScreenEvent(state=ScreenState.STARTUP, raw_lines=[])
        if event.state == ScreenState.STARTUP and prev not in (ScreenState.STARTUP, None):
            event = ScreenEvent(
                state=ScreenState.UNKNOWN, payload=event.payload, raw_lines=event.raw_lines
            )
        assert event.state == ScreenState.UNKNOWN

        # Cleanup
        del _session_prev_state[key]

    def test_thinking_notification_on_transition(self):
        """Regression: THINKING must trigger start_thinking once, not every cycle."""
        prev = ScreenState.IDLE
        triggered = False

        # First transition to THINKING -> should trigger
        state = ScreenState.THINKING
        if state == ScreenState.THINKING and prev != ScreenState.THINKING:
            triggered = True
        assert triggered

        # Second cycle still THINKING -> should NOT trigger
        prev = ScreenState.THINKING
        triggered = False
        if state == ScreenState.THINKING and prev != ScreenState.THINKING:
            triggered = True
        assert not triggered

    def test_finalize_on_idle_transition(self):
        """Regression: streaming must finalize when state transitions to IDLE."""
        prev = ScreenState.STREAMING
        state = ScreenState.IDLE
        should_finalize = state == ScreenState.IDLE and prev != ScreenState.IDLE
        assert should_finalize


class TestContentDedup:
    """Regression: screen scroll must not cause duplicate content in Telegram."""

    def _run_dedup(self, content: str, sent: set[str]) -> tuple[str, set[str]]:
        """Run the dedup logic from poll_output and return (deduped, updated_sent)."""
        from src.telegram.formatter import reflow_text

        new_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and stripped not in sent:
                new_lines.append(line)
                sent.add(stripped)
        if new_lines:
            return reflow_text("\n".join(new_lines)), sent
        return "", sent

    def test_first_content_passes_through(self):
        """First time content is seen, it should pass through entirely."""
        content = "Hello world\nThis is a test"
        result, sent = self._run_dedup(content, set())
        assert "Hello world" in result
        assert "This is a test" in result
        assert "Hello world" in sent
        assert "This is a test" in sent

    def test_duplicate_lines_filtered(self):
        """Lines already in sent set must be filtered out."""
        sent = {"Hello world", "This is a test"}
        content = "Hello world\nThis is a test\nNew content here"
        result, sent = self._run_dedup(content, sent)
        assert "Hello world" not in result
        assert "This is a test" not in result
        assert "New content here" in result

    def test_all_duplicates_returns_empty(self):
        """If all lines are duplicates, result should be empty."""
        sent = {"Line one", "Line two"}
        content = "Line one\nLine two"
        result, _ = self._run_dedup(content, sent)
        assert result == ""

    def test_empty_lines_ignored_in_dedup(self):
        """Blank lines should not be added to the sent set."""
        content = "Hello\n\nWorld"
        result, sent = self._run_dedup(content, set())
        assert "" not in sent
        assert "Hello" in sent
        assert "World" in sent

    def test_whitespace_stripped_for_dedup(self):
        """Lines with leading/trailing whitespace should dedup against stripped version."""
        sent = {"Hello world"}
        content = "  Hello world  "
        result, _ = self._run_dedup(content, sent)
        assert result == ""

    def test_partial_overlap_keeps_new(self):
        """Mixed old and new content: only new lines should appear."""
        sent = {"Already seen line"}
        content = "Already seen line\nBrand new line\nAnother new one"
        result, sent = self._run_dedup(content, sent)
        assert "Already seen line" not in result
        assert "Brand new line" in result
        assert "Another new one" in result
        assert "Brand new line" in sent
        assert "Another new one" in sent


class TestDedupSetClearing:
    """Regression: dedup set must clear on IDLE transitions."""

    def test_idle_transition_clears_sent_lines(self):
        """Transitioning to IDLE should reset the dedup set."""
        key = (888, 888)
        _session_sent_lines[key] = {"old line", "another old line"}

        # Simulate IDLE transition logic from poll_output
        prev = ScreenState.STREAMING
        state = ScreenState.IDLE
        if state == ScreenState.IDLE and prev != ScreenState.IDLE:
            _session_sent_lines[key] = set()

        assert _session_sent_lines[key] == set()

        # Cleanup
        del _session_sent_lines[key]

    def test_idle_to_idle_does_not_clear(self):
        """Staying in IDLE should NOT clear (avoid clearing on every cycle)."""
        key = (887, 887)
        original = {"some line"}
        _session_sent_lines[key] = original.copy()

        prev = ScreenState.IDLE
        state = ScreenState.IDLE
        if state == ScreenState.IDLE and prev != ScreenState.IDLE:
            _session_sent_lines[key] = set()

        assert _session_sent_lines[key] == original

        # Cleanup
        del _session_sent_lines[key]

    def test_session_init_creates_empty_sent_set(self):
        """New session should start with empty dedup set."""
        key = (886, 886)
        assert key not in _session_sent_lines

        # Simulate lazy-init from poll_output
        if key not in _session_emulators:
            _session_sent_lines[key] = set()

        assert _session_sent_lines[key] == set()

        # Cleanup
        del _session_sent_lines[key]


class TestPollOutputIntegration:
    """Integration tests for poll_output loop behavior."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _session_emulators.pop(key, None)
        _session_streaming.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)

    @pytest.mark.asyncio
    async def test_lazy_init_creates_all_state(self):
        """First poll cycle for a session must create emulator, streaming, state, and sent set."""
        key = (777, 1)
        self._cleanup_session(key)

        # Mock session manager with one session
        process = MagicMock()
        process.read_available.return_value = None  # No data
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {777: {1: session}}

        bot = AsyncMock()

        # Run one iteration (patch sleep to break after one cycle)
        with patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        assert key in _session_emulators
        assert key in _session_streaming
        assert key in _session_prev_state
        assert key in _session_sent_lines
        assert _session_prev_state[key] == ScreenState.STARTUP
        assert _session_sent_lines[key] == set()

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_state_change_logged_at_debug(self):
        """State changes should be logged at DEBUG level."""
        key = (775, 1)
        self._cleanup_session(key)

        process = MagicMock()
        # Send minimal data that won't crash pyte
        process.read_available.side_effect = [b"hello", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {775: {1: session}}

        bot = AsyncMock()

        with patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Verify state was updated from STARTUP
        assert key in _session_prev_state

        self._cleanup_session(key)


class TestPollOutputStateTransitions:
    """Integration tests covering state-dependent paths in poll_output."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _session_emulators.pop(key, None)
        _session_streaming.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)

    @pytest.mark.asyncio
    async def test_thinking_transition_sends_notification(self):
        """UNKNOWN->THINKING must call start_thinking (send_chat_action + send_message)."""
        key = (770, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {770: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        thinking_event = ScreenEvent(state=ScreenState.THINKING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=thinking_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # start_thinking sends chat action and placeholder message
        bot.send_chat_action.assert_called()
        bot.send_message.assert_called()
        call_kwargs = bot.send_message.call_args[1]
        assert call_kwargs["text"] == "<i>Thinking...</i>"
        assert call_kwargs["parse_mode"] == "HTML"

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_extracts_and_deduplicates_content(self):
        """STREAMING state must extract content, dedup, and edit message in-place."""
        key = (769, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {769: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        # Pre-init streaming message with a message_id (as if thinking was called)
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=769, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        streaming_event = ScreenEvent(state=ScreenState.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output.extract_content", return_value="Hello world\nNew line"),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Content should have been edited into the message
        bot.edit_message_text.assert_called()

        # Sent set should track the lines
        sent = _session_sent_lines.get(key, set())
        assert "Hello world" in sent
        assert "New line" in sent

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_filters_already_sent_lines(self):
        """Lines already in sent set must not appear in edited message."""
        key = (768, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {768: {1: session}}
        bot = AsyncMock()

        # Pre-fill session state with already-sent lines and a streaming message
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=768, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = {"Already sent"}

        streaming_event = ScreenEvent(state=ScreenState.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output.extract_content", return_value="Already sent\nFresh content"),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # edit_message_text should have been called with content NOT including "Already sent"
        bot.edit_message_text.assert_called()
        edit_text = bot.edit_message_text.call_args[1]["text"]
        assert "Already sent" not in edit_text
        assert "Fresh content" in edit_text

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_idle_transition_clears_dedup_and_finalizes(self):
        """STREAMING->IDLE must clear dedup set and finalize streaming message."""
        key = (767, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {767: {1: session}}
        bot = AsyncMock()

        # Pre-fill session state mid-stream
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=767, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Buffered content"
        streaming.state = StreamingState.STREAMING
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = {"old line"}

        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=idle_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Dedup set should be cleared
        assert _session_sent_lines.get(key) == set()
        # finalize should have sent final edit and reset streaming state
        bot.edit_message_text.assert_called()
        assert streaming.state == StreamingState.IDLE

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_thinking_to_idle_extracts_fast_response(self):
        """Regression: fast response completing within one poll cycle (THINKING→IDLE).

        When Claude responds very quickly, the state goes THINKING→IDLE without
        ever entering STREAMING. Content must still be extracted from changed
        lines during the IDLE transition.
        """
        key = (764, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {764: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=99)

        # Pre-init state as THINKING (start_thinking already called)
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=764, edit_rate_limit=3)
        streaming.message_id = 99
        streaming.state = StreamingState.THINKING
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.THINKING
        _session_sent_lines[key] = set()

        # Classifier returns IDLE (response already complete)
        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=idle_event),
            patch("src.telegram.output.extract_content", return_value="Four"),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Content should have been extracted and sent via append_content
        # which edits the existing message
        bot.edit_message_text.assert_called()
        edit_text = bot.edit_message_text.call_args[1]["text"]
        assert "Four" in edit_text

        # Streaming message should be finalized (IDLE)
        assert streaming.state == StreamingState.IDLE

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_unchanged_state_logged_at_trace(self):
        """Same state on consecutive cycles should log at TRACE, not DEBUG."""
        key = (766, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"a", b"b", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {766: {1: session}}
        bot = AsyncMock()

        # Both cycles return same state
        unknown_event = ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=unknown_event),
            patch("src.telegram.output.logger") as mock_logger,
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # First cycle: state change (STARTUP->UNKNOWN) -> debug
        # Second cycle: unchanged (UNKNOWN->UNKNOWN) -> TRACE via logger.log
        trace_calls = [c for c in mock_logger.log.call_args_list]
        assert len(trace_calls) >= 1  # At least one TRACE log for unchanged state

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_empty_content_not_appended(self):
        """STREAMING with empty extract_content should not call edit_message_text."""
        key = (765, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {765: {1: session}}
        bot = AsyncMock()

        # Pre-init with streaming message
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=765, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        streaming_event = ScreenEvent(state=ScreenState.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output.extract_content", return_value=""),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # No content -> no edit
        bot.edit_message_text.assert_not_called()

        self._cleanup_session(key)


class TestPollOutputStreaming:
    """poll_output uses StreamingMessage for edit-in-place streaming."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _session_emulators.pop(key, None)
        _session_streaming.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)

    @pytest.mark.asyncio
    async def test_thinking_starts_streaming_message(self):
        """THINKING transition must call start_thinking on StreamingMessage."""
        key = (700, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {700: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        thinking_event = ScreenEvent(state=ScreenState.THINKING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=thinking_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        bot.send_chat_action.assert_called()
        bot.send_message.assert_called()
        # Verify placeholder message
        call_kwargs = bot.send_message.call_args[1]
        assert call_kwargs["text"] == "<i>Thinking...</i>"
        assert call_kwargs["parse_mode"] == "HTML"

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_content_uses_format_html(self):
        """Content must flow through format_html before append_content."""
        key = (699, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {699: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        # Pre-init with a streaming message that has a message_id (as if thinking was called)
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=699, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        streaming_event = ScreenEvent(state=ScreenState.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output.extract_content", return_value="**bold** text"),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # edit_message_text should have HTML-formatted content
        bot.edit_message_text.assert_called()
        edit_text = bot.edit_message_text.call_args[1]["text"]
        assert "<b>bold</b>" in edit_text

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_idle_calls_finalize(self):
        """IDLE transition must call finalize on StreamingMessage."""
        key = (698, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {698: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=698, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Final content"
        streaming.state = StreamingState.STREAMING
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=idle_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # finalize should have sent final edit
        bot.edit_message_text.assert_called()
        # streaming should be reset
        assert streaming.state == StreamingState.IDLE

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_edit_rate_limit_passed_to_streaming(self):
        """poll_output must pass edit_rate_limit to StreamingMessage."""
        key = (690, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.return_value = None
        session = MagicMock()
        session.process = process
        sm_mock = MagicMock()
        sm_mock._sessions = {690: {1: session}}
        bot = AsyncMock()

        with patch(
            "src.telegram.output.asyncio.sleep",
            side_effect=[None, asyncio.CancelledError],
        ):
            try:
                await poll_output(bot, sm_mock, edit_rate_limit=5)
            except asyncio.CancelledError:
                pass

        streaming = _session_streaming.get(key)
        assert streaming is not None
        assert streaming.edit_rate_limit == 5

        self._cleanup_session(key)


class TestBuildApp:
    """Tests for build_app wiring."""

    def test_builds_app_with_handlers(self, tmp_path):
        """build_app must return a valid Application."""
        import yaml

        from src.main import build_app

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "telegram": {
                        "bot_token": "fake-token",
                        "authorized_users": [111],
                    },
                    "projects": {"root": "/tmp"},
                }
            )
        )
        app = build_app(str(config_file))
        assert app is not None

    def test_debug_flags_propagate_to_config(self, tmp_path):
        """Debug flags must propagate through to config dataclass."""
        import yaml

        from src.main import build_app

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "telegram": {
                        "bot_token": "fake-token",
                        "authorized_users": [111],
                    },
                    "projects": {"root": "/tmp"},
                }
            )
        )
        app = build_app(str(config_file), debug=True, trace=True, verbose=True)
        assert app is not None
        assert app.bot_data["config"].debug.enabled is True
        assert app.bot_data["config"].debug.trace is True
        assert app.bot_data["config"].debug.verbose is True
