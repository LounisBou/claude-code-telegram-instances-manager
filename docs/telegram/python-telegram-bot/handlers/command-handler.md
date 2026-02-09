# CommandHandler

> Handles bot commands like `/start`, `/help`, `/settings` with optional argument parsing.

## Overview

`CommandHandler` matches messages that begin with a `/command` (or `/command@botname` in groups). Commands are case-insensitive. Arguments after the command are automatically split by whitespace and placed in `context.args`. The handler supports filtering by additional criteria and validating argument count.

## Quick Usage

```python
from telegram.ext import CommandHandler

async def start(update, context):
    args = context.args  # e.g. ["payload"] from "/start payload"
    await update.message.reply_text(f"Hello! Args: {args}")

app.add_handler(CommandHandler("start", start))
```

## Key Classes

### `CommandHandler(command, callback, filters=None, block=True, has_args=None)`

**Constructor Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `command` | `str \| Collection[str]` | required | Command name(s) without `/`. Case-insensitive. |
| `callback` | `async (Update, Context) -> None` | required | Async function called on match. |
| `filters` | `BaseFilter \| None` | `None` | Additional filter applied after command match. Combine with `&`, `\|`, `~`. |
| `block` | `bool` | `True` | If `True`, blocks update processing until callback completes. |
| `has_args` | `bool \| int \| None` | `None` | `True` = require 1+ args, `False` = require 0 args, `int` = require exactly N args, `None` = any count. |

**Key Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `commands` | `frozenset[str]` | Lowercased command names this handler responds to. |
| `callback` | `callable` | The registered callback function. |
| `filters` | `BaseFilter` | The active filter (may be `filters.ALL` if none specified). |
| `block` | `bool` | Blocking behavior. |
| `has_args` | `bool \| int \| None` | Argument validation setting. |

**Key Methods:**

| Method | Description |
|--------|-------------|
| `check_update(update)` | Returns `None` if no match, or `(args_list, filter_result)` on match. |
| `collect_additional_context(context, update, application, check_result)` | Populates `context.args` with whitespace-split argument list. |

## Common Patterns

### Multiple commands, same handler

```python
app.add_handler(CommandHandler(["help", "info", "about"], help_handler))
```

### Command with required arguments

```python
async def ban(update, context):
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    user_id = int(context.args[0])
    await context.bot.ban_chat_member(update.effective_chat.id, user_id)

# Or use has_args for automatic validation (no match if wrong count):
app.add_handler(CommandHandler("ban", ban, has_args=1))
```

### Admin-only command with filter

```python
from telegram.ext import filters

async def admin_cmd(update, context):
    await update.message.reply_text("Admin action done.")

app.add_handler(CommandHandler(
    "admin",
    admin_cmd,
    filters=filters.ChatType.GROUPS & filters.User(username="admin_user")
))
```

### Deep linking via /start payload

```python
async def start(update, context):
    if context.args:
        # User clicked t.me/bot?start=ref123
        ref = context.args[0]  # "ref123"
        await update.message.reply_text(f"Referred by: {ref}")
    else:
        await update.message.reply_text("Welcome!")

app.add_handler(CommandHandler("start", start))
```

## Related

- [message-handler.md](message-handler.md) — handle non-command messages
- [filters.md](filters.md) — filter system for narrowing matches
- [conversation-handler.md](conversation-handler.md) — use CommandHandler as entry_points
- [index.md](index.md) — handler overview and routing
- [Telegram API — Interactivity](../../api/bots/interactivity/index.md) — commands and bot interaction patterns in the API specification
