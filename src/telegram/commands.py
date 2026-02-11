from __future__ import annotations

import asyncio
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.telegram.keyboards import format_history_entry, is_authorized
from src.git_info import get_git_info

logger = logging.getLogger(__name__)


# --- Additional command handlers ---


async def handle_history(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle the /history command by displaying recent session history.

    Retrieves up to 20 of the user's most recent sessions from the
    database and formats them as an HTML message.

    Args:
        update: Incoming Telegram update containing the /history command.
        context: Bot context providing access to bot_data (config, db).
    """
    user_id = update.effective_user.id
    logger.debug("handle_history user_id=%d", user_id)
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
    await update.message.reply_text("\n\n".join(lines), parse_mode="HTML")


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
    logger.debug("handle_git user_id=%d", user_id)
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
    await update.message.reply_text(git_info.format(), parse_mode="HTML")


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
    logger.debug("handle_update_claude user_id=%d", user_id)
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    # Confirm before updating when sessions are active — update may restart the CLI
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
    logger.debug("handle_context user_id=%d", user_id)
    config = context.bot_data["config"]

    if not is_authorized(user_id, config.telegram.authorized_users):
        await update.message.reply_text("You are not authorized to use this bot.")
        return

    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    if not active:
        await update.message.reply_text("No active session.")
        return

    await active.process.submit("/context")
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
    logger.debug("handle_download user_id=%d", user_id)
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

    # Path traversal protection: resolve symlinks and verify the path falls
    # within the active session's project or an upload directory
    session_manager = context.bot_data["session_manager"]
    active = session_manager.get_active_session(user_id)
    resolved = os.path.realpath(file_path)
    allowed_dirs = [file_handler._base_dir]
    if active:
        allowed_dirs.append(os.path.realpath(active.project_path))
    if not any(resolved.startswith(os.path.realpath(d)) for d in allowed_dirs):
        await update.message.reply_text("Access denied: path outside allowed directories.")
        return

    if not file_handler.file_exists(file_path):
        await update.message.reply_text(f"File not found: {file_path}")
        return

    with open(file_path, "rb") as f:
        await update.message.reply_document(
            document=f, filename=file_path.split("/")[-1]
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
    logger.debug("handle_file_upload user_id=%d", user_id)
    config = context.bot_data["config"]

    # Silently ignore unauthorized uploads to avoid reply spam
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
        # Telegram sends photos as an array of sizes; [-1] is the largest resolution
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
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    except asyncio.TimeoutError:
        proc.kill()
        return "Error: update command timed out after 60s"
    prefix = "OK" if proc.returncode == 0 else f"FAILED (exit {proc.returncode})"
    return f"{prefix}: {stdout.decode().strip()}"
