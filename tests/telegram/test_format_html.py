"""Tests for format_html() — Telegram HTML output formatting."""

from __future__ import annotations

from src.telegram.formatter import format_html, wrap_code_blocks


class TestFormatHtmlEscaping:
    """HTML special characters must be escaped outside tags."""

    def test_escapes_angle_brackets(self):
        assert format_html("a < b > c") == "a &lt; b &gt; c"

    def test_escapes_ampersand(self):
        assert format_html("A & B") == "A &amp; B"

    def test_empty_string(self):
        assert format_html("") == ""


class TestFormatHtmlBold:
    """**bold** must become <b>bold</b>."""

    def test_bold_conversion(self):
        result = format_html("This is **bold** text")
        assert "<b>bold</b>" in result

    def test_multiple_bold(self):
        result = format_html("**one** and **two**")
        assert "<b>one</b>" in result
        assert "<b>two</b>" in result


class TestFormatHtmlItalic:
    """*italic* must become <i>italic</i>."""

    def test_italic_conversion(self):
        result = format_html("This is *italic* text")
        assert "<i>italic</i>" in result

    def test_bold_not_treated_as_italic(self):
        result = format_html("This is **bold** text")
        assert "<i>" not in result


class TestFormatHtmlInlineCode:
    """`code` must become <code>code</code>."""

    def test_inline_code(self):
        result = format_html("Use the `print()` function")
        assert "<code>print()</code>" in result

    def test_code_content_escaped(self):
        result = format_html("Use `a < b`")
        assert "<code>a &lt; b</code>" in result


class TestFormatHtmlCodeBlocks:
    """```lang ... ``` must become <pre><code>...</code></pre>."""

    def test_code_block_with_language(self):
        text = "Before\n```python\nprint('hi')\n```\nAfter"
        result = format_html(text)
        assert '<pre><code class="language-python">' in result
        assert "print(&#x27;hi&#x27;)" in result or "print('hi')" in result
        assert "</code></pre>" in result

    def test_code_block_without_language(self):
        text = "```\nsome code\n```"
        result = format_html(text)
        assert "<pre><code>" in result
        assert "some code" in result

    def test_code_block_content_escaped(self):
        text = "```\na < b && c > d\n```"
        result = format_html(text)
        assert "a &lt; b &amp;&amp; c &gt; d" in result


class TestFormatHtmlBlockquotes:
    """Tool output lines stay as plain text after format_html."""

    def test_short_blockquote(self):
        text = "Result:\nfile.txt line 1\nfile.txt line 2"
        result = format_html(text)
        assert "file.txt line 1" in result


class TestFormatHtmlLists:
    """List items with label — description must bold the label."""

    def test_dash_label_description(self):
        result = format_html("- label — description")
        assert "• <b>label</b> — description" in result

    def test_plain_list_item(self):
        result = format_html("- plain item")
        assert "• plain item" in result

    def test_list_with_bold_no_double_tags(self):
        """Bold in list label must not create nested <b> tags."""
        result = format_html("- **label** — desc")
        assert "<b><b>" not in result
        assert "• <b>label</b> — desc" in result

    def test_ordered_list_unchanged(self):
        result = format_html("1. first item")
        assert "1. first item" in result


class TestFormatHtmlSectionHeaders:
    """Lines ending with : that look like headers get bolded."""

    def test_section_header(self):
        result = format_html("Key components:")
        assert "<b>Key components:</b>" in result

    def test_url_not_treated_as_header(self):
        """URLs containing colons must NOT be treated as section headers."""
        result = format_html("Visit https://example.com for more")
        assert "<b>" not in result


class TestFormatHtmlCombined:
    """Multiple formatting rules in one text."""

    def test_bold_and_code(self):
        result = format_html("**Important**: use `foo()`")
        assert "<b>Important</b>" in result
        assert "<code>foo()</code>" in result

    def test_full_response(self):
        text = (
            "Here's the plan:\n"
            "\n"
            "- **Step 1** — do something\n"
            "- Step 2 — do more\n"
            "\n"
            "```python\nx = 1\n```\n"
            "\n"
            "That's it."
        )
        result = format_html(text)
        assert "<b>Step 1</b>" in result
        assert "<pre><code" in result
        assert "x = 1" in result


class TestWrapCodeBlocks:
    """Heuristic code block detection for terminal-stripped content."""

    def test_python_def_wrapped(self):
        """Python function definition should be wrapped in code fences."""
        text = 'def fibonacci(n: int) -> int:\n    if n <= 1:\n        return n'
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")
        assert result.endswith("\n```")
        assert "def fibonacci" in result

    def test_python_class_wrapped(self):
        """Python class definition should be wrapped."""
        text = "class Foo:\n    pass"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_python_import_wrapped(self):
        """Python import should be wrapped."""
        text = "import os\nimport sys"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_python_from_import_wrapped(self):
        """Python from-import should be wrapped."""
        text = "from pathlib import Path\n\npath = Path('.')"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_async_def_wrapped(self):
        """Async function should be wrapped."""
        text = "async def fetch():\n    await something()"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_js_function_wrapped(self):
        """JavaScript function should be wrapped."""
        text = "function hello() {\n  return 'world';\n}"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_js_const_wrapped(self):
        """JavaScript const should be wrapped."""
        text = "const x = 42;"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_plain_text_not_wrapped(self):
        """Regular prose should NOT be wrapped."""
        text = "Four."
        result = wrap_code_blocks(text)
        assert result == "Four."

    def test_sentence_not_wrapped(self):
        """A normal sentence should NOT be wrapped."""
        text = "The capital of France is Paris."
        result = wrap_code_blocks(text)
        assert result == text

    def test_list_not_wrapped(self):
        """A numbered list should NOT be wrapped."""
        text = "1. First item\n2. Second item\n3. Third item"
        result = wrap_code_blocks(text)
        assert result == text

    def test_empty_returns_empty(self):
        """Empty input should return empty."""
        assert wrap_code_blocks("") == ""

    def test_decorator_wrapped(self):
        """Python decorator should be wrapped."""
        text = "@app.route('/api')\ndef handler():\n    pass"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_shebang_wrapped(self):
        """Shebang line should be wrapped."""
        text = "#!/usr/bin/env python3\nimport sys"
        result = wrap_code_blocks(text)
        assert result.startswith("```\n")

    def test_end_to_end_with_format_html(self):
        """Code detection + format_html should produce <pre><code>."""
        text = "def hello():\n    print('world')"
        wrapped = wrap_code_blocks(text)
        html = format_html(wrapped)
        assert "<pre><code>" in html
        assert "def hello()" in html
