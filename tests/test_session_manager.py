from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.session_manager import ClaudeSession, OutputBuffer, SessionError, SessionManager


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.create_session = AsyncMock(return_value=1)
    db.end_session = AsyncMock()
    return db


@pytest.fixture
def mock_file_handler():
    return MagicMock()


@pytest.fixture
def manager(mock_db, mock_file_handler):
    return SessionManager(
        claude_command="cat",
        claude_args=[],
        max_per_user=3,
        db=mock_db,
        file_handler=mock_file_handler,
    )


def _mock_process():
    mock_proc = AsyncMock()
    mock_proc.is_alive.return_value = True
    mock_proc.spawn = AsyncMock()
    mock_proc.terminate = AsyncMock()
    mock_proc.exit_code.return_value = 0
    return mock_proc


class TestSessionManager:
    @pytest.mark.asyncio
    async def test_create_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            session = await manager.create_session(
                user_id=111, project_name="proj", project_path="/a/proj"
            )
            assert session.user_id == 111
            assert session.project_name == "proj"
            assert session.status == "active"

    @pytest.mark.asyncio
    async def test_session_limit_enforced(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p1", "/a/p1")
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p2", "/a/p2")
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p3", "/a/p3")
            with pytest.raises(SessionError, match="limit"):
                await manager.create_session(111, "p4", "/a/p4")

    @pytest.mark.asyncio
    async def test_get_active_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            session = await manager.create_session(111, "proj", "/a/proj")
            active = manager.get_active_session(111)
            assert active is not None
            assert active.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_get_active_session_no_sessions(self, manager):
        assert manager.get_active_session(111) is None

    @pytest.mark.asyncio
    async def test_switch_session(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            s1 = await manager.create_session(111, "p1", "/a/p1")
            MockProc.return_value = _mock_process()
            s2 = await manager.create_session(111, "p2", "/a/p2")
            # Active should be s2 (last created)
            assert manager.get_active_session(111).session_id == s2.session_id
            manager.switch_session(111, s1.session_id)
            assert manager.get_active_session(111).session_id == s1.session_id

    @pytest.mark.asyncio
    async def test_switch_session_not_found(self, manager):
        with pytest.raises(SessionError, match="not found"):
            manager.switch_session(111, 99)

    @pytest.mark.asyncio
    async def test_list_sessions(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p1", "/a/p1")
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p2", "/a/p2")
            sessions = manager.list_sessions(111)
            assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, manager):
        assert manager.list_sessions(111) == []

    @pytest.mark.asyncio
    async def test_kill_session(self, manager, mock_db, mock_file_handler):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            session = await manager.create_session(111, "proj", "/a/proj")
            await manager.kill_session(111, session.session_id)
            assert len(manager.list_sessions(111)) == 0
            mock_db.end_session.assert_called_once()
            mock_file_handler.cleanup_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_kill_session_not_found(self, manager):
        with pytest.raises(SessionError, match="not found"):
            await manager.kill_session(111, 99)

    @pytest.mark.asyncio
    async def test_kill_switches_active(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            s1 = await manager.create_session(111, "p1", "/a/p1")
            MockProc.return_value = _mock_process()
            s2 = await manager.create_session(111, "p2", "/a/p2")
            # Active is s2, kill it
            await manager.kill_session(111, s2.session_id)
            # Should switch to s1
            active = manager.get_active_session(111)
            assert active is not None
            assert active.session_id == s1.session_id

    @pytest.mark.asyncio
    async def test_kill_last_session_clears_active(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            session = await manager.create_session(111, "proj", "/a/proj")
            await manager.kill_session(111, session.session_id)
            assert manager.get_active_session(111) is None

    @pytest.mark.asyncio
    async def test_different_users_independent(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p1", "/a/p1")
            MockProc.return_value = _mock_process()
            await manager.create_session(222, "p2", "/a/p2")
            assert len(manager.list_sessions(111)) == 1
            assert len(manager.list_sessions(222)) == 1

    @pytest.mark.asyncio
    async def test_has_active_sessions(self, manager):
        assert manager.has_active_sessions() is False
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "proj", "/a/proj")
            assert manager.has_active_sessions() is True

    @pytest.mark.asyncio
    async def test_active_session_count(self, manager):
        assert manager.active_session_count() == 0
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p1", "/a/p1")
            MockProc.return_value = _mock_process()
            await manager.create_session(222, "p2", "/a/p2")
            assert manager.active_session_count() == 2


class TestSessionManagerShutdown:
    """Regression: shutdown() must terminate all sessions and clear state."""

    @pytest.mark.asyncio
    async def test_shutdown_terminates_all_sessions(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            proc1 = _mock_process()
            proc2 = _mock_process()
            MockProc.side_effect = [proc1, proc2]
            await manager.create_session(111, "p1", "/a/p1")
            await manager.create_session(222, "p2", "/a/p2")

            await manager.shutdown()

            proc1.terminate.assert_called_once()
            proc2.terminate.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_clears_sessions(self, manager):
        with patch("src.session_manager.ClaudeProcess") as MockProc:
            MockProc.return_value = _mock_process()
            await manager.create_session(111, "p1", "/a/p1")

            await manager.shutdown()

            assert manager.list_sessions(111) == []
            assert manager.get_active_session(111) is None
            assert manager.active_session_count() == 0

    @pytest.mark.asyncio
    async def test_shutdown_empty_is_noop(self, manager):
        # Should not raise when no sessions exist
        await manager.shutdown()
        assert manager.active_session_count() == 0


class TestOutputBuffer:
    def test_buffer_accumulates(self):
        buf = OutputBuffer(debounce_ms=100, max_buffer=2000)
        buf.append("hello ")
        buf.append("world")
        text = buf.flush()
        assert text == "hello world"

    def test_flush_clears_buffer(self):
        buf = OutputBuffer(debounce_ms=100, max_buffer=2000)
        buf.append("hello")
        buf.flush()
        assert buf.flush() == ""

    def test_is_ready_after_debounce(self):
        import time as t

        buf = OutputBuffer(debounce_ms=50, max_buffer=2000)
        buf.append("data")
        assert buf.is_ready() is False
        t.sleep(0.06)
        assert buf.is_ready() is True

    def test_is_ready_when_max_buffer_exceeded(self):
        buf = OutputBuffer(debounce_ms=5000, max_buffer=10)
        buf.append("A" * 15)
        assert buf.is_ready() is True

    def test_empty_buffer_not_ready(self):
        buf = OutputBuffer(debounce_ms=100, max_buffer=2000)
        assert buf.is_ready() is False


class TestSessionManagerLogging:
    @pytest.mark.asyncio
    async def test_create_session_logs(self, caplog):
        from src.core.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        db = AsyncMock()
        db.create_session = AsyncMock(return_value=1)
        fh = MagicMock()
        sm = SessionManager(
            claude_command="echo", claude_args=[], max_per_user=3, db=db, file_handler=fh
        )
        with patch("src.session_manager.ClaudeProcess") as mock_cp:
            mock_cp.return_value.spawn = AsyncMock()
            with caplog.at_level(logging.DEBUG, logger="src.session_manager"):
                await sm.create_session(111, "test-project", "/tmp/test")
        assert any("create_session" in r.message for r in caplog.records)
