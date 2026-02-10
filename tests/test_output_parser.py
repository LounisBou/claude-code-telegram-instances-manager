import logging
import os

from src.output_parser import (
    TerminalEmulator,
    ScreenState,
    ScreenEvent,
    classify_line,
    extract_content,
    strip_ansi,
    clean_terminal_output,
    filter_spinners,
    detect_prompt,
    PromptType,
    DetectedPrompt,
    detect_context_usage,
    ContextUsage,
    detect_file_paths,
    format_telegram,
    split_message,
    parse_status_bar,
    parse_extra_status,
    StatusBar,
    TELEGRAM_MAX_LENGTH,
    detect_thinking,
    detect_tool_request,
    detect_todo_list,
    detect_background_task,
    detect_parallel_agents,
    classify_screen_state,
)


# ---- Real captured ANSI data from Claude Code sessions ----

# Real startup status bar (captured from PTY)
REAL_STATUS_BAR_ANSI = (
    "\x1b[34mclaude-instance-manager\x1b[1C\x1b[90m│\x1b[1C"
    "\x1b[32m⎇\x1b[1Cmain\x1b[1C⇡7\x1b[1C\x1b[90m│\x1b[1C"
    "\x1b[38;5;100mUsage:\x1b[1C32%\x1b[1C███▎░░░░░░\x1b[39m"
)

# Real trust prompt (captured from untrusted folder)
REAL_TRUST_PROMPT_ANSI = (
    "\x1b[38;5;153m❯\x1b[1C\x1b[38;5;246m1.\x1b[1C"
    "\x1b[38;5;153mYes,\x1b[1CI\x1b[1Ctrust\x1b[1Cthis\x1b[1Cfolder\x1b[39m\n"
    "\x1b[3C\x1b[38;5;246m2.\x1b[1C\x1b[39mNo,\x1b[1Cexit"
)

# Real /exit command styling
REAL_EXIT_ANSI = "\x1b[38;2;177;185;249m/exit\x1b[39m"

# Real error message
REAL_ERROR_ANSI = (
    "\x1b[38;2;255;107;128m1 MCP server failed"
    "\x1b[38;2;153;153;153m ·\x1b[1C/mcp\x1b[39m"
)

# Real startup sequence with terminal modes
REAL_STARTUP_ANSI = (
    "\x1b[?2026h\r\r\n"
    "\x1b[38;5;220m────────\x1b[39m\r\r\n"
    "\x1b[1C\x1b[1mAccessing\x1b[1Cworkspace:\x1b[22m\r\r\n"
)

# Real welcome box
REAL_BOX_ANSI = (
    "\x1b[38;5;174m╭───\x1b[1CClaude\x1b[1CCode\x1b[1C"
    "\x1b[38;5;246mv2.1.37\x1b[1C"
    "\x1b[38;5;174m──────────────────────────────────────────────────────╮\x1b[39m"
)


# ---- Real captured screen data (from docs/claude-ui-patterns.md) ----

# Real IDLE screen
REAL_IDLE_SCREEN = [
    "",
    "⏺ ping",
    "",
    "────────────────────────────────────────────────────────────",
    "❯ Try \"write a test for config.py\"",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59",
]

# Real THINKING screen
REAL_THINKING_SCREEN = [
    "",
    "❯ What is 2+2?",
    "",
    "✶ Activating sleeper agents…",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59",
]

# Real STREAMING screen
REAL_STREAMING_SCREEN = [
    "",
    "❯ What is 2+2?",
    "",
    "⏺ The answer is 4.",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░ ↻ 9:59",
]

# Real TOOL_REQUEST screen (approval menu)
REAL_TOOL_REQUEST_SCREEN = [
    "",
    "────────────────────────────────",
    " Create file",
    " ../../../../tmp/test_capture.txt",
    "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
    "  1 hello",
    "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
    " Do you want to create test_capture.txt?",
    " ❯ 1. Yes",
    "   2. Yes, allow all edits during this session (shift+tab)",
    "   3. No",
    "",
    " Esc to cancel · Tab to amend",
]

