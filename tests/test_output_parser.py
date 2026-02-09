from src.output_parser import strip_ansi, filter_spinners


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
