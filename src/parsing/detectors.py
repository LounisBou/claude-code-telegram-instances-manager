from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from src.parsing.ui_patterns import (
    AGENTS_LAUNCHED_RE,
    AGENT_COMPLETE_RE,
    AGENT_TREE_ITEM_RE,
    BACKGROUND_RE,
    EXTRA_AGENTS_RE,
    EXTRA_BASH_RE,
    EXTRA_FILES_RE,
    SELECTION_HINT_RE,
    SELECTION_SELECTED_RE,
    SELECTION_UNSELECTED_RE,
    STATUS_BAR_RE,
    THINKING_STAR_RE,
    TIMER_RE,
    TODO_HEADER_RE,
)


# --- Prompt detection ---

class PromptType(Enum):
    """Types of interactive prompts in the Claude Code UI."""

    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"


@dataclass
class DetectedPrompt:
    """A detected interactive prompt with its type, options, and default."""

    prompt_type: PromptType
    options: list[str]
    default: str | None = None
    raw_text: str = ""


_YES_NO_RE = re.compile(r"\[([Yy])/([Nn])\]|\[([Nn])/([Yy])\]")
_MULTI_CHOICE_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)
_SELECTION_MENU_RE = re.compile(r"❯\s*(\d+)\.\s+(.+)")


def detect_prompt(text: str) -> DetectedPrompt | None:
    """Detect an interactive prompt (yes/no or multiple choice) in the text.

    Looks for [Y/n] style patterns and numbered selection menus.

    Args:
        text: Screen text to scan for prompt patterns.

    Returns:
        A DetectedPrompt with type, options, and default, or None if no
        prompt pattern is found.
    """
    if not text.strip():
        return None

    match = _YES_NO_RE.search(text)
    if match:
        if match.group(1) and match.group(1).isupper():
            default = "Yes"
        elif match.group(4) and match.group(4).isupper():
            default = "Yes"
        elif match.group(2) and match.group(2).isupper():
            default = "No"
        elif match.group(3) and match.group(3).isupper():
            default = "No"
        else:
            default = None
        return DetectedPrompt(
            prompt_type=PromptType.YES_NO,
            options=["Yes", "No"],
            default=default,
            raw_text=text,
        )

    # Both ❯-prefixed and plain numbered items may match the same option;
    # dedup by number to avoid counting an option twice
    sel_matches = _SELECTION_MENU_RE.findall(text)
    other_choices = _MULTI_CHOICE_RE.findall(text)
    all_choices = sel_matches + other_choices
    if len(all_choices) >= 2:
        seen = {}
        options = []
        for num, label in all_choices:
            if num not in seen:
                seen[num] = True
                options.append(label.strip())
        if len(options) >= 2:
            return DetectedPrompt(
                prompt_type=PromptType.MULTIPLE_CHOICE,
                options=options,
                raw_text=text,
            )

    choices = _MULTI_CHOICE_RE.findall(text)
    if len(choices) >= 2:
        options = [label.strip() for _, label in choices]
        return DetectedPrompt(
            prompt_type=PromptType.MULTIPLE_CHOICE,
            options=options,
            raw_text=text,
        )

    return None


# --- Context usage detection ---

@dataclass
class ContextUsage:
    """Parsed context window usage information from the Claude Code UI."""

    percentage: int | None = None
    needs_compact: bool = False
    raw_text: str = ""


_USAGE_PCT_RE = re.compile(r"Usage:\s*(\d+)%", re.IGNORECASE)
_CONTEXT_PCT_RE = re.compile(r"(?:context|ctx)[:\s]*(\d+)\s*%", re.IGNORECASE)
_CONTEXT_TOKENS_RE = re.compile(r"(\d+)k\s*/\s*(\d+)k\s*tokens", re.IGNORECASE)
_COMPACT_RE = re.compile(r"compact|context.*(?:full|almost|running out)", re.IGNORECASE)


def detect_context_usage(text: str) -> ContextUsage | None:
    """Detect context window usage information from screen text.

    Searches for usage percentage, token counts, and compact-mode
    indicators in the Claude Code UI.

    Args:
        text: Screen text to scan for context usage patterns.

    Returns:
        A ContextUsage with percentage and compact flag, or None if no
        usage information is found.
    """
    if not text.strip():
        return None

    usage_match = _USAGE_PCT_RE.search(text)
    pct_match = _CONTEXT_PCT_RE.search(text)
    token_match = _CONTEXT_TOKENS_RE.search(text)
    compact_match = _COMPACT_RE.search(text)

    if not any([usage_match, pct_match, token_match, compact_match]):
        return None

    percentage = None
    if usage_match:
        percentage = int(usage_match.group(1))
    elif pct_match:
        percentage = int(pct_match.group(1))
    elif token_match:
        used = int(token_match.group(1))
        total = int(token_match.group(2))
        percentage = round(used / total * 100) if total > 0 else None

    return ContextUsage(
        percentage=percentage,
        needs_compact=compact_match is not None,
        raw_text=text,
    )


