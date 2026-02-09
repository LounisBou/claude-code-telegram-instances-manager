from __future__ import annotations

import asyncio

import pytest

from src.claude_process import ClaudeProcess


class TestClaudeProcess:
    @pytest.mark.asyncio
    async def test_spawn_and_read(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        assert proc.is_alive()
        await proc.write("hello\n")
        await asyncio.sleep(0.2)
        output = proc.read_available()
        assert "hello" in output
        await proc.terminate()

    @pytest.mark.asyncio
    async def test_terminate(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        assert proc.is_alive()
        await proc.terminate()
        assert not proc.is_alive()

    @pytest.mark.asyncio
    async def test_exit_code_after_terminate(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        await proc.terminate()
        exit_code = proc.exit_code()
        assert exit_code is not None

    @pytest.mark.asyncio
    async def test_write_to_terminated_process(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        await proc.terminate()
        # Should not raise
        await proc.write("hello\n")

    @pytest.mark.asyncio
    async def test_read_from_empty_buffer(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        output = proc.read_available()
        assert isinstance(output, str)
        await proc.terminate()

    @pytest.mark.asyncio
    async def test_cwd_is_set(self, tmp_path):
        proc = ClaudeProcess(command="pwd", args=[], cwd=str(tmp_path))
        await proc.spawn()
        await asyncio.sleep(0.3)
        output = proc.read_available()
        assert str(tmp_path) in output or "tmp" in output

    @pytest.mark.asyncio
    async def test_not_spawned_is_not_alive(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        assert not proc.is_alive()

    @pytest.mark.asyncio
    async def test_read_before_spawn(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        assert proc.read_available() == ""

    @pytest.mark.asyncio
    async def test_exit_code_before_spawn(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        assert proc.exit_code() is None

    @pytest.mark.asyncio
    async def test_spawn_with_args(self):
        proc = ClaudeProcess(command="echo", args=["hello", "world"], cwd="/tmp")
        await proc.spawn()
        await asyncio.sleep(0.2)
        output = proc.read_available()
        assert "hello world" in output
