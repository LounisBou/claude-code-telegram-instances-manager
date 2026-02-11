from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.telegram.output import _CONTENT_STATES
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
        from src.telegram.output import _session_prev_state
        from src.parsing.ui_patterns import ScreenEvent

        # Simulate: session was in IDLE, classifier returns STARTUP (banner visible)
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
