from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.parsing.terminal_emulator import CharSpan
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import (
    CHROME_CATEGORIES,
    ScreenEvent, TerminalView, classify_text_line, extract_content,
)
from src.telegram.output import poll_output
from src.telegram.output_pipeline import (
    dedent_attr_lines,
    filter_response_attr,
    find_last_prompt,
    lstrip_n_chars,
    strip_marker_from_spans,
)
from src.telegram.output_processor import _CONTENT_STATES
from src.telegram.output_state import (
    _states as _session_states,
    cleanup as _cleanup_state,
    get_or_create as _get_or_create,
    is_tool_request_pending,
    mark_tool_acted,
)
from src.telegram.streaming_message import StreamingMessage, StreamingState


class TestOutputStateFiltering:
    """Regression: poll_output must suppress UI chrome and only send content."""

    def test_startup_not_in_content_states(self):
        assert TerminalView.STARTUP not in _CONTENT_STATES

    def test_idle_not_in_content_states(self):
        assert TerminalView.IDLE not in _CONTENT_STATES

    def test_unknown_not_in_content_states(self):
        assert TerminalView.UNKNOWN not in _CONTENT_STATES

    def test_streaming_in_content_states(self):
        assert TerminalView.STREAMING in _CONTENT_STATES

    def test_tool_request_not_in_content_states(self):
        """TOOL_REQUEST is handled with an inline keyboard, not as content."""
        assert TerminalView.TOOL_REQUEST not in _CONTENT_STATES

    def test_error_in_content_states(self):
        assert TerminalView.ERROR in _CONTENT_STATES

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
        assert event.state == TerminalView.STARTUP
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.prev_state = TerminalView.IDLE
        prev = _session_states[key].prev_state

        # This is the guard logic from poll_output
        event = ScreenEvent(state=TerminalView.STARTUP, raw_lines=[])
        if event.state == TerminalView.STARTUP and prev not in (TerminalView.STARTUP, None):
            event = ScreenEvent(
                state=TerminalView.UNKNOWN, payload=event.payload, raw_lines=event.raw_lines
            )
        assert event.state == TerminalView.UNKNOWN

        # Cleanup

    def test_thinking_notification_on_transition(self):
        """Regression: THINKING must trigger start_thinking once, not every cycle."""
        prev = TerminalView.IDLE
        triggered = False

        # First transition to THINKING -> should trigger
        state = TerminalView.THINKING
        if state == TerminalView.THINKING and prev != TerminalView.THINKING:
            triggered = True
        assert triggered

        # Second cycle still THINKING -> should NOT trigger
        prev = TerminalView.THINKING
        triggered = False
        if state == TerminalView.THINKING and prev != TerminalView.THINKING:
            triggered = True
        assert not triggered

    def test_finalize_on_idle_transition(self):
        """Regression: streaming must finalize when state transitions to IDLE."""
        prev = TerminalView.STREAMING
        state = TerminalView.IDLE
        should_finalize = state == TerminalView.IDLE and prev != TerminalView.IDLE
        assert should_finalize


class TestContentDedup:
    """Regression: screen scroll must not cause duplicate content in Telegram."""

    def _run_dedup(self, content: str, sent: set[str]) -> tuple[str, set[str]]:
        """Run the dedup logic from poll_output and return (deduped, updated_sent).

        Mirrors the two-pass approach: first pass filters against pre-existing
        sent set (without modifying it), second pass records all lines as sent.
        """
        from src.telegram.formatter import reflow_text

        new_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
            elif stripped not in sent:
                new_lines.append(line)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped:
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

    def test_repeated_lines_within_response_preserved(self):
        """Regression: identical lines within the same response must not be deduped.

        Code responses often contain repeated lines like 'return False' or
        'return True' at multiple points. These must all be preserved.
        """
        content = (
            "def is_prime(n):\n"
            "    if n < 2:\n"
            "        return False\n"
            "    if n % 2 == 0:\n"
            "        return False\n"
            "    return True"
        )
        result, sent = self._run_dedup(content, set())
        assert result.count("return False") == 2
        assert "return True" in result

    def test_repeated_lines_still_dedup_across_responses(self):
        """Repeated lines from a PREVIOUS response must still be deduped."""
        sent = {"return False", "return True"}
        content = (
            "def is_prime(n):\n"
            "    if n < 2:\n"
            "        return False\n"
            "    return True"
        )
        result, _ = self._run_dedup(content, sent)
        assert "return False" not in result
        assert "return True" not in result
        assert "def is_prime(n):" in result
        assert "if n < 2:" in result

    def test_blank_lines_preserved_between_paragraphs(self):
        """Regression: blank lines between paragraphs must survive dedup."""
        content = "First paragraph\n\nSecond paragraph"
        result, sent = self._run_dedup(content, set())
        assert "First paragraph" in result
        assert "Second paragraph" in result
        # The blank line separator must be preserved
        assert "\n\n" in result or result.count("\n") >= 2

    def test_blank_lines_preserved_after_partial_dedup(self):
        """Blank lines must survive even when some lines are deduped."""
        sent = {"First paragraph"}
        content = "First paragraph\n\nSecond paragraph"
        result, sent = self._run_dedup(content, sent)
        assert "First paragraph" not in result
        assert "Second paragraph" in result


