from __future__ import annotations

import html


# --- Auth ---


def is_authorized(user_id: int, authorized_users: list[int]) -> bool:
    """Check whether a Telegram user is allowed to interact with the bot."""
    return user_id in authorized_users


# --- Keyboard builders ---


def build_project_keyboard(
    projects: list, page: int = 0, page_size: int = 8
) -> list[list[dict]]:
    """Build a paginated inline keyboard layout for project selection.

    Each project is rendered as a single-button row. Navigation buttons
    ("< Prev" / "Next >") are appended when additional pages exist.

    Args:
        projects: Full list of discovered projects to paginate over.
        page: Zero-based page index to display.
        page_size: Maximum number of project buttons per page.

    Returns:
        A list of rows, where each row is a list of button dicts with
        "text" and "callback_data" keys. Returns an empty list when
        projects is empty.
    """
    if not projects:
        return []

    start = page * page_size
    end = start + page_size
    page_projects = projects[start:end]

    rows = []
    for proj in page_projects:
        rows.append([{"text": proj.name, "callback_data": f"project:{proj.path}"}])

    nav = []
    if page > 0:
        nav.append({"text": "< Prev", "callback_data": f"page:{page - 1}"})
    if end < len(projects):
        nav.append({"text": "Next >", "callback_data": f"page:{page + 1}"})
    if nav:
        rows.append(nav)

    return rows


def build_sessions_keyboard(
    sessions: list, active_id: int | None
) -> list[list[dict]]:
    """Build an inline keyboard layout listing active sessions.

    Each session is rendered as a two-button row: one to switch to the
    session and one to kill it. The currently active session is marked
    with an asterisk (*) suffix.

    Args:
        sessions: List of session objects, each having ``session_id`` and
            ``project_name`` attributes.
        active_id: The session ID of the currently active session, or
            None if no session is active.

    Returns:
        A list of rows, where each row is a list of button dicts with
        "text" and "callback_data" keys. Returns an empty list when
        sessions is empty.
    """
    if not sessions:
        return []

    rows = []
    for s in sessions:
        marker = " *" if s.session_id == active_id else ""
        rows.append(
            [
                {
                    "text": f"#{s.session_id} {s.project_name}{marker}",
                    "callback_data": f"switch:{s.session_id}",
                },
                {"text": "Kill", "callback_data": f"kill:{s.session_id}"},
            ]
        )
    return rows


def build_tool_approval_keyboard(
    session_id: int,
) -> list[list[dict]]:
    """Build an inline keyboard for tool approval (Accept / Reject).

    Args:
        session_id: Session whose PTY receives the approval response.

    Returns:
        A list of rows with two buttons: Allow and Deny.
    """
    return [
        [
            {"text": "Allow", "callback_data": f"tool:yes:{session_id}"},
            {"text": "Deny", "callback_data": f"tool:no:{session_id}"},
        ]
    ]


# --- Message formatting ---


def format_session_started(project_name: str, session_id: int) -> str:
    """Format an HTML message announcing that a new session has started.

    Args:
        project_name: Display name of the project the session belongs to.
        session_id: Numeric identifier of the newly created session.

    Returns:
        An HTML-formatted string suitable for sending via Telegram.
    """
    safe_name = html.escape(project_name)
    return f"Session started on <b>{safe_name}</b>. Session #{session_id}"


def format_session_ended(project_name: str, session_id: int) -> str:
    """Format an HTML message announcing that a session has ended.

    Args:
        project_name: Display name of the project the session belonged to.
        session_id: Numeric identifier of the ended session.

    Returns:
        An HTML-formatted string suitable for sending via Telegram.
    """
    safe_name = html.escape(project_name)
    return f"Session #{session_id} on <b>{safe_name}</b> ended."


def _format_timestamp(raw: str) -> str:
    """Convert a raw ISO timestamp to a short human-readable format.

    Strips microseconds and timezone offset, returning ``YYYY-MM-DD HH:MM``.

    Args:
        raw: An ISO-8601 timestamp string (e.g. from the database).

    Returns:
        A short date-time string like ``2026-02-11 22:02``.
    """
    # Strip microseconds (.123456) and timezone (+00:00 / Z)
    clean = raw.split(".")[0].replace("T", " ")
    # Remove trailing timezone offset if present (e.g. +00:00)
    if "+" in clean:
        clean = clean.split("+")[0]
    elif clean.endswith("Z"):
        clean = clean[:-1]
    # Truncate to minutes (drop :SS) only when seconds are present
    # A time like "10:02:35" has 2 colons; "10:02" has 1 colon
    if clean.count(":") >= 2:
        clean = clean.rsplit(":", 1)[0]
    return clean


_STATUS_EMOJI = {"active": "🟢", "ended": "⚪", "lost": "🟡"}


def format_history_entry(entry: dict) -> str:
    """Format a single session history record as an HTML text block.

    Includes session ID, status emoji, project name, start/end times,
    status, and optional exit code.

    Args:
        entry: A dict with keys ``id``, ``project``, ``started_at``,
            ``status``, and optionally ``ended_at`` and ``exit_code``.

    Returns:
        A multi-line HTML-formatted string representing the history entry.
    """
    safe_name = html.escape(entry["project"])
    started = _format_timestamp(entry["started_at"])
    emoji = _STATUS_EMOJI.get(entry["status"], "⚪")
    sid = entry.get("id", "?")
    parts = [
        f"{emoji} <b>#{sid} {safe_name}</b>",
        f"  Started: {html.escape(started)}",
    ]
    if entry.get("ended_at"):
        ended = _format_timestamp(entry["ended_at"])
        parts.append(f"  Ended: {html.escape(ended)}")
    parts.append(f"  Status: {html.escape(entry['status'])}")
    if entry.get("exit_code") is not None:
        parts.append(f"  Exit code: {entry['exit_code']}")
    return "\n".join(parts)


# --- Command menu ---

BOT_COMMANDS = [
    ("start", "Start a new session / pick a project"),
    ("sessions", "List and switch active sessions"),
    ("exit", "Kill the active session"),
    ("history", "Show past sessions"),
    ("git", "Show git info for current project"),
    ("context", "Show context window usage"),
    ("download", "Download a file from the session"),
    ("update_claude", "Update the Claude Code CLI"),
]
