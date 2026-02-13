# Rich Output & Streaming Indicator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Telegram output pipeline from plain-text batch messages to HTML-formatted edit-in-place streaming with a visual thinking indicator.

**Architecture:** Replace `OutputBuffer` + `_flush_buffer()` with a `StreamingMessage` state machine that sends a placeholder "Thinking..." message, then edits it in-place as content arrives. A new `format_html()` function converts reflowed text to Telegram HTML (bold, italic, code blocks, blockquotes). Overflow (>4096 chars) triggers message finalization and continuation in a new message.

**Tech Stack:** Python 3.11+, python-telegram-bot (Bot API HTML parse mode), asyncio, pytest + AsyncMock

---

### Task 1: Add `edit_rate_limit` to config

**Files:**
- Modify: `src/core/config.py:19-23` (TelegramConfig dataclass)
- Modify: `src/core/config.py:128-132` (load_config telegram section)
- Modify: `config.yaml:1-4` (add setting)
- Test: `tests/test_config.py`

**Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
class TestEditRateLimit:
    """Config must support telegram.edit_rate_limit."""

    def test_default_edit_rate_limit(self, tmp_path):
        """TelegramConfig defaults edit_rate_limit to 3."""
        import yaml
        from src.core.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1]},
            "projects": {"root": "/tmp"},
        }))
        cfg = load_config(str(config_file))
        assert cfg.telegram.edit_rate_limit == 3

    def test_custom_edit_rate_limit(self, tmp_path):
        """edit_rate_limit can be overridden in config."""
        import yaml
        from src.core.config import load_config

        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({
            "telegram": {"bot_token": "tok", "authorized_users": [1], "edit_rate_limit": 5},
            "projects": {"root": "/tmp"},
        }))
        cfg = load_config(str(config_file))
        assert cfg.telegram.edit_rate_limit == 5
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py::TestEditRateLimit -v`
Expected: FAIL with `AttributeError: 'TelegramConfig' object has no attribute 'edit_rate_limit'`

**Step 3: Write minimal implementation**

In `src/core/config.py`, add field to `TelegramConfig`:

```python
@dataclass
class TelegramConfig:
    """Telegram bot connection and authorization settings."""

    bot_token: str
    authorized_users: list[int]
    edit_rate_limit: int = 3
```

In `load_config()`, update the TelegramConfig constructor:

```python
telegram=TelegramConfig(
    bot_token=telegram_raw["bot_token"],
    authorized_users=telegram_raw["authorized_users"],
    edit_rate_limit=telegram_raw.get("edit_rate_limit", 3),
),
```

In `config.yaml`, add the setting:

```yaml
telegram:
  bot_token: "..."
  authorized_users:
    - 1767688016
  edit_rate_limit: 3
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py::TestEditRateLimit -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All 425+ tests pass

**Step 6: Commit**

```bash
git add src/core/config.py config.yaml tests/test_config.py
git commit -m "feat(config): add telegram.edit_rate_limit setting"
```

---

### Task 2: Implement `format_html()` in formatter.py

**Files:**
- Modify: `src/telegram/formatter.py` (add `format_html`, keep `format_telegram` for now)
- Create: `tests/telegram/test_format_html.py`

**Step 1: Write the failing tests**

Create `tests/telegram/test_format_html.py`:

