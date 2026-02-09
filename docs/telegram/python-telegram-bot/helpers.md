# Helpers

> Utility functions for deep links, markdown escaping, and mention formatting.

## Overview

The `telegram.helpers` module provides convenience functions for common tasks: generating bot deep links, escaping text for Telegram's Markdown/MarkdownV2 formatting, and creating user mention strings. The `telegram.utils.helpers` path is deprecated in v22.x; import from `telegram.helpers` directly.

## Quick Usage

```python
from telegram.helpers import escape_markdown, mention_html, create_deep_linked_url

safe_text = escape_markdown("Price: $10 (50% off!)", version=2)
mention = mention_html(user_id=12345, name="Alice")
link = create_deep_linked_url("MyBot", payload="ref_abc123")
```

## Function Reference

### create_deep_linked_url

> Generate a `t.me` deep link for the bot.

```python
create_deep_linked_url(
    bot_username: str,
    payload: str | None = None,
    group: bool = False,
) -> str
```

| Param | Type | Default | Description |
|---|---|---|---|
| `bot_username` | `str` | required | Bot username (without `@`). |
| `payload` | `str \| None` | `None` | Start parameter. Allowed characters: `A-Z`, `a-z`, `0-9`, `_`, `-`. Max 64 characters. |
| `group` | `bool` | `False` | If `True`, generates a group join link (`?startgroup=`). If `False`, generates a private chat link (`?start=`). |

**Returns:** `str`

- No payload: `https://t.me/botname`
- With payload: `https://t.me/botname?start=payload`
- Group link: `https://t.me/botname?startgroup=payload`

When a user clicks the link and starts the bot, the payload is delivered as `context.args[0]` in the `/start` command handler.

---

### effective_message_type

> Extract the message type string from a `Message` or `Update` object.

```python
effective_message_type(
    entity: Message | Update,
) -> str | None
```

| Param | Type | Description |
|---|---|---|
| `entity` | `Message \| Update` | The message or update to inspect. If an `Update`, uses `update.effective_message`. |

**Returns:** `str | None` -- the message type (e.g., `"text"`, `"photo"`, `"sticker"`, `"voice"`, `"video"`, `"document"`, `"location"`, `"contact"`, `"new_chat_members"`, etc.), or `None` if the type cannot be determined.

---

### escape_markdown

> Escape special characters for Telegram Markdown formatting.

```python
escape_markdown(
    text: str,
    version: int = 1,
    entity_type: str | None = None,
) -> str
```

| Param | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | required | Text to escape. |
| `version` | `int` | `1` | Markdown version. Use `2` for MarkdownV2 (recommended). |
| `entity_type` | `str \| None` | `None` | When set to `"pre"` or `"code"`, only escapes `` ` `` and `\`. When `"text_link"`, only escapes `)` and `\`. Optimizes escaping for content inside these entity types. Only applies to version 2. |

**Returns:** `str` -- the escaped text.

**Characters escaped by version:**

- **Version 1 (Markdown):** `_`, `*`, `` ` ``, `[`
- **Version 2 (MarkdownV2):** `_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`

---

### mention_html

> Create an HTML user mention link.

```python
mention_html(
    user_id: int,
    name: str,
) -> str
```

| Param | Type | Description |
|---|---|---|
| `user_id` | `int` | Telegram user ID. |
| `name` | `str` | Display text for the mention. |

**Returns:** `str` -- `<a href="tg://user?id={user_id}">{name}</a>`

The `name` is HTML-escaped automatically.

---

### mention_markdown

> Create a Markdown user mention link.

```python
mention_markdown(
    user_id: int,
    name: str,
    version: int = 1,
) -> str
```

| Param | Type | Default | Description |
|---|---|---|---|
| `user_id` | `int` | required | Telegram user ID. |
| `name` | `str` | required | Display text for the mention. |
| `version` | `int` | `1` | Markdown version. Use `2` for MarkdownV2. |

**Returns:** `str`
- Version 1: `[name](tg://user?id={user_id})`
- Version 2: `[name](tg://user?id={user_id})` (with `name` escaped for MarkdownV2)

## Common Patterns

### Deep links for bot referral tracking

```python
from telegram.helpers import create_deep_linked_url
from telegram.ext import CommandHandler, ContextTypes
from telegram import Update

# Generate referral link
link = create_deep_linked_url("MyBot", payload="ref_user42")
# https://t.me/MyBot?start=ref_user42

# Handle the deep link in /start
async def start(update: Update, context: ContextTypes.DefaultType):
    if context.args and context.args[0].startswith("ref_"):
        referrer = context.args[0][4:]  # "user42"
        await update.message.reply_text(f"Welcome! Referred by {referrer}.")
    else:
        await update.message.reply_text("Welcome!")

app.add_handler(CommandHandler("start", start))
```

### Escaping user input for MarkdownV2

```python
from telegram.helpers import escape_markdown

user_input = "Hello! This costs $10 (50% off)."
safe = escape_markdown(user_input, version=2)
# "Hello\! This costs \$10 \(50% off\)\."

await bot.send_message(
    chat_id=chat_id,
    text=f"*User said:*\n{safe}",
    parse_mode="MarkdownV2",
)
```

### HTML mentions in formatted messages

```python
from telegram.helpers import mention_html

name = mention_html(user_id=update.effective_user.id, name=update.effective_user.first_name)
await update.message.reply_text(
    f"Thanks, {name}! Your request has been processed.",
    parse_mode="HTML",
)
```

## Related

- [Constants](constants.md) -- ParseMode values for formatting
- [Bot](bot.md) -- send_message and parse_mode parameter
- [Types](types/index.md) -- Message, Update objects used with effective_message_type
- [Telegram API — Formatting](../api/bots/messages/formatting.md) -- Markdown and HTML formatting rules in the API specification
