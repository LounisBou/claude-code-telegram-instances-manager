from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from pydevmate import DebugIt, LogIt
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot import (
    handle_callback_query,
    handle_context,
    handle_download,
    handle_exit,
    handle_file_upload,
    handle_git,
    handle_history,
    handle_sessions,
    handle_start,
    handle_text_message,
    handle_update_claude,
)
from src.config import load_config
from src.database import Database
from src.file_handler import FileHandler
from src.session_manager import SessionManager


def _setup_logging(debug: bool) -> LogIt:
    """Configure application logging with PyDevMate LogIt.

    Args:
        debug: If True, sets log level to DEBUG; otherwise INFO.

    Returns:
        The configured LogIt logger instance.
    """
    level = logging.DEBUG if debug else logging.INFO
    return LogIt(name="claude-bot", level=level, console=True, file=False)


def build_app(config_path: str, debug: bool = False) -> Application:
    """Build and configure the Telegram bot application.

    Loads configuration, initializes core services (database, session manager,
    file handler), stores them in bot_data, and registers all command, callback,
    and message handlers.

    Args:
        config_path: Filesystem path to the YAML configuration file.
        debug: If True, enables debug mode (overrides config).

    Returns:
        A fully configured telegram.ext.Application instance ready to be
        initialized and started.
    """
    config = load_config(config_path)

    # --debug flag overrides config file setting
    if debug:
        config.debug.enabled = True

    app = Application.builder().token(config.telegram.bot_token).build()

    db = Database(config.database.path)
    file_handler = FileHandler()
    session_manager = SessionManager(
        claude_command=config.claude.command,
        claude_args=config.claude.default_args,
        max_per_user=config.sessions.max_per_user,
        db=db,
        file_handler=file_handler,
    )

    app.bot_data["config"] = config
    app.bot_data["db"] = db
    app.bot_data["session_manager"] = session_manager
    app.bot_data["file_handler"] = file_handler

    # Apply DebugIt decorator to key sync functions when debug mode is on
    if config.debug.enabled:
        import src.output_parser as op

        op.classify_screen_state = DebugIt()(op.classify_screen_state)

    # Command handlers
    app.add_handler(CommandHandler(["start", "new"], handle_start))
    app.add_handler(CommandHandler("sessions", handle_sessions))
    app.add_handler(CommandHandler("exit", handle_exit))
    app.add_handler(CommandHandler("history", handle_history))
    app.add_handler(CommandHandler("git", handle_git))
    app.add_handler(CommandHandler("context", handle_context))
    app.add_handler(CommandHandler("download", handle_download))
    app.add_handler(CommandHandler("update_claude", handle_update_claude))

    # Callback query handler
    app.add_handler(CallbackQueryHandler(handle_callback_query))

    # File uploads
    app.add_handler(
        MessageHandler(filters.ATTACHMENT & ~filters.COMMAND, handle_file_upload)
    )

    # Text handler registered last so commands and callbacks take priority
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    return app


async def _on_startup(app: Application) -> None:
    """Run one-time initialization tasks after the application starts.

    Initializes the database schema and marks any previously active sessions
    as lost, since they could not have survived a bot restart.

    Args:
        app: The Telegram application instance whose bot_data contains
            the Database dependency.

    Returns:
        None.
    """
    logger = logging.getLogger(__name__)
    db: Database = app.bot_data["db"]
    await db.initialize()
    # Sessions from a previous run can't survive a bot restart; mark them lost
    lost = await db.mark_active_sessions_lost()
    if lost:
        logger.info(f"Marked {len(lost)} stale sessions as lost on startup")


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed namespace with 'config' (str) and 'debug' (bool) attributes.
    """
    parser = argparse.ArgumentParser(description="Claude Instance Manager Bot")
    parser.add_argument("config", nargs="?", default="config.yaml",
                        help="Path to YAML config file (default: config.yaml)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode (verbose logging)")
    return parser.parse_args()


async def main() -> None:
    """Entry point for the ClaudeInstanceManager Telegram bot.

    Parses command-line arguments, sets up logging, builds the application,
    registers the startup hook, and runs the bot with long-polling until
    interrupted. On shutdown, gracefully stops the updater and the application.

    Returns:
        None.
    """
    args = _parse_args()
    logger = _setup_logging(args.debug)

    app = build_app(args.config, debug=args.debug)
    app.post_init = _on_startup

    logger.info("Starting ClaudeInstanceManager bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Event().wait() keeps the bot running indefinitely until KeyboardInterrupt
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
