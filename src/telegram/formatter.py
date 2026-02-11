from __future__ import annotations

import html as _html_mod
import re


# --- Telegram formatting ---

_TG_ESCAPE_CHARS = r"_*[]()~`>#+-=|{}.!\\"
_TG_ESCAPE_RE = re.compile(r"([" + re.escape(_TG_ESCAPE_CHARS) + r"])")

_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _escape_telegram(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2 format.

    Args:
        text: Plain text to escape.

    Returns:
        Text with all Telegram MarkdownV2 special characters backslash-escaped.
    """
    return _TG_ESCAPE_RE.sub(r"\\\1", text)


def format_telegram(text: str) -> str:
    """Convert markdown text to Telegram MarkdownV2 format.

    Preserves code blocks and inline code verbatim while escaping special
    characters in surrounding text. Converts **bold** and *italic*
    markers to Telegram equivalents.

    Args:
        text: Markdown-formatted text to convert.

    Returns:
        Telegram MarkdownV2-formatted string ready for the Bot API.
        Empty string if input is empty.
    """
    if not text:
        return ""

    code_blocks: list[tuple[str, str]] = []
    inline_codes: list[str] = []

    # Replace code blocks/inline code with NUL-byte placeholders before escaping,
    # then restore them after — this protects code content from being escaped
    def _save_block(match: re.Match) -> str:
        idx = len(code_blocks)
        code_blocks.append((match.group(1), match.group(2)))
        return f"\x00CODEBLOCK{idx}\x00"

    def _save_inline(match: re.Match) -> str:
        idx = len(inline_codes)
        inline_codes.append(match.group(1))
        return f"\x00INLINE{idx}\x00"

    result = _CODE_BLOCK_RE.sub(_save_block, text)
    result = _INLINE_CODE_RE.sub(_save_inline, result)

    result = _BOLD_RE.sub(lambda m: f"\x00BOLDOPEN{m.group(1)}\x00BOLDCLOSE", result)
    result = _ITALIC_RE.sub(lambda m: f"\x00ITALICOPEN{m.group(1)}\x00ITALICCLOSE", result)

    result = _escape_telegram(result)

    result = result.replace("\x00BOLDOPEN", "*").replace("\x00BOLDCLOSE", "*")
    result = result.replace("\x00ITALICOPEN", "_").replace("\x00ITALICCLOSE", "_")

    for idx, (lang, code) in enumerate(code_blocks):
        placeholder = _escape_telegram(f"\x00CODEBLOCK{idx}\x00")
        result = result.replace(placeholder, f"```{lang}\n{code}```")

    for idx, code in enumerate(inline_codes):
        placeholder = _escape_telegram(f"\x00INLINE{idx}\x00")
        result = result.replace(placeholder, f"`{code}`")

    return result


# Patterns that indicate a line starts a new block (should NOT be joined to previous)
_BLOCK_START_RE = re.compile(
    r"^(?:"
    r"[-*•]\s"           # unordered list
    r"|\d+[.)]\s"        # ordered list
    r"|#+\s"             # heading
    r"|\|"               # table row
    r"|```"              # code fence
    r"|>\ "              # blockquote
    r"|Key components:"  # common label lines
    r")"
)


def reflow_text(text: str) -> str:
    """Reflow terminal-wrapped text into natural paragraphs for Telegram.

    Joins continuation lines (caused by pyte's fixed-width terminal) with
    spaces, while preserving intentional structure: blank lines, list items,
    table rows, code fences, and headings.

    Args:
        text: Content extracted from the terminal with hard line wraps.

    Returns:
        Reflowed text suitable for Telegram display.
    """
    if not text:
        return ""

    lines = text.split("\n")
    result: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Preserve blank lines as paragraph separators
        if not line.strip():
            result.append("")
            i += 1
            continue

        # Preserve code fences and their content verbatim
        if line.strip().startswith("```"):
            result.append(line)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                result.append(lines[i])
                i += 1
            if i < len(lines):
                result.append(lines[i])
                i += 1
            continue

        # Start accumulating a paragraph
        paragraph = line

        # Join subsequent lines that look like continuations
        while i + 1 < len(lines):
            next_line = lines[i + 1]

            # Stop joining at blank lines
            if not next_line.strip():
                break

            # Stop joining at block-start patterns
            if _BLOCK_START_RE.match(next_line.strip()):
                break

            # Stop joining at code fences
            if next_line.strip().startswith("```"):
                break

            # If current line ends with a colon, it's a label — don't join
            if paragraph.rstrip().endswith(":"):
                break

            # Join the continuation line
            paragraph = paragraph.rstrip() + " " + next_line.strip()
            i += 1

        result.append(paragraph)
        i += 1

    return "\n".join(result)


TELEGRAM_MAX_LENGTH = 4096


def split_message(text: str, max_length: int = TELEGRAM_MAX_LENGTH) -> list[str]:
    """Split a long message into chunks that fit within Telegram's limit.

    Splits preferring double-newline paragraph breaks, then single
    newlines, then spaces, falling back to hard cuts at max_length.

    Args:
        text: The message text to split.
        max_length: Maximum character length per chunk. Defaults to
            TELEGRAM_MAX_LENGTH (4096).

    Returns:
        List of message chunks. Returns [text] if it already fits
        (including empty strings).
    """
    if not text or len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        split_at = remaining.rfind("\n\n", 0, max_length)

        if split_at == -1:
            split_at = remaining.rfind("\n", 0, max_length)

        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_length)

        if split_at == -1:
            split_at = max_length

        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()

    return chunks if chunks else [""]


# --- Telegram HTML formatting ---

def _escape_html(text: str) -> str:
    """Escape HTML special characters: <, >, &.

    Args:
        text: Plain text to escape.

    Returns:
        Text with ``<``, ``>``, and ``&`` replaced by HTML entities.
    """
    return _html_mod.escape(text, quote=False)


# Patterns for format_html
_MD_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_MD_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_LABEL_DASH_RE = re.compile(r"^- (.+?) — (.+)$", re.MULTILINE)
_PLAIN_DASH_RE = re.compile(r"^- (.+)$", re.MULTILINE)
_SECTION_HEADER_RE = re.compile(r"^([A-Z][^:\n]{2,50}):$", re.MULTILINE)


def format_html(text: str) -> str:
    """Convert reflowed plain text to Telegram HTML.

    Handles: bold, italic, inline code, code blocks, list items
    with label--description, section headers, and HTML escaping.

    Processing order:
      1. Extract code blocks and inline code (protect from escaping).
      2. Extract bold and italic markers.
      3. Escape HTML in remaining text.
      4. Restore bold/italic with ``<b>``/``<i>`` tags.
      5. Restore code blocks with ``<pre><code>``.
      6. Restore inline code with ``<code>``.
      7. Convert list items (``- label -- desc`` and ``- item``).
      8. Bold section headers (``Word(s):`` alone on a line).

    Args:
        text: Reflowed text from :func:`reflow_text`.

    Returns:
        Telegram HTML-formatted string. Empty string if input is empty.
    """
    if not text:
        return ""

    # 1. Extract code blocks and inline code before escaping
    code_blocks: list[tuple[str, str]] = []
    inline_codes: list[str] = []

    def _save_block(match: re.Match) -> str:
        idx = len(code_blocks)
        code_blocks.append((match.group(1), match.group(2)))
        return f"\x00HTMLBLOCK{idx}\x00"

    def _save_inline(match: re.Match) -> str:
        idx = len(inline_codes)
        inline_codes.append(match.group(1))
        return f"\x00HTMLINLINE{idx}\x00"

    result = _MD_CODE_BLOCK_RE.sub(_save_block, text)
    result = _MD_INLINE_CODE_RE.sub(_save_inline, result)

    # 2. Extract bold and italic before escaping
    bolds: list[str] = []
    italics: list[str] = []

    def _save_bold(match: re.Match) -> str:
        idx = len(bolds)
        bolds.append(match.group(1))
        return f"\x00HTMLBOLD{idx}\x00"

    def _save_italic(match: re.Match) -> str:
        idx = len(italics)
        italics.append(match.group(1))
        return f"\x00HTMLITALIC{idx}\x00"

    result = _MD_BOLD_RE.sub(_save_bold, result)
    result = _MD_ITALIC_RE.sub(_save_italic, result)

    # 3. Escape HTML in remaining text
    result = _escape_html(result)

    # 4. Restore bold/italic with HTML tags (content also escaped)
    for idx, content in enumerate(bolds):
        result = result.replace(
            f"\x00HTMLBOLD{idx}\x00", f"<b>{_escape_html(content)}</b>"
        )

    for idx, content in enumerate(italics):
        result = result.replace(
            f"\x00HTMLITALIC{idx}\x00", f"<i>{_escape_html(content)}</i>"
        )

    # 5. Restore code blocks
    for idx, (lang, code) in enumerate(code_blocks):
        escaped_code = _escape_html(code)
        if lang:
            replacement = (
                f'<pre><code class="language-{_escape_html(lang)}">'
                f"{escaped_code}</code></pre>"
            )
        else:
            replacement = f"<pre><code>{escaped_code}</code></pre>"
        result = result.replace(f"\x00HTMLBLOCK{idx}\x00", replacement)

    # 6. Restore inline code
    for idx, code in enumerate(inline_codes):
        result = result.replace(
            f"\x00HTMLINLINE{idx}\x00", f"<code>{_escape_html(code)}</code>"
        )

    # 7. List items: label — description (must run before plain dash)
    def _label_replace(m: re.Match) -> str:
        label = m.group(1)
        desc = m.group(2)
        # Skip wrapping if bold was already applied (avoids nested <b> tags)
        if "<b>" in label:
            return f"• {label} — {desc}"
        return f"• <b>{label}</b> — {desc}"

    result = _LABEL_DASH_RE.sub(_label_replace, result)
    # Plain list items
    result = _PLAIN_DASH_RE.sub(lambda m: f"• {m.group(1)}", result)

    # 8. Section headers (line = "Word(s):" alone on a line)
    # Only match lines that don't contain :// (URLs)
    def _header_replace(m: re.Match) -> str:
        line = m.group(0)
        if "://" in line:
            return line
        return f"<b>{m.group(1)}:</b>"

    result = _SECTION_HEADER_RE.sub(_header_replace, result)

    return result
