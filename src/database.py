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
    def __init__(self, path: str) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def create_session(
        self, user_id: int, project: str, project_path: str
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self._db.execute(
            "INSERT INTO sessions (user_id, project, project_path, started_at, status) "
            "VALUES (?, ?, ?, ?, 'active')",
            (user_id, project, project_path, now),
        )
        await self._db.commit()
        return cursor.lastrowid

    async def get_session(self, session_id: int) -> dict | None:
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def end_session(
        self, session_id: int, exit_code: int | None, status: str
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "UPDATE sessions SET ended_at = ?, exit_code = ?, status = ? WHERE id = ?",
            (now, exit_code, status, session_id),
        )
        await self._db.commit()

    async def list_sessions(self, user_id: int) -> list[dict]:
        cursor = await self._db.execute(
            "SELECT * FROM sessions WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def mark_active_sessions_lost(self) -> list[dict]:
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
