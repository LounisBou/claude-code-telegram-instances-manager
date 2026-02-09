from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.claude_process import ClaudeProcess
from src.database import Database
from src.file_handler import FileHandler


class SessionError(Exception):
    pass


@dataclass
class ClaudeSession:
    session_id: int
    user_id: int
    project_name: str
    project_path: str
    process: ClaudeProcess
    status: str = "active"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    db_session_id: int = 0


class SessionManager:
    def __init__(
        self,
        claude_command: str,
        claude_args: list[str],
        max_per_user: int,
        db: Database,
        file_handler: FileHandler,
    ) -> None:
        self._command = claude_command
        self._args = claude_args
        self._max_per_user = max_per_user
        self._db = db
        self._file_handler = file_handler
        # {user_id: {session_id: ClaudeSession}}
        self._sessions: dict[int, dict[int, ClaudeSession]] = {}
        # {user_id: active_session_id}
        self._active: dict[int, int] = {}
        self._next_id: dict[int, int] = {}

    async def create_session(
        self, user_id: int, project_name: str, project_path: str
    ) -> ClaudeSession:
        user_sessions = self._sessions.get(user_id, {})
        if len(user_sessions) >= self._max_per_user:
            raise SessionError(
                f"Session limit reached ({self._max_per_user}). "
                f"Kill a session first."
            )

        session_id = self._next_id.get(user_id, 1)
        self._next_id[user_id] = session_id + 1

        process = ClaudeProcess(
            command=self._command, args=self._args, cwd=project_path
        )
        await process.spawn()

        db_id = await self._db.create_session(
            user_id=user_id, project=project_name, project_path=project_path
        )

        session = ClaudeSession(
            session_id=session_id,
            user_id=user_id,
            project_name=project_name,
            project_path=project_path,
            process=process,
            db_session_id=db_id,
        )

        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        self._sessions[user_id][session_id] = session
        self._active[user_id] = session_id

        return session

    def get_active_session(self, user_id: int) -> ClaudeSession | None:
        active_id = self._active.get(user_id)
        if active_id is None:
            return None
        return self._sessions.get(user_id, {}).get(active_id)

    def switch_session(self, user_id: int, session_id: int) -> None:
        if session_id not in self._sessions.get(user_id, {}):
            raise SessionError(f"Session {session_id} not found")
        self._active[user_id] = session_id

    def list_sessions(self, user_id: int) -> list[ClaudeSession]:
        return list(self._sessions.get(user_id, {}).values())

    async def kill_session(self, user_id: int, session_id: int) -> None:
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

        remaining = self._sessions.get(user_id, {})
        if remaining:
            self._active[user_id] = next(iter(remaining))
        else:
            self._active.pop(user_id, None)

    def has_active_sessions(self) -> bool:
        return any(len(s) > 0 for s in self._sessions.values())

    def active_session_count(self) -> int:
        return sum(len(s) for s in self._sessions.values())


class OutputBuffer:
    def __init__(self, debounce_ms: int, max_buffer: int) -> None:
        self._debounce_s = debounce_ms / 1000.0
        self._max_buffer = max_buffer
        self._buffer: str = ""
        self._last_append: float = 0

    def append(self, text: str) -> None:
        self._buffer += text
        self._last_append = time.monotonic()

    def flush(self) -> str:
        result = self._buffer
        self._buffer = ""
        self._last_append = 0
        return result

    def is_ready(self) -> bool:
        if not self._buffer:
            return False
        if len(self._buffer) >= self._max_buffer:
            return True
        if self._last_append and (time.monotonic() - self._last_append) >= self._debounce_s:
            return True
        return False
