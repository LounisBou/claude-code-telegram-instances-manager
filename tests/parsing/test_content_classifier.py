"""Tests for ANSI-aware content region classifier."""

from src.parsing.content_classifier import (
    ContentRegion,
    classify_line,
    classify_regions,
    _insert_inline_code_markers,
    _has_code_colors,
)
from src.parsing.terminal_emulator import CharSpan, TerminalEmulator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spans(text: str, fg: str = "default", bold: bool = False) -> list[CharSpan]:
    """Create a single-span line."""
    return [CharSpan(text=text, fg=fg, bold=bold)]


def _multi_spans(*specs: tuple) -> list[CharSpan]:
    """Create multi-span line from (text, fg, bold) tuples."""
    return [
        CharSpan(text=t, fg=f, bold=b if len(s) > 2 else False)
        for s in specs
        for t, f, b in [s if len(s) == 3 else (*s, False)]
    ]


# ---------------------------------------------------------------------------
# classify_line
# ---------------------------------------------------------------------------

class TestClassifyLine:
    def test_empty_spans(self):
        assert classify_line([]) == "blank"

    def test_whitespace_only(self):
        assert classify_line(_spans("    ")) == "blank"

    def test_prose_default_fg(self):
        assert classify_line(_spans("This is plain text.")) == "prose"

    def test_code_blue_keyword(self):
        spans = [
            CharSpan(text="def", fg="blue"),
            CharSpan(text=" ", fg="default"),
            CharSpan(text="foo", fg="brown"),
            CharSpan(text="():", fg="default"),
        ]
        assert classify_line(spans) == "code"

    def test_code_red_string(self):
        spans = [
            CharSpan(text='    ', fg="default"),
            CharSpan(text='"hello"', fg="red"),
        ]
        assert classify_line(spans) == "code"

    def test_code_cyan_builtin(self):
        spans = [
            CharSpan(text="    ", fg="default"),
            CharSpan(text="print", fg="cyan"),
            CharSpan(text="(x)", fg="default"),
        ]
        assert classify_line(spans) == "code"

    def test_code_brown_identifier(self):
        spans = [
            CharSpan(text="    ", fg="default"),
            CharSpan(text="my_var", fg="brown"),
            CharSpan(text=" = 42", fg="default"),
        ]
        assert classify_line(spans) == "code"

    def test_code_green_literal(self):
        spans = [
            CharSpan(text="    ", fg="default"),
            CharSpan(text="True", fg="green"),
        ]
        assert classify_line(spans) == "code"

    def test_heading_bold_default_fg(self):
        assert classify_line(_spans("Important Note", bold=True)) == "heading"

    def test_heading_not_if_colored(self):
        """Bold + colored = code, not heading."""
        spans = [CharSpan(text="def", fg="blue", bold=True)]
        assert classify_line(spans) == "code"

    def test_list_item_dash(self):
        assert classify_line(_spans("- Item one")) == "list_item"

    def test_list_item_asterisk(self):
        assert classify_line(_spans("* Another item")) == "list_item"

    def test_list_item_numbered(self):
        assert classify_line(_spans("1. First item")) == "list_item"
        assert classify_line(_spans("42) Last item")) == "list_item"

    def test_list_item_bullet(self):
        assert classify_line(_spans("• Bullet item")) == "list_item"

    def test_separator_box_drawing(self):
        assert classify_line(_spans("─" * 40)) == "separator"

    def test_separator_with_fffd(self):
        """pyte produces trailing U+FFFD artifacts on separator lines."""
        assert classify_line(_spans("─" * 30 + "\ufffd\ufffd")) == "separator"


# ---------------------------------------------------------------------------
# _has_code_colors
# ---------------------------------------------------------------------------

class TestHasCodeColors:
    def test_no_colors(self):
        assert not _has_code_colors(_spans("hello"))

    def test_blue(self):
        assert _has_code_colors([CharSpan(text="def", fg="blue")])

    def test_whitespace_only_colored_ignored(self):
        """Whitespace-only spans with code colors should not count."""
        assert not _has_code_colors([CharSpan(text="   ", fg="blue")])


# ---------------------------------------------------------------------------
# _insert_inline_code_markers
# ---------------------------------------------------------------------------

