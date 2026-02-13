from __future__ import annotations

import html as _html_mod
import re

from src.parsing.content_classifier import ContentRegion



def render_regions(regions: list[ContentRegion]) -> str:
    """Convert classified content regions to markdown-annotated text.

    Produces text with standard markdown markers that :func:`format_html`
    can consume:

    - ``code_block`` → triple-backtick fenced code
    - ``prose`` → plain text (may contain backtick-wrapped inline code)
    - ``heading`` → ``**text**`` bold markers
    - ``list`` → preserved as-is (may contain backtick inline code)
    - ``separator`` → empty string (suppressed)
    - ``blank`` → empty line

    Code block regions preserve original indentation verbatim — no dedent
    and no reflow.

    Args:
        regions: Ordered list of :class:`ContentRegion` from
            :func:`~src.parsing.content_classifier.classify_regions`.

    Returns:
        Markdown-annotated text ready for :func:`reflow_text` and
        :func:`format_html`.
    """
    parts: list[str] = []

    for region in regions:
        if region.type == "code_block":
            lang = region.language or ""
            parts.append(f"```{lang}")
            parts.append(region.text)
            parts.append("```")
        elif region.type == "heading":
            parts.append(f"**{region.text}**")
        elif region.type == "separator":
            # Suppress visual separators — they're UI chrome
            continue
        elif region.type == "blank":
            parts.append("")
        else:
            # prose and list: text already has inline code backticks
            parts.append(region.text)

    return "\n".join(parts)


# Patterns that indicate a line starts a new block (should NOT be joined to previous)
_BLOCK_START_RE = re.compile(
    r"^(?:"
    r"[-*•]\s"           # unordered list
    r"|\d+[.)]\s"        # ordered list
    r"|#+\s"             # heading
    r"|\|"               # table row
    r"|```"              # code fence
    r"|>\ "              # blockquote
    r"|[A-Z]\w+:"        # capitalized label (Class:, Fields:, Purpose:)
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

            # Short lines are intentional breaks, not terminal wrapping.
            # pyte content area is ~80 chars (based on separator width).
            # Lines well below that are intentional line breaks (e.g. a
            # list without bullets, short phrases, single words).
            last_physical = paragraph.rsplit("\n", 1)[-1] if "\n" in paragraph else paragraph
            if len(last_physical.rstrip()) < 72:
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


# File path auto-link prevention.
# Telegram auto-links text matching TLD patterns (.py = Paraguay, .js, .io,
# etc.).  Wrapping file paths in backticks before code extraction lets the
# existing inline-code pipeline render them as <code>, which suppresses
# Telegram's auto-linking.
_TLD_EXTS = (
    r"py|js|ts|go|rs|sh|ai|me|so|do|cc|co|in|io|it|la|ph|to|am|fm|eu|pl|md"
)
_FILE_PATH_RE = re.compile(
    r"(?<![`\w:/\\])"  # not preceded by backtick, word, colon, slash, backslash
    r"("
    r"(?:\w[\w.-]*/)+\w[\w.-]*\.\w+"  # path/to/file.ext (any extension)
    r"|\w[\w.-]*\.(?:" + _TLD_EXTS + r")"  # bare file.ext (TLD extensions)
    r")"
    r"(?![`\w/])",  # not followed by backtick, word, or slash
    re.IGNORECASE,
)


def _wrap_file_paths(text: str) -> str:
    """Wrap file-path patterns in backticks to prevent Telegram auto-linking.

    Telegram treats extensions like ``.py``, ``.js``, ``.io`` as domain
    names and renders them as clickable links.  Wrapping in backticks
    causes :func:`format_html` to emit ``<code>`` tags, which suppresses
    the auto-linking behaviour.

    Args:
        text: Raw text before code extraction.

    Returns:
        Text with file paths wrapped in backticks.
    """
    return _FILE_PATH_RE.sub(r"`\1`", text)


# Patterns for format_html
_MD_CODE_BLOCK_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_MD_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_LABEL_DASH_RE = re.compile(r"^- ([^:\n]{2,30}) — (.+)$", re.MULTILINE)
_PLAIN_DASH_RE = re.compile(r"^- (.+)$", re.MULTILINE)
_SECTION_HEADER_RE = re.compile(r"^([A-Z][^:\n]{2,50}):$", re.MULTILINE)


def format_html(text: str) -> str:
    """Convert reflowed plain text to Telegram HTML.

    Handles: bold, italic, inline code, code blocks, list items
    with label--description, section headers, and HTML escaping.

    Processing order:
      0. Wrap file paths in backticks (prevents Telegram auto-linking).
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

    # 0. Wrap file paths in backticks to prevent Telegram auto-linking
    text = _wrap_file_paths(text)

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
