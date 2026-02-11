from __future__ import annotations

import logging
import re

from src.parsing.detectors import (
    detect_background_task,
    detect_parallel_agents,
    detect_thinking,
    detect_todo_list,
    detect_tool_request,
)
from src.core.log_setup import TRACE
from src.parsing.ui_patterns import (
    ScreenEvent,
    ScreenState,
    _BARE_TIME_RE,
    _CLAUDE_HINT_RE,
    _ERROR_RE,
    _EXTRA_AGENTS_RE,
    _EXTRA_BASH_RE,
    _EXTRA_FILES_RE,
    _LOGO_RE,
    _PR_INDICATOR_RE,
    _PROMPT_MARKER_RE,
    _RESPONSE_MARKER_RE,
    _SEPARATOR_PREFIX_RE,
    _SEPARATOR_RE,
    _STARTUP_RE,
    _STATUS_BAR_RE,
    _TIMER_RE,
    _TIP_RE,
    _TOOL_BASH_RE,
    _TOOL_DIFF_RE,
    _TOOL_FILE_RE,
    _TOOL_HOOKS_RE,
    _TOOL_STATUS_RE,
)

logger = logging.getLogger(__name__)


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
    logger.log(TRACE, "classify_screen_state lines=%d non_empty=%d", len(lines), len(non_empty))

    def _return(event: ScreenEvent) -> ScreenEvent:
        logger.log(TRACE, "classify_screen_state -> %s payload_keys=%s", event.state.name, list(event.payload.keys()))
        return event

    if not non_empty:
        return _return(ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=lines))

    # --- First pass: screen-wide patterns (need full context) ---

    # 1. Tool approval / selection menu (needs user action - highest priority)
    payload = detect_tool_request(lines)
    if payload:
        return _return(ScreenEvent(state=ScreenState.TOOL_REQUEST, payload=payload, raw_lines=lines))

    # 2. TODO list
    payload = detect_todo_list(lines)
    if payload:
        return _return(ScreenEvent(state=ScreenState.TODO_LIST, payload=payload, raw_lines=lines))

    # 3. Parallel agents
    payload = detect_parallel_agents(lines)
    if payload:
        return _return(ScreenEvent(state=ScreenState.PARALLEL_AGENTS, payload=payload, raw_lines=lines))

    # --- Second pass: bottom-up scan for current activity ---

    # Find last meaningful line (skip status bar, separators, empty lines).
    # Must skip ALL patterns that classify_line() considers non-content UI:
    # tips, bare times, claude hints, timer lines, and separators with
    # trailing text overlay (_SEPARATOR_PREFIX_RE).  Missing any of these
    # makes the scan stop on a UI chrome line, which breaks IDLE detection
    # (the prompt ❯ never becomes last_line).
    active_idx = len(lines) - 1
    while active_idx >= 0:
        stripped = lines[active_idx].strip()
        if (
            stripped
            and not _STATUS_BAR_RE.search(stripped)
            and not _SEPARATOR_RE.match(stripped)
            and not _SEPARATOR_PREFIX_RE.match(stripped)
            and not _TIP_RE.match(stripped)
            and not _BARE_TIME_RE.match(stripped)
            and not _CLAUDE_HINT_RE.search(stripped)
            and not _TIMER_RE.search(stripped)
            and not _EXTRA_BASH_RE.search(stripped)
            and not _EXTRA_AGENTS_RE.search(stripped)
            and not _EXTRA_FILES_RE.search(stripped)
            and not _PR_INDICATOR_RE.match(stripped)
        ):
            break
        active_idx -= 1

    if active_idx < 0:
        return _return(ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=lines))

    # Check the bottom content area (last ~8 meaningful lines)
    bottom_start = max(0, active_idx - 7)
    bottom_lines = lines[bottom_start : active_idx + 1]

    # 4. Thinking indicator
    payload = detect_thinking(bottom_lines)
    if payload:
        return _return(ScreenEvent(state=ScreenState.THINKING, payload=payload, raw_lines=lines))

    # 5. Tool running/waiting
    for line in reversed(bottom_lines):
        if _TOOL_STATUS_RE.search(line) or _TOOL_HOOKS_RE.search(line):
            tool_info = _extract_tool_info(lines)
            return _return(ScreenEvent(
                state=ScreenState.TOOL_RUNNING, payload=tool_info, raw_lines=lines
            ))

    # 6. Tool result (diff summary)
    for line in reversed(bottom_lines):
        m = _TOOL_DIFF_RE.search(line)
        if m:
            return _return(ScreenEvent(
                state=ScreenState.TOOL_RESULT,
                payload={"added": int(m.group(1)), "removed": int(m.group(2))},
                raw_lines=lines,
            ))

    # 7. Background task
    payload = detect_background_task(bottom_lines)
    if payload:
        return _return(ScreenEvent(
            state=ScreenState.BACKGROUND_TASK, payload=payload, raw_lines=lines
        ))

    # --- Third pass: check last meaningful line ---

    last_line = lines[active_idx].strip()

    # 8. IDLE: ❯ between separators — 3-line gap tolerance because pyte
    #    may insert blank/artifact lines between the separator and prompt.
    #    Check both _SEPARATOR_RE (pure separator) and _SEPARATOR_PREFIX_RE
    #    (separator with trailing text overlay from pyte column bleed).
    if _PROMPT_MARKER_RE.match(last_line):
        found_sep_above = False
        for i in range(active_idx - 1, max(-1, active_idx - 4), -1):
            if i < 0:
                break
            s = lines[i].strip()
            if s and (_SEPARATOR_RE.match(s) or _SEPARATOR_PREFIX_RE.match(s)):
                found_sep_above = True
                break
        found_sep_below = False
        for i in range(active_idx + 1, min(len(lines), active_idx + 4)):
            s = lines[i].strip()
            if s and (_SEPARATOR_RE.match(s) or _SEPARATOR_PREFIX_RE.match(s)):
                found_sep_below = True
                break
        if found_sep_above and found_sep_below:
            placeholder = re.sub(r"^❯\s*", "", last_line)
            return _return(ScreenEvent(
                state=ScreenState.IDLE,
                payload={"placeholder": placeholder},
                raw_lines=lines,
            ))

    # 9. Streaming: ⏺ response marker visible below the last ❯ prompt.
    # Only count ⏺ markers that appear AFTER the most recent ❯ prompt line
    # to avoid matching markers from previous responses that persist on the
    # pyte screen (pyte never clears old content). Without this, the user's
    # message echo phase is misclassified as STREAMING because the old ⏺
    # from the previous response is still visible above the new ❯ line.
    last_prompt_idx = -1
    for i, line in enumerate(lines):
        if _PROMPT_MARKER_RE.match(line.strip()):
            last_prompt_idx = i

    for line in lines[last_prompt_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        m = _RESPONSE_MARKER_RE.match(stripped)
        if m:
            return _return(ScreenEvent(
                state=ScreenState.STREAMING,
                payload={"text": m.group(1)},
                raw_lines=lines,
            ))

    # 10. User message: ❯ followed by text (not between separators)
    if _PROMPT_MARKER_RE.match(last_line):
        user_text = re.sub(r"^❯\s*", "", last_line)
        return _return(ScreenEvent(
            state=ScreenState.USER_MESSAGE,
            payload={"text": user_text},
            raw_lines=lines,
        ))

    # 11. Startup — only if no ⏺ response marker visible.
    # pyte never clears the banner (logo + version) because Claude Code
    # redraws in-place rather than scrolling. Without this guard, every
    # screen after startup would match STARTUP as a fallback.
    has_response = any(_RESPONSE_MARKER_RE.match(l.strip()) for l in non_empty)
    if not has_response:
        for line in non_empty[:10]:
            if _STARTUP_RE.search(line):
                return _return(ScreenEvent(state=ScreenState.STARTUP, raw_lines=lines))
            stripped = line.strip()
            if _LOGO_RE.search(stripped) and sum(1 for c in stripped if _LOGO_RE.match(c)) >= 3:
                return _return(ScreenEvent(state=ScreenState.STARTUP, raw_lines=lines))

    # 12. Error
    for line in non_empty:
        if _ERROR_RE.search(line):
            return _return(ScreenEvent(
                state=ScreenState.ERROR,
                payload={"text": line.strip()},
                raw_lines=lines,
            ))

    return _return(ScreenEvent(state=ScreenState.UNKNOWN, raw_lines=lines))
