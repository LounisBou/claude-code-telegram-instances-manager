from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.git_info import get_git_info
from src.project_scanner import Project, scan_projects


# --- Auth ---


def is_authorized(user_id: int, authorized_users: list[int]) -> bool:
    """Check whether a Telegram user is allowed to interact with the bot.

    Args:
        user_id: The Telegram user ID to verify.
        authorized_users: List of Telegram user IDs permitted to use the bot.

    Returns:
        True if the user ID is present in the authorized list, False otherwise.
    """
    return user_id in authorized_users


# --- Keyboard builders ---


def build_project_keyboard(
    projects: list[Project], page: int = 0, page_size: int = 8
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


# --- Message formatting ---


def format_session_started(project_name: str, session_id: int) -> str:
    """Format a Markdown message announcing that a new session has started.

    Args:
        project_name: Display name of the project the session belongs to.
        session_id: Numeric identifier of the newly created session.

    Returns:
        A Markdown-formatted string suitable for sending via Telegram.
    """
    return f"Session started on *{project_name}*. Session #{session_id}"


def format_session_ended(project_name: str, session_id: int) -> str:
    """Format a Markdown message announcing that a session has ended.

    Args:
        project_name: Display name of the project the session belonged to.
        session_id: Numeric identifier of the ended session.

    Returns:
        A Markdown-formatted string suitable for sending via Telegram.
    """
    return f"Session #{session_id} on *{project_name}* ended."


def format_history_entry(entry: dict) -> str:
    """Format a single session history record as a Markdown text block.

    Includes the project name, start time, optional end time, status, and
    optional exit code.

    Args:
        entry: A dict with keys ``project``, ``started_at``, ``status``,
            and optionally ``ended_at`` and ``exit_code``.

    Returns:
        A multi-line Markdown-formatted string representing the history
        entry.
    """
    parts = [
        f"*{entry['project']}*",
        f"Started: {entry['started_at']}",
    ]
    if entry.get("ended_at"):
        parts.append(f"Ended: {entry['ended_at']}")
    parts.append(f"Status: {entry['status']}")
    if entry.get("exit_code") is not None:
        parts.append(f"Exit code: {entry['exit_code']}")
    return "\n".join(parts)


# --- Command handlers ---


async def handle_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /start command by presenting a project selection keyboard.

    Scans the configured project root for available projects and sends an
    inline keyboard so the user can select one to start a session on.
    Unauthorized users receive a rejection message.

    Args:
        update: Incoming Telegram update containing the /start command.
        context: Bot context providing access to bot_data (config, etc.).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    projects = scan_projects(config.projects.root, depth=config.projects.scan_depth)
    if not projects:
        await update.message.reply_text("No projects found.")
        return

    keyboard_data = build_project_keyboard(projects)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=btn["text"], callback_data=btn["callback_data"]
                )
                for btn in row
            ]
            for row in keyboard_data
        ]
    )
    await update.message.reply_text("Choose a project:", reply_markup=keyboard)


async def handle_sessions(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /sessions command by listing all active sessions.

    Displays an inline keyboard with one row per active session, allowing
    the user to switch to or kill any session. The currently active
    session is marked with an asterisk.

    Args:
        update: Incoming Telegram update containing the /sessions command.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    sessions = session_manager.list_sessions(user_id)
    if not sessions:
        await update.message.reply_text("No active sessions.")
        return

    active = session_manager.get_active_session(user_id)
    active_id = active.session_id if active else None
    keyboard_data = build_sessions_keyboard(sessions, active_id)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=btn["text"], callback_data=btn["callback_data"]
                )
                for btn in row
            ]
            for row in keyboard_data
        ]
    )
    await update.message.reply_text("Active sessions:", reply_markup=keyboard)


async def handle_exit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /exit command by killing the current active session.

    Terminates the user's active session and notifies them. If another
    session exists, automatically switches to it and includes that info
    in the reply.

    Args:
        update: Incoming Telegram update containing the /exit command.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session to exit.")
        return

    await session_manager.kill_session(user_id, active.session_id)
    msg = format_session_ended(active.project_name, active.session_id)

    new_active = session_manager.get_active_session(user_id)
    if new_active:
        msg += f"\nSwitched to *{new_active.project_name}* (session #{new_active.session_id})"

    await update.message.reply_text(msg)


async def handle_text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle plain text messages by forwarding them to the active session.

    Writes the message text followed by a newline to the active session's
    PTY process. If no session is active, prompts the user to start one.
    Unauthorized users are silently ignored.

    Args:
        update: Incoming Telegram update containing a text message.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session. Use /start to begin one.")
        return

    await active.process.write(update.message.text + "\n")


# --- Callback query handler ---


