from src.telegram.formatter import TELEGRAM_MAX_LENGTH, format_telegram, reflow_text, split_message


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


class TestReflowText:
    """Tests for reflow_text: terminal-wrapped text → natural paragraphs."""

    def test_empty_string(self):
        assert reflow_text("") == ""

    def test_blank_lines_preserved(self):
        """Blank lines are paragraph separators and must be kept."""
        result = reflow_text("First paragraph\n\nSecond paragraph")
        assert "\n\n" in result

    def test_continuation_lines_joined(self):
        """Lines that look like terminal wraps get joined with spaces."""
        result = reflow_text("This is a long sentence that was\nwrapped by the terminal")
        assert "that was wrapped by" in result

    def test_code_fence_preserved_verbatim(self):
        """Code blocks must not be reflowed."""
        text = "Before\n```python\nline1\nline2\n```\nAfter"
        result = reflow_text(text)
        assert "line1\nline2" in result

    def test_code_fence_without_closing(self):
        """Unclosed code fence preserves remaining lines."""
        text = "```\nline1\nline2"
        result = reflow_text(text)
        assert "line1" in result
        assert "line2" in result

    def test_list_items_not_joined(self):
        """List items are block-start patterns and must not be joined."""
        text = "Introduction\n- item one\n- item two"
        result = reflow_text(text)
        assert "- item one\n- item two" in result

    def test_ordered_list_not_joined(self):
        """Ordered list items must not be joined to previous lines."""
        text = "Introduction\n1. first\n2. second"
        result = reflow_text(text)
        assert "1. first\n2. second" in result

    def test_colon_label_stops_joining(self):
        """Lines ending with colon are labels — next line must not join."""
        text = "Key components:\nThe first module handles input"
        result = reflow_text(text)
        assert "Key components:\n" in result

    def test_code_fence_mid_paragraph_stops_joining(self):
        """A code fence appearing after text must not be joined."""
        text = "Here is code\n```\nfoo()\n```"
        result = reflow_text(text)
        assert "Here is code\n```" in result

    def test_heading_not_joined(self):
        """Headings (# prefix) are block-start and must not be joined."""
        text = "Some text\n## Heading"
        result = reflow_text(text)
        assert "Some text\n## Heading" in result

    def test_table_row_not_joined(self):
        """Table rows (| prefix) are block-start and must not be joined."""
        text = "Table below\n| col1 | col2 |"
        result = reflow_text(text)
        assert "Table below\n| col1 | col2 |" in result


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