```python
from src.telegram.formatter import format_html


class TestFormatHtmlEscaping:
    """HTML special characters must be escaped outside tags."""

    def test_escapes_angle_brackets(self):
        assert format_html("a < b > c") == "a &lt; b &gt; c"

    def test_escapes_ampersand(self):
        assert format_html("A & B") == "A &amp; B"

    def test_empty_string(self):
        assert format_html("") == ""


class TestFormatHtmlBold:
    """**bold** must become <b>bold</b>."""

    def test_bold_conversion(self):
        result = format_html("This is **bold** text")
        assert "<b>bold</b>" in result

    def test_multiple_bold(self):
        result = format_html("**one** and **two**")
        assert "<b>one</b>" in result
        assert "<b>two</b>" in result


class TestFormatHtmlItalic:
    """*italic* must become <i>italic</i>."""

    def test_italic_conversion(self):
        result = format_html("This is *italic* text")
        assert "<i>italic</i>" in result

    def test_bold_not_treated_as_italic(self):
        result = format_html("This is **bold** text")
        assert "<i>" not in result


class TestFormatHtmlInlineCode:
    """`code` must become <code>code</code>."""

    def test_inline_code(self):
        result = format_html("Use the `print()` function")
        assert "<code>print()</code>" in result

    def test_code_content_escaped(self):
        result = format_html("Use `a < b`")
        assert "<code>a &lt; b</code>" in result


class TestFormatHtmlCodeBlocks:
    """```lang ... ``` must become <pre><code>...</code></pre>."""

    def test_code_block_with_language(self):
        text = "Before\n```python\nprint('hi')\n```\nAfter"
        result = format_html(text)
        assert '<pre><code class="language-python">' in result
        assert "print('hi')" in result
        assert "</code></pre>" in result

    def test_code_block_without_language(self):
        text = "```\nsome code\n```"
        result = format_html(text)
        assert "<pre><code>" in result
        assert "some code" in result

    def test_code_block_content_escaped(self):
        text = "```\na < b && c > d\n```"
        result = format_html(text)
        assert "a &lt; b &amp;&amp; c &gt; d" in result


class TestFormatHtmlBlockquotes:
    """Tool output (⎿ lines) must become blockquotes."""

    def test_short_blockquote(self):
        text = "Result:\nfile.txt line 1\nfile.txt line 2"
        # format_html receives already-extracted content (⎿ stripped by extract_content)
        # Blockquotes are added when caller wraps content with blockquote markers
        result = format_html(text)
        # Plain content stays as plain text after format_html
        assert "file.txt line 1" in result


class TestFormatHtmlLists:
    """List items with label — description must bold the label."""

    def test_dash_label_description(self):
        result = format_html("- label — description")
        assert "• <b>label</b> — description" in result

    def test_plain_list_item(self):
        result = format_html("- plain item")
        assert "• plain item" in result

    def test_ordered_list_unchanged(self):
        result = format_html("1. first item")
        assert "1. first item" in result


class TestFormatHtmlSectionHeaders:
    """Lines ending with : that look like headers get bolded."""

    def test_section_header(self):
        result = format_html("Key components:")
        assert "<b>Key components:</b>" in result

    def test_url_not_treated_as_header(self):
        """URLs containing colons must NOT be treated as section headers."""
        result = format_html("Visit https://example.com for more")
        assert "<b>" not in result


class TestFormatHtmlCombined:
    """Multiple formatting rules in one text."""

    def test_bold_and_code(self):
        result = format_html("**Important**: use `foo()`")
        assert "<b>Important</b>" in result
        assert "<code>foo()</code>" in result

    def test_full_response(self):
        text = (
            "Here's the plan:\n"
            "\n"
            "- **Step 1** — do something\n"
            "- Step 2 — do more\n"
            "\n"
            "```python\nx = 1\n```\n"
            "\n"
            "That's it."
        )
        result = format_html(text)
        assert "<b>Step 1</b>" in result
        assert "<pre><code" in result
        assert "x = 1" in result
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/telegram/test_format_html.py -v`
Expected: FAIL with `ImportError: cannot import name 'format_html'`

**Step 3: Write the implementation**

Add to `src/telegram/formatter.py` (after existing code):

```python
import html as _html_mod


def _escape_html(text: str) -> str:
    """Escape HTML special characters: <, >, &."""
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
    with label—description, section headers, and HTML escaping.

    Args:
        text: Reflowed text from reflow_text().

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
        result = result.replace(f"\x00HTMLBOLD{idx}\x00", f"<b>{_escape_html(content)}</b>")

    for idx, content in enumerate(italics):
        result = result.replace(f"\x00HTMLITALIC{idx}\x00", f"<i>{_escape_html(content)}</i>")

    # 5. Restore code blocks
    for idx, (lang, code) in enumerate(code_blocks):
        escaped_code = _escape_html(code)
        if lang:
            replacement = f'<pre><code class="language-{_escape_html(lang)}">{escaped_code}</code></pre>'
        else:
            replacement = f"<pre><code>{escaped_code}</code></pre>"
        result = result.replace(f"\x00HTMLBLOCK{idx}\x00", replacement)

    # 6. Restore inline code
    for idx, code in enumerate(inline_codes):
        result = result.replace(
            f"\x00HTMLINLINE{idx}\x00", f"<code>{_escape_html(code)}</code>"
        )

    # 7. List items: label — description (must run before plain dash)
    result = _LABEL_DASH_RE.sub(
        lambda m: f"• <b>{m.group(1)}</b> — {m.group(2)}", result
    )
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
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/telegram/test_format_html.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/telegram/formatter.py tests/telegram/test_format_html.py
git commit -m "feat(formatter): add format_html for Telegram HTML output"
```