async def handle_callback_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline keyboard callback queries.

    Dispatches based on the callback_data prefix:
      - ``project:<path>`` -- creates a new session for the selected project.
      - ``switch:<id>`` -- switches the active session to the given ID.
      - ``kill:<id>`` -- kills the session with the given ID.
      - ``page:<n>`` -- navigates to a different page of the project list.

    Args:
        update: Incoming Telegram update containing the callback query.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    query = update.callback_query
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await query.answer("Not authorized")
        return

    data = query.data
    session_manager = context.bot_data["session_manager"]

    if data.startswith("project:"):
        project_path = data[len("project:") :]
        project_name = project_path.rstrip("/").split("/")[-1]
        session = await session_manager.create_session(
            user_id, project_name, project_path
        )
        git_info = await get_git_info(project_path)
        msg = format_session_started(project_name, session.session_id)
        msg += f"\n{git_info.format()}"
        await query.answer()
        await query.edit_message_text(msg)

    elif data.startswith("switch:"):
        session_id = int(data[len("switch:") :])
        session_manager.switch_session(user_id, session_id)
        active = session_manager.get_active_session(user_id)
        await query.answer()
        await query.edit_message_text(
            f"Switched to *{active.project_name}* (session #{active.session_id})"
        )

    elif data.startswith("kill:"):
        session_id = int(data[len("kill:") :])
        await session_manager.kill_session(user_id, session_id)
        await query.answer()
        await query.edit_message_text(f"Session #{session_id} killed.")

    elif data.startswith("page:"):
        page = int(data[len("page:") :])
        projects = scan_projects(
            config.projects.root, depth=config.projects.scan_depth
        )
        keyboard_data = build_project_keyboard(projects, page=page)
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=btn["text"], callback_data=btn["callback_data"]
                    )
                    for btn in row
                ]
                for row in keyboard_data
            ]
        )
        await query.answer()
        await query.edit_message_text("Choose a project:", reply_markup=keyboard)


# --- Additional command handlers ---


async def handle_history(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /history command by displaying recent session history.

    Retrieves up to 20 of the user's most recent sessions from the
    database and formats them as a Markdown message.

    Args:
        update: Incoming Telegram update containing the /history command.
        context: Bot context providing access to bot_data (config, db).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    db = context.bot_data["db"]
    sessions = await db.list_sessions(user_id)
    if not sessions:
        await update.message.reply_text("No session history.")
        return

    lines = [format_history_entry(s) for s in sessions[:20]]
    await update.message.reply_text("\n\n".join(lines))


async def handle_git(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /git command by showing git info for the active session.

    Retrieves branch name, pull request URL, title, and state for the
    project associated with the user's active session and replies with
    a formatted summary.

    Args:
        update: Incoming Telegram update containing the /git command.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session.")
        return

    git_info = await get_git_info(active.project_path)
    await update.message.reply_text(git_info.format())


async def handle_update_claude(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /update_claude command to update the Claude Code CLI.

    If active sessions exist, prompts for confirmation before proceeding.
    Otherwise, runs the configured update command immediately and replies
    with its output.

    Args:
        update: Incoming Telegram update containing the /update_claude
            command.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    if session_manager.has_active_sessions():
        count = session_manager.active_session_count()
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Yes, update", callback_data="update:confirm"
                    ),
                    InlineKeyboardButton("Cancel", callback_data="update:cancel"),
                ]
            ]
        )
        await update.message.reply_text(
            f"{count} active session(s) running. Update anyway?",
            reply_markup=keyboard,
        )
        return

    result = await _run_update_command(config.claude.update_command)
    await update.message.reply_text(f"Update result:\n{result}")


async def handle_context(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /context command by requesting context info from Claude.

    Sends the ``/context`` slash command to the active session's PTY
    process. The actual output is delivered asynchronously through the
    normal output pipeline.

    Args:
        update: Incoming Telegram update containing the /context command.
        context: Bot context providing access to bot_data (config,
            session_manager).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session.")
        return

    await active.process.write("/context\n")
    await update.message.reply_text("Context info requested. Output will follow.")


async def handle_download(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /download command by sending a file to the user.

    Expects the command to be followed by an absolute file path. If the
    file exists, it is sent as a Telegram document attachment.

    Args:
        update: Incoming Telegram update containing the /download command
            and file path argument.
        context: Bot context providing access to bot_data (config,
            file_handler).
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    file_handler = context.bot_data["file_handler"]
    text = update.message.text
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /download /path/to/file")
        return

    file_path = parts[1].strip()
    if not file_handler.file_exists(file_path):
        await update.message.reply_text(f"File not found: {file_path}")
        return

    await update.message.reply_document(
        document=open(file_path, "rb"), filename=file_path.split("/")[-1]
    )


async def handle_file_upload(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle file or photo uploads by saving them to the project directory.

    Downloads the uploaded document (or the largest photo variant) to the
    active session's upload directory and notifies the Claude process
    about the new file. Unauthorized users are silently ignored.

    Args:
        update: Incoming Telegram update containing a document or photo
            attachment.
        context: Bot context providing access to bot_data (config,
            session_manager, file_handler) and the bot instance for
            file downloads.
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session. Upload ignored.")
        return

    file_handler = context.bot_data["file_handler"]
    document = update.message.document
    if document is None and update.message.photo:
        document = update.message.photo[-1]
    if document is None:
        return

    file_obj = await context.bot.get_file(document.file_id)
    filename = getattr(document, "file_name", None) or f"{document.file_id}.bin"
    save_path = file_handler.get_upload_path(
        active.project_name, active.session_id, filename
    )
    await file_obj.download_to_drive(save_path)

    await active.process.write(f"User uploaded a file: {save_path}\n")
    await update.message.reply_text(f"File uploaded: `{save_path}`")


async def _run_update_command(command: str) -> str:
    """Execute a shell command to update the Claude Code CLI.

    Runs the command in a subprocess, capturing stdout and stderr into a
    single combined output stream.

    Args:
        command: The shell command string to execute (e.g.
            ``npm install -g @anthropic-ai/claude-code``).

    Returns:
        The combined stdout/stderr output of the command, stripped of
        leading and trailing whitespace.
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()
