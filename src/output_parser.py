from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import pyte


class TerminalEmulator:
    """Virtual terminal using pyte to reconstruct screen from raw PTY bytes.

    This is the core of output parsing: instead of regex-stripping ANSI codes,
    we feed raw PTY bytes into a real terminal emulator and read the screen buffer.
    """

    def __init__(self, rows: int = 40, cols: int = 120):
        """Initialize the terminal emulator with a virtual screen.

        Args:
            rows: Number of rows in the virtual terminal. Defaults to 40.
            cols: Number of columns in the virtual terminal. Defaults to 120.
        """
        self.rows = rows
        self.cols = cols
        self.screen = pyte.Screen(cols, rows)
        self.stream = pyte.Stream(self.screen)
        self._prev_display: list[str] = [""] * rows

    def feed(self, data: bytes | str) -> None:
        """Feed raw PTY bytes into the terminal emulator.

        Args:
            data: Raw bytes or a string from the PTY. Bytes are decoded
                as UTF-8 with replacement characters for invalid sequences.
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        self.stream.feed(data)

    def get_display(self) -> list[str]:
        """Return all screen lines, right-stripped of trailing whitespace.

        Returns:
            List of strings, one per terminal row.
        """
        return [line.rstrip() for line in self.screen.display]

    def get_text(self) -> str:
        """Return full screen content as text with blank lines collapsed.

        Runs of three or more newlines are reduced to double newlines, and
        leading/trailing whitespace is stripped.

        Returns:
            The reconstructed screen content as a single string.
        """
        lines = self.get_display()
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_changes(self) -> list[str]:
        """Return lines that changed since the last call to get_changes.

        Compares the current display against a saved snapshot and returns
        only lines whose content differs and is non-blank.

        Returns:
            List of changed, non-empty screen lines.
        """
        current = self.get_display()
        changed = []
        for i, (cur, prev) in enumerate(zip(current, self._prev_display)):
            if cur != prev and cur.strip():
                changed.append(cur)
        self._prev_display = list(current)
        return changed

    def get_new_content(self) -> str:
        """Return changed lines joined as a single string.

        Returns:
            Newline-joined string of lines that changed since last check,
            stripped of leading/trailing whitespace.
        """
        lines = self.get_changes()
        return "\n".join(lines).strip()

    def reset(self) -> None:
        """Reset the terminal to its initial blank state.

        Clears the pyte screen buffer and the internal previous-display
        snapshot used by get_changes.
        """
        self.screen.reset()
        self._prev_display = [""] * self.rows


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

_SEPARATOR_RE = re.compile(r"^[─━═]{4,}\uFFFD*$")
_DIFF_DELIMITER_RE = re.compile(r"^[╌]{4,}\uFFFD*$")
_STATUS_BAR_RE = re.compile(
    r"(?P<project>[\w\-]+)\s*│\s*"
    r"(?:⎇\s*(?P<branch>[\w\-/]+)(?P<dirty>\*)?)?\s*"
    r"(?:⇡(?P<ahead>\d+)\s*)?│?\s*"
    r"(?:Usage:\s*(?P<usage>\d+)%)?"
)
_TIMER_RE = re.compile(r"↻\s*([\d:]+)")
_PROMPT_MARKER_RE = re.compile(r"^❯(?:\s|$)")
_BOX_CHAR_RE = re.compile(r"[╭╮╰╯│├┤┬┴┼]")
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
        One of: 'separator', 'diff_delimiter', 'status_bar', 'thinking',
        'tool_header', 'response', 'tool_connector', 'todo_item',
        'agent_tree', 'prompt', 'box', 'logo', 'empty', or 'content'.
    """
    stripped = line.strip()
    if not stripped:
        return "empty"
    if _SEPARATOR_RE.match(stripped):
        return "separator"
    if _DIFF_DELIMITER_RE.match(stripped):
        return "diff_delimiter"
    if _STATUS_BAR_RE.search(stripped):
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
    if re.match(r"^[├└]\s*─", stripped):
        return "agent_tree"
    if _PROMPT_MARKER_RE.match(stripped):
        return "prompt"
    if _BOX_CHAR_RE.search(stripped) and len(stripped) > 10:
        box_chars = sum(1 for c in stripped if _BOX_CHAR_RE.match(c))
        if box_chars >= 2:
            return "box"
    if _LOGO_RE.search(stripped):
        logo_chars = sum(1 for c in stripped if _LOGO_RE.match(c))
        if logo_chars >= 3:
            return "logo"
    return "content"


