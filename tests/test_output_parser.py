from src.output_parser import (
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
        """Real Claude output: words separated by ESC[1C instead of spaces."""
        assert strip_ansi("Hello\x1b[1Cworld") == "Hello world"

    def test_cursor_forward_multiple(self):
        """ESC[3C = 3 spaces (used for indentation)."""
        assert strip_ansi("\x1b[3Cindented") == "   indented"

    def test_real_claude_word_spacing(self):
        """Real captured: 'Accessing\x1b[1Cworkspace:' """
        text = "\x1b[1mAccessing\x1b[1Cworkspace:\x1b[22m"
        assert strip_ansi(text) == "Accessing workspace:"

    def test_strips_private_mode_sequences(self):
        """ESC[?2026h, ESC[?25l etc."""
        text = "\x1b[?2026h\x1b[?25lhello\x1b[?25h"
        assert strip_ansi(text) == "hello"

    def test_real_claude_status_line(self):
        """Real captured status bar with ESC[1C spacing."""
        text = "\x1b[34mtmp\x1b[1C\x1b[90m│\x1b[1C\x1b[38;5;100mUsage:\x1b[1C32%\x1b[1C███▎░░░░░░\x1b[39m"
        result = strip_ansi(text)
        assert "tmp" in result
        assert "Usage: 32%" in result

    def test_real_claude_rgb_color(self):
        """Real captured: ESC[38;2;177;185;249m for /exit command color."""
        text = "\x1b[38;2;177;185;249m/exit\x1b[39m"
        assert strip_ansi(text) == "/exit"


class TestCleanTerminalOutput:
    def test_strips_terminal_modes(self):
        text = "\x1b[?2026h\x1b[?2004hhello\x1b[?2026l"
        assert clean_terminal_output(text) == "hello"

    def test_normalizes_crlf(self):
        text = "line1\r\r\nline2\r\r\n"
        assert clean_terminal_output(text) == "line1\nline2"

    def test_collapses_blank_lines(self):
        text = "a\n\n\n\n\nb"
        assert clean_terminal_output(text) == "a\n\nb"

    def test_removes_screen_clear(self):
        text = "\x1b[2J\x1b[3J\x1b[Hhello"
        assert clean_terminal_output(text) == "hello"

    def test_full_real_startup(self):
        """Test with fragment of real Claude startup output."""
        text = (
            "\x1b[?2026h\r\r\n"
            "\x1b[38;5;220m────────\x1b[39m\r\r\n"
            "\x1b[1C\x1b[1mAccessing\x1b[1Cworkspace:\x1b[22m\r\r\n"
        )
        result = clean_terminal_output(text)
        assert "Accessing workspace:" in result
        assert "\x1b" not in result
        assert "\r" not in result


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
        """Real Claude status bar: 'Usage: 32% ███▎░░░░░░'"""
        result = detect_context_usage("Usage: 32% ███▎░░░░░░")
        assert result is not None
        assert result.percentage == 32

    def test_detects_usage_in_status_line(self):
        """Real status bar after ANSI stripping."""
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

    def test_parses_real_captured_status_bar(self):
        """After strip_ansi, real captured status bar."""
        raw = "\x1b[34mclaude-instance-manager\x1b[1C\x1b[90m│\x1b[1C\x1b[32m⎇\x1b[1Cmain\x1b[1C⇡7\x1b[1C\x1b[90m│\x1b[1C\x1b[38;5;100mUsage:\x1b[1C32%\x1b[1C███▎░░░░░░\x1b[39m"
        clean = strip_ansi(raw)
        result = parse_status_bar(clean)
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
