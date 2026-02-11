from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


# --- Screen state model ---


class ScreenState(Enum):
    """Possible states of the Claude Code terminal screen."""

    STARTUP = "startup"
    IDLE = "idle"
    THINKING = "thinking"
    STREAMING = "streaming"
    USER_MESSAGE = "user_message"
    TOOL_REQUEST = "tool_request"
    TOOL_RUNNING = "tool_running"
    TOOL_RESULT = "tool_result"
    BACKGROUND_TASK = "background_task"
    PARALLEL_AGENTS = "parallel_agents"
    TODO_LIST = "todo_list"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class ScreenEvent:
    """Classified screen state with extracted payload and raw lines."""

    state: ScreenState
    payload: dict = field(default_factory=dict)
    raw_lines: list[str] = field(default_factory=list)
    timestamp: float = 0.0


# --- UI element classification ---

# Trailing \uFFFD allowed because pyte renders partial ANSI sequences as replacement chars
_SEPARATOR_RE = re.compile(r"^[─━═]{4,}\uFFFD*$")
# Separator with trailing text overlay from pyte (status text bleeds into separator row)
_SEPARATOR_PREFIX_RE = re.compile(r"^[─━═]{20,}")
_DIFF_DELIMITER_RE = re.compile(r"^[╌]{4,}\uFFFD*$")
_STATUS_BAR_RE = re.compile(
    r"(?P<project>[\w\-]+)\s*│\s*"
    r"(?:⎇\s*(?P<branch>[\w\-/]+)(?P<dirty>\*)?)?\s*"
    r"(?:⇡(?P<ahead>\d+)\s*)?│?\s*"
    r"(?:Usage:\s*(?P<usage>\d+)%)?"
)
_TIMER_RE = re.compile(r"↻\s*([\d:]+)")
# (?:\s|$) instead of \s to handle bare ❯ at end of line without trailing space
_PROMPT_MARKER_RE = re.compile(r"^❯(?:\s|$)")
_BOX_CHAR_RE = re.compile(r"[╭╮╰╯│├┤┬┴┼┌┐└┘]")
_LOGO_RE = re.compile(r"[▐▛▜▌▝▘█▞▚]")

# Thinking stars: ✶✳✻✽✢· followed by text ending with …
_THINKING_STAR_RE = re.compile(r"^[✶✳✻✽✢·]\s+(.+…(?:\s*\(.+\))?)$")

# Claude response marker
_RESPONSE_MARKER_RE = re.compile(r"^⏺\s+(.*)")

# Tool connector
_TOOL_CONNECTOR_RE = re.compile(r"^\s*⎿")

# Tool running/waiting status
_TOOL_STATUS_RE = re.compile(r"^\s*⎿\s+(Running|Waiting)…")
_TOOL_HOOKS_RE = re.compile(r"^\s*⎿\s+Running \w+ hooks…")

# Tool diff result
_TOOL_DIFF_RE = re.compile(r"^\s*⎿\s+Added (\d+) lines?, removed (\d+) lines?")

# Tool header patterns
# Optional ⏺ prefix: Claude sometimes wraps tool calls inside response markers
_TOOL_HEADER_LINE_RE = re.compile(
    r"^\s*(?:⏺\s+)?"
    r"(?:Bash\(|Write\(|Update\(|Read(?:ing)?\s*[\d(]|Searched\s+for\s)"
)
_TOOL_BASH_RE = re.compile(r"Bash\((.+?)\)")
_TOOL_FILE_RE = re.compile(r"(?:Write|Update|Read(?:ing)?)\((.+?)\)")
_TOOL_READ_COLLAPSED_RE = re.compile(r"Read (\d+) files? \(ctrl\+o")
_TOOL_SEARCH_COLLAPSED_RE = re.compile(r"Searched for (.+?) \(ctrl\+o")

# Selection menu
_SELECTION_SELECTED_RE = re.compile(r"^\s*❯\s+(\d+)\.\s+(.+)$")
_SELECTION_UNSELECTED_RE = re.compile(r"^\s+(\d+)\.\s+(.+)$")
_SELECTION_HINT_RE = re.compile(r"Esc to cancel")

# Background task
_BACKGROUND_RE = re.compile(r"in the background")

# Parallel agents
_AGENTS_LAUNCHED_RE = re.compile(r"(\d+) agents? launched")
_AGENT_TREE_ITEM_RE = re.compile(r"^\s*[├└]\s*─\s*(.*)")
_AGENT_COMPLETE_RE = re.compile(r'Agent "(.+?)" completed')
_LOCAL_AGENTS_RE = re.compile(r"(\d+) local agents?")

# TODO list
_TODO_HEADER_RE = re.compile(
    r"(\d+) tasks? \((\d+) done(?:, (\d+) in progress)?, (\d+) open\)"
)
_TODO_ITEM_RE = re.compile(r"^[◻◼✔]\s+")

# Error patterns
_ERROR_RE = re.compile(
    r"MCP server failed|(?:^|\s)Error:|ENOENT|EPERM", re.IGNORECASE
)

# Startup
_STARTUP_RE = re.compile(r"Claude Code v[\d.]+")

# Status bar tip / hint lines
_TIP_RE = re.compile(r"^(?:\w+\s+)?[Tt]ip:\s")
_BARE_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")
_CLAUDE_HINT_RE = re.compile(r"claude\s+--(?:continue|resume)")

