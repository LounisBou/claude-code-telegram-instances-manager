import os

from src.parsing.terminal_emulator import (
    TerminalEmulator,
    clean_terminal_output,
    filter_spinners,
    strip_ansi,
)
from tests.parsing.conftest import (
    REAL_BOX_ANSI,
    REAL_STARTUP_ANSI,
    REAL_STATUS_BAR_ANSI,
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


    def test_scrollback_history_preserved(self):
        """Regression: long output that scrolls past screen height must be
        preserved in the scrollback buffer via pyte.HistoryScreen."""
        emu = TerminalEmulator(rows=10, cols=80)
        # Feed 30 lines — only last 10 fit on screen
        for i in range(30):
            emu.feed(f"Line {i}\r\n")
        display = emu.get_display()
        full = emu.get_full_display()
        # Display should only have last ~10 lines
        display_text = "\n".join(display)
        assert "Line 0" not in display_text
        assert "Line 29" in display_text
        # Full display should have ALL lines including scrollback
        full_text = "\n".join(full)
        assert "Line 0" in full_text
        assert "Line 15" in full_text
        assert "Line 29" in full_text

    def test_clear_history(self):
        """clear_history() discards scrollback without affecting current display."""
        emu = TerminalEmulator(rows=10, cols=80)
        for i in range(30):
            emu.feed(f"Line {i}\r\n")
        assert len(emu.get_full_display()) > 10
        emu.clear_history()
        full_after = emu.get_full_display()
        # After clearing, full display should equal visible display
        assert len(full_after) == 10
        assert "Line 0" not in "\n".join(full_after)

    def test_reset_clears_history(self):
        """reset() must clear both screen and scrollback history."""
        emu = TerminalEmulator(rows=10, cols=80)
        for i in range(30):
            emu.feed(f"Line {i}\r\n")
        emu.reset()
        assert emu.get_text() == ""
        assert emu.get_full_display() == [""] * 10


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
