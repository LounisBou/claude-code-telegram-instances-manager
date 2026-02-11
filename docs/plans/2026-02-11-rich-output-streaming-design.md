# Rich Output & Streaming Indicator Design

## Summary

Transform the Telegram output pipeline from plain-text batch messages to **HTML-formatted edit-in-place streaming** with a visual thinking indicator.

## Goals

1. Show "typing..." bubble + `<i>Thinking...</i>` placeholder while Claude thinks
2. Edit the placeholder in-place as content streams in (single growing message)
3. Format output as Telegram HTML: bold, italic, code blocks, blockquotes, bullet lists
4. Handle overflow (>4096 chars) by finalizing current message and starting a new one

## Pipeline Change

```
BEFORE:
  PTY → pyte → get_changes() → extract_content() → reflow_text() → OutputBuffer → send_message(plain text)

AFTER:
  PTY → pyte → get_changes() → extract_content() → reflow_text() → format_html() → StreamingMessage
                                                                                         │
                                                                          sendChatAction("typing")     [THINKING]
                                                                          send_message(<i>Thinking...</i>) [THINKING→STREAMING]
                                                                          edit_message(growing HTML)    [each flush, throttled ~3/sec]
                                                                          new message                   [overflow >4096]
                                                                          final edit                    [→IDLE]
```

## Component: `format_html(text) → str`

**Location:** `src/telegram/formatter.py` (replaces unused `format_telegram()`)

Converts reflowed plain text to Telegram HTML.

### Formatting Rules

| Claude output | Telegram HTML |
|---|---|
| Regular text | Plain text (`<>&` escaped) |
| `**bold**` | `<b>bold</b>` |
| `*italic*` | `<i>italic</i>` |
| `` `inline code` `` | `<code>inline code</code>` |
| ` ```lang ... ``` ` | `<pre><code class="language-lang">...</code></pre>` |
| Tool output (⎿ lines) | `<blockquote>content</blockquote>` |
| Long tool results (>10 lines) | `<blockquote expandable>content</blockquote>` |
| `- label — description` | `• <b>label</b> — description` |
| `- plain item` | `• plain item` |
| `1. ordered item` | `1. ordered item` (keep as-is) |
| Section headers ending `:` | `<b>Header:</b>` |

### Escaping

HTML mode only requires escaping `<`, `>`, `&` in non-tag content. Much safer than MarkdownV2.

## Component: `StreamingMessage`

**Location:** `src/telegram/output.py`

Manages the edit-in-place lifecycle for a single Claude response.

### State Machine

```
IDLE → start_thinking() → THINKING → first_content() → STREAMING → finalize() → IDLE
                              │                              │
                       sendChatAction("typing")      edit_message (throttled)
                       send placeholder msg           overflow → new message
                       (every 4s)                     (>4096 chars)
```

### Interface

```python
class StreamingMessage:
    def __init__(self, bot: Bot, chat_id: int):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id: int | None = None      # Current message being edited
        self.accumulated: str = ""                # Full HTML content so far
        self.last_edit_time: float = 0            # Throttle edits to 1/sec
        self._typing_task: asyncio.Task | None = None

    async def start_thinking(self) -> None:
        """Send typing action and placeholder message."""
        await self.bot.send_chat_action(chat_id=self.chat_id, action="typing")
        msg = await self.bot.send_message(
            chat_id=self.chat_id,
            text="<i>Thinking...</i>",
            parse_mode="HTML",
        )
        self.message_id = msg.message_id
        # Start background task to resend typing action every 4s
        self._typing_task = asyncio.create_task(self._typing_loop())

    async def append_content(self, html: str) -> None:
        """Add content and edit message if throttle allows."""
        # Stop typing indicator on first content
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None

        self.accumulated += html

        # Check for overflow
        if len(self.accumulated) > 4096:
            await self._overflow()
            return

        # Throttle edits (rate from config, Telegram allows 5/sec)
        now = time.monotonic()
        min_interval = 1.0 / self.edit_rate_limit  # from config
        if now - self.last_edit_time < min_interval:
            return  # Will be sent on next flush or finalize

        await self._edit()

    async def finalize(self) -> None:
        """Final edit to ensure all content is sent."""
        if self._typing_task:
            self._typing_task.cancel()
            self._typing_task = None
        if self.accumulated:
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
            logger.warning("edit_message failed: %s", exc)

    async def _overflow(self) -> None:
        """Content exceeds 4096: finalize current, start new message."""
        # Split at safe boundary
        split_at = self.accumulated.rfind("\n", 0, 4096)
        if split_at == -1:
            split_at = 4000
        # Finalize current message with content up to split
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
        """Reset for next response."""
        self.message_id = None
        self.accumulated = ""
        self.last_edit_time = 0
```

## Changes to `poll_output()`

Replace `OutputBuffer` + `_flush_buffer()` with `StreamingMessage`:

```python
# Per-session streaming message (replaces OutputBuffer for output)
_session_streaming: dict[tuple[int, int], StreamingMessage] = {}

# In the poll loop:
if event.state == ScreenState.THINKING and prev != ScreenState.THINKING:
    await streaming.start_thinking()

if event.state in _CONTENT_STATES:
    content = extract_content(changed)
    if content:
        # Dedup + reflow + format
        html = format_html(reflow_text(deduped_content))
        await streaming.append_content(html)

if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
    await streaming.finalize()
```

## Error Handling

- `edit_message` failure: log warning, continue accumulating. Next edit will include all content.
- Message too old to edit (Telegram 48h limit): send as new message instead.
- Rate limit hit (429): back off and retry on next cycle.
- HTML parse error: fall back to plain text for that chunk.

## Configuration

Add to `config.yaml`:

```yaml
telegram:
  edit_rate_limit: 3  # max edit_message calls per second (Telegram allows 5)
```

This allows tuning the streaming responsiveness without code changes.

## Files to Modify

| File | Change |
|---|---|
| `src/telegram/formatter.py` | Add `format_html()`, remove/replace `format_telegram()` |
| `src/telegram/output.py` | Add `StreamingMessage`, refactor `poll_output()` to use it |
| `tests/telegram/test_formatter.py` | Tests for `format_html()` |
| `src/core/config.py` | Add `edit_rate_limit` to telegram config |
| `config.yaml` | Add `telegram.edit_rate_limit` setting |
| `tests/telegram/test_output.py` | Tests for `StreamingMessage` |
