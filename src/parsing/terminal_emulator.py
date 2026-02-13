from __future__ import annotations

import re
from dataclasses import dataclass

import pyte

# Colors that indicate syntax-highlighted code in Claude Code's TUI.
CODE_FG_COLORS: frozenset[str] = frozenset({
    "blue",       # keywords: def, import, class, return, ...
    "red",        # string literals: "hello", '''docstring'''
    "cyan",       # builtins: print, len, range, ...
    "brown",      # identifiers / function names
    "green",      # some literals, boolean True/False
    "lightblue",  # alternate keyword highlighting
    "lightred",   # alternate string highlighting
    "lightcyan",  # alternate builtin highlighting
    "lightgreen", # alternate literal highlighting
})


@dataclass(frozen=True, slots=True)
class CharSpan:
    """A contiguous run of characters sharing the same terminal attributes.

    Used by :meth:`TerminalEmulator.get_attributed_lines` to expose pyte's
    per-character styling as coarser, easier-to-process spans.

    Attributes:
        text: The character data for this span.
        fg: Normalized foreground color name (e.g. ``"default"``, ``"blue"``).
        bold: Whether the span is rendered in bold.
        italic: Whether the span is rendered in italic.
    """

    text: str
    fg: str = "default"
    bold: bool = False
    italic: bool = False