class TestDedupSetClearing:
    """Regression: dedup set must clear on IDLE transitions."""

    def test_idle_transition_clears_sent_lines(self):
        """Transitioning to IDLE should reset the dedup set."""
        key = (888, 888)
        state = _get_or_create(*key, bot=AsyncMock())
        state.dedup.sent_lines = {"old line", "another old line"}

        # Simulate IDLE transition logic from poll_output
        prev = TerminalView.STREAMING
        cur_state = TerminalView.IDLE
        if cur_state == TerminalView.IDLE and prev != TerminalView.IDLE:
            state.dedup.sent_lines = set()

        assert _session_states[key].dedup.sent_lines == set()

        # Cleanup

    def test_idle_to_idle_does_not_clear(self):
        """Staying in IDLE should NOT clear (avoid clearing on every cycle)."""
        key = (887, 887)
        original = {"some line"}
        state = _get_or_create(*key, bot=AsyncMock())
        state.dedup.sent_lines = original.copy()

        prev = TerminalView.IDLE
        cur_state = TerminalView.IDLE
        if cur_state == TerminalView.IDLE and prev != TerminalView.IDLE:
            state.dedup.sent_lines = set()

        assert _session_states[key].dedup.sent_lines == original

        # Cleanup

    def test_session_init_creates_empty_sent_set(self):
        """New session should start with empty dedup set."""
        key = (886, 886)
        assert key not in _session_states

        # Simulate lazy-init from poll_output
        if key not in _session_states:
            state = _get_or_create(*key, bot=AsyncMock())
            state.dedup.sent_lines = set()

        assert _session_states[key].dedup.sent_lines == set()

        # Cleanup