def extract_content(lines: list[str]) -> str:
    """Extract meaningful content from screen lines, filtering UI chrome.

    Keeps only lines classified as 'content' by classify_line, stripping
    surrounding whitespace.

    Args:
        lines: List of terminal screen lines to filter.

    Returns:
        Newline-joined string of content lines, stripped.
    """
    content_lines = []
    for line in lines:
        if classify_line(line) == "content":
            content_lines.append(line.strip())
    return "\n".join(content_lines).strip()


# --- Spinner filtering ---

_BRAILLE_SPINNER = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*")
_DOTS_SPINNER = re.compile(r"^(.+?)\.{1,3}$", re.MULTILINE)


def filter_spinners(text: str) -> str:
    """Remove braille spinner characters and deduplicate trailing-dot variants.

    Strips braille spinner prefixes from lines, then collapses progressive
    dot sequences (e.g. "Loading.", "Loading..", "Loading...") into the
    longest variant only.

    Args:
        text: Raw text that may contain spinner artifacts.

    Returns:
        Cleaned text with spinners removed. Empty string if nothing remains.
    """
    if not text:
        return ""
    lines = text.split("\n")
    seen_spinners: dict[str, str] = {}
    result_lines = []

    for line in lines:
        stripped = _BRAILLE_SPINNER.sub("", line).strip()
        if stripped != line.strip() and stripped:
            seen_spinners[stripped] = stripped
            continue
        result_lines.append(line)

    for spinner_text in seen_spinners.values():
        result_lines.append(spinner_text)

    final_text = "\n".join(result_lines)
    dot_groups: dict[str, int] = {}
    for match in _DOTS_SPINNER.finditer(final_text):
        base = match.group(1).rstrip(".")
        dot_groups[base] = max(dot_groups.get(base, 0), len(match.group(0)) - len(base))

    for base, dot_count in dot_groups.items():
        if dot_count > 1:
            for i in range(1, dot_count):
                final_text = final_text.replace(f"{base}{'.' * i}\n", "")
            final_text = final_text.strip()

    return final_text.strip() if final_text.strip() else ""


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

    # Selection menu: ❯ 1. Option / 2. Option
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
    match = _STATUS_BAR_RE.search(text)
    if not match:
        return None
    project = match.group("project")
    branch = match.group("branch")
    usage = match.group("usage")
    if not project:
        return None
    dirty = bool(match.group("dirty"))
    ahead = match.group("ahead")
    timer_match = _TIMER_RE.search(text)
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
    m = _EXTRA_BASH_RE.search(text)
    if m:
        result["bash_tasks"] = int(m.group(1))
    m = _EXTRA_AGENTS_RE.search(text)
    if m:
        result["local_agents"] = int(m.group(1))
    m = _EXTRA_FILES_RE.search(text)
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
        m = _THINKING_STAR_RE.match(line.strip())
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
        m = _SELECTION_SELECTED_RE.match(stripped)
        if m:
            has_selection = True
            idx = int(m.group(1))
            options.append((idx, m.group(2).strip()))
            selected_idx = idx
            continue

        # Unselected option: N. text (indented)
        m = _SELECTION_UNSELECTED_RE.match(line)
        if m and has_selection:
            options.append((int(m.group(1)), m.group(2).strip()))
            continue

        # Hint line
        if _SELECTION_HINT_RE.search(stripped):
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

        m = _TODO_HEADER_RE.search(stripped)
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
        if _BACKGROUND_RE.search(line):
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

        m = _AGENTS_LAUNCHED_RE.search(stripped)
        if m:
            count = int(m.group(1))
            continue

        m = _AGENT_COMPLETE_RE.search(stripped)
        if m:
            completed.append(m.group(1))
            continue

        # Agent tree items: ├─ name (description)
        m = _AGENT_TREE_ITEM_RE.match(stripped)
        if m and m.group(1).strip():
            agents.append(m.group(1).strip())

    if count is not None or agents or completed:
        return {
            "count": count,
            "agents": agents,
            "completed": completed,
        }
    return None


