from __future__ import annotations

import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.telegram.commands import _run_update_command
from src.telegram.keyboards import (
    BOT_COMMANDS,
    build_project_keyboard,
    build_sessions_keyboard,
    format_session_ended,
    format_session_started,
    is_authorized,
)
from src.git_info import get_git_info
from src.project_scanner import scan_projects
from src.telegram.output import is_tool_request_pending, mark_tool_acted

logger = logging.getLogger(__name__)


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
    logger.debug("handle_start user_id=%d", user_id)
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
    logger.debug("handle_sessions user_id=%d", user_id)
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    sessions = session_manager.list_sessions(user_id)
    if not sessions:
        await update.message.reply_text("No active sessions. Use /start to begin one.")
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
    logger.debug("handle_exit user_id=%d", user_id)
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session. Use /start to begin one.")
        return

    await session_manager.kill_session(user_id, active.session_id)
    msg = format_session_ended(active.project_name, active.session_id)

    new_active = session_manager.get_active_session(user_id)
    if new_active:
        safe_name = html.escape(new_active.project_name)
        msg += f"\nSwitched to <b>{safe_name}</b> (session #{new_active.session_id})"

    await update.message.reply_text(msg, parse_mode="HTML")


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
    logger.debug("handle_text_message user_id=%d len=%d", user_id, len(update.message.text))
    config = context.bot_data["config"]

    # Silently ignore unauthorized users for text messages to avoid reply spam
    if not is_authorized(user_id, config.telegram.authorized_users):
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session. Use /start to begin one.")
        return

    if is_tool_request_pending(user_id, active.session_id):
        await update.message.reply_text(
            "A tool approval is pending. Please respond to it first."
        )
        return

    await active.process.submit(update.message.text)


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
    logger.debug("handle_callback_query user_id=%d data=%s", user_id, data)
    session_manager = context.bot_data["session_manager"]

    if data.startswith("project:"):
        project_path = data[len("project:") :]
        # Extract project name from path to avoid storing it separately in callback_data
        project_name = project_path.rstrip("/").split("/")[-1]
        try:
            session = await session_manager.create_session(
                user_id, project_name, project_path
            )
        except Exception as exc:
            logger.error("Failed to create session for %s: %s", project_name, exc)
            await query.answer()
            safe_name = html.escape(project_name)
            safe_exc = html.escape(str(exc))
            await query.edit_message_text(
                f"Failed to start Claude for <b>{safe_name}</b>:\n<code>{safe_exc}</code>",
                parse_mode="HTML",
            )
            return
        git_info = await get_git_info(project_path)
        msg = format_session_started(project_name, session.session_id)
        msg += f"\n{git_info.format()}"
        await query.answer()
        await query.edit_message_text(msg, parse_mode="HTML")

    elif data.startswith("switch:"):
        session_id = int(data[len("switch:") :])
        session_manager.switch_session(user_id, session_id)
        active = session_manager.get_active_session(user_id)
        await query.answer()
        safe_name = html.escape(active.project_name)
        await query.edit_message_text(
            f"Switched to <b>{safe_name}</b> (session #{active.session_id})",
            parse_mode="HTML",
        )

    elif data.startswith("kill:"):
        session_id = int(data[len("kill:") :])
        await session_manager.kill_session(user_id, session_id)
        await query.answer()
        await query.edit_message_text(f"Session #{session_id} killed.")

    elif data.startswith("update:"):
        action = data[len("update:"):]
        if action == "confirm":
            await query.answer()
            await query.edit_message_text("Updating Claude CLI...")
            result = await _run_update_command(config.claude.update_command)
            await query.edit_message_text(
                f"Update result:\n<code>{html.escape(result)}</code>",
                parse_mode="HTML",
            )
        else:
            await query.answer()
            await query.edit_message_text("Update cancelled.")

    elif data.startswith("tool:"):
        # Tool approval/selection callbacks:
        #   "tool:yes:<sid>"                    — Accept default (Enter)
        #   "tool:no:<sid>"                     — Cancel (Escape)
        #   "tool:pick:<selected>:<target>:<sid>" — Multi-choice selection
        parts = data.split(":")
        action = parts[1]
        if action == "pick":
            # Multi-choice: navigate from current selection to target
            selected = int(parts[2])
            target = int(parts[3])
            session_id = int(parts[4])
            session = session_manager._sessions.get(user_id, {}).get(session_id)
            if not session:
                await query.answer("Session no longer active")
                return
            delta = target - selected
            # Send arrow keys to move cursor, then Enter to confirm
            if delta > 0:
                keys = "\x1b[B" * delta  # Down arrow
            elif delta < 0:
                keys = "\x1b[A" * abs(delta)  # Up arrow
            else:
                keys = ""
            await session.process.write(keys + "\r")
            # Extract the label from the button that was clicked
            label = query.data.split(":", 1)[0] if not query.message else ""
            # Use the button text from the inline keyboard
            label = "Selected"
        else:
            session_id = int(parts[2])
            session = session_manager._sessions.get(user_id, {}).get(session_id)
            if not session:
                await query.answer("Session no longer active")
                return
            if action == "yes":
                # Press Enter to accept the default (Yes) option
                await session.process.write("\r")
                label = "Allowed"
            else:
                # Press Escape to cancel the tool request
                await session.process.write("\x1b")
                label = "Denied"
        mark_tool_acted(user_id, session_id)
        await query.answer(label)
        # Update the message to show the decision (remove keyboard)
        original_text = query.message.text or query.message.caption or ""
        await query.edit_message_text(
            f"{html.escape(original_text)}\n\n<i>{label}</i>",
            parse_mode="HTML",
        )

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


async def handle_unknown_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Forward unrecognised slash commands to the active Claude session.

    Claude Code has its own slash commands (/status, /approve, etc.).
    If the user has an active session, forward the text as-is.
    Otherwise reply with the list of valid bot commands.
    """
    user_id = update.effective_user.id
    config = context.bot_data["config"]
    if not is_authorized(user_id, config.telegram.authorized_users):
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if active:
        if is_tool_request_pending(user_id, active.session_id):
            await update.message.reply_text(
                "A tool approval is pending. Please respond to it first."
            )
            return
        await active.process.submit(update.message.text)
        return

    known = "\n".join(f"/{cmd} — {desc}" for cmd, desc in BOT_COMMANDS)
    await update.message.reply_text(f"Unknown command.\n\n{known}")
