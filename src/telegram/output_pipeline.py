"""Rendering pipeline helpers for terminal-to-Telegram output.

Contains span manipulation utilities and rendering pipeline functions
that transform terminal content into Telegram HTML.

Functions:
    - :func:`strip_marker_from_spans` — remove ⏺/⎿ Unicode markers
    - :func:`lstrip_n_chars` — strip N leading chars from spans
    - :func:`dedent_attr_lines` — remove common leading whitespace
    - :func:`filter_response_attr` — filter attributed lines to response content
    - :func:`find_last_prompt` — locate user prompt boundary on display
    - :func:`render_heuristic` — keyword-based code block detection pipeline
    - :func:`render_ansi` — ANSI-aware region classification pipeline
"""

from __future__ import annotations

from src.parsing.content_classifier import classify_regions
from src.parsing.terminal_emulator import CharSpan
from src.parsing.ui_patterns import classify_text_line
from src.telegram.formatter import (
    format_html, reflow_text, render_regions, wrap_code_blocks,
)


# ---------------------------------------------------------------------------
# Span manipulation helpers
# ---------------------------------------------------------------------------

def strip_marker_from_spans(
    spans: list[CharSpan], marker: str,
) -> list[CharSpan]:
    """Remove a leading Unicode marker (⏺ or ⎿) from attributed spans.

    Strips the marker character and any following space from the first
    non-whitespace span.  Returns a new span list; original is not modified.

    Args:
        spans: Attributed spans for a terminal line.
        marker: The marker character to strip (e.g. '⏺' or '⎿').

    Returns:
        Span list with the marker removed from the leading span.
    """
    result: list[CharSpan] = []
    stripped = False
    for span in spans:
        if not stripped and marker in span.text:
            new_text = span.text.replace(marker, "", 1)
            if new_text.startswith(" "):
                new_text = new_text[1:]
            stripped = True
            if new_text:
                result.append(CharSpan(
                    text=new_text, fg=span.fg,
                    bold=span.bold, italic=span.italic,
                ))
        else:
            result.append(span)
    return result


def lstrip_n_chars(spans: list[CharSpan], n: int) -> list[CharSpan]:
    """Strip *n* leading characters from the start of a span list.

    Removes exactly *n* characters from the beginning of the combined
    span text, splitting spans if necessary.

    Args:
        spans: Attributed spans for one line.
        n: Number of leading characters to strip.

    Returns:
        New span list with *n* characters removed from the front.
    """
    remaining = n
    result: list[CharSpan] = []
    for span in spans:
        if remaining <= 0:
            result.append(span)
            continue
        if len(span.text) <= remaining:
            remaining -= len(span.text)
            continue
        result.append(CharSpan(
            text=span.text[remaining:],
            fg=span.fg, bold=span.bold, italic=span.italic,
        ))
        remaining = 0
    return result


def dedent_attr_lines(
    lines: list[list[CharSpan]],
    skip_indices: set[int] | None = None,
) -> list[list[CharSpan]]:
    """Remove common leading whitespace from attributed lines.

    Computes the minimum indent (leading spaces) across all non-empty
    lines, then strips that many characters from each line's spans.

    Lines whose index is in *skip_indices* are excluded from the
    minimum-indent computation **and** from stripping.

    Args:
        lines: Filtered attributed span lists (one per line).
        skip_indices: Indices of lines to exclude from indent
            computation and stripping (e.g. marker-stripped lines).

    Returns:
        Dedented span lists with common leading whitespace removed.
    """
    _skip = skip_indices or set()
    min_indent = float("inf")
    for i, spans in enumerate(lines):
        if i in _skip:
            continue
        text = "".join(s.text for s in spans)
        lstripped = text.lstrip()
        if lstripped:
            indent = len(text) - len(lstripped)
            min_indent = min(min_indent, indent)
    if min_indent in (0, float("inf")):
        return lines
    result: list[list[CharSpan]] = []
    for spans in lines:
        text = "".join(s.text for s in spans)
        lstripped = text.lstrip()
        indent = (len(text) - len(lstripped)) if lstripped else 0
        if indent >= min_indent:
            result.append(lstrip_n_chars(spans, min_indent))
        else:
            result.append(spans)
    return result


def filter_response_attr(
    source: list[str],
    attr: list[list[CharSpan]],
) -> list[list[CharSpan]]:
    """Filter attributed lines to response content only.

    Uses :func:`~src.parsing.ui_patterns.classify_text_line` on the plain
    text version of each line to identify terminal chrome and returns only
    the attributed lines that correspond to Claude's actual response.

    Marker lines (``⏺``, ``⎿``) have their marker + trailing space
    stripped.  Then :func:`dedent_attr_lines` removes the common
    terminal margin.

    Args:
        source: Plain text lines (parallel to *attr*).
        attr: Attributed span lists (one per line, same length as *source*).

    Returns:
        Filtered and dedented list of attributed span lists.
    """
    result: list[list[CharSpan]] = []
    marker_indices: set[int] = set()
    in_prompt = False
    for plain, spans in zip(source, attr):
        cls = classify_text_line(plain)
        if cls == "prompt":
            in_prompt = True
            continue
        if in_prompt:
            if cls in (
                "response", "tool_connector", "tool_header",
                "thinking", "separator",
            ):
                in_prompt = False
            else:
                continue
        if cls == "content":
            result.append(spans)
        elif cls == "response":
            marker_indices.add(len(result))
            result.append(strip_marker_from_spans(spans, "⏺"))
        elif cls == "tool_connector":
            marker_indices.add(len(result))
            result.append(strip_marker_from_spans(spans, "⎿"))
    return dedent_attr_lines(result, skip_indices=marker_indices)


def find_last_prompt(display: list[str]) -> int | None:
    """Find index of the last user prompt line on the display.

    Looks for ``❯`` lines with text longer than 2 chars, then validates
    that response content (a ``⏺`` marker) exists below the prompt.

    Args:
        display: Terminal display lines from the emulator.

    Returns:
        Line index of the last prompt with response content below it,
        or ``None`` if no qualifying prompt is visible.
    """
    result = None
    for i, line in enumerate(display):
        s = line.strip()
        if s.startswith("❯") and len(s) > 2:
            if any(
                dl.strip().startswith("⏺") for dl in display[i + 1:]
            ):
                result = i
    return result


# ---------------------------------------------------------------------------
# Rendering pipelines
# ---------------------------------------------------------------------------

# States that produce user-visible output sent to Telegram.
CONTENT_STATES = {
    "streaming",
    "tool_running",
    "tool_result",
    "error",
    "todo_list",
    "parallel_agents",
    "background_task",
}


def render_heuristic(content: str) -> str:
    """Render content using the keyword-based heuristic pipeline.

    Applies code block wrapping based on keyword detection, then reflowing
    and HTML formatting.

    Args:
        content: Plain text content extracted from terminal.

    Returns:
        Telegram HTML string.
    """
    return format_html(reflow_text(wrap_code_blocks(content)))


def render_ansi(
    source: list[str],
    attr: list[list[CharSpan]],
) -> str:
    """Render content using the ANSI-aware pipeline.

    Filters attributed lines to response content, classifies them into
    semantic regions (code blocks, prose, headings, lists) using pyte
    color attributes, then renders to Telegram HTML.

    Args:
        source: Plain text display lines.
        attr: Attributed span lists (parallel to *source*).

    Returns:
        Telegram HTML string.
    """
    filtered = filter_response_attr(source, attr)
    regions = classify_regions(filtered)
    rendered = render_regions(regions)
    return format_html(reflow_text(rendered))
