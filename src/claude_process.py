from __future__ import annotations

import asyncio
import logging

import pexpect

logger = logging.getLogger(__name__)


class ClaudeProcess:
    """Async wrapper around a pexpect-managed Claude Code CLI subprocess.

    Manages the full lifecycle of a Claude Code PTY process: spawning,
    reading output, writing input, and termination. Uses pexpect for
    PTY management and asyncio executors for non-blocking I/O.
    """

    def __init__(self, command: str, args: list[str], cwd: str) -> None:
        """Initialize a ClaudeProcess without spawning it.

        Args:
            command: The CLI command to execute (e.g. "claude").
            args: List of command-line arguments to pass.
            cwd: Working directory in which to spawn the process.
        """
        self._command = command
        self._args = args
        self._cwd = cwd
        self._process: pexpect.spawn | None = None
        self._buffer: str = ""

    async def spawn(self) -> None:
        """Spawn the Claude Code CLI process in a PTY.

        Builds the full command string from the stored command and args,
        then creates a pexpect.spawn instance on a background thread
        to avoid blocking the event loop.
        """
        cmd = self._command
        if self._args:
            cmd = f"{self._command} {' '.join(self._args)}"
        loop = asyncio.get_event_loop()
        self._process = await loop.run_in_executor(
            None,
            lambda: pexpect.spawn(
                cmd,
                cwd=self._cwd,
                encoding="utf-8",
                timeout=5,
                maxread=4096,
            ),
        )

    def is_alive(self) -> bool:
        """Check whether the underlying PTY process is still running.

        Returns:
            True if the process has been spawned and is alive,
            False otherwise.
        """
        if self._process is None:
            return False
        return self._process.isalive()

    async def write(self, text: str) -> None:
        """Send text to the process stdin via the PTY.

        Does nothing if the process is not alive. Runs the write
        on a background thread to avoid blocking the event loop.

        Args:
            text: The string to send to the process.
        """
        if not self.is_alive():
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._process.send, text)

    def read_available(self) -> str:
        """Read all currently available output from the PTY buffer.

        Drains the PTY read buffer in a non-blocking loop, appending
        chunks to the internal buffer. Returns and clears the
        accumulated content. Safe to call when no output is available.

        Returns:
            All accumulated output since the last read, or an empty
            string if nothing is available or the process is not spawned.
        """
        if self._process is None:
            return ""
        try:
            while True:
                try:
                    chunk = self._process.read_nonblocking(size=4096, timeout=0)
                    self._buffer += chunk
                except pexpect.TIMEOUT:
                    break
                except pexpect.EOF:
                    break
        except Exception as exc:
            logger.warning("Unexpected error draining PTY buffer: %s", exc)
        result = self._buffer
        self._buffer = ""
        return result

    async def terminate(self) -> None:
        """Terminate the PTY process if it is still alive.

        Calls pexpect close with force=True on a background thread.
        Does nothing if the process was never spawned.
        """
        if self._process is None:
            return
        loop = asyncio.get_event_loop()
        if self._process.isalive():
            await loop.run_in_executor(None, self._process.close, True)

    def exit_code(self) -> int | None:
        """Return the exit code or signal number of the terminated process.

        Prefers exitstatus (normal exit) over signalstatus (killed by
        signal). Returns None if the process was never spawned or has
        neither status set.

        Returns:
            The integer exit code, the signal number that killed the
            process, or None if unavailable.
        """
        if self._process is None:
            return None
        # pexpect sets signalstatus (not exitstatus) when process is killed by signal
        if self._process.exitstatus is not None:
            return self._process.exitstatus
        return self._process.signalstatus