# PR indicator in status bar area (standalone "PR #13" line)
_PR_INDICATOR_RE = re.compile(r"^PR\s*#\d+$")

# Context window progress bar (block elements) and/or timer (↻ HH:MM)
_CONTEXT_TIMER_RE = re.compile(r"↻\s*\d+:\d+")
_PROGRESS_BAR_RE = re.compile(r"^[▊▉█▌▍▎▏░▒▓\s]+$")

# Extra status line
_EXTRA_BASH_RE = re.compile(r"(\d+) bash")
_EXTRA_AGENTS_RE = re.compile(r"(\d+) local agents?")
_EXTRA_FILES_RE = re.compile(r"(\d+) files? \+(\d+) -(\d+)")

def classify_line(line: str) -> str:
    """Classify a screen line as a UI element or content.

    Checks the line against known Claude Code UI patterns (separators,
    status bars, thinking indicators, tool headers, etc.) and returns a
    category string.

    Args:
        line: A single terminal screen line to classify.

    Returns:
        One of: 'separator', 'diff_delimiter', 'status_bar', 'startup',
        'thinking', 'tool_header', 'response', 'tool_connector',
        'todo_item', 'agent_tree', 'prompt', 'box', 'logo', 'empty',
        or 'content'.
    """
    stripped = line.strip()
    if not stripped:
        return "empty"
    if _SEPARATOR_RE.match(stripped):
        return "separator"
    # Separator with trailing text overlay (pyte bleed from adjacent columns)
    if _SEPARATOR_PREFIX_RE.match(stripped):
        return "separator"
    if _DIFF_DELIMITER_RE.match(stripped):
        return "diff_delimiter"
    # Startup banner line (e.g. "Claude Code v2.1.39") — must be filtered
    # to prevent leaking into response content when pyte redraws the screen.
    if _STARTUP_RE.search(stripped):
        return "startup"
    # Pre-check: require distinctive status bar markers (⎇ branch or Usage:)
    # to avoid false positives on table data rows containing │
    if ("⎇" in stripped or "Usage:" in stripped) and _STATUS_BAR_RE.search(stripped):
        return "status_bar"
    # Tip/hint lines from Claude Code UI
    if _TIP_RE.match(stripped):
        return "status_bar"
    if _BARE_TIME_RE.match(stripped):
        return "status_bar"
    if _CLAUDE_HINT_RE.search(stripped):
        return "status_bar"
    if _PR_INDICATOR_RE.match(stripped):
        return "status_bar"
    # Context window progress bar and/or timer (e.g. "▊░░░░░░░░░ ↻ 11:00")
    if _CONTEXT_TIMER_RE.search(stripped):
        return "status_bar"
    if _PROGRESS_BAR_RE.match(stripped):
        return "status_bar"
    if _THINKING_STAR_RE.match(stripped):
        return "thinking"
    if _TOOL_HEADER_LINE_RE.match(stripped):
        return "tool_header"
    if stripped.startswith("⏺"):
        return "response"
    if _TOOL_CONNECTOR_RE.match(stripped):
        return "tool_connector"
    if _TODO_ITEM_RE.match(stripped):
        return "todo_item"
    # Agent tree: ├─ name or └─ name (must have text after dash, not pure border)
    if re.match(r"^[├└]\s*─+\s+\w", stripped):
        return "agent_tree"
    if _PROMPT_MARKER_RE.match(stripped):
        return "prompt"
    # Box detection: require 2+ box-drawing chars AND length > 10.
    # But only classify as "box" if the line is mostly structural (borders).
    # Lines with substantial alphabetic content between box chars are table
    # data rows from Claude's response — keep those as "content".
    if _BOX_CHAR_RE.search(stripped) and len(stripped) > 10:
        box_chars = sum(1 for c in stripped if _BOX_CHAR_RE.match(c))
        if box_chars >= 2:
            alpha_chars = sum(1 for c in stripped if c.isalpha())
            if alpha_chars <= 3:
                return "box"
    # Require 3+ block-element chars to distinguish logo from occasional Unicode in content
    if _LOGO_RE.search(stripped):
        logo_chars = sum(1 for c in stripped if _LOGO_RE.match(c))
        if logo_chars >= 3:
            return "logo"
    return "content"


def extract_content(lines: list[str]) -> str:
    """Extract meaningful content from screen lines, filtering UI chrome.

    Keeps lines classified as 'content', 'response' (⏺ prefix stripped),
    and 'tool_connector' (⎿ prefix stripped) by classify_line.

    Args:
        lines: List of terminal screen lines to filter.

    Returns:
        Newline-joined string of content lines, stripped.
    """
    content_lines = []
    for line in lines:
        cls = classify_line(line)
        if cls == "content":
            content_lines.append(line.strip())
        elif cls == "response":
            # ⏺ lines carry Claude's response text — strip the marker.
            # Without this, the first line of every response was silently dropped.
            m = _RESPONSE_MARKER_RE.match(line.strip())
            if m and m.group(1).strip():
                content_lines.append(m.group(1).strip())
        elif cls == "tool_connector":
            # ⎿ lines carry tool output (file contents, command results).
            # Strip the connector prefix to get the actual content.
            text = re.sub(r"^\s*⎿\s*", "", line).strip()
            if text:
                content_lines.append(text)
    return "\n".join(content_lines).strip()
