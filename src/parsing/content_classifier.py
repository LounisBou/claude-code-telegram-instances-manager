"""Classify attributed terminal lines into semantic content regions.

Uses pyte buffer character attributes (foreground color, bold, italic) from
:class:`~src.parsing.terminal_emulator.CharSpan` to reliably distinguish code
blocks, prose, headings, list items, separators, and inline code — replacing
heuristic text-pattern matching.

Claude Code's TUI applies syntax highlighting colors to code (blue for
keywords, red for strings, cyan for builtins, brown for identifiers) while
rendering prose in the default terminal foreground.  This module exploits that
signal to produce :class:`ContentRegion` objects that downstream formatters
can convert directly to Telegram HTML.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from src.parsing.terminal_emulator import CODE_FG_COLORS, CharSpan

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

RegionType = Literal[
    "code_block", "prose", "heading", "list", "separator", "blank"
]


@dataclass
class ContentRegion:
    """A contiguous block of semantically uniform content.

    Attributes:
        type: The semantic category of this region.
        text: Plain text content (may contain backtick markers for inline code
            in prose regions, or raw code for code_block regions).
        language: Optional language hint for code blocks (empty string if
            unknown).
    """

    type: RegionType
    text: str
    language: str = ""


# ---------------------------------------------------------------------------
# Per-line classification
# ---------------------------------------------------------------------------

_LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-*•]\s|\d+[.)]\s)")
_SEPARATOR_RE = re.compile(r"^[─━─\u2500-\u257F\uFFFD\s]+$")


def _has_code_colors(spans: list[CharSpan]) -> bool:
    """Return True if any span uses a syntax-highlighting foreground color."""
    return any(span.fg in CODE_FG_COLORS for span in spans if span.text.strip())


def _all_default_fg(spans: list[CharSpan]) -> bool:
    """Return True if every non-whitespace span has fg='default'."""
    return all(
        span.fg == "default"
        for span in spans
        if span.text.strip()
    )


def _first_nonblank_bold(spans: list[CharSpan]) -> bool:
    """Return True if the first non-whitespace span is bold."""
    for span in spans:
        if span.text.strip():
            return span.bold
    return False


def _spans_to_text(spans: list[CharSpan]) -> str:
    """Concatenate span texts into a single string."""
    return "".join(span.text for span in spans)


def _line_text(spans: list[CharSpan]) -> str:
    """Get the right-stripped text of a span list."""
    return _spans_to_text(spans).rstrip()


LineType = Literal[
    "code", "prose", "heading", "list_item", "separator", "blank"
]


def classify_attr_line(spans: list[CharSpan]) -> LineType:
    """Classify a single line (list of CharSpan) into a semantic type.

    Args:
        spans: Attributed character spans for one terminal line.

    Returns:
        The line's semantic classification.
    """
    if not spans:
        return "blank"

    text = _line_text(spans)
    if not text.strip():
        return "blank"

    # Separator lines: all box-drawing characters / dashes
    if _SEPARATOR_RE.match(text):
        return "separator"

    # List items: starts with - , * , 1. , etc.
    if _LIST_ITEM_RE.match(text):
        return "list_item"

    # Code: any syntax-highlighting color present
    if _has_code_colors(spans):
        return "code"

    # Heading: all default fg, first span bold
    if _all_default_fg(spans) and _first_nonblank_bold(spans):
        return "heading"

    # Default: prose
    return "prose"


# ---------------------------------------------------------------------------
# Inline code detection within prose lines
# ---------------------------------------------------------------------------

def _insert_inline_code_markers(spans: list[CharSpan]) -> str:
    """Build prose text with backtick markers around colored (code) spans.

    Within a prose line, short spans with syntax-highlighting colors represent
    inline code references (variable names, function calls, keywords).  This
    function wraps them in backticks so downstream formatters render them as
    ``<code>`` tags.

    Args:
        spans: Attributed character spans for a prose line.

    Returns:
        Text with backtick-wrapped inline code segments.
    """
    parts: list[str] = []
    for span in spans:
        text = span.text
        if not text:
            continue
        # Colored non-whitespace spans shorter than 60 chars → inline code
        if (
            span.fg in CODE_FG_COLORS
            and text.strip()
            and len(text.strip()) < 60
        ):
            # Preserve leading/trailing whitespace outside the backticks
            stripped = text.strip()
            leading = text[: len(text) - len(text.lstrip())]
            trailing = text[len(text.rstrip()) :]
            parts.append(f"{leading}`{stripped}`{trailing}")
        else:
            parts.append(text)
    return "".join(parts).rstrip()


# ---------------------------------------------------------------------------
# Region grouping
# ---------------------------------------------------------------------------

def classify_regions(
    attributed_lines: list[list[CharSpan]],
) -> list[ContentRegion]:
    """Classify attributed lines into a list of content regions.

    Adjacent lines of the same type are merged into a single region.
    Code lines merge into ``code_block`` regions with 1-line gap tolerance
    (a single non-code line between two code lines stays in the block, as
    it's likely a comment rendered without highlighting).

    Prose lines get inline code markers inserted for any colored spans.

    Args:
        attributed_lines: List of lines, each a list of :class:`CharSpan`.

    Returns:
        Ordered list of :class:`ContentRegion` objects.
    """
    if not attributed_lines:
        return []

    # Step 1: classify each line
    line_types: list[LineType] = []
    line_texts: list[str] = []

    for spans in attributed_lines:
        lt = classify_attr_line(spans)
        line_types.append(lt)
        # For prose lines, insert inline code markers
        if lt == "prose":
            line_texts.append(_insert_inline_code_markers(spans))
        elif lt == "list_item":
            # List items may also contain inline code
            line_texts.append(_insert_inline_code_markers(spans))
        else:
            line_texts.append(_line_text(spans))

    # Step 2: apply 1-line gap tolerance for code blocks.
    # If a non-code line is surrounded by code lines, reclassify it as code.
    for i in range(1, len(line_types) - 1):
        if line_types[i] in ("prose", "blank") and \
           line_types[i - 1] == "code" and line_types[i + 1] == "code":
            line_types[i] = "code"
            # Re-extract text without inline code markers
            line_texts[i] = _line_text(attributed_lines[i])

    # Step 3: group adjacent same-type lines into regions
    regions: list[ContentRegion] = []
    i = 0
    while i < len(line_types):
        lt = line_types[i]
        text = line_texts[i]

        if lt == "blank":
            regions.append(ContentRegion(type="blank", text=""))
            i += 1
            continue

        if lt == "separator":
            regions.append(ContentRegion(type="separator", text=text))
            i += 1
            continue

        if lt == "heading":
            regions.append(ContentRegion(type="heading", text=text))
            i += 1
            continue

        if lt == "code":
            # Collect consecutive code lines into a code block
            code_lines: list[str] = [text]
            i += 1
            while i < len(line_types) and line_types[i] == "code":
                code_lines.append(line_texts[i])
                i += 1
            regions.append(ContentRegion(
                type="code_block",
                text="\n".join(code_lines),
            ))
            continue

        if lt == "list_item":
            # Collect consecutive list items
            list_lines: list[str] = [text]
            i += 1
            while i < len(line_types) and line_types[i] == "list_item":
                list_lines.append(line_texts[i])
                i += 1
            regions.append(ContentRegion(
                type="list",
                text="\n".join(list_lines),
            ))
            continue

        if lt == "prose":
            # Collect consecutive prose lines
            prose_lines: list[str] = [text]
            i += 1
            while i < len(line_types) and line_types[i] == "prose":
                prose_lines.append(line_texts[i])
                i += 1
            regions.append(ContentRegion(
                type="prose",
                text="\n".join(prose_lines),
            ))
            continue

        # Fallback: treat as prose
        regions.append(ContentRegion(type="prose", text=text))
        i += 1

    return regions
