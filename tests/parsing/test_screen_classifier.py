from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import ScreenEvent, ScreenState
from tests.parsing.conftest import (
    REAL_BACKGROUND_SCREEN,
    REAL_ERROR_SCREEN,
    REAL_IDLE_SCREEN,
    REAL_PARALLEL_AGENTS_SCREEN,
    REAL_STARTUP_SCREEN,
    REAL_STREAMING_SCREEN,
    REAL_THINKING_SCREEN,
    REAL_TODO_LIST_SCREEN,
    REAL_TOOL_REQUEST_SCREEN,
    REAL_TOOL_RESULT_SCREEN,
    REAL_TOOL_RUNNING_SCREEN,
    REAL_USER_MESSAGE_SCREEN,
)


class TestClassifyScreenState:
    def test_idle_screen(self):
        event = classify_screen_state(REAL_IDLE_SCREEN)
        assert event.state == ScreenState.IDLE
        assert "placeholder" in event.payload

    def test_thinking_screen(self):
        event = classify_screen_state(REAL_THINKING_SCREEN)
        assert event.state == ScreenState.THINKING
        assert "Activating sleeper agents…" in event.payload["text"]

    def test_streaming_screen(self):
        event = classify_screen_state(REAL_STREAMING_SCREEN)
        assert event.state == ScreenState.STREAMING
        assert "The answer is 4" in event.payload["text"]

    def test_tool_request_screen(self):
        event = classify_screen_state(REAL_TOOL_REQUEST_SCREEN)
        assert event.state == ScreenState.TOOL_REQUEST
        assert len(event.payload["options"]) == 3
        assert event.payload["options"][0] == "Yes"

    def test_tool_running_screen(self):
        event = classify_screen_state(REAL_TOOL_RUNNING_SCREEN)
        assert event.state == ScreenState.TOOL_RUNNING
        assert event.payload.get("tool") == "Bash"

    def test_tool_result_screen(self):
        event = classify_screen_state(REAL_TOOL_RESULT_SCREEN)
        assert event.state == ScreenState.TOOL_RESULT
        assert event.payload["added"] == 4
        assert event.payload["removed"] == 1

    def test_todo_list_screen(self):
        event = classify_screen_state(REAL_TODO_LIST_SCREEN)
        assert event.state == ScreenState.TODO_LIST
        assert event.payload["total"] == 5
        assert len(event.payload["items"]) == 5

    def test_parallel_agents_screen(self):
        event = classify_screen_state(REAL_PARALLEL_AGENTS_SCREEN)
        assert event.state == ScreenState.PARALLEL_AGENTS
        assert event.payload["count"] == 4

    def test_background_task_screen(self):
        event = classify_screen_state(REAL_BACKGROUND_SCREEN)
        assert event.state == ScreenState.BACKGROUND_TASK

    def test_startup_screen(self):
        event = classify_screen_state(REAL_STARTUP_SCREEN)
        assert event.state == ScreenState.STARTUP

    def test_user_message_screen(self):
        event = classify_screen_state(REAL_USER_MESSAGE_SCREEN)
        assert event.state == ScreenState.USER_MESSAGE
        assert "2+2" in event.payload["text"]

    def test_error_screen(self):
        event = classify_screen_state(REAL_ERROR_SCREEN)
        assert event.state == ScreenState.ERROR
        assert "MCP server failed" in event.payload["text"]

    def test_empty_screen(self):
        event = classify_screen_state(["", "", ""])
        assert event.state == ScreenState.UNKNOWN

    def test_unknown_content(self):
        event = classify_screen_state(["Some random content that matches nothing"])
        assert event.state == ScreenState.UNKNOWN

    def test_preserves_raw_lines(self):
        event = classify_screen_state(REAL_IDLE_SCREEN)
        assert event.raw_lines == REAL_IDLE_SCREEN

    def test_idle_bare_prompt_no_trailing_space(self):
        """Regression: bare ❯ with no trailing text should be IDLE, not UNKNOWN."""
        lines = [""] * 10
        lines[5] = "─" * 40
        lines[6] = "❯"
        lines[7] = "─" * 40
        lines[8] = "  my-project │ ⎇ main │ Usage: 5% ▋░░░░░░░░░"
        event = classify_screen_state(lines)
        assert event.state == ScreenState.IDLE
        assert event.payload["placeholder"] == ""

    def test_idle_separator_with_trailing_fffd_artifacts(self):
        """Regression: pyte renders trailing U+FFFD on separator lines."""
        lines = [""] * 10
        lines[5] = "─" * 38 + "\uFFFD\uFFFD"
        lines[6] = "❯ Try something"
        lines[7] = "─" * 40
        lines[8] = "  my-project │ ⎇ main │ Usage: 5% ▋░░░░░░░░░"
        event = classify_screen_state(lines)
        assert event.state == ScreenState.IDLE
        assert event.payload["placeholder"] == "Try something"

    def test_idle_with_artifact_between_separator_and_prompt(self):
        """Regression: pyte artifact line between separator and ❯ prompt."""
        lines = [""] * 12
        lines[5] = "─" * 40
        lines[6] = "\uFFFD─"  # artifact line
        lines[7] = "❯\xa0Try something"
        lines[8] = "─" * 40
        lines[9] = "  my-project │ ⎇ main │ Usage: 5% ▋░░░░░░░░░"
        event = classify_screen_state(lines)
        assert event.state == ScreenState.IDLE

    def test_idle_with_startup_logo_and_prompt(self):
        """Regression: startup_raw has both logo and idle prompt — should be IDLE."""
        lines = [""] * 15
        lines[0] = "uuuu"
        lines[1] = "           Claude Code v2.1.37"
        lines[2] = " ▐▛███▜▌   Opus 4.6"
        lines[3] = "▝▜█████▛▘  ~/dev/project"
        lines[4] = "  ▘▘ ▝▝    Some tip"
        lines[8] = "─" * 40
        lines[9] = "❯\xa0Try something"
        lines[10] = "─" * 40
        lines[11] = "  my-project │ ⎇ main │ Usage: 6% ▋░░░░░░░░░"
        event = classify_screen_state(lines)
        assert event.state == ScreenState.IDLE

    def test_streaming_with_content_below_response_marker(self):
        """Regression: ⏺ not on last line — content lines below must still detect STREAMING."""
        lines = [""] * 15
        lines[0] = " ▐▛███▜▌   Opus 4.6"
        lines[1] = "▝▜█████▛▘  ~/dev/project"
        lines[2] = "  ▘▘ ▝▝"
        lines[5] = "⏺ Here's what I found:"
        lines[6] = "  1. File A"
        lines[7] = "  2. File B"
        lines[10] = "─" * 40
        lines[11] = "  my-project │ ⎇ main │ Usage: 7%"
        event = classify_screen_state(lines)
        assert event.state == ScreenState.STREAMING

    def test_startup_suppressed_when_response_marker_visible(self):
        """Regression: banner persists in pyte — STARTUP must not fire if ⏺ is visible."""
        lines = [""] * 15
        lines[0] = " ▐▛███▜▌   Opus 4.6"
        lines[1] = "▝▜█████▛▘  ~/dev/project"
        lines[2] = "  ▘▘ ▝▝"
        lines[5] = "⏺ Hello!"
        event = classify_screen_state(lines)
        # Must NOT be STARTUP — the ⏺ marker means Claude already responded
        assert event.state != ScreenState.STARTUP

    def test_streaming_long_response_marker_far_above(self):
        """Regression: ⏺ scrolled far above last content line must still detect STREAMING."""
        lines = [""] * 20
        lines[2] = "⏺ Here is a detailed analysis:"
        # Content fills bottom area — ⏺ is far above
        lines[10] = "  - Point one about the architecture"
        lines[11] = "  - Point two about the data flow"
        lines[12] = "  - Point three about error handling"
        lines[13] = "  - Point four about testing strategy"
        lines[15] = "─" * 40
        lines[16] = "  my-project │ ⎇ main │ Usage: 7%"
        event = classify_screen_state(lines)
        assert event.state == ScreenState.STREAMING

    def test_separator_classify_line_with_fffd(self):
        """Regression: classify_line should return 'separator' for artifact separators."""
        from src.parsing.ui_patterns import classify_line as _classify_line
        assert _classify_line("─" * 38 + "\uFFFD\uFFFD") == "separator"


class TestClassifyScreenStateLogging:
    def test_classify_logs_result_at_trace(self, caplog):
        from src.core.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        lines = [""] * 40
        lines[18] = "❯"
        lines[17] = "─" * 20
        lines[19] = "─" * 20
        with caplog.at_level(TRACE, logger="src.parsing.screen_classifier"):
            result = classify_screen_state(lines)
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert any("IDLE" in r.message for r in trace_records)

    def test_classify_logs_line_count_at_trace(self, caplog):
        from src.core.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        lines = ["content line"] * 5 + [""] * 35
        with caplog.at_level(TRACE, logger="src.parsing.screen_classifier"):
            classify_screen_state(lines)
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert any("non_empty=5" in r.message for r in trace_records)