# --- Status bar parsing ---

@dataclass
class StatusBar:
    """Parsed status bar fields from the Claude Code bottom-of-screen bar."""

    project: str | None = None
    branch: str | None = None
    dirty: bool = False
    commits_ahead: int = 0
    usage_pct: int | None = None
    timer: str | None = None
    raw_text: str = ""


def parse_status_bar(text: str) -> StatusBar | None:
    """Parse Claude Code's status bar line.

    Real format: "claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 7% ▋░░░░░░░░░ ↻ 9:59"

    Args:
        text: A single status bar line from the terminal screen.

    Returns:
        A StatusBar with project, branch, dirty flag, usage percentage,
        and timer, or None if the text does not match the status bar format.
    """
    if not text.strip():
        return None
    match = STATUS_BAR_RE.search(text)
    if not match:
        return None
    project = match.group("project")
    branch = match.group("branch")
    usage = match.group("usage")
    if not project:
        return None
    dirty = bool(match.group("dirty"))
    ahead = match.group("ahead")
    timer_match = TIMER_RE.search(text)
    return StatusBar(
        project=project,
        branch=branch,
        dirty=dirty,
        commits_ahead=int(ahead) if ahead else 0,
        usage_pct=int(usage) if usage else None,
        timer=timer_match.group(1) if timer_match else None,
        raw_text=text,
    )


def parse_extra_status(text: str) -> dict:
    """Parse the extra status line below the main status bar.

    Real formats:
      "1 bash · 1 file +194 -192"
      "4 local agents · 1 file +194 -192"
      "1 file +194 -192"

    Args:
        text: The extra status line text to parse.

    Returns:
        Dict with optional keys 'bash_tasks', 'local_agents',
        'files_changed', 'lines_added', and 'lines_removed'. Empty dict
        if no patterns match.
    """
    result: dict = {}
    m = EXTRA_BASH_RE.search(text)
    if m:
        result["bash_tasks"] = int(m.group(1))
    m = EXTRA_AGENTS_RE.search(text)
    if m:
        result["local_agents"] = int(m.group(1))
    m = EXTRA_FILES_RE.search(text)
    if m:
        result["files_changed"] = int(m.group(1))
        result["lines_added"] = int(m.group(2))
        result["lines_removed"] = int(m.group(3))
    return result


# --- File path detection ---

_FILE_PATH_RE = re.compile(
    r"(?:wrote to|saved|created|generated|output)\s+"
    r"(\/[\w./\-]+\.\w+)",
    re.IGNORECASE,
)


def detect_file_paths(text: str) -> list[str]:
    """Detect absolute file paths mentioned in tool output text.

    Looks for paths following keywords like "wrote to", "saved", "created",
    etc. Only returns paths longer than 5 characters.

    Args:
        text: Screen text to scan for file path references.

    Returns:
        List of detected absolute file path strings.
    """
    if not text.strip():
        return []
    matches = _FILE_PATH_RE.findall(text)
    # Min-length 5 filters out false-positive short paths like "/a.b"
    return [m for m in matches if len(m) > 5]


# --- Screen state detector functions ---


def detect_thinking(lines: list[str]) -> dict | None:
    """Detect a thinking indicator (star + ellipsis) from screen lines.

    Matches lines starting with a thinking star character (e.g. ✶, ✳)
    followed by text ending with an ellipsis, optionally with an elapsed
    time parenthetical.

    Args:
        lines: Terminal screen lines to scan.

    Returns:
        Dict with 'text' (the thinking message) and 'elapsed' (e.g. "5s"
        or None), or None if no thinking indicator is found.
    """
    for line in lines:
        m = THINKING_STAR_RE.match(line.strip())
        if m:
            text = m.group(1)
            elapsed = None
            elapsed_m = re.search(r"\(thought for (\d+s)\)", text)
            if elapsed_m:
                elapsed = elapsed_m.group(1)
            return {"text": text, "elapsed": elapsed}
    return None