# Real TOOL_RUNNING screen
REAL_TOOL_RUNNING_SCREEN = [
    "",
    "  Bash(echo 'capture_test_ok')",
    "  ⎿  Running…",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real TOOL_RESULT screen
REAL_TOOL_RESULT_SCREEN = [
    "",
    "  ⎿  Added 4 lines, removed 1 line",
    "       91  self.raw_log.extend(chunk)",
    "       92  ...",
    "       94 -  except (pexpect.TIMEOUT, pexpect.EOF):",
    "       94 +  except pexpect.TIMEOUT:",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real TODO_LIST screen
REAL_TODO_LIST_SCREEN = [
    "  5 tasks (2 done, 1 in progress, 2 open) · ctrl+t to hide tasks",
    "  ◼ Fix substring-vs-set check in smoke test",
    "  ◻ Fix stale docstring \"steps 1-8\" to \"steps 1-5\"",
    "  ✔ Separate pexpect.EOF from TIMEOUT in feed()",
    "  ✔ Replace bare except Exception: pass in close()",
    "  ✔ Remove dead since_last variable",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real PARALLEL_AGENTS screen
REAL_PARALLEL_AGENTS_SCREEN = [
    "⏺ 4 agents launched (ctrl+o to expand)",
    "   ├─ pr-review-toolkit:code-reviewer (Code review of PR changes)",
    "   │  ⎿  Running in the background (shift+↑ to manage)",
    "   ├─ pr-review-toolkit:silent-failure-hunter (Silent failure hunting)",
    "   │  ⎿  Running in the background (shift+↑ to manage)",
    "   ├─ pr-review-toolkit:code-simplifier (Code simplification review)",
    "   │  ⎿  Running in the background (shift+↑ to manage)",
    "   └─ pr-review-toolkit:comment-analyzer (Comment accuracy analysis)",
    "      ⎿  Running in the background (shift+↑ to manage)",
    "",
    "  4 local agents · 1 file +194 -192",
]

# Real BACKGROUND_TASK screen
REAL_BACKGROUND_SCREEN = [
    "",
    "⏺ 60-second timer launched.",
    "     Running in the background (↓ to manage)",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
    "  1 bash · 1 file +194 -192",
]

# Real STARTUP screen
REAL_STARTUP_SCREEN = [
    " uuuu",
    "            Claude Code v2.1.37",
    "  ▐▛███▜▌   Opus 4.6 · Claude Max",
    " ▝▜█████▛▘  ~/dev/claude-instance-manager",
    "   ▘▘ ▝▝    Opus 4.6 is here · ...",
    "",
    "   General tip: Leave code cleaner than found",
]

# Real USER_MESSAGE screen (no separators around ❯)
REAL_USER_MESSAGE_SCREEN = [
    "",
    "❯ What is 2+2? Reply with just the number, nothing else.",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real ERROR screen
REAL_ERROR_SCREEN = [
    "",
    "1 MCP server failed · /mcp",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]


class TestTerminalEmulator:
    def test_basic_text(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("Hello world")
        assert "Hello world" in emu.get_text()

    def test_ansi_colors_stripped(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("\x1b[31mred text\x1b[0m")
        assert "red text" in emu.get_text()
        assert "\x1b" not in emu.get_text()

    def test_cursor_forward_becomes_space(self):
        emu = TerminalEmulator(rows=5, cols=80)
        emu.feed("\x1b[1mAccessing\x1b[1Cworkspace:\x1b[22m")
        text = emu.get_text()
        assert "Accessing" in text
        assert "workspace:" in text

    def test_screen_clear_resets(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("old text\x1b[2J\x1b[Hnew text")
        text = emu.get_text()
        assert "new text" in text

    def test_real_status_bar(self):
        emu = TerminalEmulator(rows=5, cols=120)
        emu.feed(REAL_STATUS_BAR_ANSI)
        text = emu.get_text()
        assert "claude-instance-manager" in text
        assert "main" in text
        assert "Usage:" in text
        assert "32%" in text

    def test_real_startup_sequence(self):
        emu = TerminalEmulator(rows=10, cols=80)
        emu.feed(REAL_STARTUP_ANSI)
        text = emu.get_text()
        assert "Accessing" in text
        assert "workspace:" in text
        assert "\x1b" not in text

    def test_real_welcome_box(self):
        emu = TerminalEmulator(rows=5, cols=120)
        emu.feed(REAL_BOX_ANSI)
        text = emu.get_text()
        assert "Claude" in text
        assert "Code" in text
        assert "v2.1.37" in text

    def test_get_changes_tracks_diffs(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("line 1")
        changes1 = emu.get_changes()
        assert any("line 1" in c for c in changes1)

        # No new data = no changes
        changes2 = emu.get_changes()
        assert changes2 == []

        # New data = new changes
        emu.feed("\nline 2")
        changes3 = emu.get_changes()
        assert any("line 2" in c for c in changes3)

    def test_get_new_content(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("hello")
        content = emu.get_new_content()
        assert "hello" in content

        # Second call = empty (no changes)
        assert emu.get_new_content() == ""

    def test_reset(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("some text")
        assert "some text" in emu.get_text()
        emu.reset()
        assert emu.get_text() == ""

    def test_feed_bytes(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed(b"Hello from bytes")
        assert "Hello from bytes" in emu.get_text()

    def test_real_full_startup_binary(self):
        """Feed real captured binary data from session2 startup."""
        path = "/tmp/claude-capture/session2/01_startup_raw.bin"
        if not os.path.exists(path):
            return  # Skip if capture files not available
        with open(path, "rb") as f:
            data = f.read()
        emu = TerminalEmulator(rows=40, cols=120)
        emu.feed(data)
        text = emu.get_text()
        assert "Claude Code" in text
        assert "claude-instance-manager" in text

    def test_real_full_session_binary(self):
        """Feed real captured full session binary data."""
        path = "/tmp/claude-capture/session2/full_session.bin"
        if not os.path.exists(path):
            return
        with open(path, "rb") as f:
            data = f.read()
        emu = TerminalEmulator(rows=40, cols=120)
        emu.feed(data)
        text = emu.get_text()
        # Should reconstruct the final screen state
        assert "claude-instance-manager" in text


class TestScreenState:
    def test_all_states_exist(self):
        assert ScreenState.STARTUP.value == "startup"
        assert ScreenState.IDLE.value == "idle"
        assert ScreenState.THINKING.value == "thinking"
        assert ScreenState.STREAMING.value == "streaming"
        assert ScreenState.USER_MESSAGE.value == "user_message"
        assert ScreenState.TOOL_REQUEST.value == "tool_request"
        assert ScreenState.TOOL_RUNNING.value == "tool_running"
        assert ScreenState.TOOL_RESULT.value == "tool_result"
        assert ScreenState.BACKGROUND_TASK.value == "background_task"
        assert ScreenState.PARALLEL_AGENTS.value == "parallel_agents"
        assert ScreenState.TODO_LIST.value == "todo_list"
        assert ScreenState.ERROR.value == "error"
        assert ScreenState.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        assert len(ScreenState) == 13


class TestScreenEvent:
    def test_default_values(self):
        event = ScreenEvent(state=ScreenState.UNKNOWN)
        assert event.state == ScreenState.UNKNOWN
        assert event.payload == {}
        assert event.raw_lines == []
        assert event.timestamp == 0.0

    def test_with_payload(self):
        event = ScreenEvent(
            state=ScreenState.THINKING,
            payload={"text": "Deploying robot army…"},
            raw_lines=["✶ Deploying robot army…"],
            timestamp=1234.5,
        )
        assert event.state == ScreenState.THINKING
        assert event.payload["text"] == "Deploying robot army…"
        assert len(event.raw_lines) == 1


class TestClassifyLine:
    def test_empty(self):
        assert classify_line("") == "empty"
        assert classify_line("   ") == "empty"

    def test_separator(self):
        assert classify_line("────────────────────") == "separator"
        assert classify_line("━━━━━━━━━━━━━━━━━━━━") == "separator"

    def test_diff_delimiter(self):
        assert classify_line("╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌") == "diff_delimiter"

    def test_status_bar(self):
        assert classify_line("my-project │ ⎇ main │ Usage: 50%") == "status_bar"
        assert (
            classify_line(
                "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
            )
            == "status_bar"
        )

    def test_thinking_star(self):
        assert classify_line("✶ Activating sleeper agents…") == "thinking"
        assert classify_line("✳ Deploying robot army…") == "thinking"
        assert classify_line("✻ Deploying robot army… (thought for 1s)") == "thinking"
        assert classify_line("✽ Fixing error handling in close()…") == "thinking"
        assert classify_line("· Assimilating human knowledge…") == "thinking"

    def test_tool_header(self):
        assert classify_line("  Bash(echo 'capture_test_ok')") == "tool_header"
        assert classify_line("⏺ Write(/tmp/test_capture.txt)") == "tool_header"
        assert classify_line("⏺ Update(scripts/capture_claude_ui.py)") == "tool_header"
        assert classify_line("⏺ Read 1 file (ctrl+o to expand)") == "tool_header"
        assert classify_line("  Searched for *.py (ctrl+o to expand)") == "tool_header"
        assert classify_line("  Reading 1 file… (ctrl+o to expand)") == "tool_header"

    def test_response(self):
        assert classify_line("⏺ ping") == "response"
        assert classify_line("⏺ The project name is claude-instance-manager.") == "response"
        assert classify_line("⏺ Done. Created /tmp/test_capture.txt.") == "response"
        assert classify_line("⏺ 4 agents launched (ctrl+o to expand)") == "response"

    def test_tool_connector(self):
        assert classify_line("  ⎿  Running…") == "tool_connector"
        assert classify_line("  ⎿  Waiting…") == "tool_connector"
        assert classify_line("  ⎿  Added 4 lines, removed 1 line") == "tool_connector"
        assert classify_line("  ⎿  Running PreToolUse hooks…") == "tool_connector"

    def test_todo_item(self):
        assert classify_line("◻ Fix stale docstring") == "todo_item"
        assert classify_line("◼ Fix substring-vs-set check") == "todo_item"
        assert classify_line("✔ Separate pexpect.EOF from TIMEOUT") == "todo_item"

    def test_agent_tree(self):
        assert (
            classify_line("├─ pr-review-toolkit:code-reviewer (Code review)")
            == "agent_tree"
        )
        assert (
            classify_line("└─ pr-review-toolkit:comment-analyzer (Comment analysis)")
            == "agent_tree"
        )

    def test_prompt_marker(self):
        assert classify_line('❯ Try "how does <filepath> work?"') == "prompt"

    def test_box_drawing(self):
        assert (
            classify_line("╭─── Claude Code v2.1.37 ─────────────────────────╮")
            == "box"
        )
        assert classify_line("│            Welcome back!           │") == "box"
        assert classify_line("╰──────────────────────────────────────╯") == "box"

    def test_logo(self):
        assert classify_line("▐▛███▜▌   Opus 4.6") == "logo"
        assert classify_line("▝▜█████▛▘  ~/dev/project") == "logo"

    def test_content(self):
        assert classify_line("Hello, this is a response from Claude") == "content"
        assert classify_line("4") == "content"
        assert classify_line("The answer is 42.") == "content"


class TestExtractContent:
    def test_filters_ui_chrome(self):
        lines = [
            "────────────────────────────────",
            "claude-instance-manager │ ⎇ main │ Usage: 32%",
            "❯ Try something",
            "Hello, this is actual content",
            "More content here",
            "",
            "────────────────────────────────",
        ]
        result = extract_content(lines)
        assert "Hello, this is actual content" in result
        assert "More content here" in result
        assert "────" not in result
        assert "claude-instance-manager" not in result
        assert "❯" not in result

    def test_preserves_all_content(self):
        lines = ["First line", "Second line", "Third line"]
        result = extract_content(lines)
        assert "First line" in result
        assert "Second line" in result
        assert "Third line" in result

    def test_empty_lines(self):
        lines = ["", "", ""]
        assert extract_content(lines) == ""


class TestStripAnsi:
    def test_strips_color_codes(self):
        assert strip_ansi("\x1b[31mred text\x1b[0m") == "red text"

    def test_strips_bold(self):
        assert strip_ansi("\x1b[1mbold\x1b[0m") == "bold"

    def test_strips_cursor_movement(self):
        assert strip_ansi("\x1b[2J\x1b[H hello") == " hello"

    def test_strips_multiple_codes(self):
        assert strip_ansi("\x1b[1;32mgreen bold\x1b[0m normal") == "green bold normal"

    def test_preserves_plain_text(self):
        assert strip_ansi("hello world") == "hello world"

    def test_strips_256_color(self):
        assert strip_ansi("\x1b[38;5;196mred\x1b[0m") == "red"

    def test_strips_rgb_color(self):
        assert strip_ansi("\x1b[38;2;255;0;0mred\x1b[0m") == "red"

    def test_empty_string(self):
        assert strip_ansi("") == ""

    def test_strips_erase_line(self):
        assert strip_ansi("\x1b[2Ksome text") == "some text"

    def test_cursor_forward_becomes_space(self):
        assert strip_ansi("Hello\x1b[1Cworld") == "Hello world"

    def test_cursor_forward_multiple(self):
        assert strip_ansi("\x1b[3Cindented") == "   indented"

    def test_real_claude_word_spacing(self):
        text = "\x1b[1mAccessing\x1b[1Cworkspace:\x1b[22m"
        assert strip_ansi(text) == "Accessing workspace:"

    def test_strips_private_mode_sequences(self):
        text = "\x1b[?2026h\x1b[?25lhello\x1b[?25h"
        assert strip_ansi(text) == "hello"

    def test_real_claude_status_line(self):
        result = strip_ansi(REAL_STATUS_BAR_ANSI)
        assert "claude-instance-manager" in result
        assert "Usage: 32%" in result

    def test_real_claude_rgb_color(self):
        text = "\x1b[38;2;177;185;249m/exit\x1b[39m"
        assert strip_ansi(text) == "/exit"


class TestCleanTerminalOutput:
    def test_basic_text_via_pyte(self):
        assert "hello" in clean_terminal_output("hello")

    def test_strips_ansi_via_pyte(self):
        result = clean_terminal_output("\x1b[31mred\x1b[0m text")
        assert "red" in result
        assert "\x1b" not in result

    def test_screen_clear_handled(self):
        text = "old\x1b[2J\x1b[Hnew"
        result = clean_terminal_output(text)
        assert "new" in result

    def test_real_startup_fragment(self):
        result = clean_terminal_output(REAL_STARTUP_ANSI)
        assert "Accessing" in result
        assert "workspace:" in result
        assert "\x1b" not in result

    def test_empty_string(self):
        assert clean_terminal_output("") == ""


class TestFilterSpinners:
    def test_collapses_braille_spinners(self):
        text = "⠋ Working...\n⠙ Working...\n⠹ Working...\n⠸ Working..."
        result = filter_spinners(text)
        assert result == "Working..."

    def test_preserves_non_spinner_text(self):
        text = "Hello world\nThis is normal text"
        assert filter_spinners(text) == text

    def test_collapses_dots_spinner(self):
        text = "Loading.\nLoading..\nLoading..."
        result = filter_spinners(text)
        assert result == "Loading..."

    def test_empty_string(self):
        assert filter_spinners("") == ""

    def test_mixed_content(self):
        text = "Starting\n⠋ Thinking...\n⠙ Thinking...\nDone!"
        result = filter_spinners(text)
        assert "Done!" in result
        assert result.count("Thinking") == 1


class TestDetectPrompt:
    def test_detects_yes_no_uppercase_default(self):
        result = detect_prompt("Allow Read tool? [Y/n]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO
        assert result.options == ["Yes", "No"]
        assert result.default == "Yes"

    def test_detects_yes_no_lowercase_default(self):
        result = detect_prompt("Continue? [y/N]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO
        assert result.default == "No"

    def test_detects_multiple_choice(self):
        text = "Choose an option:\n  1. Option A\n  2. Option B\n  3. Option C\n> "
        result = detect_prompt(text)
        assert result is not None
        assert result.prompt_type == PromptType.MULTIPLE_CHOICE
        assert len(result.options) == 3

    def test_detects_tool_approval(self):
        result = detect_prompt("Allow Bash tool? [Y/n]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO

    def test_no_prompt_in_regular_text(self):
        result = detect_prompt("Hello, this is normal output from Claude.")
        assert result is None

    def test_empty_string(self):
        result = detect_prompt("")
        assert result is None

    def test_detects_selection_menu(self):
        """Real Claude trust prompt: ❯ 1. Yes, I trust this folder / 2. No, exit"""
        text = "❯ 1. Yes, I trust this folder\n   2. No, exit"
        result = detect_prompt(text)
        assert result is not None
        assert result.prompt_type == PromptType.MULTIPLE_CHOICE
        assert len(result.options) == 2
        assert "Yes, I trust this folder" in result.options[0]


class TestDetectContextUsage:
    def test_detects_percentage(self):
        result = detect_context_usage("Context: 75% used")
        assert result is not None
        assert result.percentage == 75

    def test_detects_compact_suggestion(self):
        result = detect_context_usage(
            "Context window is almost full. Consider using /compact"
        )
        assert result is not None
        assert result.needs_compact is True

    def test_no_context_info(self):
        result = detect_context_usage("Hello world, just some normal output")
        assert result is None

    def test_empty_string(self):
        result = detect_context_usage("")
        assert result is None

    def test_detects_token_count(self):
        result = detect_context_usage("Context: 150k/200k tokens used")
        assert result is not None

    def test_detects_real_claude_usage_format(self):
        result = detect_context_usage("Usage: 32% ███▎░░░░░░")
        assert result is not None
        assert result.percentage == 32

    def test_detects_usage_in_status_line(self):
        text = "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
        result = detect_context_usage(text)
        assert result is not None
        assert result.percentage == 32


class TestParseStatusBar:
    def test_parses_full_status_bar(self):
        text = "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "claude-instance-manager"
        assert result.branch == "main"
        assert result.usage_pct == 32

    def test_parses_status_bar_no_branch(self):
        text = "my-project │ Usage: 50% █████░░░░░"
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "my-project"
        assert result.usage_pct == 50

    def test_parses_pyte_reconstructed_status_bar(self):
        """Feed real ANSI through pyte, then parse the result."""
        emu = TerminalEmulator(rows=5, cols=120)
        emu.feed(REAL_STATUS_BAR_ANSI)
        text = emu.get_text()
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "claude-instance-manager"
        assert result.branch == "main"
        assert result.usage_pct == 32

    def test_empty_string(self):
        assert parse_status_bar("") is None

    def test_no_match(self):
        assert parse_status_bar("just some random text") is None

    def test_dirty_branch(self):
        text = "claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59"
        result = parse_status_bar(text)
        assert result is not None
        assert result.dirty is True
        assert result.branch == "main"

    def test_commits_ahead(self):
        text = "claude-instance-manager │ ⎇ main ⇡12 │ Usage: 6%"
        result = parse_status_bar(text)
        assert result is not None
        assert result.commits_ahead == 12

    def test_timer(self):
        text = "claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░ ↻ 9:59"
        result = parse_status_bar(text)
        assert result is not None
        assert result.timer == "9:59"

    def test_no_timer(self):
        text = "claude-instance-manager │ ⎇ main │ Usage: 7%"
        result = parse_status_bar(text)
        assert result is not None
        assert result.timer is None

    def test_all_fields(self):
        text = "claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59"
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "claude-instance-manager"
        assert result.branch == "main"
        assert result.dirty is True
        assert result.commits_ahead == 12
        assert result.usage_pct == 6
        assert result.timer == "9:59"


class TestParseExtraStatus:
    def test_bash_tasks(self):
        result = parse_extra_status("  1 bash · 1 file +194 -192")
        assert result["bash_tasks"] == 1

    def test_local_agents(self):
        result = parse_extra_status("  4 local agents · 1 file +194 -192")
        assert result["local_agents"] == 4

    def test_file_changes(self):
        result = parse_extra_status("  1 file +194 -192")
        assert result["files_changed"] == 1
        assert result["lines_added"] == 194
        assert result["lines_removed"] == 192

    def test_combined(self):
        result = parse_extra_status("  1 bash · 1 file +194 -192")
        assert result["bash_tasks"] == 1
        assert result["files_changed"] == 1
        assert result["lines_added"] == 194

    def test_empty(self):
        result = parse_extra_status("just random text")
        assert result == {}


class TestDetectFilePaths:
    def test_detects_wrote_to(self):
        paths = detect_file_paths("Wrote to /home/user/output.png")
        assert "/home/user/output.png" in paths

    def test_detects_saved(self):
        paths = detect_file_paths("File saved /tmp/result.pdf")
        assert "/tmp/result.pdf" in paths

    def test_detects_created(self):
        paths = detect_file_paths("Created /home/user/project/new_file.py")
        assert "/home/user/project/new_file.py" in paths

    def test_no_paths_in_regular_text(self):
        paths = detect_file_paths("Hello world, just some text")
        assert paths == []

    def test_multiple_paths(self):
        text = "Wrote to /a/file1.txt and saved /b/file2.txt"
        paths = detect_file_paths(text)
        assert len(paths) == 2

    def test_empty_string(self):
        assert detect_file_paths("") == []

    def test_ignores_short_paths(self):
        paths = detect_file_paths("Wrote to /tmp")
        assert paths == []


class TestDetectThinking:
    def test_basic_thinking(self):
        lines = ["✶ Activating sleeper agents…"]
        result = detect_thinking(lines)
        assert result is not None
        assert result["text"] == "Activating sleeper agents…"
        assert result["elapsed"] is None

    def test_thinking_with_elapsed(self):
        lines = ["✻ Deploying robot army… (thought for 1s)"]
        result = detect_thinking(lines)
        assert result is not None
        assert "Deploying robot army…" in result["text"]
        assert result["elapsed"] == "1s"

    def test_thinking_with_hook(self):
        lines = ["✶ Enslaving smart toasters… (running stop hook)"]
        result = detect_thinking(lines)
        assert result is not None
        assert "Enslaving smart toasters…" in result["text"]

    def test_minimal_thinking_dot(self):
        lines = ["· Assimilating human knowledge…"]
        result = detect_thinking(lines)
        assert result is not None
        assert "Assimilating human knowledge…" in result["text"]

    def test_all_star_variants(self):
        for star in "✶✳✻✽✢·":
            lines = [f"{star} Working on something…"]
            result = detect_thinking(lines)
            assert result is not None, f"Failed for star: {star}"

    def test_no_thinking(self):
        lines = ["Hello, this is normal text", "More text here"]
        assert detect_thinking(lines) is None

    def test_empty_lines(self):
        assert detect_thinking([]) is None
        assert detect_thinking([""]) is None

    def test_mixed_content(self):
        lines = [
            "❯ What is 2+2?",
            "",
            "✶ Activating sleeper agents…",
        ]
        result = detect_thinking(lines)
        assert result is not None
        assert result["text"] == "Activating sleeper agents…"


class TestDetectToolRequest:
    def test_approval_menu(self):
        lines = [
            " Do you want to create test_capture.txt?",
            " ❯ 1. Yes",
            "   2. Yes, allow all edits during this session (shift+tab)",
            "   3. No",
            "",
            " Esc to cancel · Tab to amend",
        ]
        result = detect_tool_request(lines)
        assert result is not None
        assert result["options"] == [
            "Yes",
            "Yes, allow all edits during this session (shift+tab)",
            "No",
        ]
        assert result["selected"] == 0
        assert result["has_hint"] is True
        assert result["question"] == "Do you want to create test_capture.txt?"

    def test_trust_prompt(self):
        lines = [
            "❯ 1. Yes, I trust this folder",
            "   2. No, exit",
        ]
        result = detect_tool_request(lines)
        assert result is not None
        assert len(result["options"]) == 2
        assert "Yes, I trust this folder" in result["options"][0]
        assert result["selected"] == 0

    def test_no_menu(self):
        lines = ["Hello", "World", "Just text"]
        assert detect_tool_request(lines) is None

    def test_empty_lines(self):
        assert detect_tool_request([]) is None
        assert detect_tool_request([""]) is None

    def test_single_option_not_menu(self):
        lines = ["❯ 1. Yes"]
        assert detect_tool_request(lines) is None


class TestDetectTodoList:
    def test_full_todo(self):
        lines = [
            "  5 tasks (2 done, 1 in progress, 2 open) · ctrl+t to hide tasks",
            "  ◼ Fix substring-vs-set check in smoke test",
            '  ◻ Fix stale docstring "steps 1-8" to "steps 1-5"',
            "  ✔ Separate pexpect.EOF from TIMEOUT in feed()",
            "  ✔ Replace bare except Exception: pass in close()",
            "  ✔ Remove dead since_last variable",
        ]
        result = detect_todo_list(lines)
        assert result is not None
        assert result["total"] == 5
        assert result["done"] == 2
        assert result["in_progress"] == 1
        assert result["open"] == 2
        assert len(result["items"]) == 5

    def test_item_statuses(self):
        lines = [
            "  ◻ Pending task",
            "  ◼ In-progress task",
            "  ✔ Completed task",
        ]
        result = detect_todo_list(lines)
        assert result is not None
        items = result["items"]
        assert items[0]["status"] == "pending"
        assert items[0]["text"] == "Pending task"
        assert items[1]["status"] == "in_progress"
        assert items[1]["text"] == "In-progress task"
        assert items[2]["status"] == "completed"
        assert items[2]["text"] == "Completed task"

    def test_header_without_in_progress(self):
        lines = [
            "  3 tasks (1 done, 2 open)",
            "  ✔ Done task",
            "  ◻ Open task 1",
            "  ◻ Open task 2",
        ]
        result = detect_todo_list(lines)
        assert result is not None
        assert result["total"] == 3
        assert result["in_progress"] == 0

    def test_no_todo(self):
        lines = ["Hello", "World"]
        assert detect_todo_list(lines) is None

    def test_empty_lines(self):
        assert detect_todo_list([]) is None
        assert detect_todo_list([""]) is None


class TestDetectBackgroundTask:
    def test_background_down_hint(self):
        lines = ["     Running in the background (↓ to manage)"]
        result = detect_background_task(lines)
        assert result is not None
        assert "in the background" in result["raw"]

    def test_background_shift_hint(self):
        lines = ["   ⎿  Running in the background (shift+↑ to manage)"]
        result = detect_background_task(lines)
        assert result is not None

    def test_no_background(self):
        lines = ["Hello", "World"]
        assert detect_background_task(lines) is None

    def test_empty_lines(self):
        assert detect_background_task([]) is None


class TestDetectParallelAgents:
    def test_agents_launched(self):
        lines = [
            "⏺ 4 agents launched (ctrl+o to expand)",
            "   ├─ pr-review-toolkit:code-reviewer (Code review of PR changes)",
            "   ├─ pr-review-toolkit:silent-failure-hunter (Silent failure hunting)",
            "   ├─ pr-review-toolkit:code-simplifier (Code simplification review)",
            "   └─ pr-review-toolkit:comment-analyzer (Comment accuracy analysis)",
        ]
        result = detect_parallel_agents(lines)
        assert result is not None
        assert result["count"] == 4
        assert len(result["agents"]) == 4

    def test_agent_completion(self):
        lines = [
            '⏺ Agent "Code simplification review" completed',
            "⏺ Code review is done. 2 of 4 agents complete.",
        ]
        result = detect_parallel_agents(lines)
        assert result is not None
        assert len(result["completed"]) == 1
        assert result["completed"][0] == "Code simplification review"

    def test_no_agents(self):
        lines = ["Hello", "World"]
        assert detect_parallel_agents(lines) is None

    def test_empty_lines(self):
        assert detect_parallel_agents([]) is None


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

    def test_separator_classify_line_with_fffd(self):
        """Regression: classify_line should return 'separator' for artifact separators."""
        from src.output_parser import classify_line
        assert classify_line("─" * 38 + "\uFFFD\uFFFD") == "separator"


class TestFormatTelegram:
    def test_escapes_special_chars(self):
        result = format_telegram("Hello! How are you?")
        assert "\\!" in result

    def test_preserves_code_blocks(self):
        text = "Here is code:\n```python\nprint('hello')\n```"
        result = format_telegram(text)
        assert "```python" in result
        assert "print('hello')" in result

    def test_preserves_inline_code(self):
        text = "Use the `print()` function"
        result = format_telegram(text)
        assert "`print()`" in result

    def test_converts_bold(self):
        text = "This is **bold** text"
        result = format_telegram(text)
        assert "*bold*" in result

    def test_converts_italic(self):
        text = "This is *italic* text"
        result = format_telegram(text)
        assert "_italic_" in result

    def test_empty_string(self):
        assert format_telegram("") == ""

    def test_plain_text_with_dots(self):
        result = format_telegram("version 1.2.3 is out")
        assert "\\." in result


class TestSplitMessage:
    def test_short_message_unchanged(self):
        result = split_message("Hello world")
        assert result == ["Hello world"]

    def test_splits_at_paragraph_boundary(self):
        text = "A" * 3000 + "\n\n" + "B" * 3000
        result = split_message(text)
        assert len(result) == 2
        assert result[0].strip().endswith("A" * 3000)
        assert result[1].strip().startswith("B" * 3000)

    def test_splits_long_message(self):
        text = "A" * 5000
        result = split_message(text)
        assert len(result) >= 2
        assert all(len(chunk) <= TELEGRAM_MAX_LENGTH for chunk in result)

    def test_preserves_code_blocks(self):
        text = "before\n```python\n" + "x = 1\n" * 500 + "```\nafter"
        result = split_message(text)
        for chunk in result:
            if "```python" in chunk:
                assert "```" in chunk[chunk.index("```python") + 10 :]

    def test_empty_string(self):
        assert split_message("") == [""]

    def test_exactly_max_length(self):
        text = "A" * TELEGRAM_MAX_LENGTH
        result = split_message(text)
        assert len(result) == 1


class TestClassifyScreenStateLogging:
    def test_classify_logs_result_at_trace(self, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        lines = [""] * 40
        lines[18] = "❯"
        lines[17] = "─" * 20
        lines[19] = "─" * 20
        with caplog.at_level(TRACE, logger="src.output_parser"):
            result = classify_screen_state(lines)
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert any("IDLE" in r.message for r in trace_records)

    def test_classify_logs_line_count_at_trace(self, caplog):
        from src.log_setup import TRACE, setup_logging
        setup_logging(debug=False, trace=False, verbose=False)
        lines = ["content line"] * 5 + [""] * 35
        with caplog.at_level(TRACE, logger="src.output_parser"):
            classify_screen_state(lines)
        trace_records = [r for r in caplog.records if r.levelno == TRACE]
        assert any("non_empty=5" in r.message for r in trace_records)