---

### Task 3: Implement `StreamingMessage` class

**Files:**
- Modify: `src/telegram/output.py` (add StreamingMessage class)
- Create: `tests/telegram/test_streaming_message.py`

**Step 1: Write the failing tests**

Create `tests/telegram/test_streaming_message.py`:

```python
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.telegram.output import StreamingMessage, StreamingState


class TestStreamingMessageInit:
    """StreamingMessage must initialize in IDLE state."""

    def test_initial_state_is_idle(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        assert sm.state == StreamingState.IDLE
        assert sm.message_id is None
        assert sm.accumulated == ""


class TestStreamingMessageThinking:
    """start_thinking() must send typing action and placeholder."""

    @pytest.mark.asyncio
    async def test_sends_typing_action(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()

        bot.send_chat_action.assert_called_once_with(chat_id=123, action="typing")

    @pytest.mark.asyncio
    async def test_sends_placeholder_message(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()

        bot.send_message.assert_called_once_with(
            chat_id=123, text="<i>Thinking...</i>", parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_stores_message_id(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()

        assert sm.message_id == 42
        assert sm.state == StreamingState.THINKING

    @pytest.mark.asyncio
    async def test_starts_typing_loop(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()

        assert sm._typing_task is not None
        assert not sm._typing_task.done()

        # Cleanup
        sm._typing_task.cancel()
        try:
            await sm._typing_task
        except asyncio.CancelledError:
            pass


class TestStreamingMessageAppendContent:
    """append_content() must edit message with accumulated HTML."""

    @pytest.mark.asyncio
    async def test_first_content_cancels_typing(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()
        typing_task = sm._typing_task

        await sm.append_content("Hello")

        assert sm._typing_task is None
        assert typing_task.cancelled()

    @pytest.mark.asyncio
    async def test_accumulates_content(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()
        sm.last_edit_time = 0  # Force allow edit

        await sm.append_content("Hello ")
        await sm.append_content("World")

        assert sm.accumulated == "Hello World"

    @pytest.mark.asyncio
    async def test_edits_message_when_throttle_allows(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()
        sm.last_edit_time = 0  # Force allow edit

        await sm.append_content("Hello")

        bot.edit_message_text.assert_called_with(
            chat_id=123, message_id=42, text="Hello", parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_throttles_edits(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()
        # Simulate recent edit
        sm.last_edit_time = time.monotonic()

        await sm.append_content("Hello")

        # Should NOT have called edit (throttled)
        bot.edit_message_text.assert_not_called()
        # But content is accumulated
        assert sm.accumulated == "Hello"

    @pytest.mark.asyncio
    async def test_state_transitions_to_streaming(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()
        sm.last_edit_time = 0
        await sm.append_content("Hello")

        assert sm.state == StreamingState.STREAMING


class TestStreamingMessageOverflow:
    """Content exceeding 4096 chars must trigger overflow."""

    @pytest.mark.asyncio
    async def test_overflow_splits_at_newline(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=99)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0

        # Content that will exceed 4096 with a newline near the split point
        content = "A" * 4000 + "\n" + "B" * 200
        await sm.append_content(content)

        # Should have edited original message and sent new one
        bot.edit_message_text.assert_called()
        assert bot.send_message.call_count >= 1

    @pytest.mark.asyncio
    async def test_overflow_continues_with_remainder(self):
        bot = AsyncMock()
        new_msg = MagicMock(message_id=99)
        bot.send_message.return_value = new_msg
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0

        content = "A" * 4000 + "\n" + "B" * 200
        await sm.append_content(content)

        # New message_id should be set
        assert sm.message_id == 99


class TestStreamingMessageFinalize:
    """finalize() must send final edit and reset state."""

    @pytest.mark.asyncio
    async def test_finalize_sends_final_edit(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.accumulated = "Final content"
        sm.state = StreamingState.STREAMING

        await sm.finalize()

        bot.edit_message_text.assert_called_with(
            chat_id=123, message_id=42, text="Final content", parse_mode="HTML"
        )

    @pytest.mark.asyncio
    async def test_finalize_resets_state(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.accumulated = "Content"
        sm.state = StreamingState.STREAMING

        await sm.finalize()

        assert sm.state == StreamingState.IDLE
        assert sm.message_id is None
        assert sm.accumulated == ""

    @pytest.mark.asyncio
    async def test_finalize_cancels_typing_task(self):
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.start_thinking()
        typing_task = sm._typing_task

        await sm.finalize()

        assert typing_task.cancelled()

    @pytest.mark.asyncio
    async def test_finalize_noop_when_empty(self):
        bot = AsyncMock()
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)

        await sm.finalize()

        bot.edit_message_text.assert_not_called()


class TestStreamingMessageEdgeErrors:
    """Error handling in StreamingMessage."""

    @pytest.mark.asyncio
    async def test_edit_failure_logged_not_raised(self):
        bot = AsyncMock()
        bot.edit_message_text.side_effect = Exception("Bad request")
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0

        # Should not raise
        await sm.append_content("Hello")
        assert sm.accumulated == "Hello"

    @pytest.mark.asyncio
    async def test_html_fallback_on_parse_error(self):
        """If edit_message fails with parse error, retry as plain text."""
        from telegram.error import BadRequest

        bot = AsyncMock()
        bot.edit_message_text.side_effect = [
            BadRequest("Can't parse entities"),
            None,  # second call (plain text) succeeds
        ]
        sm = StreamingMessage(bot=bot, chat_id=123, edit_rate_limit=3)
        sm.message_id = 42
        sm.state = StreamingState.STREAMING
        sm.last_edit_time = 0

        await sm.append_content("Hello <bad")

        # Should have retried without parse_mode
        assert bot.edit_message_text.call_count == 2
        second_call = bot.edit_message_text.call_args_list[1]
        assert "parse_mode" not in second_call.kwargs or second_call.kwargs.get("parse_mode") is None
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/telegram/test_streaming_message.py -v`
Expected: FAIL with `ImportError: cannot import name 'StreamingMessage'`

