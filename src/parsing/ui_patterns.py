from __future__ import annotations

import re

from src.parsing.models import ScreenEvent, TerminalView  # noqa: F401 — re-exported


# --- UI element classification ---

# Trailing \uFFFD allowed because pyte renders partial ANSI sequences as replacement chars
SEPARATOR_RE = re.compile(r"^[─━═]{4,}\uFFFD*$")
# Separator with trailing text overlay from pyte (status text bleeds into separator row)
SEPARATOR_PREFIX_RE = re.compile(r"^[─━═]{20,}")
DIFF_DELIMITER_RE = re.compile(r"^[╌]{4,}\uFFFD*$")
STATUS_BAR_RE = re.compile(
    r"(?P<project>[\w\-]+)\s*│\s*"
    r"(?:⎇\s*(?P<branch>[\w\-/]+)(?P<dirty>\*)?)?\s*"
    r"(?:⇡(?P<ahead>\d+)\s*)?│?\s*"
    r"(?:Usage:\s*(?P<usage>\d+)%)?"
)
TIMER_RE = re.compile(r"↻\s*([\d:]+)")
# (?:\s|$) instead of \s to handle bare ❯ at end of line without trailing space
PROMPT_MARKER_RE = re.compile(r"^❯(?:\s|$)")
BOX_CHAR_RE = re.compile(r"[╭╮╰╯│├┤┬┴┼┌┐└┘]")
LOGO_RE = re.compile(r"[▐▛▜▌▝▘█▞▚]")

# Thinking stars: ✶✳✻✽✢· followed by text ending with …
THINKING_STAR_RE = re.compile(r"^[✶✳✻✽✢·]\s+(.+…(?:\s*\(.+\))?)$")

# Claude response marker
RESPONSE_MARKER_RE = re.compile(r"^⏺\s+(.*)")

# Auth/login screen indicators
AUTH_SIGN_IN_RE = re.compile(r"sign in|log in", re.IGNORECASE)
AUTH_PASTE_CODE_RE = re.compile(r"Paste code here", re.IGNORECASE)
AUTH_OAUTH_URL_RE = re.compile(r"claude\.ai/oauth/authorize")

# Tool connector
TOOL_CONNECTOR_RE = re.compile(r"^\s*⎿")

# Tool running/waiting status
TOOL_STATUS_RE = re.compile(r"^\s*⎿\s+(Running|Waiting)…")
TOOL_HOOKS_RE = re.compile(r"^\s*⎿\s+Running \w+ hooks…")

# Tool diff result
TOOL_DIFF_RE = re.compile(r"^\s*⎿\s+Added (\d+) lines?, removed (\d+) lines?")

# Tool header patterns
# Optional ⏺ prefix: Claude sometimes wraps tool calls inside response markers
TOOL_HEADER_LINE_RE = re.compile(
    r"^\s*(?:⏺\s+)?"
    r"(?:Bash\(|Write\(|Update\(|Read(?:ing)?\s*[\d(]|Searched\s+for\s)"
)
TOOL_BASH_RE = re.compile(r"Bash\((.+?)\)")
TOOL_FILE_RE = re.compile(r"(?:Write|Update|Read(?:ing)?)\((.+?)\)")
TOOL_READ_COLLAPSED_RE = re.compile(r"Read (\d+) files? \(ctrl\+o")
TOOL_SEARCH_COLLAPSED_RE = re.compile(r"Searched for (.+?) \(ctrl\+o")

# Selection menu
SELECTION_SELECTED_RE = re.compile(r"^\s*❯\s+(\d+)\.\s+(.+)$")
SELECTION_UNSELECTED_RE = re.compile(r"^\s+(\d+)\.\s+(.+)$")
SELECTION_HINT_RE = re.compile(r"Esc to cancel")

# Background task
BACKGROUND_RE = re.compile(r"in the background")

# Parallel agents
AGENTS_LAUNCHED_RE = re.compile(r"(\d+) agents? launched")
AGENT_TREE_ITEM_RE = re.compile(r"^\s*[├└]\s*─\s*(.*)")
AGENT_COMPLETE_RE = re.compile(r'Agent "(.+?)" completed')
LOCAL_AGENTS_RE = re.compile(r"(\d+) local agents?")

# TODO list
TODO_HEADER_RE = re.compile(
    r"(\d+) tasks? \((\d+) done(?:, (\d+) in progress)?, (\d+) open\)"
)
TODO_ITEM_RE = re.compile(r"^[◻◼✔]\s+")

# Error patterns
ERROR_RE = re.compile(
    r"MCP server failed|(?:^|\s)Error:|ENOENT|EPERM", re.IGNORECASE
)

# Startup
STARTUP_RE = re.compile(r"Claude Code v[\d.]+")

# Status bar tip / hint lines
TIP_RE = re.compile(r"^(?:\w+\s+)?[Tt]ip:\s")
BARE_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
CLAUDE_HINT_RE = re.compile(r"claude\s+--(?:continue|resume)")

