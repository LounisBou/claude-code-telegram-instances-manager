# MessageHandler

> Handles messages matching a filter — text, photos, documents, locations, or any message type.

## Overview

`MessageHandler` routes incoming messages based entirely on the filter system. Unlike `CommandHandler`, it has no built-in command parsing; the `filters` parameter is required and determines which messages match. This is the primary handler for non-command text input, media messages, and any other message type.

## Quick Usage

```python
from telegram.ext import MessageHandler, filters

async def handle_text(update, context):
    await update.message.reply_text(f"You said: {update.message.text}")

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
```

## Key Classes

### `MessageHandler(filters, callback, block=True)`

**Constructor Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `filters` | `BaseFilter` | required | Determines which messages this handler matches. Use `filters.ALL` to match everything. |
| `callback` | `async (Update, Context) -> None` | required | Async function called on match. |
| `block` | `bool` | `True` | If `True`, blocks update processing until callback completes. |

**Key Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `filters` | `BaseFilter` | The active filter instance. |
| `callback` | `callable` | The registered callback function. |
| `block` | `bool` | Blocking behavior. |

**Key Methods:**

| Method | Description |
|--------|-------------|
| `check_update(update)` | Returns filter result if message matches, `None` otherwise. Only matches updates containing `update.message` or `update.edited_message` (if `filters.UpdateType.EDITED_MESSAGE` is used). |

## Common Patterns

### Handle photos

```python
async def handle_photo(update, context):
    photo = update.message.photo[-1]  # largest size
    file = await photo.get_file()
    await file.download_to_drive("photo.jpg")
    await update.message.reply_text("Photo saved!")

app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
```

### Handle multiple media types

```python
app.add_handler(MessageHandler(
    filters.PHOTO | filters.VIDEO | filters.Document.ALL,
    handle_media
))
```

### Regex text matching

```python
from telegram.ext import filters

async def handle_email(update, context):
    # context.matches contains re.Match objects when using filters.Regex
    email = context.matches[0].group(0)
    await update.message.reply_text(f"Found email: {email}")

app.add_handler(MessageHandler(
    filters.Regex(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    handle_email
))
```

### Filter by chat type

```python
# Only handle text in private chats
app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.PRIVATE,
    private_text_handler
))

# Only handle text in groups
app.add_handler(MessageHandler(
    filters.TEXT & filters.ChatType.GROUPS,
    group_text_handler
))
```

### Catch-all handler (last resort)

```python
# Place this AFTER all other handlers in the same group
app.add_handler(MessageHandler(filters.ALL, fallback_handler))
```

## Important Notes

- `MessageHandler` only matches updates with `update.message` by default. To also match edited messages, include `filters.UpdateType.EDITED_MESSAGE`.
- `filters.TEXT` matches messages with text content but excludes commands. Use `filters.TEXT & ~filters.COMMAND` to be explicit, or just `filters.TEXT` (commands are already excluded from `filters.TEXT` — but `~filters.COMMAND` makes intent clear).
- `filters.ALL` matches all messages but NOT other update types (callback queries, inline queries, etc.).

## Related

- [filters.md](filters.md) — complete filter reference (required reading for MessageHandler)
- [command-handler.md](command-handler.md) — for `/command` messages specifically
- [callback-query-handler.md](callback-query-handler.md) — for inline keyboard button presses
- [index.md](index.md) — handler overview and routing
- [Telegram API — Messages](../../api/bots/messages/index.md) — message types and structure in the API specification