# --- Screen state classifier ---


def _extract_tool_info(lines: list[str]) -> dict:
    """Extract tool name and target from screen lines.

    Scans for Bash(...) or Write/Update/Read(...) patterns and returns
    the tool name with its argument.

    Args:
        lines: Terminal screen lines to scan for tool headers.

    Returns:
        Dict with 'tool' and either 'command' (for Bash) or 'target'
        (for file tools). Empty dict if no tool header is found.
    """
    for line in lines:
        m = _TOOL_BASH_RE.search(line)
        if m:
            return {"tool": "Bash", "command": m.group(1)}
        m = _TOOL_FILE_RE.search(line)
        if m:
            tool_name = "Write" if "Write" in line else "Update" if "Update" in line else "Read"
            return {"tool": tool_name, "target": m.group(1)}
    return {}


def classify_screen_state(
    lines: list[str],
    prev_state: ScreenState | None = None,
) -> ScreenEvent:
    """Classify the current screen state from terminal display lines.

    Examines all screen lines and returns the most prominent current state
    with extracted payload data. Uses priority-ordered detection to resolve
    ambiguity when multiple patterns are present:
      1. Tool approval menus (need user action, highest priority)
      2. TODO lists and parallel agents (screen-wide patterns)
      3. Thinking indicators, running tools, tool results (bottom-up scan)
      4. Idle prompt, streaming, user message (last meaningful line)
      5. Startup and error (fallback patterns)

    Args:
        lines: Full terminal display lines from the pyte screen.
        prev_state: The previously classified state, reserved for future
            hysteresis logic. Currently unused.

    Returns:
        A ScreenEvent with the classified state, extracted payload dict,
        and the original raw lines.
    """
    non_empty = [l for l in lines if l.strip()]

    if not non_empty:
        return ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=lines)

    # --- First pass: screen-wide patterns (need full context) ---

    # 1. Tool approval / selection menu (needs user action - highest priority)
    payload = detect_tool_request(lines)
    if payload:
        return ScreenEvent(state=ScreenState.TOOL_REQUEST, payload=payload, raw_lines=lines)

    # 2. TODO list
    payload = detect_todo_list(lines)
    if payload:
        return ScreenEvent(state=ScreenState.TODO_LIST, payload=payload, raw_lines=lines)

    # 3. Parallel agents
    payload = detect_parallel_agents(lines)
    if payload:
        return ScreenEvent(state=ScreenState.PARALLEL_AGENTS, payload=payload, raw_lines=lines)

    # --- Second pass: bottom-up scan for current activity ---

    # Find last meaningful line (skip status bar, separators, empty lines)
    active_idx = len(lines) - 1
    while active_idx >= 0:
        stripped = lines[active_idx].strip()
        if (
            stripped
            and not _STATUS_BAR_RE.search(stripped)
            and not _SEPARATOR_RE.match(stripped)
            and not _EXTRA_BASH_RE.search(stripped)
            and not _EXTRA_AGENTS_RE.search(stripped)
            and not _EXTRA_FILES_RE.search(stripped)
        ):
            break
        active_idx -= 1

    if active_idx < 0:
        return ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=lines)

    # Check the bottom content area (last ~8 meaningful lines)
    bottom_start = max(0, active_idx - 7)
    bottom_lines = lines[bottom_start : active_idx + 1]

    # 4. Thinking indicator
    payload = detect_thinking(bottom_lines)
    if payload:
        return ScreenEvent(state=ScreenState.THINKING, payload=payload, raw_lines=lines)

    # 5. Tool running/waiting
    for line in reversed(bottom_lines):
        if _TOOL_STATUS_RE.search(line) or _TOOL_HOOKS_RE.search(line):
            tool_info = _extract_tool_info(lines)
            return ScreenEvent(
                state=ScreenState.TOOL_RUNNING, payload=tool_info, raw_lines=lines
            )

    # 6. Tool result (diff summary)
    for line in reversed(bottom_lines):
        m = _TOOL_DIFF_RE.search(line)
        if m:
            return ScreenEvent(
                state=ScreenState.TOOL_RESULT,
                payload={"added": int(m.group(1)), "removed": int(m.group(2))},
                raw_lines=lines,
            )

    # 7. Background task
    payload = detect_background_task(bottom_lines)
    if payload:
        return ScreenEvent(
            state=ScreenState.BACKGROUND_TASK, payload=payload, raw_lines=lines
        )

    # --- Third pass: check last meaningful line ---

    last_line = lines[active_idx].strip()

    # 8. IDLE: ❯ between separators (allow up to 3 lines gap for artifacts)
    if _PROMPT_MARKER_RE.match(last_line):
        found_sep_above = False
        for i in range(active_idx - 1, max(-1, active_idx - 4), -1):
            if i < 0:
                break
            s = lines[i].strip()
            if s and _SEPARATOR_RE.match(s):
                found_sep_above = True
                break
        found_sep_below = False
        for i in range(active_idx + 1, min(len(lines), active_idx + 4)):
            s = lines[i].strip()
            if s and _SEPARATOR_RE.match(s):
                found_sep_below = True
                break
        if found_sep_above and found_sep_below:
            placeholder = re.sub(r"^❯\s*", "", last_line)
            return ScreenEvent(
                state=ScreenState.IDLE,
                payload={"placeholder": placeholder},
                raw_lines=lines,
            )

    # 9. Streaming: last line starts with ⏺
    m = _RESPONSE_MARKER_RE.match(last_line)
    if m:
        return ScreenEvent(
            state=ScreenState.STREAMING,
            payload={"text": m.group(1)},
            raw_lines=lines,
        )

    # 10. User message: ❯ followed by text (not between separators)
    if _PROMPT_MARKER_RE.match(last_line):
        user_text = re.sub(r"^❯\s*", "", last_line)
        return ScreenEvent(
            state=ScreenState.USER_MESSAGE,
            payload={"text": user_text},
            raw_lines=lines,
        )

    # 11. Startup
    for line in non_empty[:10]:
        if _STARTUP_RE.search(line):
            return ScreenEvent(state=ScreenState.STARTUP, raw_lines=lines)
        stripped = line.strip()
        if _LOGO_RE.search(stripped) and sum(1 for c in stripped if _LOGO_RE.match(c)) >= 3:
            return ScreenEvent(state=ScreenState.STARTUP, raw_lines=lines)

    # 12. Error
    for line in non_empty:
        if _ERROR_RE.search(line):
            return ScreenEvent(
                state=ScreenState.ERROR,
                payload={"text": line.strip()},
                raw_lines=lines,
            )

    return ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=lines)


