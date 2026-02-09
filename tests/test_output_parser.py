import os

from src.output_parser import (
    TerminalEmulator,
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
    StatusBar,
    TELEGRAM_MAX_LENGTH,
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


class TestClassifyLine:
    def test_empty(self):
        assert classify_line("") == "empty"
        assert classify_line("   ") == "empty"

    def test_separator(self):
        assert classify_line("────────────────────") == "separator"
        assert classify_line("━━━━━━━━━━━━━━━━━━━━") == "separator"

    def test_status_bar(self):
        assert classify_line("my-project │ ⎇ main │ Usage: 50%") == "status_bar"
        assert classify_line("claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00") == "status_bar"

    def test_prompt_marker(self):
        assert classify_line("❯ Try \"how does <filepath> work?\"") == "prompt"

    def test_box_drawing(self):
        assert classify_line("╭─── Claude Code v2.1.37 ─────────────────────────╮") == "box"
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
        result = detect_context_usage("Context window is almost full. Consider using /compact")
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