class TestInsertInlineCodeMarkers:
    def test_no_colored_spans(self):
        spans = [CharSpan(text="This is plain text.", fg="default")]
        assert _insert_inline_code_markers(spans) == "This is plain text."

    def test_single_inline_code(self):
        spans = [
            CharSpan(text="Use the ", fg="default"),
            CharSpan(text="print", fg="cyan"),
            CharSpan(text=" function.", fg="default"),
        ]
        result = _insert_inline_code_markers(spans)
        assert result == "Use the `print` function."

    def test_multiple_inline_codes(self):
        spans = [
            CharSpan(text="Call ", fg="default"),
            CharSpan(text="foo", fg="brown"),
            CharSpan(text=" and ", fg="default"),
            CharSpan(text="bar", fg="brown"),
            CharSpan(text=".", fg="default"),
        ]
        result = _insert_inline_code_markers(spans)
        assert result == "Call `foo` and `bar`."

    def test_long_colored_span_not_wrapped(self):
        """Colored spans >= 60 chars should not get backtick-wrapped."""
        long_text = "x" * 60
        spans = [CharSpan(text=long_text, fg="blue")]
        result = _insert_inline_code_markers(spans)
        assert "`" not in result

    def test_preserves_whitespace_around_code(self):
        spans = [
            CharSpan(text="Use ", fg="default"),
            CharSpan(text=" def ", fg="blue"),
            CharSpan(text=" keyword", fg="default"),
        ]
        result = _insert_inline_code_markers(spans)
        assert "`def`" in result


# ---------------------------------------------------------------------------
# classify_regions
# ---------------------------------------------------------------------------

class TestClassifyRegions:
    def test_empty_input(self):
        assert classify_regions([]) == []

    def test_single_prose_line(self):
        lines = [_spans("Hello world")]
        regions = classify_regions(lines)
        assert len(regions) == 1
        assert regions[0].type == "prose"
        assert regions[0].text == "Hello world"

    def test_single_code_block(self):
        lines = [
            [CharSpan(text="def", fg="blue"), CharSpan(text=" foo():", fg="default")],
            [CharSpan(text="    ", fg="default"), CharSpan(text="print", fg="cyan"),
             CharSpan(text="(42)", fg="default")],
        ]
        regions = classify_regions(lines)
        code_blocks = [r for r in regions if r.type == "code_block"]
        assert len(code_blocks) == 1
        assert "def foo():" in code_blocks[0].text
        assert "print(42)" in code_blocks[0].text

    def test_prose_then_code_then_prose(self):
        lines = [
            _spans("Here is an example:"),
            [],  # blank
            [CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="    ", fg="default"), CharSpan(text="pass", fg="blue")],
            [],  # blank
            _spans("That was the function."),
        ]
        regions = classify_regions(lines)
        types = [r.type for r in regions]
        assert "prose" in types
        assert "code_block" in types
        assert types.count("code_block") == 1

    def test_gap_tolerance_comment_in_code(self):
        """A single non-code line between code lines stays in the code block."""
        lines = [
            [CharSpan(text="x", fg="brown"), CharSpan(text=" = 1", fg="default")],
            _spans("# This is a comment"),  # default fg, between code
            [CharSpan(text="y", fg="brown"), CharSpan(text=" = 2", fg="default")],
        ]
        regions = classify_regions(lines)
        code_blocks = [r for r in regions if r.type == "code_block"]
        assert len(code_blocks) == 1
        assert "# This is a comment" in code_blocks[0].text

    def test_heading_region(self):
        lines = [_spans("Summary", bold=True)]
        regions = classify_regions(lines)
        assert len(regions) == 1
        assert regions[0].type == "heading"
        assert regions[0].text == "Summary"

    def test_list_region(self):
        lines = [
            _spans("- First item"),
            _spans("- Second item"),
        ]
        regions = classify_regions(lines)
        assert len(regions) == 1
        assert regions[0].type == "list"
        assert "First item" in regions[0].text
        assert "Second item" in regions[0].text

    def test_list_with_inline_code(self):
        lines = [
            [CharSpan(text="- Use ", fg="default"), CharSpan(text="print", fg="cyan")],
            _spans("- Simple text"),
        ]
        regions = classify_regions(lines)
        list_regions = [r for r in regions if r.type == "list"]
        assert len(list_regions) == 1
        assert "`print`" in list_regions[0].text

    def test_separator_region(self):
        lines = [_spans("─" * 40)]
        regions = classify_regions(lines)
        assert len(regions) == 1
        assert regions[0].type == "separator"

    def test_blank_region(self):
        lines = [[], _spans("text"), []]
        regions = classify_regions(lines)
        types = [r.type for r in regions]
        assert types[0] == "blank"
        assert types[-1] == "blank"

    def test_adjacent_code_lines_merge(self):
        """Multiple consecutive code lines should merge into one code_block."""
        lines = [
            [CharSpan(text="import", fg="blue"), CharSpan(text=" os", fg="default")],
            [CharSpan(text="import", fg="blue"), CharSpan(text=" sys", fg="default")],
            [CharSpan(text="import", fg="blue"), CharSpan(text=" re", fg="default")],
        ]
        regions = classify_regions(lines)
        code_blocks = [r for r in regions if r.type == "code_block"]
        assert len(code_blocks) == 1
        assert code_blocks[0].text.count("import") == 3

    def test_adjacent_prose_lines_merge(self):
        lines = [
            _spans("First paragraph line."),
            _spans("Second line of same paragraph."),
        ]
        regions = classify_regions(lines)
        prose = [r for r in regions if r.type == "prose"]
        assert len(prose) == 1

    def test_full_claude_response_simulation(self):
        """Simulate a typical Claude response with mixed content."""
        emu = TerminalEmulator(rows=20, cols=80)
        emu.feed("Here is a Python function:\r\n")
        emu.feed("\r\n")
        emu.feed("\x1b[34mdef\x1b[0m \x1b[33mgreet\x1b[0m(name):\r\n")
        emu.feed("    \x1b[36mprint\x1b[0m(\x1b[31mf\"Hello, {name}!\"\x1b[0m)\r\n")
        emu.feed("\r\n")
        emu.feed("This function:\r\n")
        emu.feed("- Takes a \x1b[33mname\x1b[0m parameter\r\n")
        emu.feed("- Uses \x1b[36mprint\x1b[0m to output\r\n")

        lines = emu.get_attributed_lines()
        regions = classify_regions(lines)

        # Should have: prose, blank, code_block, blank, prose, list
        types = [r.type for r in regions if r.type != "blank"]
        assert "prose" in types
        assert "code_block" in types
        assert "list" in types

        # Code block should contain the function
        code = next(r for r in regions if r.type == "code_block")
        assert "def greet" in code.text
        assert "print" in code.text

        # List should have inline code markers
        list_r = next(r for r in regions if r.type == "list")
        assert "`name`" in list_r.text
        assert "`print`" in list_r.text


