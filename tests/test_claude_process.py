from __future__ import annotations

import asyncio
import logging

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


class TestBuildEnv:
    def test_merges_extra_vars(self):
        env = ClaudeProcess._build_env({"MY_VAR": "hello"})
        assert env["MY_VAR"] == "hello"
        # Inherits existing env
        assert "PATH" in env

    def test_expands_tilde_in_values(self):
        import os
        env = ClaudeProcess._build_env({"MY_DIR": "~/.my-config"})
        expected = os.path.expanduser("~/.my-config")
        assert env["MY_DIR"] == expected
        assert "~" not in env["MY_DIR"]

    def test_no_tilde_left_unchanged(self):
        env = ClaudeProcess._build_env({"FOO": "/absolute/path"})
        assert env["FOO"] == "/absolute/path"

    def test_empty_extra_returns_environ_copy(self):
        import os
        env = ClaudeProcess._build_env({})
        assert env == os.environ.copy()

    def test_env_passed_to_pexpect(self):
        proc = ClaudeProcess(
            command="echo", args=[], cwd="/tmp",
            env={"CLAUDE_CONFIG_DIR": "~/.claude-work"},
        )
        assert "CLAUDE_CONFIG_DIR" in proc._env
        assert "~" not in proc._env["CLAUDE_CONFIG_DIR"]


class TestSubmit:
    @pytest.mark.asyncio
    async def test_submit_sends_text_then_cr(self):
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        await proc.spawn()
        await proc.submit("hello")
        await asyncio.sleep(0.3)
        output = proc.read_available()
        # Both the text and the carriage return should have been received
        assert "hello" in output
        await proc.terminate()

    @pytest.mark.asyncio
    async def test_submit_calls_write_twice(self):
        """submit() must send text and \\r as two separate writes."""
        proc = ClaudeProcess(command="cat", args=[], cwd="/tmp")
        calls = []
        async def mock_write(text):
            calls.append(text)
        proc.write = mock_write
        await proc.submit("test msg")
        assert len(calls) == 2
        assert calls[0] == "test msg"
        assert calls[1] == "\r"


class TestClaudeProcessLogging:
    @pytest.mark.asyncio
    async def test_spawn_logs_command(self, caplog):
        from src.log_setup import setup_logging
        setup_logging(debug=True, trace=False, verbose=False)
        proc = ClaudeProcess(command="echo", args=["hello"], cwd="/tmp")
        with caplog.at_level(logging.DEBUG, logger="src.claude_process"):
            await proc.spawn()
        assert any("spawn" in r.message.lower() for r in caplog.records)
        await proc.terminate()