# PR indicator in status bar area (standalone "PR #13" line)
PR_INDICATOR_RE = re.compile(r"^PR\s*#\d+$")

# Context window progress bar (block elements) and/or timer (↻ HH:MM)
CONTEXT_TIMER_RE = re.compile(r"↻\s*\d+:\d+")
PROGRESS_BAR_RE = re.compile(r"^[▊▉█▌▍▎▏░▒▓\s]+$")

# Extra status line
EXTRA_BASH_RE = re.compile(r"(\d+) bash")
EXTRA_AGENTS_RE = re.compile(r"(\d+) local agents?")
EXTRA_FILES_RE = re.compile(r"(\d+) files? \+(\d+) -(\d+)")

CHROME_CATEGORIES = frozenset({
    "separator", "diff_delimiter", "status_bar", "prompt",
    "thinking", "startup", "logo", "box", "empty",
})


def classify_text_line(line: str) -> str:
    """Classify a screen line as a UI element or content.

    Checks the line against known Claude Code UI patterns (separators,
    status bars, thinking indicators, tool headers, etc.) and returns a
    category string.

    Args:
        line: A single terminal screen line to classify.

    Returns:
        One of: 'separator', 'diff_delimiter', 'status_bar' (includes
        extra status lines like file-change counters), 'startup',
        'thinking', 'tool_header', 'response', 'tool_connector',
        'todo_item', 'agent_tree', 'prompt', 'box', 'logo', 'empty',
        or 'content'.
    """
    stripped = line.strip()
    if not stripped:
        return "empty"
    if SEPARATOR_RE.match(stripped):
        return "separator"
    # Separator with trailing text overlay (pyte bleed from adjacent columns)
    if SEPARATOR_PREFIX_RE.match(stripped):
        return "separator"
    if DIFF_DELIMITER_RE.match(stripped):
        return "diff_delimiter"
    # Startup banner line (e.g. "Claude Code v2.1.39") — must be filtered
    # to prevent leaking into response content when pyte redraws the screen.
    if STARTUP_RE.search(stripped):
        return "startup"
    # Pre-check: require distinctive status bar markers (⎇ branch or Usage:)
    # to avoid false positives on table data rows containing │
    if ("⎇" in stripped or "Usage:" in stripped) and STATUS_BAR_RE.search(stripped):
        return "status_bar"
    # Tip/hint lines from Claude Code UI
    if TIP_RE.match(stripped):
        return "status_bar"
    if BARE_TIME_RE.match(stripped):
        return "status_bar"
    if CLAUDE_HINT_RE.search(stripped):
        return "status_bar"
    if PR_INDICATOR_RE.match(stripped):
        return "status_bar"
    # Extra status line: "4 files +0 -0 · PR #5", "1 bash · 1 file +194 -192"
    # These are Claude Code's bottom-row status counters.  EXTRA_FILES_RE
    # has a very specific format (N files? +N -N) that doesn't appear in prose.
    # EXTRA_BASH_RE / EXTRA_AGENTS_RE require a · separator to avoid false
    # positives on prose containing "bash" or "local agents".
    if EXTRA_FILES_RE.search(stripped):
        return "status_bar"
    if "\u00b7" in stripped and (
        EXTRA_BASH_RE.search(stripped)
        or EXTRA_AGENTS_RE.search(stripped)
    ):
        return "status_bar"
    # Context window progress bar and/or timer (e.g. "▊░░░░░░░░░ ↻ 11:00")
    if CONTEXT_TIMER_RE.search(stripped):
        return "status_bar"
    if PROGRESS_BAR_RE.match(stripped):
        return "status_bar"
    if THINKING_STAR_RE.match(stripped):
        return "thinking"
    if TOOL_HEADER_LINE_RE.match(stripped):
        return "tool_header"
    if stripped.startswith("⏺"):
        return "response"
    if TOOL_CONNECTOR_RE.match(stripped):
        return "tool_connector"
    if TODO_ITEM_RE.match(stripped):
        return "todo_item"
    # Agent tree: ├─ name or └─ name (must have text after dash, not pure border)
    if re.match(r"^[├└]\s*─+\s+\w", stripped):
        return "agent_tree"
    if PROMPT_MARKER_RE.match(stripped):
        return "prompt"
    # Box detection: require 2+ box-drawing chars AND length > 10.
    # But only classify as "box" if the line is mostly structural (borders).
    # Lines with substantial alphabetic content between box chars are table
    # data rows from Claude's response — keep those as "content".
    if BOX_CHAR_RE.search(stripped) and len(stripped) > 10:
        box_chars = sum(1 for c in stripped if BOX_CHAR_RE.match(c))
        if box_chars >= 2:
            alpha_chars = sum(1 for c in stripped if c.isalpha())
            if alpha_chars <= 3:
                return "box"
    # Require 3+ block-element chars to distinguish logo from occasional Unicode in content
    if LOGO_RE.search(stripped):
        logo_chars = sum(1 for c in stripped if LOGO_RE.match(c))
        if logo_chars >= 3:
            return "logo"
    return "content"

