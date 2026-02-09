from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

# Cursor forward: ESC[NC — replace with N spaces (Claude uses ESC[1C between words)
_CURSOR_FORWARD_RE = re.compile(r"\x1b\[(\d+)C")

# All other ANSI sequences: CSI, OSC, SGR — remove entirely
_ANSI_FULL_RE = re.compile(
    r"\x1b"
    r"(?:"
    r"\[[0-9;]*[a-zA-Z]"       # CSI sequences: ESC [ ... letter
    r"|\][^\x07]*\x07"         # OSC sequences: ESC ] ... BEL
    r"|\[[0-9;]*m"             # SGR (color) sequences
    r"|\[\?[0-9;]*[a-zA-Z]"   # Private mode sequences: ESC[?...
    r"|>[0-9]*[a-zA-Z]"        # DEC sequences: ESC>...
    r"|<[a-zA-Z]"              # ESC< sequences
    r")"
)

# Terminal control sequences to strip before any other processing
_TERMINAL_MODES_RE = re.compile(
    r"\x1b\[\?(?:2026|2004|1004|25|1)[hlHL]"  # Synchronized output, bracketed paste, etc.
)
_SCREEN_CLEAR_RE = re.compile(r"\x1b\[2J|\x1b\[3J|\x1b\[H")
_ERASE_LINE_RE = re.compile(r"\x1b\[2?K")
_CURSOR_UP_RE = re.compile(r"\x1b\[\d*A")


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes, converting cursor-forward to spaces."""
    # First convert cursor-forward to spaces (ESC[1C -> " ")
    text = _CURSOR_FORWARD_RE.sub(lambda m: " " * int(m.group(1)), text)
    # Then remove everything else
    return _ANSI_FULL_RE.sub("", text)


def clean_terminal_output(text: str) -> str:
    """Full terminal output cleanup: strip all ANSI, normalize whitespace, remove UI chrome."""
    # Remove terminal mode switches
    text = _TERMINAL_MODES_RE.sub("", text)
    # Remove screen clears
    text = _SCREEN_CLEAR_RE.sub("", text)
    # Remove erase-line sequences
    text = _ERASE_LINE_RE.sub("", text)
    # Remove cursor-up (used for status bar repositioning)
    text = _CURSOR_UP_RE.sub("", text)
    # Strip ANSI (converts cursor-forward to spaces)
    text = strip_ansi(text)
    # Normalize \r\r\n and \r\n to \n
    text = text.replace("\r\r\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_BRAILLE_SPINNER = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*")
_DOTS_SPINNER = re.compile(r"^(.+?)\.{1,3}$", re.MULTILINE)


def filter_spinners(text: str) -> str:
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


class PromptType(Enum):
    YES_NO = "yes_no"
    MULTIPLE_CHOICE = "multiple_choice"


@dataclass
class DetectedPrompt:
    prompt_type: PromptType
    options: list[str]
    default: str | None = None
    raw_text: str = ""


_YES_NO_RE = re.compile(r"\[([Yy])/([Nn])\]|\[([Nn])/([Yy])\]")
_MULTI_CHOICE_RE = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)


def detect_prompt(text: str) -> DetectedPrompt | None:
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

    choices = _MULTI_CHOICE_RE.findall(text)
    if len(choices) >= 2:
        options = [label.strip() for _, label in choices]
        return DetectedPrompt(
            prompt_type=PromptType.MULTIPLE_CHOICE,
            options=options,
            raw_text=text,
        )

    return None


@dataclass
class ContextUsage:
    percentage: int | None = None
    needs_compact: bool = False
    raw_text: str = ""


# Real Claude status bar format: "Usage: 32% ███▎░░░░░░"
_USAGE_PCT_RE = re.compile(r"Usage:\s*(\d+)%", re.IGNORECASE)
# Also handle generic context patterns
_CONTEXT_PCT_RE = re.compile(r"(?:context|ctx)[:\s]*(\d+)\s*%", re.IGNORECASE)
_CONTEXT_TOKENS_RE = re.compile(r"(\d+)k\s*/\s*(\d+)k\s*tokens", re.IGNORECASE)
_COMPACT_RE = re.compile(r"compact|context.*(?:full|almost|running out)", re.IGNORECASE)


def detect_context_usage(text: str) -> ContextUsage | None:
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


@dataclass
class StatusBar:
    project: str | None = None
    branch: str | None = None
    usage_pct: int | None = None
    raw_text: str = ""


_STATUS_BAR_RE = re.compile(
    r"(?P<project>[\w\-]+)\s*│\s*"
    r"(?:⎇\s*(?P<branch>[\w\-/]+))?\s*"
    r"(?:⇡\d+\s*)?│?\s*"
    r"(?:Usage:\s*(?P<usage>\d+)%)?"
)


def parse_status_bar(text: str) -> StatusBar | None:
    """Parse Claude Code's status bar line.

    Real format: "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
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
    return StatusBar(
        project=project,
        branch=branch,
        usage_pct=int(usage) if usage else None,
        raw_text=text,
    )


_FILE_PATH_RE = re.compile(
    r"(?:wrote to|saved|created|generated|output)\s+"
    r"(\/[\w./\-]+\.\w+)",
    re.IGNORECASE,
)


def detect_file_paths(text: str) -> list[str]:
    if not text.strip():
        return []
    matches = _FILE_PATH_RE.findall(text)
    return [m for m in matches if len(m) > 5]


_TG_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!\\"
_TG_ESCAPE_RE = re.compile(r"([" + re.escape(_TG_ESCAPE_CHARS) + r"])")

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _escape_telegram(text: str) -> str:
    return _TG_ESCAPE_RE.sub(r"\\\1", text)


def format_telegram(text: str) -> str:
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
