"""Tests for output_pipeline.py — span helpers and rendering pipelines."""

from __future__ import annotations

from src.parsing.terminal_emulator import CharSpan
from src.telegram.output_pipeline import (
    CONTENT_STATES,
    dedent_attr_lines,
    filter_response_attr,
    find_last_prompt,
    lstrip_n_chars,
    render_ansi,
    render_heuristic,
    strip_marker_from_spans,
)


def _span(text: str, fg: str = "default", bold: bool = False) -> CharSpan:
    return CharSpan(text=text, fg=fg, bold=bold, italic=False)


class TestStripMarkerFromSpans:
    """strip_marker_from_spans removes Unicode markers from spans."""

    def test_strips_response_marker(self):
        spans = [_span("⏺ Hello")]
        result = strip_marker_from_spans(spans, "⏺")
        assert len(result) == 1
        assert result[0].text == "Hello"

    def test_strips_tool_connector(self):
        spans = [_span("⎿ Output")]
        result = strip_marker_from_spans(spans, "⎿")
        assert len(result) == 1
        assert result[0].text == "Output"

    def test_preserves_attributes(self):
        spans = [_span("⏺ Code", fg="blue", bold=True)]
        result = strip_marker_from_spans(spans, "⏺")
        assert result[0].fg == "blue"
        assert result[0].bold is True

    def test_no_marker_returns_same(self):
        spans = [_span("No marker")]
        result = strip_marker_from_spans(spans, "⏺")
        assert result[0].text == "No marker"

    def test_empty_after_strip_omitted(self):
        spans = [_span("⏺"), _span(" rest")]
        result = strip_marker_from_spans(spans, "⏺")
        assert len(result) == 1
        assert result[0].text == " rest"


class TestLstripNChars:
    """lstrip_n_chars removes N leading characters across spans."""

    def test_strips_from_single_span(self):
        spans = [_span("  Hello")]
        result = lstrip_n_chars(spans, 2)
        assert result[0].text == "Hello"

    def test_strips_across_spans(self):
        spans = [_span("  "), _span("Hello")]
        result = lstrip_n_chars(spans, 2)
        assert len(result) == 1
        assert result[0].text == "Hello"

    def test_splits_span_at_boundary(self):
        spans = [_span("  Hello")]
        result = lstrip_n_chars(spans, 1)
        assert result[0].text == " Hello"

    def test_zero_noop(self):
        spans = [_span("Hello")]
        result = lstrip_n_chars(spans, 0)
        assert result[0].text == "Hello"


class TestDedentAttrLines:
    """dedent_attr_lines removes common leading whitespace."""

    def test_removes_common_margin(self):
        lines = [
            [_span("  Hello")],
            [_span("  World")],
        ]
        result = dedent_attr_lines(lines)
        assert "".join(s.text for s in result[0]) == "Hello"
        assert "".join(s.text for s in result[1]) == "World"

    def test_preserves_relative_indent(self):
        lines = [
            [_span("  Hello")],
            [_span("    Indented")],
        ]
        result = dedent_attr_lines(lines)
        text_0 = "".join(s.text for s in result[0])
        text_1 = "".join(s.text for s in result[1])
        assert text_0 == "Hello"
        assert text_1 == "  Indented"

    def test_skip_indices_excluded_from_computation(self):
        lines = [
            [_span("Hello")],       # index 0: skip (no indent)
            [_span("  World")],     # index 1: has indent
            [_span("  More")],      # index 2: has indent
        ]
        result = dedent_attr_lines(lines, skip_indices={0})
        text_0 = "".join(s.text for s in result[0])
        text_1 = "".join(s.text for s in result[1])
        assert text_0 == "Hello"  # unchanged (skipped)
        assert text_1 == "World"  # dedented


class TestFilterResponseAttr:
    """filter_response_attr keeps only response content spans."""

    def test_keeps_content_lines(self):
        source = ["Hello world"]
        attr = [[_span("Hello world")]]
        result = filter_response_attr(source, attr)
        assert len(result) == 1

    def test_filters_separator(self):
        source = ["────────────────────"]
        attr = [[_span("────────────────────")]]
        result = filter_response_attr(source, attr)
        assert len(result) == 0

    def test_strips_response_marker(self):
        source = ["⏺ Hello"]
        attr = [[_span("⏺ Hello")]]
        result = filter_response_attr(source, attr)
        text = "".join(s.text for s in result[0])
        assert "⏺" not in text

    def test_skips_prompt_continuation(self):
        source = ["❯ user input", "continuation", "⏺ Response"]
        attr = [
            [_span("❯ user input")],
            [_span("continuation")],
            [_span("⏺ Response")],
        ]
        result = filter_response_attr(source, attr)
        assert len(result) == 1  # only the response line


class TestFindLastPrompt:
    """find_last_prompt finds user prompt boundary."""

    def test_finds_prompt_with_response_below(self):
        display = [
            "❯ hello world",
            "⏺ Response text",
            "",
        ]
        assert find_last_prompt(display) == 0

    def test_ignores_bare_prompt(self):
        display = [
            "❯",
            "⏺ Response",
        ]
        assert find_last_prompt(display) is None

    def test_ignores_prompt_without_response_below(self):
        display = [
            "❯ hello world",
            "Some other text",
        ]
        assert find_last_prompt(display) is None

    def test_returns_last_matching(self):
        display = [
            "❯ first input",
            "⏺ First response",
            "❯ second input",
            "⏺ Second response",
        ]
        assert find_last_prompt(display) == 2


class TestContentStates:
    """CONTENT_STATES includes the right state values."""

    def test_streaming_in_content_states(self):
        assert "streaming" in CONTENT_STATES

    def test_startup_not_in_content_states(self):
        assert "startup" not in CONTENT_STATES

    def test_idle_not_in_content_states(self):
        assert "idle" not in CONTENT_STATES


class TestRenderHeuristic:
    """render_heuristic produces HTML from plain text."""

    def test_wraps_code_blocks(self):
        content = "Hello\n```python\nprint('hi')\n```"
        result = render_heuristic(content)
        assert "<pre>" in result or "<code>" in result

    def test_plain_text_passes_through(self):
        result = render_heuristic("Hello world")
        assert "Hello world" in result


class TestRenderAnsi:
    """render_ansi produces HTML from attributed spans."""

    def test_renders_prose(self):
        source = ["  Hello world"]
        attr = [[_span("  Hello world")]]
        result = render_ansi(source, attr)
        assert "Hello world" in result

    def test_renders_code_with_colors(self):
        source = ["  def foo():"]
        attr = [[_span("  "), _span("def", fg="blue"), _span(" foo():")]]
        result = render_ansi(source, attr)
        assert "def" in result
