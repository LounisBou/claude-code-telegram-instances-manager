"""StreamingMessage: edit-in-place streaming for Telegram responses."""

from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum

from telegram import Bot
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

logger = logging.getLogger(__name__)


class StreamingState(Enum):
    """State of a StreamingMessage lifecycle.

    Values:
        IDLE: No active response. Ready to begin a new cycle.
        THINKING: Placeholder message sent, typing indicator active.
        STREAMING: Content is being appended and edited in-place.
    """

    IDLE = "idle"
    THINKING = "thinking"
    STREAMING = "streaming"


class StreamingMessage:
    """Manages edit-in-place streaming for a single Claude response.

    State machine: IDLE -> start_thinking() -> THINKING -> first content -> STREAMING -> finalize() -> IDLE

    In THINKING state, sends typing action every 4s.
    In STREAMING state, edits message in-place at throttled rate.
    On overflow (>4096 chars), finalizes current message and starts a new one.
    """

    def __init__(self, bot: Bot, chat_id: int, edit_rate_limit: int = 3) -> None:
        """Initialize streaming message manager.

        Args:
            bot: Telegram Bot instance for API calls.
            chat_id: Telegram chat ID to send messages to.
            edit_rate_limit: Maximum edit_message calls per second.
        """
        self.bot = bot
        self.chat_id = chat_id
        self.edit_rate_limit = edit_rate_limit
        self.message_id: int | None = None
        self.accumulated: str = ""
        self.last_edit_time: float = 0
        self.state: StreamingState = StreamingState.IDLE
        self._typing_task: asyncio.Task | None = None

    async def start_thinking(self) -> None:
        """Send typing action and placeholder message.

        Transitions: IDLE -> THINKING.
        If still in STREAMING state (previous response not finalized),
        auto-finalizes the previous response first.
        Starts a background task that resends typing action every 4 seconds.
        """
        # Safety net: if previous response was not finalized (IDLE missed),
        # finalize it now before starting a new response cycle.
        if self.state == StreamingState.STREAMING:
            logger.warning(
                "start_thinking called while still STREAMING — "
                "auto-finalizing previous response"
            )
            await self.finalize()

        await self.bot.send_chat_action(chat_id=self.chat_id, action="typing")
        msg = await self.bot.send_message(
            chat_id=self.chat_id,
            text="<i>Thinking...</i>",
            parse_mode="HTML",
        )
        self.message_id = msg.message_id
        self.state = StreamingState.THINKING
        self._typing_task = asyncio.create_task(self._typing_loop())

    async def append_content(self, html: str) -> None:
        """Add content and edit message if throttle allows.

        On first call, cancels typing indicator and transitions to STREAMING.
        Handles overflow when accumulated content exceeds 4096 chars.

        Safety net: if called while IDLE (start_thinking was never called,
        e.g. classifier skipped THINKING state), sends a new message first
        so there is a message_id to edit.

        Args:
            html: HTML-formatted content to append.
        """
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None

        # Safety net: create a message if start_thinking() was never called
        if self.state == StreamingState.IDLE or self.message_id is None:
            logger.warning(
                "append_content called without start_thinking — "
                "sending new message (state=%s)",
                self.state.value,
            )
            msg = await self.bot.send_message(
                chat_id=self.chat_id, text=html, parse_mode="HTML"
            )
            self.message_id = msg.message_id
            self.accumulated = html
            self.last_edit_time = time.monotonic()
            self.state = StreamingState.STREAMING
            return

        self.state = StreamingState.STREAMING
        self.accumulated += html

        if len(self.accumulated) > 4096:
            await self._overflow()
            return

        now = time.monotonic()
        min_interval = 1.0 / self.edit_rate_limit
        if now - self.last_edit_time < min_interval:
            return

        await self._edit()

    async def finalize(self) -> None:
        """Final edit to ensure all content is sent, then reset.

        Transitions: any -> IDLE.
        """
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None
        if self.accumulated and self.message_id:
            await self._edit()
        self.reset()

    async def _edit(self) -> None:
        """Edit the current message with accumulated content."""
        if not self.message_id or not self.accumulated:
            return
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=self.accumulated,
                parse_mode="HTML",
            )
            self.last_edit_time = time.monotonic()
        except BadRequest as exc:
            exc_str = str(exc).lower()
            if "parse entities" in exc_str:
                logger.warning(
                    "HTML parse error — falling back to plain text. "
                    "html=%r", self.accumulated[:300],
                )
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        text=self.accumulated,
                        parse_mode=None,
                    )
                    self.last_edit_time = time.monotonic()
                except BadRequest as inner_exc:
                    logger.warning(
                        "edit_message plain-text fallback failed: %s", inner_exc
                    )
            elif "message is not modified" in exc_str:
                # Harmless: finalize() re-editing with same content
                pass
            else:
                logger.warning("edit_message BadRequest: %s", exc)
        except RetryAfter as exc:
            logger.warning(
                "Rate limited by Telegram, backing off %ss", exc.retry_after
            )
            # Push last_edit_time forward so the throttle respects the backoff
            self.last_edit_time = time.monotonic() + exc.retry_after
        except Forbidden:
            raise  # User blocked bot — let poll_output handle
        except NetworkError as exc:
            logger.warning("edit_message network error: %s", exc)

    async def _overflow(self) -> None:
        """Content exceeds 4096: finalize current message, start new one."""
        split_at = self.accumulated.rfind("\n", 0, 4096)
        if split_at == -1:
            split_at = 4000
        current = self.accumulated[:split_at]
        remainder = self.accumulated[split_at:].lstrip()
        self.accumulated = current
        await self._edit()
        if remainder:
            try:
                msg = await self.bot.send_message(
                    chat_id=self.chat_id, text=remainder, parse_mode="HTML"
                )
                self.message_id = msg.message_id
                self.accumulated = remainder
                self.last_edit_time = time.monotonic()
            except Forbidden:
                raise  # User blocked bot — let poll_output handle
            except Exception as exc:
                logger.error(
                    "Failed to send overflow message, "
                    "content will retry next cycle: %s", exc,
                )
                # Keep remainder so next append_content retries
                self.accumulated = remainder

    async def _typing_loop(self) -> None:
        """Resend typing action every 4 seconds."""
        try:
            while True:
                await asyncio.sleep(4)
                try:
                    await self.bot.send_chat_action(
                        chat_id=self.chat_id, action="typing"
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.debug("typing indicator failed: %s", exc)
        except asyncio.CancelledError:
            pass

    def replace_content(self, html: str) -> None:
        """Replace accumulated content (e.g. for ANSI re-render on finalization).

        Args:
            html: New HTML content to replace the current accumulated text.
        """
        self.accumulated = html

    def reset(self) -> None:
        """Reset to IDLE for next response."""
        self.message_id = None
        self.accumulated = ""
        self.last_edit_time = 0
        self.state = StreamingState.IDLE
