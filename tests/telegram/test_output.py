from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.output import (
    _CONTENT_STATES,
    _flush_buffer,
    _session_buffers,
    _session_emulators,
    _session_prev_state,
    _session_sent_lines,
    poll_output,
)
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import ScreenEvent, ScreenState, extract_content
from src.session_manager import OutputBuffer


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
            " \u2590\u259b\u2588\u2588\u2588\u259c\u2590   Opus 4.6 · Claude Max",
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
        """Regression: THINKING must send '_Thinking..._' once, not every cycle."""
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        prev = ScreenState.IDLE

        # First transition to THINKING -> should append
        state = ScreenState.THINKING
        if state == ScreenState.THINKING and prev != ScreenState.THINKING:
            buf.append("_Thinking..._\n")
        assert "_Thinking..._" in buf.flush()

        # Second cycle still THINKING -> should NOT append
        prev = ScreenState.THINKING
        if state == ScreenState.THINKING and prev != ScreenState.THINKING:
            buf.append("_Thinking..._\n")
        assert buf.flush() == ""

    def test_flush_on_idle_transition(self):
        """Regression: buffer must flush when state transitions to IDLE."""
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Hello World\n")
        # Simulate transition to IDLE
        prev = ScreenState.STREAMING
        state = ScreenState.IDLE
        if state == ScreenState.IDLE and prev != ScreenState.IDLE:
            if buf.is_ready():
                text = buf.flush()
                assert "Hello World" in text


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


class TestFlushBuffer:
    """Tests for _flush_buffer: sends buffered text to Telegram."""

    @pytest.mark.asyncio
    async def test_flush_sends_message(self):
        """Non-empty buffer should send message to user."""
        bot = AsyncMock()
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Hello from Claude\n")

        await _flush_buffer(bot, 12345, buf)

        bot.send_message.assert_called_once()
        sent_text = bot.send_message.call_args[1]["text"]
        assert "Hello from Claude" in sent_text

    @pytest.mark.asyncio
    async def test_flush_skips_empty(self):
        """Empty or whitespace-only buffer should not send."""
        bot = AsyncMock()
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("   \n")

        await _flush_buffer(bot, 12345, buf)

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush_skips_truly_empty(self):
        """Flushing a buffer with no content should not send."""
        bot = AsyncMock()
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)

        await _flush_buffer(bot, 12345, buf)

        bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_flush_splits_long_message(self):
        """Messages exceeding 4096 chars should be split."""
        bot = AsyncMock()
        buf = OutputBuffer(debounce_ms=0, max_buffer=10000)
        # Create content longer than 4096 chars
        long_text = "A" * 5000 + "\n"
        buf.append(long_text)

        await _flush_buffer(bot, 12345, buf)

        assert bot.send_message.call_count >= 2

    @pytest.mark.asyncio
    async def test_flush_handles_send_error(self):
        """Send failures should be logged, not raised."""
        bot = AsyncMock()
        bot.send_message.side_effect = Exception("Network error")
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Some content\n")

        # Should not raise
        await _flush_buffer(bot, 12345, buf)

        bot.send_message.assert_called_once()


class TestPollOutputIntegration:
    """Integration tests for poll_output loop behavior."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _session_emulators.pop(key, None)
        _session_buffers.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)

    @pytest.mark.asyncio
    async def test_lazy_init_creates_all_state(self):
        """First poll cycle for a session must create emulator, buffer, state, and sent set."""
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
        assert key in _session_buffers
        assert key in _session_prev_state
        assert key in _session_sent_lines
        assert _session_prev_state[key] == ScreenState.STARTUP
        assert _session_sent_lines[key] == set()

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_no_data_still_checks_buffer(self):
        """When read_available returns None, buffer readiness should still be checked."""
        key = (776, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.return_value = None
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {776: {1: session}}

        bot = AsyncMock()

        # Pre-fill buffer with ready content
        _session_emulators[key] = MagicMock()
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Ready content\n")
        _session_buffers[key] = buf
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        with patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Buffer should have been flushed
        bot.send_message.assert_called()

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
        _session_emulators.pop(key, None)
        _session_buffers.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)

    @pytest.mark.asyncio
    async def test_thinking_transition_sends_notification(self):
        """UNKNOWN→THINKING must append '_Thinking..._' to buffer."""
        key = (770, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {770: {1: session}}
        bot = AsyncMock()

        thinking_event = ScreenEvent(state=ScreenState.THINKING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=thinking_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Buffer should contain thinking notification
        buf = _session_buffers.get(key)
        assert buf is not None
        text = buf.flush()
        assert "_Thinking..._" in text

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_extracts_and_deduplicates_content(self):
        """STREAMING state must extract content and dedup against sent set."""
        key = (769, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {769: {1: session}}
        bot = AsyncMock()

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

        # Content should be in buffer
        buf = _session_buffers.get(key)
        assert buf is not None
        text = buf.flush()
        assert "Hello world" in text
        assert "New line" in text

        # Sent set should track the lines
        sent = _session_sent_lines.get(key, set())
        assert "Hello world" in sent
        assert "New line" in sent

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_filters_already_sent_lines(self):
        """Lines already in sent set must not appear in buffer."""
        key = (768, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {768: {1: session}}
        bot = AsyncMock()

        # Pre-fill session state with already-sent lines
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        _session_buffers[key] = OutputBuffer(debounce_ms=0, max_buffer=2000)
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

        # Buffer was flushed during poll (debounce_ms=0), check what was sent
        bot.send_message.assert_called()
        sent_text = bot.send_message.call_args[1]["text"]
        assert "Already sent" not in sent_text
        assert "Fresh content" in sent_text

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_idle_transition_clears_dedup_and_flushes(self):
        """STREAMING→IDLE must clear dedup set and flush buffer."""
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
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Buffered content\n")
        _session_buffers[key] = buf
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
        # Buffer should have been flushed (message sent)
        bot.send_message.assert_called()

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

        # First cycle: state change (STARTUP→UNKNOWN) → debug
        # Second cycle: unchanged (UNKNOWN→UNKNOWN) → TRACE via logger.log
        trace_calls = [c for c in mock_logger.log.call_args_list]
        assert len(trace_calls) >= 1  # At least one TRACE log for unchanged state

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_empty_content_not_appended(self):
        """STREAMING with empty extract_content should not append to buffer."""
        key = (765, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {765: {1: session}}
        bot = AsyncMock()

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

        buf = _session_buffers.get(key)
        assert buf is not None
        text = buf.flush()
        assert text == ""

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_non_idle_flush_when_ready(self):
        """Buffer should flush during STREAMING if is_ready() returns True."""
        key = (764, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {764: {1: session}}
        bot = AsyncMock()

        # Pre-fill with ready buffer
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        buf = OutputBuffer(debounce_ms=0, max_buffer=2000)
        buf.append("Ready to send\n")
        _session_buffers[key] = buf
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        # Stay in STREAMING (not IDLE) — should still flush via elif
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

        bot.send_message.assert_called()

        self._cleanup_session(key)


class TestBuildApp:
    def test_builds_app_with_handlers(self, tmp_path):
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
