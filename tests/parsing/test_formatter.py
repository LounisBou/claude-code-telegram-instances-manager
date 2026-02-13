from src.parsing.content_classifier import ContentRegion
from src.telegram.formatter import (
    TELEGRAM_MAX_LENGTH,
    _wrap_file_paths,
    format_html,
    reflow_text,
    render_regions,
    split_message,
)


class TestReflowText:
    """Tests for reflow_text: terminal-wrapped text → natural paragraphs."""

    def test_empty_string(self):
        assert reflow_text("") == ""

    def test_blank_lines_preserved(self):
        """Blank lines are paragraph separators and must be kept."""
        result = reflow_text("First paragraph\n\nSecond paragraph")
        assert "\n\n" in result

    def test_continuation_lines_joined(self):
        """Lines that look like terminal wraps (≥72 chars) get joined with spaces."""
        # Simulate pyte wrapping at ~80 cols: first line is 75 chars
        long_line = "This is a long sentence that demonstrates how pyte wraps text at the column"
        result = reflow_text(f"{long_line}\nlimit of the terminal")
        assert "column limit" in result

    def test_short_lines_not_joined(self):
        """Short lines (<72 chars) are intentional breaks, not terminal wraps."""
        result = reflow_text("Red\nGreen\nBlue")
        assert result == "Red\nGreen\nBlue"

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

    def test_capitalized_label_not_joined(self):
        """Regression: capitalized labels like Class:, Fields: must break."""
        # Simulate terminal output where a long line is followed by labels
        long_line = "Fields: enabled: bool = False, trace: bool = False, verbose: bool = False"
        text = f"{long_line}\nPurpose: Debug flags\nClass: AppConfig"
        result = reflow_text(text)
        # Each label should be on its own line, not joined
        assert "Purpose: Debug flags" in result
        assert "\nClass: AppConfig" in result


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


class TestRenderRegions:
    """Tests for render_regions: ContentRegion list → markdown text."""

    def test_empty_regions(self):
        assert render_regions([]) == ""

    def test_prose_region(self):
        regions = [ContentRegion(type="prose", text="Hello world")]
        assert render_regions(regions) == "Hello world"

    def test_code_block_region(self):
        regions = [ContentRegion(type="code_block", text="def foo():\n    pass")]
        result = render_regions(regions)
        assert result.startswith("```")
        assert "def foo():" in result
        assert result.endswith("```")

    def test_code_block_with_language(self):
        regions = [ContentRegion(
            type="code_block", text="print('hi')", language="python"
        )]
        result = render_regions(regions)
        assert "```python" in result

    def test_heading_region(self):
        regions = [ContentRegion(type="heading", text="Summary")]
        assert render_regions(regions) == "**Summary**"

    def test_separator_suppressed(self):
        regions = [ContentRegion(type="separator", text="────────")]
        assert render_regions(regions) == ""

    def test_blank_region(self):
        regions = [ContentRegion(type="blank", text="")]
        assert render_regions(regions) == ""

    def test_list_region(self):
        regions = [ContentRegion(type="list", text="- Item 1\n- Item 2")]
        assert render_regions(regions) == "- Item 1\n- Item 2"

    def test_mixed_regions(self):
        regions = [
            ContentRegion(type="prose", text="Introduction:"),
            ContentRegion(type="blank", text=""),
            ContentRegion(type="code_block", text="x = 1"),
            ContentRegion(type="blank", text=""),
            ContentRegion(type="prose", text="The variable `x` is set."),
        ]
        result = render_regions(regions)
        assert "Introduction:" in result
        assert "```\nx = 1\n```" in result
        assert "`x`" in result

    def test_full_pipeline_code_becomes_pre(self):
        """End-to-end: render_regions → reflow_text → format_html."""
        regions = [
            ContentRegion(type="prose", text="Example:"),
            ContentRegion(type="code_block", text="def hello():\n    print('hi')"),
            ContentRegion(type="prose", text="Uses the `print` builtin."),
        ]
        rendered = render_regions(regions)
        html = format_html(reflow_text(rendered))
        assert "<pre><code>" in html
        assert "def hello():" in html
        assert "<code>print</code>" in html

    def test_full_pipeline_heading_becomes_bold(self):
        regions = [
            ContentRegion(type="heading", text="Important"),
            ContentRegion(type="prose", text="This matters."),
        ]
        rendered = render_regions(regions)
        html = format_html(reflow_text(rendered))
        assert "<b>Important</b>" in html

    def test_full_pipeline_list_becomes_bullets(self):
        regions = [
            ContentRegion(type="list", text="- First\n- Second"),
        ]
        rendered = render_regions(regions)
        html = format_html(reflow_text(rendered))
        assert "•" in html


class TestFilePathAutoLinkPrevention:
    """Regression tests for issue 002: Telegram auto-links .py/.js/etc as URLs."""

    def test_bare_filename_wrapped_in_code(self):
        """Bare filenames with TLD extensions must be wrapped in <code>."""
        result = format_html("Here is main.py for you")
        assert "<code>main.py</code>" in result
        # Should not be plain text that Telegram can auto-link
        assert "main.py</code>" in result

    def test_path_wrapped_in_code(self):
        """File paths with slashes must be wrapped in <code>."""
        result = format_html("Look at src/main.py please")
        assert "<code>src/main.py</code>" in result

    def test_url_not_wrapped(self):
        """URLs must NOT be wrapped — only file paths."""
        result = _wrap_file_paths("Visit https://main.py/path")
        assert "`" not in result

    def test_already_in_backticks_not_double_wrapped(self):
        """File paths already in backticks must not get double-wrapped."""
        result = format_html("See `main.py` here")
        assert "<code>main.py</code>" in result
        # No double <code> tags
        assert "<code><code>" not in result

    def test_non_tld_extension_not_wrapped_bare(self):
        """Bare filenames with non-TLD extensions should not be wrapped."""
        result = _wrap_file_paths("See readme.txt")
        assert "`" not in result

    def test_various_tld_extensions(self):
        """Common code extensions that are also TLDs must be wrapped."""
        for ext in ["py", "js", "ts", "go", "rs", "sh", "io", "md"]:
            result = _wrap_file_paths(f"file.{ext}")
            assert f"`file.{ext}`" in result, f".{ext} not wrapped"

    def test_init_py_wrapped(self):
        """__init__.py must be wrapped (common Python pattern)."""
        result = format_html("The __init__.py file")
        assert "<code>__init__.py</code>" in result