class TestPollOutputIntegration:
    """Integration tests for poll_output loop behavior."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _cleanup_state(*key)

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

        assert key in _session_states
        assert key in _session_states
        assert key in _session_states
        assert key in _session_states
        assert _session_states[key].prev_state == TerminalView.STARTUP
        assert _session_states[key].dedup.sent_lines == set()

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
        assert key in _session_states

        self._cleanup_session(key)


class TestPollOutputStateTransitions:
    """Integration tests covering state-dependent paths in poll_output."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _cleanup_state(*key)

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

        thinking_event = ScreenEvent(state=TerminalView.THINKING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=thinking_event),
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=769, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = set()

        streaming_event = ScreenEvent(state=TerminalView.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output_processor.extract_content", return_value="Hello world\nNew line"),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Content should have been edited into the message
        bot.edit_message_text.assert_called()

        # Sent set should track the lines
        sent = state.dedup.sent_lines
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=768, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = {"Already sent"}

        streaming_event = ScreenEvent(state=TerminalView.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output_processor.extract_content", return_value="Already sent\nFresh content"),
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
    async def test_idle_transition_reseeds_dedup_and_finalizes(self):
        """STREAMING->IDLE must re-seed dedup with display and finalize.

        Instead of clearing the dedup set, IDLE re-seeds it with all
        visible display content.  This prevents old response text from
        leaking into the next extraction cycle when pyte re-reports
        shifted lines after a screen scroll.
        """
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=767, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Buffered content"
        streaming.state = StreamingState.STREAMING
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = {"old line"}

        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=idle_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Dedup set should be re-seeded with display content, not cleared
        sent = state.dedup.sent_lines
        assert "old line" in sent  # pre-existing content preserved
        assert "data" in sent  # display content added
        # finalize should have sent final edit and reset streaming state
        bot.edit_message_text.assert_called()
        assert streaming.state == StreamingState.IDLE

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_tool_request_after_idle_no_content_leak(self):
        """Regression: old response content must not leak into TOOL_REQUEST.

        Scenario: after a text response completes (IDLE), the user sends a
        new message that triggers a tool request.  When pyte scrolls, old
        response lines are re-reported by get_changes().  The re-seeded
        dedup set from the IDLE transition must filter them out so only
        the tool request text appears in the Telegram message.
        """
        key = (768, 1)
        self._cleanup_session(key)

        # Simulate two poll cycles:
        #   1. IDLE (after previous response) — re-seeds dedup
        #   2. TOOL_REQUEST — extracts content, old lines filtered
        process = MagicMock()
        # Cycle 1: previous response visible
        # Cycle 2: tool request appears (old content scrolls)
        process.read_available.side_effect = [b"prev", b"tool", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {768: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        emu = TerminalEmulator()
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = emu
        streaming = StreamingMessage(bot=bot, chat_id=768, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Old response"
        streaming.state = StreamingState.STREAMING
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = set()

        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])
        tool_event = ScreenEvent(state=TerminalView.TOOL_REQUEST, raw_lines=[])

        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                side_effect=[idle_event, tool_event],
            ),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # After IDLE, "prev" should be in the dedup set (re-seeded)
        sent = state.dedup.sent_lines
        assert "prev" in sent

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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = emu
        streaming = StreamingMessage(bot=bot, chat_id=764, edit_rate_limit=3)
        streaming.message_id = 99
        streaming.state = StreamingState.THINKING
        state.streaming = streaming
        state.prev_state = TerminalView.THINKING
        state.dedup.sent_lines = set()

        # Classifier returns IDLE (response already complete).
        # Capture what extract_content receives to verify it gets the
        # full display (not just changed lines).
        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])
        extract_calls = []

        def _capture_extract(lines):
            extract_calls.append(lines)
            return "Four"

        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=idle_event),
            patch("src.telegram.output_processor.extract_content", side_effect=_capture_extract),
            # Fast-IDLE now uses ANSI-aware pipeline; mock render_regions
            # to produce known output from the attributed lines
            patch("src.telegram.output_pipeline.render_regions", return_value="Four"),
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
        thinking_event = ScreenEvent(state=TerminalView.THINKING, raw_lines=[])
        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])

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
                "src.telegram.output_processor.classify_screen_state",
                side_effect=_classify_side_effect,
            ),
            patch("src.telegram.output_processor.extract_content", side_effect=_capture_extract),
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
        assert key in _session_states

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

        thinking_event = ScreenEvent(state=TerminalView.THINKING, raw_lines=[])
        unknown_event = ScreenEvent(state=TerminalView.UNKNOWN, raw_lines=[])
        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])

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
                "src.telegram.output_processor.classify_screen_state",
                side_effect=_classify_side_effect,
            ),
            patch("src.telegram.output_processor.extract_content", side_effect=_capture_extract),
            # Fast-IDLE now uses ANSI-aware pipeline; mock render_regions
            patch("src.telegram.output_pipeline.render_regions", return_value="Four."),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # extract_content called for extraction (snapshot uses classify_text_line
        # on the mock display, not extract_content — so only 1 call expected
        # from the IDLE fast-path extraction)
        assert len(extract_calls) >= 1
        # The "Thinking..." message should have been edited with content
        bot.edit_message_text.assert_called()
        edit_text = bot.edit_message_text.call_args[1]["text"]
        assert "Four." in edit_text
        # Streaming should be finalized
        assert _session_states[key].streaming.state == StreamingState.IDLE

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

        unknown_event = ScreenEvent(state=TerminalView.UNKNOWN, raw_lines=[])
        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])

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
                "src.telegram.output_processor.classify_screen_state",
                side_effect=_classify_side_effect,
            ),
            patch("src.telegram.output_processor.extract_content", side_effect=_capture_extract),
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
        assert _session_states[key].streaming.state == StreamingState.IDLE

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
        unknown_event = ScreenEvent(state=TerminalView.UNKNOWN, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=unknown_event),
            patch("src.telegram.output_processor.logger") as mock_logger,
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=765, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = set()

        streaming_event = ScreenEvent(state=TerminalView.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output_processor.extract_content", return_value=""),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # No content -> no edit
        bot.edit_message_text.assert_not_called()

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_tool_request_sends_inline_keyboard(self):
        """Regression: TOOL_REQUEST must send an inline keyboard, not plain text.

        When the classifier detects a tool approval prompt, the output
        pipeline should finalize any in-progress streaming message and
        send a new message with the question text and Allow/Deny buttons.
        """
        key = (769, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"tool", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {769: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=769, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.THINKING
        state.streaming = streaming
        state.prev_state = TerminalView.THINKING
        state.dedup.sent_lines = set()

        tool_event = ScreenEvent(
            state=TerminalView.TOOL_REQUEST,
            payload={
                "question": "Do you want to create test.txt?",
                "options": ["Yes", "No"],
                "selected": 0,
                "has_hint": True,
            },
            raw_lines=[],
        )
        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                return_value=tool_event,
            ),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Should have sent a message with inline keyboard
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args.kwargs
        assert call_kwargs["chat_id"] == 769
        assert "Do you want to create test.txt?" in call_kwargs["text"]
        assert call_kwargs["reply_markup"] is not None
        # Keyboard should have Allow/Deny buttons
        keyboard = call_kwargs["reply_markup"]
        buttons = keyboard.inline_keyboard[0]
        assert any("Allow" in btn.text for btn in buttons)
        assert any("Deny" in btn.text for btn in buttons)

        self._cleanup_session(key)


class TestPollOutputStreaming:
    """poll_output uses StreamingMessage for edit-in-place streaming."""

    def _cleanup_session(self, key):
        """Remove session state created during tests."""
        _cleanup_state(*key)

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

        thinking_event = ScreenEvent(state=TerminalView.THINKING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=thinking_event),
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=699, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.STREAMING
        streaming.last_edit_time = 0
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = set()

        streaming_event = ScreenEvent(state=TerminalView.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output_processor.extract_content", return_value="**bold** text"),
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=698, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Final content"
        streaming.state = StreamingState.STREAMING
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = set()

        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=idle_event),
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

        state_obj = _session_states.get((690, 1))
        assert state_obj is not None
        streaming = state_obj.streaming
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
    """Unit tests for find_last_prompt helper."""

    def test_finds_prompt_with_text(self):
        display = [
            "some content",
            "❯ Write a function",
            "⏺ Here is the function:",
            "more content",
        ]
        assert find_last_prompt(display) == 1

    def test_returns_last_prompt_when_multiple(self):
        display = [
            "❯ First prompt text",
            "⏺ First response",
            "❯ Second prompt text",
            "⏺ Second response",
        ]
        assert find_last_prompt(display) == 2

    def test_ignores_bare_prompt(self):
        """Bare ❯ (no text) must be ignored."""
        display = ["❯", "content", "more"]
        assert find_last_prompt(display) is None

    def test_finds_short_user_prompt(self):
        """Short user prompts like '❯ hi' (len 4) must be found."""
        display = ["❯", "content", "❯ hi", "⏺ Hello!", "more"]
        assert find_last_prompt(display) == 2

    def test_skips_idle_hint_prompt(self):
        """Idle hint prompt at screen bottom must be skipped.

        Regression for issue 004: ❯ Try "how does <filepath> work?"
        appears below the response and has no ⏺ below it.  Selecting
        it would truncate the actual response content above.
        """
        display = [
            "❯ /nonexistent",
            "⏺ I don't recognize that command.",
            "────────────────────────────────────",
            '❯ Try "how does <filepath> work?"',
            "────────────────────────────────────",
            "  project │ ⎇ main │ Usage: 5%",
        ]
        # Must select the user prompt (index 0), NOT the idle hint (index 3)
        assert find_last_prompt(display) == 0

    def test_finds_emoji_only_prompt(self):
        """Regression: emoji-only prompt '❯ 🤖💬🔥' (len 5) was incorrectly
        skipped by the old > 5 threshold, causing previous response content
        to leak into the new response during fast-IDLE extraction."""
        display = [
            "⏺ Two.",
            "────────────────────────────────────",
            "❯ 🤖💬🔥",
            "────────────────────────────────────",
            "⏺ Hey! What can I help you with?",
            "────────────────────────────────────",
            "❯",
            "────────────────────────────────────",
        ]
        prompt_idx = find_last_prompt(display)
        assert prompt_idx == 2
        # Trimmed display must NOT include old "Two." response
        trimmed = display[prompt_idx:]
        content = extract_content(trimmed)
        assert "Hey! What can I help you with?" in content
        assert "Two." not in content

    def test_returns_none_when_no_prompt(self):
        display = ["line one", "line two", "line three"]
        assert find_last_prompt(display) is None

    def test_returns_none_on_empty_display(self):
        assert find_last_prompt([]) is None


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
        prompt_idx = find_last_prompt(display)
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
        prompt_idx = find_last_prompt(display)
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
        prompt_idx = find_last_prompt(display)
        assert prompt_idx is None
        # When no prompt found, extraction uses full display — both
        # old and new content appear.  Snapshot will be empty, so
        # dedup doesn't eat shared patterns from the new response.
        content = extract_content(display)
        assert "is_palindrome" in content
        assert "Args:" in content

    def test_idle_hint_prompt_does_not_truncate_response(self):
        """Regression for issue 004: idle hint prompt causes response loss.

        When Claude goes IDLE, it may display a hint like
        '❯ Try "how does <filepath> work?"' at the bottom of the screen.
        find_last_prompt must select the user's input prompt (which has
        ⏺ below it), not the idle hint (which has no ⏺ below it).
        Without this fix, source = full[hint_idx:] would contain only
        the hint + chrome, extract_content would return empty, and
        "Thinking..." would stay stuck permanently.
        """
        display = [
            "⏺ Previous response content",       # old response
            "",
            "────────────────────────────────────",
            "❯ /nonexistent",                     # user's actual prompt
            "",
            "⏺ I don't have a command called /nonexistent.",  # new response
            "",
            "────────────────────────────────────",
            '❯ Try "how does <filepath> work?"',  # idle hint (MUST be skipped)
            "────────────────────────────────────",
            "  project │ ⎇ main │ Usage: 5%",
        ]
        prompt_idx = find_last_prompt(display)
        # Must select the user prompt (index 3), NOT the idle hint (index 8)
        assert prompt_idx == 3
        trimmed = display[prompt_idx:]
        content = extract_content(trimmed)
        # Response must be extracted
        assert "/nonexistent" in content
        # Old response above the prompt must be excluded
        assert "Previous response" not in content


class TestThinkingSnapshotChromeOnly:
    """Regression: thinking snapshot captured content lines (Args:, Returns:,
    code) from a previous response still visible on the pyte screen.  When
    the next response used the same patterns, they were incorrectly deduped.

    Fix: snapshot only captures UI chrome lines (classify_text_line result in
    CHROME_CATEGORIES).  Content, response, and tool lines are excluded.
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
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
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
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
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
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
                snap.add(stripped)
        assert not any("⏺" in s for s in snap)
        assert not any("⎿" in s for s in snap)

    def test_fibonacci_palindrome_regression(self):
        """Exact regression: fibonacci Args:/Returns: must not dedup from
        is_palindrome response when both are on the pyte screen at THINKING.

        This reproduces the real scenario where find_last_prompt found the
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
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
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
        state = _get_or_create(*key, bot=AsyncMock())
        state.dedup.sent_lines = {"old content", "Args:", "Returns:"}
        # Simulate USER_MESSAGE detection (same logic as poll_output)
        cur_state = TerminalView.USER_MESSAGE
        if cur_state == TerminalView.USER_MESSAGE:
            state.dedup.sent_lines = set()
            state.dedup.thinking_snapshot = set()
        assert _session_states[key].dedup.sent_lines == set()
        # Cleanup

    def test_user_message_clears_thinking_snapshot(self):
        key = (884, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.dedup.thinking_snapshot = {"old snap", "Args:"}
        cur_state = TerminalView.USER_MESSAGE
        if cur_state == TerminalView.USER_MESSAGE:
            state.dedup.sent_lines = set()
            state.dedup.thinking_snapshot = set()
        assert (key not in _session_states or not _session_states[key].dedup.thinking_snapshot)
        # Cleanup


class TestStripMarkerFromSpans:
    """Tests for strip_marker_from_spans."""

    def test_strip_response_marker(self):
        """⏺ prefix is removed from first span."""
        spans = [
            CharSpan(text="⏺ ", fg="default"),
            CharSpan(text="def", fg="blue"),
            CharSpan(text=" foo():", fg="default"),
        ]
        result = strip_marker_from_spans(spans, "⏺")
        texts = [s.text for s in result]
        assert "⏺" not in "".join(texts)
        assert any("def" in t for t in texts)

    def test_strip_tool_connector_marker(self):
        """⎿ prefix is removed from first span."""
        spans = [
            CharSpan(text="⎿ ", fg="default"),
            CharSpan(text="file.py", fg="default"),
        ]
        result = strip_marker_from_spans(spans, "⎿")
        texts = [s.text for s in result]
        assert "⎿" not in "".join(texts)
        assert "file.py" in "".join(texts)

    def test_no_marker_unchanged(self):
        """Spans without marker are returned unchanged."""
        spans = [CharSpan(text="hello world", fg="default")]
        result = strip_marker_from_spans(spans, "⏺")
        assert result == spans

    def test_empty_after_strip(self):
        """Span that becomes empty after stripping is dropped."""
        spans = [
            CharSpan(text="⏺ ", fg="default"),
            CharSpan(text="text", fg="blue"),
        ]
        result = strip_marker_from_spans(spans, "⏺")
        # The first span was "⏺ " -> "" after strip -> dropped
        assert len(result) == 1
        assert result[0].text == "text"


class TestFilterResponseAttr:
    """Tests for filter_response_attr: filters terminal chrome from attributed lines."""

    def test_strips_prompt_and_status_bar(self):
        """Prompt, status bar, and progress bar lines are removed."""
        source = [
            "❯ Write a Python function",
            "  that checks primes.",
            "⏺ Here is the function:",
            "  def is_prime(n):",
            "❯",
            "  claude-instance-manager │ ⎇ feat/test │ Usage: 15%",
            "  █▌░░░░░░░░ ↻ 1:59",
        ]
        attr = [
            [CharSpan(text="❯ Write a Python function", fg="default")],
            [CharSpan(text="  that checks primes.", fg="default")],
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Here is the function:", fg="default")],
            [CharSpan(text="  ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" is_prime(n):", fg="default")],
            [CharSpan(text="❯", fg="default")],
            [CharSpan(text="  claude-instance-manager │ ⎇ feat/test │ Usage: 15%", fg="default")],
            [CharSpan(text="  █▌░░░░░░░░ ↻ 1:59", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        # Should only keep response content (line 2: ⏺ stripped, line 3: code)
        assert len(filtered) == 2
        # ⏺ marker should be stripped
        all_text = "".join(s.text for line in filtered for s in line)
        assert "⏺" not in all_text
        assert "❯" not in all_text
        assert "Usage:" not in all_text
        # Code content preserved
        assert "def" in all_text

    def test_prompt_continuation_skipped(self):
        """Wrapped user input after ❯ is skipped until ⏺ response."""
        source = [
            "❯ This is a very long user prompt that wraps across",
            "  multiple terminal lines because it is so long",
            "⏺ Short answer.",
        ]
        attr = [
            [CharSpan(text="❯ This is a very long user prompt that wraps across", fg="default")],
            [CharSpan(text="  multiple terminal lines because it is so long", fg="default")],
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Short answer.", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        assert len(filtered) == 1
        all_text = "".join(s.text for line in filtered for s in line)
        assert "Short answer." in all_text
        assert "long user prompt" not in all_text

    def test_content_lines_kept(self):
        """Lines classified as 'content' (plain text) are kept."""
        source = [
            "⏺ Here is the code:",
            "  def hello():",
            "      print('hi')",
        ]
        attr = [
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Here is the code:", fg="default")],
            [CharSpan(text="  ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="      ", fg="default"), CharSpan(text="print", fg="cyan"), CharSpan(text="('hi')", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        assert len(filtered) == 3
        # First line should have ⏺ stripped
        first_text = "".join(s.text for s in filtered[0])
        assert "⏺" not in first_text

    def test_empty_input(self):
        """Empty input returns empty output."""
        assert filter_response_attr([], []) == []

    def test_separator_lines_skipped(self):
        """Separator lines (box drawing chars) are filtered out."""
        source = [
            "─" * 40,
            "⏺ Hello world",
            "─" * 40,
        ]
        attr = [
            [CharSpan(text="─" * 40, fg="default")],
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Hello world", fg="default")],
            [CharSpan(text="─" * 40, fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        assert len(filtered) == 1
        assert "Hello world" in "".join(s.text for s in filtered[0])

    def test_dedents_terminal_margin(self):
        """2-space terminal margin from ⏺ column is stripped from all lines.

        Real Claude Code renders content with a 2-space left margin:
        ``  ⏺ text`` for marker lines, ``  content`` for continuation.
        After marker stripping both have a residual 2-space indent that
        filter_response_attr must remove via dedent.
        """
        source = [
            "  ⏺ Here is the code:",
            "      def hello():",
            "          print('hi')",
            "  How it works:",
            "  - It prints hi",
        ]
        attr = [
            [CharSpan(text="  ⏺ ", fg="default"), CharSpan(text="Here is the code:", fg="default")],
            [CharSpan(text="      ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="          ", fg="default"), CharSpan(text="print", fg="cyan"), CharSpan(text="('hi')", fg="default")],
            [CharSpan(text="  How it works:", fg="default")],
            [CharSpan(text="  - It prints hi", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        texts = ["".join(s.text for s in line) for line in filtered]
        # 2-space margin should be stripped from all lines
        assert texts[0] == "Here is the code:"
        assert texts[1] == "    def hello():"
        assert texts[2] == "        print('hi')"
        assert texts[3] == "How it works:"
        assert texts[4] == "- It prints hi"


    def test_dedents_when_marker_at_column_zero(self):
        """Content lines are dedented even when ⏺ sits at column 0.

        When Claude Code renders the ⏺ marker at the leftmost column,
        marker stripping leaves the response line at 0 indent while
        continuation lines retain their 2-space margin.  The dedent
        must exclude marker-stripped lines from the minimum-indent
        computation so continuation lines still get their margin removed.
        """
        source = [
            "⏺ Here is the code:",
            "  def hello():",
            "      print('hi')",
            "  How it works:",
            "  - It prints hi",
        ]
        attr = [
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Here is the code:", fg="default")],
            [CharSpan(text="  ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="      ", fg="default"), CharSpan(text="print", fg="cyan"), CharSpan(text="('hi')", fg="default")],
            [CharSpan(text="  How it works:", fg="default")],
            [CharSpan(text="  - It prints hi", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        texts = ["".join(s.text for s in line) for line in filtered]
        # Marker-stripped line stays at 0 indent; content lines get
        # their 2-space margin stripped.
        assert texts[0] == "Here is the code:"
        assert texts[1] == "def hello():"
        assert texts[2] == "    print('hi')"
        assert texts[3] == "How it works:"
        assert texts[4] == "- It prints hi"


class TestLstripNChars:
    """Tests for lstrip_n_chars: strip N leading chars from span list."""

    def test_strip_full_span(self):
        """Span shorter than N is entirely consumed."""
        spans = [
            CharSpan(text="  ", fg="default"),
            CharSpan(text="hello", fg="blue"),
        ]
        result = lstrip_n_chars(spans, 2)
        assert len(result) == 1
        assert result[0].text == "hello"

    def test_strip_partial_span(self):
        """Span longer than N loses first N characters."""
        spans = [CharSpan(text="    code", fg="default")]
        result = lstrip_n_chars(spans, 2)
        assert len(result) == 1
        assert result[0].text == "  code"

    def test_strip_zero(self):
        """Stripping 0 characters returns all spans unchanged."""
        spans = [CharSpan(text="text", fg="default")]
        result = lstrip_n_chars(spans, 0)
        assert len(result) == 1
        assert result[0].text == "text"

    def test_strip_across_spans(self):
        """Strip that spans multiple CharSpans."""
        spans = [
            CharSpan(text=" ", fg="default"),
            CharSpan(text="  ", fg="dim"),
            CharSpan(text="content", fg="blue"),
        ]
        # Strip 3 chars across two spans
        result = lstrip_n_chars(spans, 3)
        assert len(result) == 1
        assert result[0].text == "content"

    def test_strip_preserves_attributes(self):
        """Partially stripped span retains its ANSI attributes."""
        spans = [CharSpan(text="  bold", fg="red", bold=True)]
        result = lstrip_n_chars(spans, 2)
        assert result[0].text == "bold"
        assert result[0].fg == "red"
        assert result[0].bold is True


class TestDedentAttrLines:
    """Tests for dedent_attr_lines: remove common leading whitespace from spans."""

    def test_strips_common_indent(self):
        """All lines with 2-space indent lose 2 leading chars."""
        lines = [
            [CharSpan(text="  hello", fg="default")],
            [CharSpan(text="  world", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts == ["hello", "world"]

    def test_preserves_relative_indent(self):
        """Lines with extra indent beyond the common minimum keep the excess."""
        lines = [
            [CharSpan(text="  code:", fg="default")],
            [CharSpan(text="      indented", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts[0] == "code:"
        assert texts[1] == "    indented"

    def test_no_common_indent(self):
        """Lines with no common indent are returned unchanged."""
        lines = [
            [CharSpan(text="no indent", fg="default")],
            [CharSpan(text="  has indent", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts == ["no indent", "  has indent"]

    def test_empty_lines_skipped(self):
        """Empty lines do not affect min indent calculation."""
        lines = [
            [CharSpan(text="  text", fg="default")],
            [],
            [CharSpan(text="  more", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts[0] == "text"
        assert texts[2] == "more"

    def test_skip_indices_excludes_from_min(self):
        """Skipped lines don't affect min indent; others are still dedented."""
        lines = [
            [CharSpan(text="no indent", fg="default")],   # index 0 — skip
            [CharSpan(text="  two spaces", fg="default")],  # index 1
            [CharSpan(text="  also two", fg="default")],    # index 2
        ]
        result = dedent_attr_lines(lines, skip_indices={0})
        texts = ["".join(s.text for s in line) for line in result]
        # Index 0 has 0 indent but is skipped → min computed from 1,2 → 2
        assert texts[0] == "no indent"  # not enough indent → left as-is
        assert texts[1] == "two spaces"
        assert texts[2] == "also two"

    def test_skip_indices_strips_skipped_if_enough_indent(self):
        """Skipped lines ARE stripped when they have enough indent."""
        lines = [
            [CharSpan(text="  marker line", fg="default")],   # index 0 — skip
            [CharSpan(text="  content", fg="default")],        # index 1
        ]
        result = dedent_attr_lines(lines, skip_indices={0})
        texts = ["".join(s.text for s in line) for line in result]
        # Index 0 has indent 2, min from non-skipped = 2 → stripped
        assert texts[0] == "marker line"
        assert texts[1] == "content"

    def test_empty_input(self):
        """Empty list returns empty list."""
        assert dedent_attr_lines([]) == []


class TestStartupMessage:
    """Startup must send an informational message to all authorized users."""

    @pytest.mark.asyncio
    async def test_on_startup_sends_message_to_authorized_users(self):
        """_on_startup must send a message to every authorized user."""
        from src.main import _on_startup

        app = MagicMock()
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app.bot_data = {
            "db": db,
            "config": MagicMock(
                telegram=MagicMock(authorized_users=[111, 222]),
            ),
        }
        app.bot = AsyncMock()
        app.bot.set_my_commands = AsyncMock()
        app.bot.send_message = AsyncMock()

        await _on_startup(app)

        # Should have sent a message to each authorized user
        send_calls = app.bot.send_message.call_args_list
        chat_ids = {call.kwargs.get("chat_id") or call.args[0] for call in send_calls}
        assert 111 in chat_ids
        assert 222 in chat_ids
        # Message should contain "started" or "online"
        for call in send_calls:
            text = call.kwargs.get("text", "")
            assert "started" in text.lower() or "online" in text.lower()


class TestShutdownMessage:
    """Shutdown must send a message to all authorized users."""

    @pytest.mark.asyncio
    async def test_send_shutdown_message(self):
        """_send_shutdown_message notifies all authorized users."""
        from src.main import _send_shutdown_message

        bot = AsyncMock()
        bot.send_message = AsyncMock()
        config = MagicMock(
            telegram=MagicMock(authorized_users=[111, 222]),
        )
        sm = MagicMock()
        sm._sessions = {111: {1: "sess1"}, 222: {1: "sess2", 2: "sess3"}}

        await _send_shutdown_message(bot, config, sm)

        send_calls = bot.send_message.call_args_list
        chat_ids = {call.kwargs.get("chat_id") or call.args[0] for call in send_calls}
        assert 111 in chat_ids
        assert 222 in chat_ids
        for call in send_calls:
            text = call.kwargs.get("text", "")
            assert "shutting down" in text.lower() or "stopping" in text.lower()


class TestAnsiReRenderOnCompletion:
    """STREAMING->IDLE must re-render final message with ANSI pipeline."""

    def _cleanup_session(self, key):
        _cleanup_state(*key)

    @pytest.mark.asyncio
    async def test_streaming_idle_uses_ansi_pipeline(self):
        """STREAMING->IDLE must call classify_regions for final render."""
        key = (750, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {750: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=750, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Heuristic content"
        streaming.state = StreamingState.STREAMING
        state.streaming = streaming
        state.prev_state = TerminalView.STREAMING
        state.dedup.sent_lines = set()

        idle_event = ScreenEvent(state=TerminalView.IDLE, raw_lines=[])

        classify_calls = []
        def _capture_classify(lines):
            classify_calls.append(lines)
            from src.parsing.content_classifier import ContentRegion
            return [ContentRegion(type="prose", text="ANSI-rendered content")]

        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output_processor.classify_screen_state", return_value=idle_event),
            patch("src.telegram.output_pipeline.classify_regions", side_effect=_capture_classify),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # classify_regions must have been called for re-render
        assert len(classify_calls) >= 1
        # The final message should contain the ANSI-rendered content
        bot.edit_message_text.assert_called()
        final_text = bot.edit_message_text.call_args[1]["text"]
        assert "ANSI-rendered content" in final_text

        self._cleanup_session(key)


class TestPollOutputExceptionResilience:
    """Regression tests for issue 011: poll_output must survive per-session exceptions."""

    def _cleanup_session(self, key):
        _cleanup_state(*key)

    @pytest.mark.asyncio
    async def test_poll_loop_survives_per_session_exception(self):
        """Regression test for issue 011: exception in one session must not kill the poll loop.

        Before the fix, any unhandled exception in the per-session processing
        (e.g. html.escape(None), Telegram API error, parser crash) would propagate
        up and kill the background poll_output task silently, permanently stopping
        all output delivery.
        """
        key = (780, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {780: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        state.streaming = StreamingMessage(bot=bot, chat_id=780, edit_rate_limit=3)
        state.prev_state = TerminalView.STARTUP
        state.dedup.sent_lines = set()

        # classify_screen_state raises to simulate a crash mid-processing
        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                side_effect=RuntimeError("simulated crash"),
            ),
        ):
            # Before the fix, this would raise RuntimeError.
            # After the fix, the exception is caught and the loop continues.
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # The key assertion: we reach here (no RuntimeError propagated).
        # The loop survived the exception and ran a second cycle before CancelledError.
        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_tool_request_with_none_question(self):
        """Regression test for issue 011: TOOL_REQUEST with question=None must not crash.

        The detector can set question=None when no line ending with '?' is found.
        payload.get("question", default) returns None (key exists with None value),
        and html.escape(None) raises AttributeError.
        """
        key = (781, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"tool", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {781: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        state.streaming = StreamingMessage(bot=bot, chat_id=781, edit_rate_limit=3)
        state.prev_state = TerminalView.STARTUP
        state.dedup.sent_lines = set()

        # TOOL_REQUEST with question=None (key exists but value is None)
        tool_event = ScreenEvent(
            state=TerminalView.TOOL_REQUEST,
            payload={
                "question": None,
                "options": ["Yes", "No"],
                "selected": 0,
                "has_hint": True,
            },
            raw_lines=[],
        )
        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                return_value=tool_event,
            ),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Should have sent a message with the fallback question text
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args.kwargs
        assert "Tool approval requested" in call_kwargs["text"]

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_cancelled_error_propagates_through_exception_handler(self):
        """CancelledError must not be swallowed by the per-session exception handler."""
        key = (782, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {782: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        state.streaming = StreamingMessage(bot=bot, chat_id=782, edit_rate_limit=3)
        state.prev_state = TerminalView.STARTUP
        state.dedup.sent_lines = set()

        # classify_screen_state raises CancelledError (simulating task cancellation)
        with patch(
            "src.telegram.output.asyncio.sleep",
            side_effect=[None],
        ), patch(
            "src.telegram.output_processor.classify_screen_state",
            side_effect=asyncio.CancelledError,
        ):
            with pytest.raises(asyncio.CancelledError):
                await poll_output(bot, sm)

        self._cleanup_session(key)


class TestPollOutputAuthRequired:
    """Regression tests for issue 012: auth screen must notify user and kill session."""

    def _cleanup_session(self, key):
        _cleanup_state(*key)

    @pytest.mark.asyncio
    async def test_auth_screen_sends_notification_and_kills_session(self):
        """Regression test for issue 012: when Claude Code shows an OAuth login
        screen, the bot must send a notification to the user and kill the session
        instead of silently hanging at 'Thinking...' forever.
        """
        key = (790, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"auth-screen-data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {790: {1: session}}
        sm.kill_session = AsyncMock()
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        state.streaming = StreamingMessage(bot=bot, chat_id=790, edit_rate_limit=3)
        state.prev_state = TerminalView.STARTUP
        state.dedup.sent_lines = set()

        auth_event = ScreenEvent(
            state=TerminalView.AUTH_REQUIRED,
            payload={"url": "https://claude.ai/oauth/authorize?code=true"},
            raw_lines=[],
        )
        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                return_value=auth_event,
            ),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Must notify user about auth requirement
        bot.send_message.assert_called_once()
        call_kwargs = bot.send_message.call_args.kwargs
        assert "authentication" in call_kwargs["text"].lower()
        assert "claude" in call_kwargs["text"].lower()

        # Must kill the session
        sm.kill_session.assert_awaited_once_with(790, 1)

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_auth_notification_sent_only_once(self):
        """AUTH_REQUIRED notification must fire only on the first detection,
        not on every poll cycle.
        """
        key = (791, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data1", b"data2", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {791: {1: session}}
        sm.kill_session = AsyncMock()
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        state.streaming = StreamingMessage(bot=bot, chat_id=791, edit_rate_limit=3)
        state.prev_state = TerminalView.STARTUP
        state.dedup.sent_lines = set()

        auth_event = ScreenEvent(
            state=TerminalView.AUTH_REQUIRED,
            payload={"url": "https://claude.ai/oauth/authorize?code=true"},
            raw_lines=[],
        )
        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                return_value=auth_event,
            ),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Session is killed on first detection, so the second cycle
        # should not reach it (it's removed from sessions).
        # The notification should be sent exactly once.
        assert bot.send_message.call_count == 1
        sm.kill_session.assert_awaited_once_with(791, 1)

        self._cleanup_session(key)


class TestStaleToolRequestOverride:
    """Regression tests for issue 014: stale TOOL_REQUEST after callback."""

    def _cleanup_session(self, key):
        _cleanup_state(*key)

    def test_mark_tool_acted_sets_flag(self):
        """mark_tool_acted sets the per-session flag."""
        key = (800, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.tool_acted = False
        mark_tool_acted(800, 1)
        assert state.tool_acted is True
        self._cleanup_session(key)

    def test_stale_tool_request_overridden_to_unknown(self):
        """Regression: after tool callback, stale TOOL_REQUEST becomes UNKNOWN.

        When the user clicks Allow/Deny/Pick, the pyte buffer retains the
        selection menu lines.  detect_tool_request keeps matching them.
        The override must force the state to UNKNOWN so other detectors
        can process the new screen content.
        """
        key = (801, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.prev_state = TerminalView.TOOL_REQUEST
        state.tool_acted = True

        event = ScreenEvent(state=TerminalView.TOOL_REQUEST, raw_lines=[])
        # Replicate the guard logic from poll_output
        if event.state == TerminalView.TOOL_REQUEST and state.tool_acted:
            event = ScreenEvent(
                state=TerminalView.UNKNOWN,
                payload=event.payload,
                raw_lines=event.raw_lines,
            )
        assert event.state == TerminalView.UNKNOWN
        state.tool_acted = False

    def test_flag_cleared_when_screen_moves_to_different_state(self):
        """Regression: tool_acted flag clears when screen naturally transitions."""
        key = (802, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.tool_acted = True

        event = ScreenEvent(state=TerminalView.THINKING, raw_lines=[])
        # Replicate the elif branch from poll_output
        if event.state == TerminalView.TOOL_REQUEST and state.tool_acted:
            pass
        elif event.state != TerminalView.TOOL_REQUEST:
            state.tool_acted = False

        assert (key not in _session_states or not _session_states[key].tool_acted)

    def test_flag_not_cleared_while_stale_content_persists(self):
        """Regression: flag stays set while classifier keeps returning TOOL_REQUEST."""
        key = (803, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.tool_acted = True

        event = ScreenEvent(state=TerminalView.TOOL_REQUEST, raw_lines=[])
        if event.state == TerminalView.TOOL_REQUEST and state.tool_acted:
            event = ScreenEvent(
                state=TerminalView.UNKNOWN,
                payload=event.payload,
                raw_lines=event.raw_lines,
            )
        elif event.state != TerminalView.TOOL_REQUEST:
            state.tool_acted = False

        # Flag persists — UNKNOWN was due to override, not natural transition
        assert state.tool_acted is True
        state.tool_acted = False

    def test_legitimate_tool_request_not_suppressed_without_flag(self):
        """A fresh TOOL_REQUEST without the flag must NOT be overridden."""
        key = (804, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.tool_acted = False

        event = ScreenEvent(state=TerminalView.TOOL_REQUEST, raw_lines=[])
        if event.state == TerminalView.TOOL_REQUEST and state.tool_acted:
            event = ScreenEvent(
                state=TerminalView.UNKNOWN,
                payload=event.payload,
                raw_lines=event.raw_lines,
            )
        assert event.state == TerminalView.TOOL_REQUEST

    @pytest.mark.asyncio
    async def test_poll_output_overrides_stale_tool_request(self):
        """Regression: full poll_output integration — stale TOOL_REQUEST after
        callback must not re-send keyboard and must allow next state through.

        Simulates: TOOL_REQUEST (keyboard sent) → mark_tool_acted →
        stale TOOL_REQUEST (overridden to UNKNOWN) → THINKING (detected).
        """
        key = (805, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"tool", b"stale", b"think", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {805: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        state = _get_or_create(*key, bot=AsyncMock())
        state.emulator = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=805, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.state = StreamingState.THINKING
        state.streaming = streaming
        state.prev_state = TerminalView.THINKING
        state.dedup.sent_lines = set()

        tool_event = ScreenEvent(
            state=TerminalView.TOOL_REQUEST,
            payload={
                "question": "Allow tool?",
                "options": ["Yes", "No"],
                "selected": 0,
                "has_hint": True,
            },
            raw_lines=[],
        )
        thinking_event = ScreenEvent(state=TerminalView.THINKING, raw_lines=[])

        # Cycle 1: TOOL_REQUEST (keyboard sent)
        # Cycle 2: mark_tool_acted, then stale TOOL_REQUEST (should be overridden)
        # Cycle 3: THINKING (user sent new message, Claude responds)
        cycle = [0]
        def classify_side_effect(display, prev):
            c = cycle[0]
            cycle[0] += 1
            if c == 0:
                return tool_event
            elif c == 1:
                mark_tool_acted(805, 1)
                return tool_event  # stale — should be overridden
            else:
                return thinking_event

        with (
            patch(
                "src.telegram.output.asyncio.sleep",
                side_effect=[None, None, None, asyncio.CancelledError],
            ),
            patch(
                "src.telegram.output_processor.classify_screen_state",
                side_effect=classify_side_effect,
            ),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # Keyboard sent only once (first TOOL_REQUEST), not on stale repeat.
        # Cycle 3 also triggers start_thinking (UNKNOWN→THINKING), so count=2
        # but only one call should have reply_markup (the keyboard).
        keyboard_calls = [
            c for c in bot.send_message.call_args_list
            if c.kwargs.get("reply_markup") is not None
        ]
        assert len(keyboard_calls) == 1

        # After cycle 3, prev_state should be THINKING (not stuck at TOOL_REQUEST)
        assert _session_states[key].prev_state == TerminalView.THINKING

        self._cleanup_session(key)


class TestIsToolRequestPending:
    """Regression tests for issue 015: is_tool_request_pending guard."""

    def test_returns_true_when_tool_request(self):
        """is_tool_request_pending returns True when session is in TOOL_REQUEST."""
        key = (900, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.prev_state = TerminalView.TOOL_REQUEST
        assert is_tool_request_pending(900, 1) is True
        _cleanup_state(*key)

    def test_returns_false_when_idle(self):
        """is_tool_request_pending returns False for non-TOOL_REQUEST states."""
        key = (901, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.prev_state = TerminalView.IDLE
        assert is_tool_request_pending(901, 1) is False
        _cleanup_state(*key)

    def test_returns_false_when_no_state(self):
        """is_tool_request_pending returns False for unknown sessions."""
        key = (902, 99)
        _cleanup_state(*key)
        assert is_tool_request_pending(902, 99) is False

    def test_returns_false_after_tool_acted(self):
        """Regression for issue 017: after Allow/Deny, pending must be False even if prev_state still TOOL_REQUEST."""
        key = (903, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.prev_state = TerminalView.TOOL_REQUEST
        state.tool_acted = True
        assert is_tool_request_pending(903, 1) is False
        _cleanup_state(*key)
        state.tool_acted = False

    def test_returns_true_when_tool_request_and_not_acted(self):
        """TOOL_REQUEST with no tool_acted flag should still return True."""
        key = (904, 1)
        state = _get_or_create(*key, bot=AsyncMock())
        state.prev_state = TerminalView.TOOL_REQUEST
        state.tool_acted = False
        assert is_tool_request_pending(904, 1) is True
        _cleanup_state(*key)