# ---------------------------------------------------------------------------
# Integration: TerminalEmulator → classify_regions
# ---------------------------------------------------------------------------

class TestAttributedIntegration:
    def test_get_attributed_lines_basic(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("\x1b[34mdef\x1b[0m \x1b[33mhello\x1b[0m():")
        lines = emu.get_attributed_lines()
        assert len(lines) == 5  # all rows returned
        first = lines[0]
        assert any(s.fg == "blue" for s in first)
        assert any(s.fg == "brown" for s in first)

    def test_get_attributed_lines_empty_screen(self):
        emu = TerminalEmulator(rows=3, cols=20)
        lines = emu.get_attributed_lines()
        assert len(lines) == 3
        assert all(len(line) == 0 for line in lines)

    def test_get_full_attributed_lines_with_history(self):
        emu = TerminalEmulator(rows=5, cols=40)
        for i in range(10):
            emu.feed(f"\x1b[34mline_{i}\x1b[0m\r\n")
        full = emu.get_full_attributed_lines()
        # Should have history + display
        assert len(full) > 5
        # First line in history should have blue color
        first_history = full[0]
        assert any(s.fg == "blue" for s in first_history)

    def test_get_attributed_changes_tracks_diffs(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("hello")
        ch1 = emu.get_attributed_changes()
        assert len(ch1) == 1

        # No new data = no changes
        ch2 = emu.get_attributed_changes()
        assert ch2 == []

        # New data with color = changes with attributes
        emu.feed("\r\n\x1b[31mred text\x1b[0m")
        ch3 = emu.get_attributed_changes()
        assert len(ch3) == 1
        assert any(s.fg == "red" for s in ch3[0])

    def test_char_span_frozen(self):
        """CharSpan is frozen (immutable)."""
        span = CharSpan(text="hello", fg="blue", bold=True)
        assert span.text == "hello"
        assert span.fg == "blue"
        assert span.bold is True
        try:
            span.text = "world"
            assert False, "Should not be mutable"
        except AttributeError:
            pass

    def test_attributed_to_regions_no_colors(self):
        """Plain text without any ANSI colors should classify as prose."""
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("    x = 42\r\n    y = x + 1")
        lines = emu.get_attributed_lines()
        regions = classify_regions(lines)
        # Without color, classified as prose (not code)
        prose = [r for r in regions if r.type == "prose"]
        assert len(prose) >= 1
        assert "x = 42" in prose[0].text

    def test_bold_text_classified_as_heading(self):
        emu = TerminalEmulator(rows=3, cols=40)
        emu.feed("\x1b[1mSection Title\x1b[0m")
        lines = emu.get_attributed_lines()
        regions = classify_regions(lines)
        headings = [r for r in regions if r.type == "heading"]
        assert len(headings) == 1
        assert headings[0].text == "Section Title"

    def test_separator_classified(self):
        emu = TerminalEmulator(rows=3, cols=60)
        emu.feed("─" * 40)
        lines = emu.get_attributed_lines()
        regions = classify_regions(lines)
        seps = [r for r in regions if r.type == "separator"]
        assert len(seps) == 1
