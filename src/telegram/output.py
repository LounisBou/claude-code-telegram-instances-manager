"""Background loop that reads Claude output and streams it to Telegram.

Thin orchestration loop that polls active sessions every 300ms, feeds PTY
bytes to the terminal emulator, classifies the screen, and dispatches
transitions through PipelineRunner.
"""

from __future__ import annotations

import asyncio
import logging

from telegram import Bot

from src.parsing.screen_classifier import classify_screen_state
from src.telegram.pipeline_runner import PipelineRunner

logger = logging.getLogger(__name__)


async def poll_output(
    bot: Bot, session_manager,
) -> None:
    """Background loop that reads Claude output and streams it to Telegram."""
    while True:
        await asyncio.sleep(0.3)
        for user_id, sessions in list(session_manager._sessions.items()):
            for sid, session in list(sessions.items()):
              try:
                if session.pipeline is None:
                    continue
                pipeline = session.pipeline

                raw = session.process.read_available()
                if not raw:
                    continue

                pipeline.emulator.feed(raw)
                display = pipeline.emulator.get_display()
                event = classify_screen_state(display, pipeline.prev_view)

                runner = PipelineRunner(
                    state=pipeline,
                    user_id=user_id,
                    session_id=sid,
                    bot=bot,
                    session_manager=session_manager,
                )
                await runner.process(event)

              except asyncio.CancelledError:
                raise
              except Exception:
                logger.exception(
                    "poll_output crash for user=%d sid=%d — will retry next cycle",
                    user_id, sid,
                )
