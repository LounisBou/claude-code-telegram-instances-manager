from __future__ import annotations

import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.git_info import get_git_info
from src.project_scanner import Project, scan_projects


# --- Auth ---


def is_authorized(user_id: int, authorized_users: list[int]) -> bool:
    return user_id in authorized_users


# --- Keyboard builders ---


def build_project_keyboard(
    projects: list[Project], page: int = 0, page_size: int = 8
) -> list[list[dict]]:
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
    return f"Session started on *{project_name}*. Session #{session_id}"


def format_session_ended(project_name: str, session_id: int) -> str:
    return f"Session #{session_id} on *{project_name}* ended."


def format_history_entry(entry: dict) -> str:
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
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip()