**Step 3: Write the implementation**

Add to `src/telegram/output.py`:

```python
import time
from enum import Enum


class StreamingState(Enum):
    """State of a StreamingMessage lifecycle."""
    IDLE = "idle"
    THINKING = "thinking"
    STREAMING = "streaming"


class StreamingMessage:
    """Manages edit-in-place streaming for a single Claude response.

    State machine: IDLE → start_thinking() → THINKING → first content → STREAMING → finalize() → IDLE

    In THINKING state, sends typing action every 4s.
    In STREAMING state, edits message in-place at throttled rate.
    On overflow (>4096 chars), finalizes current message and starts a new one.
    """

    def __init__(self, bot: Bot, chat_id: int, edit_rate_limit: int = 3) -> None:
        """Initialize streaming message manager.

        Args:
            bot: Telegram Bot instance for API calls.
            chat_id: Telegram chat ID to send messages to.
            edit_rate_limit: Maximum edit_message calls per second.
        """
        self.bot = bot
        self.chat_id = chat_id
        self.edit_rate_limit = edit_rate_limit
        self.message_id: int | None = None
        self.accumulated: str = ""
        self.last_edit_time: float = 0
        self.state: StreamingState = StreamingState.IDLE
        self._typing_task: asyncio.Task | None = None

    async def start_thinking(self) -> None:
        """Send typing action and placeholder message.

        Transitions: IDLE → THINKING.
        Starts a background task that resends typing action every 4 seconds.
        """
        await self.bot.send_chat_action(chat_id=self.chat_id, action="typing")
        msg = await self.bot.send_message(
            chat_id=self.chat_id,
            text="<i>Thinking...</i>",
            parse_mode="HTML",
        )
        self.message_id = msg.message_id
        self.state = StreamingState.THINKING
        self._typing_task = asyncio.create_task(self._typing_loop())

    async def append_content(self, html: str) -> None:
        """Add content and edit message if throttle allows.

        On first call, cancels typing indicator and transitions to STREAMING.
        Handles overflow when accumulated content exceeds 4096 chars.

        Args:
            html: HTML-formatted content to append.
        """
        # Stop typing indicator on first content
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None

        self.state = StreamingState.STREAMING
        self.accumulated += html

        # Check for overflow
        if len(self.accumulated) > 4096:
            await self._overflow()
            return

        # Throttle edits
        now = time.monotonic()
        min_interval = 1.0 / self.edit_rate_limit
        if now - self.last_edit_time < min_interval:
            return  # Will be sent on next flush or finalize

        await self._edit()

    async def finalize(self) -> None:
        """Final edit to ensure all content is sent, then reset.

        Transitions: any → IDLE.
        """
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None
        if self.accumulated and self.message_id:
            await self._edit()
        self.reset()

    async def _edit(self) -> None:
        """Edit the current message with accumulated content."""
        if not self.message_id or not self.accumulated:
            return
        try:
            await self.bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=self.accumulated,
                parse_mode="HTML",
            )
            self.last_edit_time = time.monotonic()
        except Exception as exc:
            exc_str = str(exc)
            # If HTML parsing fails, retry without parse_mode
            if "parse entities" in exc_str.lower():
                try:
                    await self.bot.edit_message_text(
                        chat_id=self.chat_id,
                        message_id=self.message_id,
                        text=self.accumulated,
                        parse_mode=None,
                    )
                    self.last_edit_time = time.monotonic()
                except Exception as inner_exc:
                    logger.warning("edit_message plain-text fallback failed: %s", inner_exc)
            else:
                logger.warning("edit_message failed: %s", exc)

    async def _overflow(self) -> None:
        """Content exceeds 4096: finalize current message, start new one."""
        split_at = self.accumulated.rfind("\n", 0, 4096)
        if split_at == -1:
            split_at = 4000
        current = self.accumulated[:split_at]
        remainder = self.accumulated[split_at:].lstrip()
        self.accumulated = current
        await self._edit()
        # Start new message with remainder
        if remainder:
            msg = await self.bot.send_message(
                chat_id=self.chat_id, text=remainder, parse_mode="HTML"
            )
            self.message_id = msg.message_id
            self.accumulated = remainder
            self.last_edit_time = time.monotonic()

    async def _typing_loop(self) -> None:
        """Resend typing action every 4 seconds."""
        try:
            while True:
                await asyncio.sleep(4)
                await self.bot.send_chat_action(
                    chat_id=self.chat_id, action="typing"
                )
        except asyncio.CancelledError:
            pass

    def reset(self) -> None:
        """Reset to IDLE for next response."""
        self.message_id = None
        self.accumulated = ""
        self.last_edit_time = 0
        self.state = StreamingState.IDLE
```

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/telegram/test_streaming_message.py -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/telegram/output.py tests/telegram/test_streaming_message.py
git commit -m "feat(output): add StreamingMessage with edit-in-place streaming"
```

---

### Task 4: Refactor `poll_output()` to use `StreamingMessage`

**Files:**
- Modify: `src/telegram/output.py` (replace OutputBuffer with StreamingMessage in poll loop)
- Modify: `tests/telegram/test_output.py` (update tests for new pipeline)

**Step 1: Write failing tests for new behavior**

Update `tests/telegram/test_output.py` — replace `OutputBuffer`-based tests with `StreamingMessage`-based ones:

```python
class TestPollOutputStreaming:
    """poll_output must use StreamingMessage instead of OutputBuffer."""

    def _cleanup_session(self, key):
        from src.telegram.output import (
            _session_emulators, _session_prev_state,
            _session_sent_lines, _session_streaming,
        )
        _session_emulators.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)
        _session_streaming.pop(key, None)

    @pytest.mark.asyncio
    async def test_thinking_transition_calls_start_thinking(self):
        """UNKNOWN→THINKING must call StreamingMessage.start_thinking()."""
        key = (700, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {700: {1: session}}
        bot = AsyncMock()

        thinking_event = ScreenEvent(state=ScreenState.THINKING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=thinking_event),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # StreamingMessage should have been created and start_thinking called
        from src.telegram.output import _session_streaming
        streaming = _session_streaming.get(key)
        assert streaming is not None

        # Verify typing action was sent (from start_thinking)
        bot.send_chat_action.assert_called()

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_streaming_content_calls_append(self):
        """STREAMING state must format content and call append_content()."""
        key = (699, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {699: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        streaming_event = ScreenEvent(state=ScreenState.STREAMING, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=streaming_event),
            patch("src.telegram.output.extract_content", return_value="Hello world"),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # edit_message_text should have been called (from append_content)
        # The content flows through format_html before being appended
        bot.edit_message_text.assert_called()

        self._cleanup_session(key)

    @pytest.mark.asyncio
    async def test_idle_transition_calls_finalize(self):
        """STREAMING→IDLE must call finalize()."""
        key = (698, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm_mock = MagicMock()
        sm_mock._sessions = {698: {1: session}}
        bot = AsyncMock()
        bot.send_message.return_value = MagicMock(message_id=42)

        # Pre-fill with streaming state
        from src.telegram.output import (
            _session_emulators, _session_prev_state,
            _session_sent_lines, _session_streaming,
            StreamingMessage,
        )
        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()
        streaming = StreamingMessage(bot=bot, chat_id=698, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Final content"
        streaming.state = StreamingState.STREAMING
        _session_streaming[key] = streaming

        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])
        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=idle_event),
        ):
            try:
                await poll_output(bot, sm_mock)
            except asyncio.CancelledError:
                pass

        # Final edit should have been sent
        bot.edit_message_text.assert_called()
        # Streaming message should be reset
        assert streaming.state == StreamingState.IDLE

        self._cleanup_session(key)
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/telegram/test_output.py::TestPollOutputStreaming -v`
Expected: FAIL (imports like `_session_streaming` don't exist yet in poll_output)

**Step 3: Refactor poll_output()**

Replace the `OutputBuffer` / `_flush_buffer` pattern in `src/telegram/output.py`:

1. Replace `_session_buffers` dict with `_session_streaming` dict
2. Remove `_flush_buffer()` function
3. Remove `OutputBuffer` import
4. In the poll loop:
   - Lazy-init `StreamingMessage` instead of `OutputBuffer`
   - On THINKING transition: call `streaming.start_thinking()`
   - On content extraction: call `streaming.append_content(format_html(reflow_text(deduped)))`
   - On IDLE transition: call `streaming.finalize()`
   - Remove the `buf.is_ready()` checks (StreamingMessage handles its own timing)

Key changes to `poll_output()`:

```python
from src.telegram.formatter import format_html, reflow_text

# Replace _session_buffers with:
_session_streaming: dict[tuple[int, int], StreamingMessage] = {}

# In the poll loop, replace OutputBuffer init with:
if key not in _session_emulators:
    _session_emulators[key] = TerminalEmulator()
    _session_streaming[key] = StreamingMessage(
        bot=bot, chat_id=user_id, edit_rate_limit=3,
    )
    _session_prev_state[key] = ScreenState.STARTUP
    _session_sent_lines[key] = set()

# Read the streaming message:
streaming = _session_streaming[key]

# Replace THINKING notification:
if event.state == ScreenState.THINKING and prev != ScreenState.THINKING:
    await streaming.start_thinking()

# Replace content buffering:
if event.state in _CONTENT_STATES:
    content = extract_content(changed)
    if content:
        sent = _session_sent_lines.get(key, set())
        new_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped and stripped not in sent:
                new_lines.append(line)
                sent.add(stripped)
        if new_lines:
            deduped = "\n".join(new_lines)
            html = format_html(reflow_text(deduped))
            await streaming.append_content(html)

# Replace flush logic:
if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
    _session_sent_lines[key] = set()
    await streaming.finalize()
```

Also remove the "no raw data" buffer check — `StreamingMessage` doesn't need it (it manages its own state).

**Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/telegram/test_output.py -v`
Expected: PASS

**Step 5: Update existing tests that reference OutputBuffer/flush**

Some existing tests in `test_output.py` reference `_session_buffers`, `_flush_buffer`, and `OutputBuffer`. Update these:

- `TestFlushBuffer` — remove entirely (replaced by `StreamingMessage` tests)
- `TestPollOutputIntegration` — update to check `_session_streaming` instead of `_session_buffers`
- `TestOutputStateFiltering` — keep as-is (tests `_CONTENT_STATES`, not buffer logic)
- `TestContentDedup` — keep as-is (tests dedup logic, independent of output mechanism)
- `TestDedupSetClearing` — keep as-is
- `TestPollOutputStateTransitions` — update tests that inspect buffer to inspect `StreamingMessage` instead

**Step 6: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass

**Step 7: Commit**

```bash
git add src/telegram/output.py tests/telegram/test_output.py
git commit -m "refactor(output): replace OutputBuffer with StreamingMessage in poll_output"
```

---

### Task 5: Wire `edit_rate_limit` config into poll_output

**Files:**
- Modify: `src/telegram/output.py` (accept config in poll_output or pass to StreamingMessage)
- Modify: `src/main.py` (pass config to poll_output)
- Test: `tests/telegram/test_output.py`

**Step 1: Write the failing test**

```python
class TestEditRateLimitWiring:
    """poll_output must pass edit_rate_limit from config to StreamingMessage."""

    @pytest.mark.asyncio
    async def test_streaming_message_uses_config_rate(self):
        key = (690, 1)
        # cleanup
        from src.telegram.output import (
            _session_emulators, _session_prev_state,
            _session_sent_lines, _session_streaming,
        )
        for d in [_session_emulators, _session_prev_state, _session_sent_lines, _session_streaming]:
            d.pop(key, None)

        process = MagicMock()
        process.read_available.return_value = None
        session = MagicMock()
        session.process = process
        sm_mock = MagicMock()
        sm_mock._sessions = {690: {1: session}}
        bot = AsyncMock()

        with patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
            try:
                await poll_output(bot, sm_mock, edit_rate_limit=5)
            except asyncio.CancelledError:
                pass

        streaming = _session_streaming.get(key)
        assert streaming is not None
        assert streaming.edit_rate_limit == 5

        for d in [_session_emulators, _session_prev_state, _session_sent_lines, _session_streaming]:
            d.pop(key, None)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/telegram/test_output.py::TestEditRateLimitWiring -v`
Expected: FAIL (poll_output doesn't accept edit_rate_limit param)

**Step 3: Implement**

Update `poll_output()` signature:

```python
async def poll_output(bot: Bot, session_manager, edit_rate_limit: int = 3) -> None:
```

Pass it when creating StreamingMessage:

```python
_session_streaming[key] = StreamingMessage(
    bot=bot, chat_id=user_id, edit_rate_limit=edit_rate_limit,
)
```

Update `src/main.py` where `poll_output` is launched to pass the config value:

```python
asyncio.create_task(
    poll_output(bot, session_manager, edit_rate_limit=config.telegram.edit_rate_limit)
)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/telegram/test_output.py::TestEditRateLimitWiring -v`
Expected: PASS

**Step 5: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass

**Step 6: Commit**

```bash
git add src/telegram/output.py src/main.py tests/telegram/test_output.py
git commit -m "feat(output): wire edit_rate_limit config to StreamingMessage"
```

---

### Task 6: Update documentation

**Files:**
- Modify: `docs/index.md` (add plan reference)
- Modify: `src/telegram/output.py` (ensure docstrings)
- Modify: `src/telegram/formatter.py` (ensure docstrings)

**Step 1: Update docs/index.md plans table**

Add the new plan to the plans table:

```markdown
| [Rich Output Streaming Design](plans/2026-02-11-rich-output-streaming-design.md) | HTML streaming output design |
| [Rich Output Streaming Plan](plans/2026-02-11-rich-output-streaming-plan.md) | Implementation plan for streaming |
```

**Step 2: Verify all public functions have docstrings**

Check that `format_html()`, `StreamingMessage`, and all its methods have complete docstrings. Already included in Task 2 and Task 3 implementations.

**Step 3: Commit**

```bash
git add docs/index.md
git commit -m "docs: add rich output streaming plan to index"
```

---

### Task 7: Final validation — full test suite + coverage

**Files:** None (verification only)

**Step 1: Run full test suite**

Run: `python -m pytest --tb=short -q`
Expected: All tests pass (425+ original + new tests)

**Step 2: Run coverage check**

Run: `python -m pytest --cov=src --cov-report=term-missing --tb=short -q`
Expected: Coverage ≥ 90% overall, new code in `formatter.py` and `output.py` ≥ 95%

**Step 3: Verify no regressions**

Run: `python -m pytest tests/parsing/ tests/telegram/ -v`
Expected: All existing parsing and telegram tests still pass

**Step 4: Manual smoke check**

Verify imports work:

```python
python -c "from src.telegram.formatter import format_html; print(format_html('**hello** `world`'))"
python -c "from src.telegram.output import StreamingMessage, StreamingState; print('OK')"
```

Expected: First prints `<b>hello</b> <code>world</code>`, second prints `OK`.
