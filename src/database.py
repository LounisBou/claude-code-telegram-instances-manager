from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    project      TEXT NOT NULL,
    project_path TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    exit_code    INTEGER,
    status       TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
"""


class Database:
    """Async SQLite wrapper for managing Claude Code session records.

    Provides methods to create, query, and update session rows
    that track a user's Claude Code interactions within a project.
    """

    def __init__(self, path: str) -> None:
        """Initialize the database handle without opening a connection.

        Args:
            path: Filesystem path to the SQLite database file.
        """
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Open the database connection and ensure the schema exists.

        Creates the sessions table and its indexes if they do not
        already exist, then commits the transaction.
        """
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection if one is open."""
        if self._db:
            await self._db.close()

    async def create_session(
        self, user_id: int, project: str, project_path: str
    ) -> int:
        """Insert a new active session row and return its ID.

        Args:
            user_id: Telegram user ID that owns this session.
            project: Human-readable project name.
            project_path: Absolute filesystem path to the project root.

        Returns:
            Auto-incremented row ID of the newly created session.
        """
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._db.execute(
            "INSERT INTO sessions (user_id, project, project_path, started_at, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (user_id, project, project_path, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_session(self, session_id: int) -> dict | None:
        """Fetch a single session by its primary key.

        Args:
            session_id: Primary key of the session row.

        Returns:
            Dict of column values if the session exists, None otherwise.
        """
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def end_session(
        self, session_id: int, exit_code: int | None, status: str
    ) -> None:
        """Mark a session as finished by setting its end timestamp and status.

        Args:
            session_id: Primary key of the session to end.
            exit_code: Process exit code, or None if the process was lost.
            status: Final status string (e.g. 'completed', 'lost', 'error').
        """
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE sessions SET ended_at = ?, exit_code = ?, status = ? WHERE id = ?",
            (now, exit_code, status, session_id),
        )
        await self._db.commit()

    async def list_sessions(self, user_id: int) -> list[dict]:
        """Return all sessions for a given user, newest first.

        Args:
            user_id: Telegram user ID whose sessions to retrieve.

        Returns:
            List of session dicts ordered by descending ID.
        """
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def mark_active_sessions_lost(self) -> list[dict]:
        """Transition every active session to 'lost' status.

        Used during startup to clean up sessions that were still
        active when the bot previously shut down or crashed.

        Returns:
            List of session dicts that were marked as lost.
        """
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE status = 'active'"
        )
        rows = await cursor.fetchall()
        lost = [dict(r) for r in rows]
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE sessions SET status = 'lost', ended_at = ? WHERE status = 'active'",
            (now,),
        )
        await self._db.commit()
        return lost
