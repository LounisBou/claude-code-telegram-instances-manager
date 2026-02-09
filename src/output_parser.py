from __future__ import annotations

import re

_ANSI_FULL_RE = re.compile(
    r"\x1b"
    r"(?:"
    r"\[[0-9;]*[a-zA-Z]"
    r"|\][^\x07]*\x07"
    r"|\[[0-9;]*m"
    r")"
)


def strip_ansi(text: str) -> str:
    return _ANSI_FULL_RE.sub("", text)