class TerminalEmulator:
    """Virtual terminal using pyte to reconstruct screen from raw PTY bytes.

    This is the core of output parsing: instead of regex-stripping ANSI codes,
    we feed raw PTY bytes into a real terminal emulator and read the screen buffer.
    """

    def __init__(self, rows: int = 40, cols: int = 120):
        """Initialize the terminal emulator with a virtual screen.

        Uses ``pyte.HistoryScreen`` so that lines scrolled off the top of
        the visible area are preserved in a scrollback buffer. This is
        critical for fast responses that exceed the screen height — without
        history, the beginning of the response would be irretrievably lost.

        Args:
            rows: Number of rows in the virtual terminal. Defaults to 40.
            cols: Number of columns in the virtual terminal. Defaults to 120.
        """
        self.rows = rows
        self.cols = cols
        self.screen = pyte.HistoryScreen(cols, rows, history=1000)
        self.stream = pyte.Stream(self.screen)
        self._prev_display: list[str] = [""] * rows

    def feed(self, data: bytes | str) -> None:
        """Feed raw PTY bytes into the terminal emulator.

        Args:
            data: Raw bytes or a string from the PTY. Bytes are decoded
                as UTF-8 with replacement characters for invalid sequences.
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        self.stream.feed(data)

    def get_display(self) -> list[str]:
        """Return all screen lines, right-stripped of trailing whitespace.

        Returns:
            List of strings, one per terminal row.
        """
        return [line.rstrip() for line in self.screen.display]

    def get_full_display(self) -> list[str]:
        """Return all screen lines **plus** scrollback history.

        Lines that scrolled off the top of the visible area are prepended
        (oldest first) to the current display. This gives a complete view
        of everything written to the terminal since the last ``reset()``,
        up to the configured history limit (1 000 lines).

        Returns:
            List of strings: scrollback history followed by current display,
            each right-stripped of trailing whitespace.
        """
        history_lines: list[str] = []
        for row in self.screen.history.top:
            rendered = "".join(
                row[col].data for col in range(self.cols)
            ).rstrip()
            history_lines.append(rendered)
        return history_lines + self.get_display()

    def clear_history(self) -> None:
        """Discard the scrollback history buffer.

        Useful after content has been extracted from the full display
        to prevent the same history lines from being re-read.
        """
        self.screen.history.top.clear()

    # --- Attributed display methods ---

    @staticmethod
    def _row_to_spans(row: dict, cols: int) -> list[CharSpan]:
        """Convert a pyte buffer row (dict of col→Char) into CharSpan list.

        Adjacent characters with identical ``(fg, bold, italics)`` attributes
        are merged into a single span.  Trailing whitespace-only spans are
        dropped to mirror :meth:`get_display` behaviour.

        Args:
            row: A pyte screen buffer row (``screen.buffer[y]``) or a
                history row (``screen.history.top[i]``).
            cols: Number of columns in the terminal.

        Returns:
            List of :class:`CharSpan` objects, with trailing blank spans
            removed.
        """
        spans: list[CharSpan] = []
        cur_text: list[str] = []
        cur_fg: str = "default"
        cur_bold: bool = False
        cur_italic: bool = False

        for col in range(cols):
            char = row[col]
            fg = char.fg if char.fg else "default"
            bold = bool(char.bold)
            italic = bool(char.italics)

            if fg == cur_fg and bold == cur_bold and italic == cur_italic:
                cur_text.append(char.data)
            else:
                if cur_text:
                    spans.append(CharSpan(
                        text="".join(cur_text),
                        fg=cur_fg,
                        bold=cur_bold,
                        italic=cur_italic,
                    ))
                cur_text = [char.data]
                cur_fg = fg
                cur_bold = bold
                cur_italic = italic

        if cur_text:
            spans.append(CharSpan(
                text="".join(cur_text),
                fg=cur_fg,
                bold=cur_bold,
                italic=cur_italic,
            ))

        # Strip trailing whitespace-only spans (equivalent to rstrip)
        while spans and not spans[-1].text.strip():
            spans.pop()
        # Rstrip the last remaining span
        if spans:
            last = spans[-1]
            rstripped = last.text.rstrip()
            if rstripped != last.text:
                if rstripped:
                    spans[-1] = CharSpan(
                        text=rstripped,
                        fg=last.fg,
                        bold=last.bold,
                        italic=last.italic,
                    )
                else:
                    spans.pop()

        return spans

    def get_attributed_lines(self) -> list[list[CharSpan]]:
        """Return current screen lines as lists of attributed character spans.

        Each line is a list of :class:`CharSpan` objects representing
        contiguous runs of identically-styled characters.  Trailing
        whitespace spans are removed, matching :meth:`get_display`.

        Returns:
            List of lists of :class:`CharSpan`, one inner list per terminal
            row.
        """
        result: list[list[CharSpan]] = []
        for y in range(self.rows):
            result.append(self._row_to_spans(self.screen.buffer[y], self.cols))
        return result

    def get_full_attributed_lines(self) -> list[list[CharSpan]]:
        """Return scrollback history + current screen as attributed spans.

        Like :meth:`get_full_display` but preserving per-character styling
        information.  History rows in pyte store full ``Char`` objects, so
        attributes are not lost when lines scroll off the visible area.

        Returns:
            List of lists of :class:`CharSpan`: history lines first, then
            current screen lines.
        """
        result: list[list[CharSpan]] = []
        for row in self.screen.history.top:
            result.append(self._row_to_spans(row, self.cols))
        result.extend(self.get_attributed_lines())
        return result

    def get_attributed_changes(self) -> list[list[CharSpan]]:
        """Return attributed spans for lines that changed since last check.

        Combines the change-detection logic of :meth:`get_changes` with the
        attribute extraction of :meth:`get_attributed_lines`.  Only lines
        whose text content differs from the previous snapshot and is
        non-blank are returned.

        .. note::
            This also updates the internal previous-display snapshot, so
            :meth:`get_changes` and this method share state.

        Returns:
            List of lists of :class:`CharSpan` for changed, non-empty lines.
        """
        current_text = self.get_display()
        changed_indices: list[int] = []
        for i, (cur, prev) in enumerate(zip(current_text, self._prev_display)):
            if cur != prev and cur.strip():
                changed_indices.append(i)
        self._prev_display = list(current_text)

        if not changed_indices:
            return []

        result: list[list[CharSpan]] = []
        for i in changed_indices:
            result.append(self._row_to_spans(self.screen.buffer[i], self.cols))
        return result

    def get_text(self) -> str:
        """Return full screen content as text with blank lines collapsed.

        Runs of three or more newlines are reduced to double newlines, and
        leading/trailing whitespace is stripped.

        Returns:
            The reconstructed screen content as a single string.
        """
        lines = self.get_display()
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def get_changes(self) -> list[str]:
        """Return lines that changed since the last call to get_changes.

        Compares the current display against a saved snapshot and returns
        only lines whose content differs and is non-blank.

        Returns:
            List of changed, non-empty screen lines.
        """
        current = self.get_display()
        changed = []
        for i, (cur, prev) in enumerate(zip(current, self._prev_display)):
            if cur != prev and cur.strip():
                changed.append(cur)
        self._prev_display = list(current)
        return changed

    def get_new_content(self) -> str:
        """Return changed lines joined as a single string.

        Returns:
            Newline-joined string of lines that changed since last check,
            stripped of leading/trailing whitespace.
        """
        lines = self.get_changes()
        return "\n".join(lines).strip()

    def reset(self) -> None:
        """Reset the terminal to its initial blank state.

        Clears the pyte screen buffer, the scrollback history, and the
        internal previous-display snapshot used by get_changes.
        """
        self.screen.reset()
        self.screen.history.top.clear()
        self._prev_display = [""] * self.rows


# --- Spinner filtering ---

_BRAILLE_SPINNER = re.compile(r"[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*")
_DOTS_SPINNER = re.compile(r"^(.+?)\.{1,3}$", re.MULTILINE)


def filter_spinners(text: str) -> str:
    """Remove braille spinner characters and deduplicate trailing-dot variants.

    Strips braille spinner prefixes from lines, then collapses progressive
    dot sequences (e.g. "Loading.", "Loading..", "Loading...") into the
    longest variant only.

    Args:
        text: Raw text that may contain spinner artifacts.

    Returns:
        Cleaned text with spinners removed. Empty string if nothing remains.
    """
    if not text:
        return ""
    lines = text.split("\n")
    seen_spinners: dict[str, str] = {}
    result_lines = []

    for line in lines:
        stripped = _BRAILLE_SPINNER.sub("", line).strip()
        if stripped != line.strip() and stripped:
            seen_spinners[stripped] = stripped
            continue
        result_lines.append(line)

    for spinner_text in seen_spinners.values():
        result_lines.append(spinner_text)

    final_text = "\n".join(result_lines)
    dot_groups: dict[str, int] = {}
    for match in _DOTS_SPINNER.finditer(final_text):
        base = match.group(1).rstrip(".")
        dot_groups[base] = max(dot_groups.get(base, 0), len(match.group(0)) - len(base))

    for base, dot_count in dot_groups.items():
        if dot_count > 1:
            for i in range(1, dot_count):
                final_text = final_text.replace(f"{base}{'.' * i}\n", "")
            final_text = final_text.strip()

    return final_text.strip() if final_text.strip() else ""


# --- Legacy helpers (kept for backward compat, delegate to pyte internally) ---

# Cursor forward: ESC[NC — replace with N spaces
_CURSOR_FORWARD_RE = re.compile(r"\x1b\[(\d+)C")

# All other ANSI sequences
_ANSI_FULL_RE = re.compile(
    r"\x1b"
    r"(?:"
    r"\[[0-9;]*[a-zA-Z]"
    r"|\][^\x07]*\x07"
    r"|\[[0-9;]*m"
    r"|\[\?[0-9;]*[a-zA-Z]"
    r"|>[0-9]*[a-zA-Z]"
    r"|<[a-zA-Z]"
    r")"
)


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes, converting cursor-forward to spaces.

    Handles ESC[NC (cursor forward) by replacing with the equivalent
    number of spaces, then removes all remaining ANSI sequences.

    Args:
        text: Raw terminal text containing ANSI escape codes.

    Returns:
        Text with all ANSI sequences removed and cursor-forward
        sequences replaced by spaces.
    """
    text = _CURSOR_FORWARD_RE.sub(lambda m: " " * int(m.group(1)), text)
    return _ANSI_FULL_RE.sub("", text)


def clean_terminal_output(text: str) -> str:
    """Clean raw terminal output using the pyte terminal emulator.

    Feeds the raw text through a virtual terminal and returns the
    reconstructed screen content with blank lines collapsed.

    Args:
        text: Raw terminal output potentially containing ANSI codes,
            cursor movements, and other control sequences.

    Returns:
        Cleaned screen content as a single string with collapsed blank
        lines and stripped whitespace.
    """
    emu = TerminalEmulator()
    emu.feed(text)
    return emu.get_text()
