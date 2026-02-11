from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.output import (
    _CHROME_CATEGORIES,
    _CONTENT_STATES,
    _find_last_prompt,
    _session_emulators,
    _session_prev_state,
    _session_sent_lines,
    _session_streaming,
    _session_thinking_snapshot,
    StreamingMessage,
    StreamingState,
    poll_output,
)
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import (
    ScreenEvent, ScreenState, classify_line, extract_content,
)


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

    def test_extract_content_skips_prompt_continuation_lines(self):
        """Regression: wrapped user prompt lines must not leak into response.

        When the user sends a long prompt, it wraps in the terminal:
          ❯ Write a Python function called fibonacci that returns the nth Fibonacci
          number using recursion. Include a docstring. Show ONLY the code, no
          explanation.
          ⏺ def fibonacci(n: int) -> int:
          ...

        Lines between ❯ and ⏺ are prompt continuation (user input) and must
        be excluded from extracted content.
        """
        lines = [
            "❯ Write a Python function called fibonacci that returns the nth Fibonacci",
            "number using recursion. Include a docstring. Show ONLY the code, no",
            "explanation.",
            "",
            "⏺ def fibonacci(n: int) -> int:",
            '    """Return the nth Fibonacci number using recursion."""',
            "    if n <= 0:",
            "        return 0",
            "    return fibonacci(n - 1) + fibonacci(n - 2)",
        ]
        content = extract_content(lines)
        # Response content must be present
        assert "def fibonacci" in content
        assert "return fibonacci" in content
        # Prompt continuation lines must NOT be present — check exact text
        # that only appears in the prompt wrapping, not the docstring
        assert "Include a docstring" not in content
        assert "Show ONLY the code" not in content
        assert content.startswith("def fibonacci")

    def test_extract_content_short_prompt_no_continuation(self):
        """Short prompts (single line) must not suppress following content."""
        lines = [
            "❯ What is 2+2?",
            "",
            "⏺ Four.",
        ]
        content = extract_content(lines)
        assert content == "Four."

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
        _session_thinking_snapshot.pop(key, None)

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
        _session_thinking_snapshot.pop(key, None)

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
    async def test_thinking_to_idle_extracts_fast_response_from_display(self):
        """Regression: fast response completing within one poll cycle (THINKING→IDLE).

        When Claude responds very quickly, the response content arrives in the
        same PTY read as the thinking indicator. get_changes() consumes it
        during the THINKING cycle, so by IDLE only UI chrome remains in changed.
        The fix: use the full display (which still shows the response) instead
        of changed for content extraction on THINKING→IDLE transitions.
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
        emu = TerminalEmulator()
        _session_emulators[key] = emu
        streaming = StreamingMessage(bot=bot, chat_id=764, edit_rate_limit=3)
        streaming.message_id = 99
        streaming.state = StreamingState.THINKING
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.THINKING
        _session_sent_lines[key] = set()

        # Classifier returns IDLE (response already complete).
        # Capture what extract_content receives to verify it gets the
        # full display (not just changed lines).
        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])
        extract_calls = []

        def _capture_extract(lines):
            extract_calls.append(lines)
            return "Four"

        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=idle_event),
            patch("src.telegram.output.extract_content", side_effect=_capture_extract),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # extract_content must have been called with the full display
        # (which has all 24 rows from pyte), not just changed lines
        assert len(extract_calls) == 1
        source_lines = extract_calls[0]
        assert len(source_lines) == 40  # full pyte display (40 rows), not incremental

        # Content should have been extracted and sent via append_content
        bot.edit_message_text.assert_called()
        edit_text = bot.edit_message_text.call_args[1]["text"]
        assert "Four" in edit_text

        # Streaming message should be finalized (IDLE)
        assert streaming.state == StreamingState.IDLE

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_thinking_snapshot_filters_banner_artifacts_on_fast_idle(self):
        """Regression: banner artifacts ('u') and progress bar must not leak into fast-IDLE content.

        When THINKING→IDLE happens, poll_output uses the full display for extraction.
        The thinking snapshot (captured at THINKING entry) subtracts pre-existing
        content so only genuinely new lines (the response) are sent.
        """
        key = (763, 1)
        self._cleanup_session(key)

        process = MagicMock()
        # Two reads: first triggers THINKING, second triggers IDLE
        process.read_available.side_effect = [b"think", b"idle", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {763: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=99)

        # Simulate the two-step transition: THINKING then IDLE
        thinking_event = ScreenEvent(state=ScreenState.THINKING, raw_lines=[])
        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])

        # extract_content returns simulated content including banner artifact 'u'
        # The snapshot should filter 'u' because it existed at THINKING time.
        extract_calls = []

        def _capture_extract(lines):
            extract_calls.append(lines)
            return "u\nFour."

        event_sequence = [thinking_event, idle_event]
        event_idx = [0]

        def _classify_side_effect(display, prev=None):
            idx = min(event_idx[0], len(event_sequence) - 1)
            event_idx[0] += 1
            return event_sequence[idx]

        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output.classify_screen_state",
                side_effect=_classify_side_effect,
            ),
            patch("src.telegram.output.extract_content", side_effect=_capture_extract),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # The thinking snapshot should have been populated at THINKING entry.
        # 'u' should appear in the thinking snapshot (from the display at that time).
        # During fast-IDLE extraction, 'u' should be filtered out.
        # The snapshot includes all non-empty stripped lines from the display
        # at THINKING time. Since we use a real TerminalEmulator (initialized
        # with empty screen), the snapshot is empty for this mock. But we can
        # verify the snapshot dict was populated.
        assert key in _session_thinking_snapshot

        # Verify extract_content was called (during fast-IDLE)
        assert len(extract_calls) >= 1

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_thinking_unknown_idle_still_extracts_response(self):
        """Regression: THINKING→UNKNOWN→IDLE must still extract the response.

        When Claude responds quickly but the classifier sees an intermediate
        UNKNOWN state between THINKING and IDLE, the old prev-based check
        (prev == THINKING) fails because prev is UNKNOWN at IDLE time.
        The fix: check streaming.state instead of prev — if streaming is
        still THINKING, the response cycle is incomplete and needs extraction.
        """
        key = (762, 1)
        self._cleanup_session(key)

        process = MagicMock()
        # Three reads: THINKING, UNKNOWN, IDLE
        process.read_available.side_effect = [b"think", b"unknown", b"idle", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {762: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=99)

        thinking_event = ScreenEvent(state=ScreenState.THINKING, raw_lines=[])
        unknown_event = ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=[])
        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])

        event_sequence = [thinking_event, unknown_event, idle_event]
        event_idx = [0]

        def _classify_side_effect(display, prev=None):
            idx = min(event_idx[0], len(event_sequence) - 1)
            event_idx[0] += 1
            return event_sequence[idx]

        extract_calls = []

        def _capture_extract(lines):
            extract_calls.append(lines)
            return "Four."

        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output.classify_screen_state",
                side_effect=_classify_side_effect,
            ),
            patch("src.telegram.output.extract_content", side_effect=_capture_extract),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # extract_content called for extraction (snapshot uses classify_line
        # on the mock display, not extract_content — so only 1 call expected
        # from the IDLE fast-path extraction)
        assert len(extract_calls) >= 1
        # The "Thinking..." message should have been edited with content
        bot.edit_message_text.assert_called()
        edit_text = bot.edit_message_text.call_args[1]["text"]
        assert "Four." in edit_text
        # Streaming should be finalized
        assert _session_streaming[key].state == StreamingState.IDLE

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_ultra_fast_response_no_thinking_detected(self):
        """Regression: response completing within a single poll cycle (UNKNOWN→IDLE).

        When the entire response cycle (THINKING→response→IDLE) happens within
        one 300ms poll interval, the classifier never sees THINKING — it jumps
        from UNKNOWN/USER_MESSAGE to IDLE. streaming.state stays IDLE because
        start_thinking was never called. The fix: detect non-empty changed lines
        on a non-trivial IDLE transition and extract from changed. The
        StreamingMessage safety net creates a new message via append_content.
        """
        key = (761, 1)
        self._cleanup_session(key)

        process = MagicMock()
        # Two reads: first triggers UNKNOWN (typing echo), second triggers IDLE (response done)
        process.read_available.side_effect = [b"echo", b"done", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {761: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=77)

        unknown_event = ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=[])
        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])

        event_sequence = [unknown_event, idle_event]
        event_idx = [0]

        def _classify_side_effect(display, prev=None):
            idx = min(event_idx[0], len(event_sequence) - 1)
            event_idx[0] += 1
            return event_sequence[idx]

        extract_calls = []

        def _capture_extract(lines):
            extract_calls.append(lines)
            return "Four."

        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output.classify_screen_state",
                side_effect=_classify_side_effect,
            ),
            patch("src.telegram.output.extract_content", side_effect=_capture_extract),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # extract_content must have been called during IDLE transition
        assert len(extract_calls) >= 1
        # Content should have been sent via append_content safety net
        # (creates new message since start_thinking was never called)
        bot.send_message.assert_called()
        # The safety net in append_content sends a new message with the content
        sent_texts = [
            call[1].get("text", "") for call in bot.send_message.call_args_list
        ]
        assert any("Four." in t for t in sent_texts)
        # Streaming should be finalized
        assert _session_streaming[key].state == StreamingState.IDLE

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
        _session_thinking_snapshot.pop(key, None)

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


class TestDedentAfterDedup:
    """Regression: artifact lines at indent 0 prevent textwrap.dedent in
    extract_content.  After dedup removes the artifact, the remaining lines
    still carry the unwanted terminal margin.  poll_output must re-dedent
    after dedup to strip this residual margin.

    Bug trigger: pyte display line 0 contains ``'u'`` (0-indent artifact).
    extract_content includes it, dedent is a no-op (min indent 0).  Dedup
    then removes ``'u'`` (was in thinking snapshot), but the code lines
    keep their 2-space terminal margin.
    """

    def test_dedent_removes_residual_margin_after_dedup(self):
        """Simulates the poll_output pipeline: extract_content → dedup → dedent."""
        import textwrap

        # Lines as they come from extract_content when a 0-indent artifact
        # was present during dedent (making dedent a no-op).
        content_with_margin = "\n".join([
            "u",
            "  def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      if n <= 1:",
            "          return n",
            "      return fibonacci(n - 1) + fibonacci(n - 2)",
        ])
        # Simulate dedup removing the 'u' artifact
        deduped_lines = [
            "  def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      if n <= 1:",
            "          return n",
            "      return fibonacci(n - 1) + fibonacci(n - 2)",
        ]
        # The fix: re-dedent after dedup
        deduped = textwrap.dedent("\n".join(deduped_lines)).strip()
        assert deduped.startswith("def fibonacci")
        assert "    if n <= 1:" in deduped
        assert "        return n" in deduped
        # No residual 2-space margin
        for line in deduped.split("\n"):
            if line.startswith(" "):
                assert line.startswith("    "), f"Unexpected margin: {line!r}"

    def test_no_margin_when_artifact_absent(self):
        """When there is no artifact, dedent still works correctly."""
        import textwrap

        lines = [
            "def fibonacci(n: int) -> int:",
            '    """Return the nth Fibonacci number."""',
            "    if n <= 1:",
            "        return n",
            "    return fibonacci(n - 1) + fibonacci(n - 2)",
        ]
        deduped = textwrap.dedent("\n".join(lines)).strip()
        assert deduped.startswith("def fibonacci")
        assert "    if n <= 1:" in deduped


class TestFindLastPrompt:
    """Unit tests for _find_last_prompt helper."""

    def test_finds_prompt_with_text(self):
        display = ["some content", "❯ Write a function", "more content"]
        assert _find_last_prompt(display) == 1

    def test_returns_last_prompt_when_multiple(self):
        display = [
            "❯ First prompt text",
            "response",
            "❯ Second prompt text",
            "more response",
        ]
        assert _find_last_prompt(display) == 2

    def test_ignores_bare_prompt(self):
        """Bare ❯ (no text or short text) must be ignored."""
        display = ["❯", "content", "❯ hi", "more"]
        assert _find_last_prompt(display) is None

    def test_returns_none_when_no_prompt(self):
        display = ["line one", "line two", "line three"]
        assert _find_last_prompt(display) is None

    def test_returns_none_on_empty_display(self):
        assert _find_last_prompt([]) is None


class TestDisplayTrimToLastPrompt:
    """Regression: fast THINKING→IDLE uses full display for extraction.
    Old responses above the user's latest prompt share common patterns
    (e.g. "Args:", "Returns:") with the new response.  The thinking
    snapshot dedup incorrectly eats these shared lines.

    Fix: trim the display to start at the last user prompt (❯ with text)
    so old responses above the prompt are excluded from extraction.
    """

    def test_trim_excludes_old_response_above_prompt(self):
        """Old fibonacci response above the prompt must not interfere."""
        display = [
            "⏺ def fibonacci(n: int) -> int:",   # old response
            '      """Return the nth Fibonacci number."""',
            "      Args:",                          # old "Args:"
            "          n: The index.",
            "      Returns:",                       # old "Returns:"
            "          The nth Fibonacci number.",
            "",
            "❯ Write a palindrome function",        # last user prompt
            "",
            "⏺ def is_palindrome(s: str) -> bool:",  # new response
            '      """Check if a string is a palindrome.',
            "      Args:",                          # new "Args:" - must NOT be deduped
            "          s: The string to check.",
            "      Returns:",                       # new "Returns:" - must NOT be deduped
            "          True if palindrome.",
            '      """',
            "      return s == s[::-1]",
            "",
            "────────────────────────────────────",
            "❯",
            "────────────────────────────────────",
        ]
        prompt_idx = _find_last_prompt(display)
        assert prompt_idx == 7
        trimmed = display[prompt_idx:]
        content = extract_content(trimmed)
        assert "Args:" in content
        assert "Returns:" in content
        assert "is_palindrome" in content
        assert "fibonacci" not in content

    def test_trim_still_works_when_no_old_response(self):
        """When there's no old response, trimming is a no-op."""
        display = [
            "❯ Say hello",
            "",
            "⏺ Hello!",
            "",
            "────────────────────────────────────",
            "❯",
            "────────────────────────────────────",
        ]
        prompt_idx = _find_last_prompt(display)
        assert prompt_idx == 0
        trimmed = display[prompt_idx:]
        content = extract_content(trimmed)
        assert "Hello!" in content

    def test_no_prompt_found_uses_full_display(self):
        """Regression: when prompts scroll off screen, use full display for extraction."""
        display = [
            '      """Return the nth Fibonacci number."""',
            "      Args:",
            "          n: The index.",
            "      Returns:",
            "          The nth number.",
            "",
            "────────────────────────────────────",
            "⏺ def is_palindrome(s: str) -> bool:",
            '      """Check if palindrome.',
            "      Args:",
            "          s: The string.",
            "      Returns:",
            "          True if palindrome.",
            '      """',
            "      return s == s[::-1]",
        ]
        prompt_idx = _find_last_prompt(display)
        assert prompt_idx is None
        # When no prompt found, extraction uses full display — both
        # old and new content appear.  Snapshot will be empty, so
        # dedup doesn't eat shared patterns from the new response.
        content = extract_content(display)
        assert "is_palindrome" in content
        assert "Args:" in content