# --- Telegram formatting ---

_TG_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!\\"
_TG_ESCAPE_RE = re.compile(r"([" + re.escape(_TG_ESCAPE_CHARS) + r"])")

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _escape_telegram(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format.

    Args:
        text: Plain text to escape.

    Returns:
        Text with all Telegram MarkdownV2 special characters backslash-escaped.
    """
    return _TG_ESCAPE_RE.sub(r"\\\1", text)


def format_telegram(text: str) -> str:
    """Convert markdown text to Telegram MarkdownV2 format.

    Preserves code blocks and inline code verbatim while escaping special
    characters in surrounding text. Converts **bold** and *italic*
    markers to Telegram equivalents.

    Args:
        text: Markdown-formatted text to convert.

    Returns:
        Telegram MarkdownV2-formatted string ready for the Bot API.
        Empty string if input is empty.
    """
    if not text:
        return ""

    code_blocks: list[tuple[str, str]] = []
    inline_codes: list[str] = []

    def _save_block(match: re.Match) -> str:
        idx = len(code_blocks)
        code_blocks.append((match.group(1), match.group(2)))
        return f"\x00CODEBLOCK{idx}\x00"

    def _save_inline(match: re.Match) -> str:
        idx = len(inline_codes)
        inline_codes.append(match.group(1))
        return f"\x00INLINE{idx}\x00"

    result = _CODE_BLOCK_RE.sub(_save_block, text)
    result = _INLINE_CODE_RE.sub(_save_inline, result)

    result = _BOLD_RE.sub(lambda m: f"\x00BOLDOPEN{m.group(1)}\x00BOLDCLOSE", result)
    result = _ITALIC_RE.sub(lambda m: f"\x00ITALICOPEN{m.group(1)}\x00ITALICCLOSE", result)

    result = _escape_telegram(result)

    result = result.replace("\x00BOLDOPEN", "*").replace("\x00BOLDCLOSE", "*")
    result = result.replace("\x00ITALICOPEN", "_").replace("\x00ITALICCLOSE", "_")

    for idx, (lang, code) in enumerate(code_blocks):
        placeholder = _escape_telegram(f"\x00CODEBLOCK{idx}\x00")
        result = result.replace(placeholder, f"```{lang}\n{code}```")

    for idx, code in enumerate(inline_codes):
        placeholder = _escape_telegram(f"\x00INLINE{idx}\x00")
        result = result.replace(placeholder, f"`{code}`")

    return result


TELEGRAM_MAX_LENGTH = 4096


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split a long message into chunks that fit within Telegram's limit.

    Splits preferring double-newline paragraph breaks, then single
    newlines, then spaces, falling back to hard cuts at max_length.

    Args:
        text: The message text to split.
        max_length: Maximum character length per chunk. Defaults to
            TELEGRAM_MAX_LENGTH (4096).

    Returns:
        List of message chunks. Returns [text] if it already fits,
        or [""] if input is empty.
    """
    if not text or len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n\n", 0, max_length)

        if split_at == -1:
            split_at = remaining.rfind("\n", 0, max_length)

        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_length)

        if split_at == -1:
            split_at = max_length

        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    return chunks if chunks else [""]


