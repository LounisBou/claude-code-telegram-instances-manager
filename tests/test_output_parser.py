from src.output_parser import strip_ansi, filter_spinners, detect_prompt, PromptType, DetectedPrompt


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