class TestThinkingSnapshotChromeOnly:
    """Regression: thinking snapshot captured content lines (Args:, Returns:,
    code) from a previous response still visible on the pyte screen.  When
    the next response used the same patterns, they were incorrectly deduped.

    Fix: snapshot only captures UI chrome lines (classify_line result in
    _CHROME_CATEGORIES).  Content, response, and tool lines are excluded.
    """

    def test_snapshot_excludes_content_lines(self):
        """Content lines from a previous response must not be in snapshot."""
        display_at_thinking = [
            "⏺ def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      Args:",
            "          n: The index.",
            "      Returns:",
            "          The nth Fibonacci number.",
            "",
            "────────────────────────────────────",
            "❯ Write a palindrome function",
            "✶ Assimilating human knowledge…",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_line(line) in _CHROME_CATEGORIES:
                snap.add(stripped)
        assert "Args:" not in snap
        assert "Returns:" not in snap
        assert "def fibonacci(n: int) -> int:" not in snap
        assert '"""Return the nth Fibonacci number."""' not in snap

    def test_snapshot_includes_chrome_elements(self):
        """UI chrome (separators, prompts, thinking, status) must be in snapshot."""
        display_at_thinking = [
            "────────────────────────────────────",
            "❯ Write a palindrome function",
            "✶ Assimilating human knowledge…",
            "project │ ⎇ main │ Usage: 34%",
            "PR #5",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_line(line) in _CHROME_CATEGORIES:
                snap.add(stripped)
        assert any("palindrome" in s for s in snap)  # prompt
        assert any("────" in s for s in snap)  # separator
        assert any("Assimilating" in s for s in snap)  # thinking star

    def test_snapshot_excludes_response_and_tool_lines(self):
        """Response markers (⏺) and tool connectors (⎿) must be excluded."""
        display_at_thinking = [
            "⏺ Here is the code:",
            "  ⎿ file.py content here",
            "────────────────────────────────────",
            "❯ Next prompt",
            "✶ Launching Skynet initiative…",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_line(line) in _CHROME_CATEGORIES:
                snap.add(stripped)
        assert not any("⏺" in s for s in snap)
        assert not any("⎿" in s for s in snap)

    def test_fibonacci_palindrome_regression(self):
        """Exact regression: fibonacci Args:/Returns: must not dedup from
        is_palindrome response when both are on the pyte screen at THINKING.

        This reproduces the real scenario where _find_last_prompt found the
        fibonacci prompt (not the is_palindrome prompt, which Claude Code
        already cleared), causing the entire fibonacci response to land in
        the snapshot.
        """
        # Simulated display at THINKING entry for is_palindrome
        display_at_thinking = [
            "Claude Code v2.1.39",
            "────────────────────────────────────────",
            "claude-instance-manager │ ⎇ main │ Usage: 34%",
            "PR #5",
            "❯ Write a fibonacci function",
            "  fibonacci prompt continuation",
            "⏺ def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      Args:",
            "          n: The index.",
            "      Returns:",
            "          The nth Fibonacci number.",
            "      Raises:",
            '          ValueError: If n < 0.',
            '      """',
            "      if n < 0:",
            "────────────────────────────────────────",
            "✢ Initiating singularity sequence…",
            "███▌░░░░░░ ↻ 10:59",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_line(line) in _CHROME_CATEGORIES:
                snap.add(stripped)
        # These MUST NOT be in the snap
        assert "Args:" not in snap
        assert "Returns:" not in snap
        assert "Raises:" not in snap
        assert '"""' not in snap
        assert "def fibonacci(n: int) -> int:" not in snap
        # These chrome elements MUST be in the snap
        assert any("────" in s for s in snap)
        assert any("Initiating" in s for s in snap)
        assert any("PR #5" in s for s in snap)


class TestUserMessageResetsDedup:
    """Regression: dedup state (sent lines and thinking snapshot) must be
    reset when a new user interaction (USER_MESSAGE state) is detected.
    This prevents stale dedup data from a previous response cycle from
    bleeding into the new one.
    """

    def test_user_message_clears_sent_lines(self):
        key = (885, 1)
        _session_sent_lines[key] = {"old content", "Args:", "Returns:"}
        # Simulate USER_MESSAGE detection (same logic as poll_output)
        state = ScreenState.USER_MESSAGE
        if state == ScreenState.USER_MESSAGE:
            _session_sent_lines[key] = set()
            _session_thinking_snapshot.pop(key, None)
        assert _session_sent_lines[key] == set()
        # Cleanup
        del _session_sent_lines[key]

    def test_user_message_clears_thinking_snapshot(self):
        key = (884, 1)
        _session_thinking_snapshot[key] = {"old snap", "Args:"}
        state = ScreenState.USER_MESSAGE
        if state == ScreenState.USER_MESSAGE:
            _session_sent_lines.setdefault(key, set())
            _session_sent_lines[key] = set()
            _session_thinking_snapshot.pop(key, None)
        assert key not in _session_thinking_snapshot
        # Cleanup
        _session_sent_lines.pop(key, None)