def detect_tool_request(lines: list[str]) -> dict | None:
    """Detect a tool approval selection menu from screen lines.

    Looks for the Claude Code pattern of a question followed by numbered
    options with a cursor marker and an "Esc to cancel" hint.

    Args:
        lines: Terminal screen lines to scan.

    Returns:
        Dict with 'question', 'options' list, 'selected' index, and
        'has_hint' flag, or None if no selection menu is found.
    """
    has_selection = False
    has_hint = False
    options: list[tuple[int, str]] = []
    selected_idx: int | None = None
    question: str | None = None

    for line in lines:
        stripped = line.strip()

        # Question line (e.g., "Do you want to create test_capture.txt?")
        if stripped.endswith("?") and not stripped.startswith("❯"):
            question = stripped

        # Selected option: ❯ N. text
        m = SELECTION_SELECTED_RE.match(stripped)
        if m:
            has_selection = True
            idx = int(m.group(1))
            options.append((idx, m.group(2).strip()))
            selected_idx = idx
            continue

        # Match on raw line (not stripped) — indentation distinguishes menu items
        # from other numbered lists in content
        m = SELECTION_UNSELECTED_RE.match(line)
        if m and has_selection:
            options.append((int(m.group(1)), m.group(2).strip()))
            continue

        # Hint line
        if SELECTION_HINT_RE.search(stripped):
            has_hint = True

    if has_selection and len(options) >= 2:
        options.sort(key=lambda x: x[0])
        return {
            "question": question,
            "options": [opt[1] for opt in options],
            "selected": (selected_idx - 1) if selected_idx else 0,
            "has_hint": has_hint,
        }
    return None


def detect_todo_list(lines: list[str]) -> dict | None:
    """Detect a TODO list display from screen lines.

    Parses the header summary (total/done/in-progress/open counts) and
    individual items with their status markers.

    Args:
        lines: Terminal screen lines to scan.

    Returns:
        Dict with counts ('total', 'done', 'in_progress', 'open') and
        'items' list (each with 'text' and 'status'), or None if no TODO
        list is detected.
    """
    header: dict | None = None
    items: list[dict] = []

    for line in lines:
        stripped = line.strip()

        m = TODO_HEADER_RE.search(stripped)
        if m:
            header = {
                "total": int(m.group(1)),
                "done": int(m.group(2)),
                "in_progress": int(m.group(3)) if m.group(3) else 0,
                "open": int(m.group(4)),
            }
            continue

        if re.match(r"^◻\s+(.+)$", stripped):
            items.append({"text": re.match(r"^◻\s+(.+)$", stripped).group(1), "status": "pending"})
            continue

        if re.match(r"^◼\s+(.+)$", stripped):
            items.append({"text": re.match(r"^◼\s+(.+)$", stripped).group(1), "status": "in_progress"})
            continue

        if re.match(r"^✔\s+(.+)$", stripped):
            items.append({"text": re.match(r"^✔\s+(.+)$", stripped).group(1), "status": "completed"})
            continue

    if header or items:
        return {
            **(header or {}),
            "items": items,
        }
    return None


def detect_background_task(lines: list[str]) -> dict | None:
    """Detect a background task indicator from screen lines.

    Looks for lines containing "in the background".

    Args:
        lines: Terminal screen lines to scan.

    Returns:
        Dict with 'raw' (the matched line text), or None if no
        background task indicator is found.
    """
    for line in lines:
        if BACKGROUND_RE.search(line):
            return {"raw": line.strip()}
    return None


def detect_parallel_agents(lines: list[str]) -> dict | None:
    """Detect a parallel agents display from screen lines.

    Parses the agent count, tree-style agent list, and completion
    messages from the Claude Code multi-agent UI.

    Args:
        lines: Terminal screen lines to scan.

    Returns:
        Dict with 'count' (number launched or None), 'agents' list of
        names, and 'completed' list of finished agent names, or None if
        no agent patterns are found.
    """
    count: int | None = None
    agents: list[str] = []
    completed: list[str] = []

    for line in lines:
        stripped = line.strip()

        m = AGENTS_LAUNCHED_RE.search(stripped)
        if m:
            count = int(m.group(1))
            continue

        m = AGENT_COMPLETE_RE.search(stripped)
        if m:
            completed.append(m.group(1))
            continue

        # Agent tree items: ├─ name (description)
        m = AGENT_TREE_ITEM_RE.match(stripped)
        if m and m.group(1).strip():
            agents.append(m.group(1).strip())

    if count is not None or agents or completed:
        return {
            "count": count,
            "agents": agents,
            "completed": completed,
        }
    return None
