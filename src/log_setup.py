from __future__ import annotations

import logging
import os
from datetime import datetime

TRACE = 5
TRACE_DIR = "debug"

logging.addLevelName(TRACE, "TRACE")


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = _trace

_CONSOLE_FMT = "%(levelname)s %(name)s: %(message)s"
_FILE_FMT = "%(asctime)s.%(msecs)03d %(levelname)s %(name)s:%(funcName)s:%(lineno)d %(message)s"
_FILE_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    *, debug: bool, trace: bool, verbose: bool
) -> logging.Logger:
    root = logging.getLogger("claude-bot")
    root.handlers.clear()
    root.setLevel(TRACE)

    # Console handler
    console = logging.StreamHandler()
    if trace and verbose:
        console.setLevel(TRACE)
    elif debug or trace:
        console.setLevel(logging.DEBUG)
    else:
        console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_CONSOLE_FMT))
    root.addHandler(console)

    # File handler (trace only)
    if trace:
        os.makedirs(TRACE_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        filepath = os.path.join(TRACE_DIR, f"trace-{timestamp}.log")
        fh = logging.FileHandler(filepath)
        fh.setLevel(TRACE)
        fh.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_FILE_DATEFMT))
        root.addHandler(fh)

    return root
