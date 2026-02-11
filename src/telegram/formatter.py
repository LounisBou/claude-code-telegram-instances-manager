from __future__ import annotations

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
