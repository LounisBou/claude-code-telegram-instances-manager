"""Background loop that reads Claude output and streams it to Telegram.

Thin orchestration loop using :class:`~src.telegram.output_processor.SessionProcessor`
for the actual event processing.  Each poll cycle (300ms) reads raw PTY bytes
from all active sessions and delegates to the processor's 3-phase pipeline:

1. Pre-extraction — state entry side effects (typing indicator, dedup, auth)
2. Extraction — content dedup, render, send to Telegram
3. Finalization — ANSI re-render, clear history, finalize message (IDLE only)
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from src.telegram.output_processor import SessionProcessor
from src.telegram.output_state import get_or_create

logger = logging.getLogger(__name__)


async def poll_output(
    bot: Bot, session_manager, *, edit_rate_limit: int = 3,
) -> None:
    """Background loop that reads Claude output and streams it to Telegram.

    Creates a :class:`SessionProcessor` per session and delegates each
    poll cycle to its ``process_cycle`` method.

    Args:
        bot: Telegram Bot instance for sending messages.
        session_manager: SessionManager with active sessions.
        edit_rate_limit: Maximum Telegram edit_message calls per second.
    """
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
              try:
                state = get_or_create(
                    user_id, sid, bot, edit_rate_limit,
                )

                raw = session.process.read_available()
                if not raw:
                    continue

                processor = SessionProcessor(
                    state=state,
                    user_id=user_id,
                    session_id=sid,
                    bot=bot,
                    session_manager=session_manager,
                )
                await processor.process_cycle(raw)

              except asyncio.CancelledError:
                raise
              except Exception:
                logger.exception(
                    "poll_output crash for user=%d sid=%d — will retry next cycle",
                    user_id, sid,
                )
