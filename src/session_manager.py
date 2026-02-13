from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.claude_process import ClaudeProcess
from src.core.database import Database
from src.file_handler import FileHandler
from src.core.log_setup import TRACE
from src.telegram.pipeline_state import PipelineState

logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Raised when a session operation fails."""

    pass


@dataclass
class ClaudeSession:
    """Active Claude Code session bound to a user and project."""

    session_id: int
    user_id: int
    project_name: str
    project_path: str
    process: ClaudeProcess
    pipeline: PipelineState | None = None
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    db_session_id: int = 0


class SessionManager:
    """Manage the lifecycle of Claude Code sessions per user."""

    def __init__(
        self,
        claude_command: str,
        claude_args: list[str],
        max_per_user: int,
        db: Database,
        file_handler: FileHandler,
        claude_env: dict[str, str] | None = None,
    ) -> None:
        """Initialize the session manager.

        Args:
            claude_command: Path or name of the Claude CLI executable.
            claude_args: Additional CLI arguments passed to every session.
            max_per_user: Maximum number of concurrent sessions per user.
            db: Database instance for persisting session records.
            file_handler: File handler for cleaning up session artifacts.
            claude_env: Extra environment variables for Claude processes.
        """
        self._command = claude_command
        self._args = claude_args
        self._env = claude_env or {}
        self._max_per_user = max_per_user
        self._db = db
        self._file_handler = file_handler
        # {user_id: {session_id: ClaudeSession}}
        self._sessions: dict[int, dict[int, ClaudeSession]] = {}
        # {user_id: active_session_id}
        self._active: dict[int, int] = {}
        self._next_id: dict[int, int] = {}
        self._bot = None
        self._edit_rate_limit: int = 3

    def set_bot(self, bot, edit_rate_limit: int = 3) -> None:
        """Store bot reference for creating PipelineState on new sessions."""
        self._bot = bot
        self._edit_rate_limit = edit_rate_limit

    async def create_session(
        self, user_id: int, project_name: str, project_path: str
    ) -> ClaudeSession:
        """Spawn a new Claude Code process and register the session.

        Args:
            user_id: Telegram user ID that owns the session.
            project_name: Human-readable project name.
            project_path: Absolute filesystem path to the project root.

        Returns:
            The newly created ClaudeSession, already set as the
            user's active session.

        Raises:
            SessionError: If the user has reached the maximum number
                of concurrent sessions.
        """
        logger.debug("create_session user_id=%d project=%s", user_id, project_name)
        # Check limit before spawning to avoid orphaned processes on rejection
        user_sessions = self._sessions.get(user_id, {})
        if len(user_sessions) >= self._max_per_user:
            raise SessionError(
                f"Session limit reached ({self._max_per_user}). "
                f"Kill a session first."
            )

        session_id = self._next_id.get(user_id, 1)
        self._next_id[user_id] = session_id + 1

        process = ClaudeProcess(
            command=self._command, args=self._args, cwd=project_path, env=self._env
        )
        await process.spawn()
        logger.debug("Session #%d created for user %d", session_id, user_id)

        db_id = await self._db.create_session(
            user_id=user_id, project=project_name, project_path=project_path
        )

        pipeline = None
        if self._bot is not None:
            from src.parsing.terminal_emulator import TerminalEmulator
            from src.telegram.streaming_message import StreamingMessage
            pipeline = PipelineState(
                emulator=TerminalEmulator(),
                streaming=StreamingMessage(
                    bot=self._bot, chat_id=user_id, edit_rate_limit=self._edit_rate_limit,
                ),
            )

        session = ClaudeSession(
            session_id=session_id,
            user_id=user_id,
            project_name=project_name,
            project_path=project_path,
            process=process,
            pipeline=pipeline,
            db_session_id=db_id,
        )

        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        self._sessions[user_id][session_id] = session
        self._active[user_id] = session_id

        return session

    def get_active_session(self, user_id: int) -> ClaudeSession | None:
        """Return the user's currently active session.

        Args:
            user_id: Telegram user ID to look up.

        Returns:
            The active ClaudeSession, or None if the user has no
            active session.
        """
        active_id = self._active.get(user_id)
        if active_id is None:
            return None
        return self._sessions.get(user_id, {}).get(active_id)

    def switch_session(self, user_id: int, session_id: int) -> None:
        """Set a different session as the user's active session.

        Args:
            user_id: Telegram user ID that owns the session.
            session_id: Numeric ID of the session to activate.

        Raises:
            SessionError: If the session does not exist for this user.
        """
        logger.debug("switch_session user_id=%d -> session_id=%d", user_id, session_id)
        if session_id not in self._sessions.get(user_id, {}):
            raise SessionError(f"Session {session_id} not found")
        self._active[user_id] = session_id

    def list_sessions(self, user_id: int) -> list[ClaudeSession]:
        """Return all sessions belonging to a user.

        Args:
            user_id: Telegram user ID to look up.

        Returns:
            List of ClaudeSession instances, possibly empty.
        """
        return list(self._sessions.get(user_id, {}).values())

    async def kill_session(self, user_id: int, session_id: int) -> None:
        """Terminate a session, clean up resources, and persist the outcome.

        The underlying Claude process is terminated, database records are
        finalized, and session file artifacts are removed. If other sessions
        remain for the user, one is promoted to active.

        Args:
            user_id: Telegram user ID that owns the session.
            session_id: Numeric ID of the session to kill.

        Raises:
            SessionError: If the session does not exist for this user.
        """
        logger.debug("kill_session user_id=%d session_id=%d", user_id, session_id)
        session = self._sessions.get(user_id, {}).get(session_id)
        if session is None:
            raise SessionError(f"Session {session_id} not found")

        await session.process.terminate()
        exit_code = session.process.exit_code()
        session.status = "dead"

        await self._db.end_session(
            session.db_session_id, exit_code=exit_code, status="ended"
        )
        self._file_handler.cleanup_session(session.project_name, session_id)
        del self._sessions[user_id][session_id]

        # Auto-promote another session to active so user isn't left with no active session
        remaining = self._sessions.get(user_id, {})
        if remaining:
            self._active[user_id] = next(iter(remaining))
        else:
            self._active.pop(user_id, None)

    async def shutdown(self) -> None:
        """Terminate all active sessions. Used during bot shutdown."""
        for user_sessions in list(self._sessions.values()):
            for session in list(user_sessions.values()):
                await session.process.terminate()
        self._sessions.clear()
        self._active.clear()

    def has_active_sessions(self) -> bool:
        """Check whether any user has at least one live session.

        Returns:
            True if one or more sessions exist across all users.
        """
        return any(len(s) > 0 for s in self._sessions.values())

    def active_session_count(self) -> int:
        """Return the total number of live sessions across all users.

        Returns:
            Count of sessions currently tracked by the manager.
        """
        return sum(len(s) for s in self._sessions.values())


class OutputBuffer:
    """Accumulate incremental output and flush when ready."""

    def __init__(self, debounce_ms: int, max_buffer: int) -> None:
        """Initialize the output buffer.

        Args:
            debounce_ms: Minimum quiet period in milliseconds before
                the buffer is considered ready to flush.
            max_buffer: Character count threshold that forces an
                immediate flush regardless of the debounce timer.
        """
        self._debounce_s = debounce_ms / 1000.0
        self._max_buffer = max_buffer
        self._buffer: str = ""
        self._last_append: float = 0

    def append(self, text: str) -> None:
        """Add text to the internal buffer and reset the debounce timer.

        Args:
            text: Output fragment to accumulate.
        """
        self._buffer += text
        self._last_append = time.monotonic()
        logger.log(TRACE, "OutputBuffer append len=%d total=%d", len(text), len(self._buffer))

    def flush(self) -> str:
        """Drain the buffer and return its contents.

        Returns:
            The accumulated text. The buffer is empty after this call.
        """
        result = self._buffer
        logger.debug("OutputBuffer flush len=%d", len(result))
        self._buffer = ""
        self._last_append = 0
        return result

    def is_ready(self) -> bool:
        """Check whether the buffer should be flushed.

        The buffer is ready when it exceeds the max size limit or when
        the debounce period has elapsed since the last append.

        Returns:
            True if the buffer has content that should be flushed.
        """
        if not self._buffer:
            return False
        # Force-flush large bursts immediately, even if debounce hasn't elapsed
        if len(self._buffer) >= self._max_buffer:
            return True
        if self._last_append and (time.monotonic() - self._last_append) >= self._debounce_s:
            return True
        return False
