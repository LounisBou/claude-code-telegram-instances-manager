from __future__ import annotations

import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.telegram.callbacks import handle_callback_query  # noqa: F401 — re-exported
from src.telegram.keyboards import (
    BOT_COMMANDS,
    build_project_keyboard,
    build_sessions_keyboard,
    format_session_ended,
    is_authorized,
)
from src.project_scanner import scan_projects
from src.telegram.pipeline_state import is_tool_request_pending

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

    if is_tool_request_pending(active.pipeline):
        await update.message.reply_text(
            "A tool approval is pending. Please respond to it first."
        )
        return

    await active.process.submit(update.message.text)


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
        if is_tool_request_pending(active.pipeline):
            await update.message.reply_text(
                "A tool approval is pending. Please respond to it first."
            )
            return
        await active.process.submit(update.message.text)
        return

    known = "\n".join(f"/{cmd} — {desc}" for cmd, desc in BOT_COMMANDS)
    await update.message.reply_text(f"Unknown command.\n\n{known}")
