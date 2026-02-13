"""Inline keyboard callback query handlers.

Dispatches callback queries based on the ``callback_data`` prefix:

- ``project:<path>`` — create a new session for the selected project
- ``switch:<id>`` — switch the active session
- ``kill:<id>`` — kill a session
- ``update:confirm|cancel`` — run/cancel Claude CLI update
- ``tool:yes|no|pick`` — tool approval actions
- ``page:<n>`` — navigate project list pages
"""

from __future__ import annotations

import html
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.telegram.commands import _run_update_command
from src.telegram.keyboards import (
    build_project_keyboard,
    format_session_started,
    is_authorized,
)
from src.git_info import get_git_info
from src.project_scanner import scan_projects
from src.telegram.output import mark_tool_acted

logger = logging.getLogger(__name__)


async def handle_callback_query(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle inline keyboard callback queries.

    Dispatches based on the callback_data prefix.

    Args:
        update: Incoming Telegram update containing the callback query.
        context: Bot context providing access to bot_data.
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
        await _handle_project(query, user_id, data, session_manager)
    elif data.startswith("switch:"):
        await _handle_switch(query, user_id, data, session_manager)
    elif data.startswith("kill:"):
        await _handle_kill(query, user_id, data, session_manager)
    elif data.startswith("update:"):
        await _handle_update(query, data, config)
    elif data.startswith("tool:"):
        await _handle_tool(query, user_id, data, session_manager)
    elif data.startswith("page:"):
        await _handle_page(query, data, config)


async def _handle_project(query, user_id, data, session_manager) -> None:
    """Create a new session for the selected project."""
    project_path = data[len("project:"):]
    project_name = project_path.rstrip("/").split("/")[-1]
    try:
        session = await session_manager.create_session(
            user_id, project_name, project_path,
        )
    except Exception as exc:
        logger.error("Failed to create session for %s: %s", project_name, exc)
        await query.answer()
        safe_name = html.escape(project_name)
        safe_exc = html.escape(str(exc))
        await query.edit_message_text(
            f"Failed to start Claude for <b>{safe_name}</b>:\n"
            f"<code>{safe_exc}</code>",
            parse_mode="HTML",
        )
        return
    git_info = await get_git_info(project_path)
    msg = format_session_started(project_name, session.session_id)
    msg += f"\n{git_info.format()}"
    await query.answer()
    await query.edit_message_text(msg, parse_mode="HTML")


async def _handle_switch(query, user_id, data, session_manager) -> None:
    """Switch the active session."""
    session_id = int(data[len("switch:"):])
    session_manager.switch_session(user_id, session_id)
    active = session_manager.get_active_session(user_id)
    await query.answer()
    safe_name = html.escape(active.project_name)
    await query.edit_message_text(
        f"Switched to <b>{safe_name}</b> (session #{active.session_id})",
        parse_mode="HTML",
    )


async def _handle_kill(query, user_id, data, session_manager) -> None:
    """Kill a session."""
    session_id = int(data[len("kill:"):])
    await session_manager.kill_session(user_id, session_id)
    await query.answer()
    await query.edit_message_text(f"Session #{session_id} killed.")


async def _handle_update(query, data, config) -> None:
    """Handle Claude CLI update confirmation/cancellation."""
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


async def _handle_tool(query, user_id, data, session_manager) -> None:
    """Handle tool approval/selection callbacks."""
    parts = data.split(":")
    action = parts[1]
    if action == "pick":
        selected = int(parts[2])
        target = int(parts[3])
        session_id = int(parts[4])
        session = session_manager._sessions.get(user_id, {}).get(session_id)
        if not session:
            await query.answer("Session no longer active")
            return
        delta = target - selected
        if delta > 0:
            keys = "\x1b[B" * delta  # Down arrow
        elif delta < 0:
            keys = "\x1b[A" * abs(delta)  # Up arrow
        else:
            keys = ""
        await session.process.write(keys + "\r")
        label = "Selected"
    else:
        session_id = int(parts[2])
        session = session_manager._sessions.get(user_id, {}).get(session_id)
        if not session:
            await query.answer("Session no longer active")
            return
        if action == "yes":
            await session.process.write("\r")
            label = "Allowed"
        else:
            await session.process.write("\x1b")
            label = "Denied"
    mark_tool_acted(user_id, session_id)
    await query.answer(label)
    original_text = query.message.text or query.message.caption or ""
    await query.edit_message_text(
        f"{html.escape(original_text)}\n\n<i>{label}</i>",
        parse_mode="HTML",
    )


async def _handle_page(query, data, config) -> None:
    """Navigate to a different page of the project list."""
    page = int(data[len("page:"):])
    projects = scan_projects(
        config.projects.root, depth=config.projects.scan_depth,
    )
    keyboard_data = build_project_keyboard(projects, page=page)
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=btn["text"], callback_data=btn["callback_data"],
                )
                for btn in row
            ]
            for row in keyboard_data
        ]
    )
    await query.answer()
    await query.edit_message_text("Choose a project:", reply_markup=keyboard)