# --- Legacy helpers (kept for backward compat, delegate to pyte internally) ---

# Cursor forward: ESC[NC — replace with N spaces
_CURSOR_FORWARD_RE = re.compile(r"\x1b\[(\d+)C")

# All other ANSI sequences
_ANSI_FULL_RE = re.compile(
    r"\x1b"
    r"(?:"
    r"\[[0-9;]*[a-zA-Z]"
    r"|\][^\x07]*\x07"
    r"|\[[0-9;]*m"
    r"|\[\?[0-9;]*[a-zA-Z]"
    r"|>[0-9]*[a-zA-Z]"
    r"|<[a-zA-Z]"
    r")"
)


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes, converting cursor-forward to spaces.

    Handles ESC[NC (cursor forward) by replacing with the equivalent
    number of spaces, then removes all remaining ANSI sequences.

    Args:
        text: Raw terminal text containing ANSI escape codes.

    Returns:
        Text with all ANSI sequences removed and cursor-forward
        sequences replaced by spaces.
    """
    text = _CURSOR_FORWARD_RE.sub(lambda m: " " * int(m.group(1)), text)
    return _ANSI_FULL_RE.sub("", text)


def clean_terminal_output(text: str) -> str:
    """Clean raw terminal output using the pyte terminal emulator.

    Feeds the raw text through a virtual terminal and returns the
    reconstructed screen content with blank lines collapsed.

    Args:
        text: Raw terminal output potentially containing ANSI codes,
            cursor movements, and other control sequences.

    Returns:
        Cleaned screen content as a single string with collapsed blank
        lines and stripped whitespace.
    """
    emu = TerminalEmulator()
    emu.feed(text)
    return emu.get_text()
