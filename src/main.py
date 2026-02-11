from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot import (
    BOT_COMMANDS,
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
    handle_unknown_command,
    handle_update_claude,
)
from src.config import load_config
from src.database import Database
from src.file_handler import FileHandler
from src.log_setup import setup_logging
from src.session_manager import SessionManager

logger = logging.getLogger(__name__)


def build_app(config_path: str, debug: bool = False, trace: bool = False, verbose: bool = False) -> Application:
    """Build and configure the Telegram bot application."""
    config = load_config(config_path)

    if debug:
        config.debug.enabled = True
    if trace:
        config.debug.trace = True
    if verbose:
        config.debug.verbose = True

    app = Application.builder().token(config.telegram.bot_token).build()

    db = Database(config.database.path)
    file_handler = FileHandler()
    session_manager = SessionManager(
        claude_command=config.claude.command,
        claude_args=config.claude.default_args,
        max_per_user=config.sessions.max_per_user,
        db=db,
        file_handler=file_handler,
        claude_env=config.claude.env,
    )

    app.bot_data["config"] = config
    app.bot_data["db"] = db
    app.bot_data["session_manager"] = session_manager
    app.bot_data["file_handler"] = file_handler

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

    # Catch-all for unknown /commands so the bot never silently ignores
    app.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))

    logger.debug("App built with %d handler groups", len(app.handlers))

    return app


async def _on_startup(app: Application) -> None:
    """Run one-time initialization tasks after the application starts."""
    logger = logging.getLogger(__name__)
    db = app.bot_data["db"]
    await db.initialize()
    lost = await db.mark_active_sessions_lost()
    if lost:
        logger.info("Marked %d stale sessions as lost on startup", len(lost))

    await app.bot.set_my_commands(
        [BotCommand(cmd, desc) for cmd, desc in BOT_COMMANDS]
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Claude Instance Manager Bot")
    parser.add_argument("config", nargs="?", default="config.yaml",
                        help="Path to YAML config file (default: config.yaml)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode (verbose logging)")
    parser.add_argument("--trace", action="store_true",
                        help="Enable trace mode (writes trace file to debug/)")
    parser.add_argument("--verbose", action="store_true",
                        help="With --trace, also send trace output to terminal")
    return parser.parse_args()


async def main() -> None:
    """Entry point for the ClaudeInstanceManager Telegram bot."""
    args = _parse_args()
    logger = setup_logging(
        debug=args.debug, trace=args.trace, verbose=args.verbose
    )

    app = build_app(args.config, debug=args.debug, trace=args.trace, verbose=args.verbose)

    logger.info("Starting ClaudeInstanceManager bot...")
    await app.initialize()
    await _on_startup(app)
    await app.start()
    await app.updater.start_polling()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    await stop_event.wait()

    # Second Ctrl+C during shutdown → force exit immediately
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.remove_signal_handler(sig)

    logger.info("Shutting down...")
    await app.updater.stop()
    await app.stop()
    session_manager = app.bot_data["session_manager"]
    await session_manager.shutdown()
    db = app.bot_data["db"]
    await db.close()
    await app.shutdown()
    logger.info("Bye.")


if __name__ == "__main__":
    asyncio.run(main())
