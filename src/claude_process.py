from __future__ import annotations

import asyncio

import pexpect


class ClaudeProcess:
    def __init__(self, command: str, args: list[str], cwd: str) -> None:
        self._command = command
        self._args = args
        self._cwd = cwd
        self._process: pexpect.spawn | None = None
        self._buffer: str = ""

    async def spawn(self) -> None:
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
        if self._process is None:
            return False
        return self._process.isalive()

    async def write(self, text: str) -> None:
        if not self.is_alive():
            return
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._process.send, text)

    def read_available(self) -> str:
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
        except Exception:
            pass
        result = self._buffer
        self._buffer = ""
        return result

    async def terminate(self) -> None:
        if self._process is None:
            return
        loop = asyncio.get_event_loop()
        if self._process.isalive():
            await loop.run_in_executor(None, self._process.close, True)

    def exit_code(self) -> int | None:
        if self._process is None:
            return None
        if self._process.exitstatus is not None:
            return self._process.exitstatus
        return self._process.signalstatus
