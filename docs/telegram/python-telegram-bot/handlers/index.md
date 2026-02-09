# Handlers

> Handler-based routing system that dispatches Telegram Updates to async callback functions.

## Overview

The `Application` dispatches incoming `Update` objects to registered handlers organized by numbered groups (lower group number = higher priority). Within a group, the first handler whose `check_update()` returns truthy wins and processes the update. Each handler wraps an async callback with signature `async def callback(update: Update, context: ContextTypes.DefaultType)`.

Handlers are added via `app.add_handler(handler, group=0)`. An update matched in group 0 still flows to group 1, 2, etc. — but within a single group, only the first match fires.

## Key Concepts

- **Group priority**: `app.add_handler(h, group=0)` runs before `group=1`. Use groups to layer error handling, logging, or access control above business logic.
- **First-match-wins**: Within a group, handlers are checked in insertion order. The first match stops further checking in that group.
- **Callback signature**: All handler callbacks receive `(update, context)`. The `context` object carries `context.bot`, `context.args`, `context.user_data`, `context.chat_data`, and more.
- **Filters**: Most handlers accept a `filters` parameter to narrow which updates they match. Filters compose with `&` (and), `|` (or), `~` (not).
- **block parameter**: When `block=True` (default), the application waits for the callback to finish before processing the next update. Set `block=False` for fire-and-forget.

## Handler Registration

```python
from telegram.ext import Application, CommandHandler, MessageHandler, filters

app = Application.builder().token("TOKEN").build()

# Group 0 (default) — main handlers
app.add_handler(CommandHandler("start", start_callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_callback))

# Group 1 — logging layer (runs even if group 0 matched)
app.add_handler(MessageHandler(filters.ALL, log_callback), group=1)

app.run_polling()
```

## Routing Table

| File | When to read |
|------|-------------|
| [command-handler.md](command-handler.md) | Handle `/commands` like `/start`, `/help` |
| [message-handler.md](message-handler.md) | Handle messages by type or content (text, photo, etc.) |
| [callback-query-handler.md](callback-query-handler.md) | Handle inline keyboard button presses |
| [conversation-handler.md](conversation-handler.md) | Multi-step conversation flows with states |
| [inline-query-handler.md](inline-query-handler.md) | Handle inline queries (`@bot query`) |
| [filters.md](filters.md) | Filter system — select which updates a handler receives |
| [other-handlers.md](other-handlers.md) | PreCheckout, Shipping, ChatMember, Poll, Prefix, Type handlers |
| [event-handlers.md](event-handlers.md) | Reactions, boosts, business account events |

## Related

- [filters.md](filters.md) — filter system used by most handlers
- [../index.md](../index.md) — python-telegram-bot top-level reference
- [../features/](../features/) — higher-level feature guides (keyboards, inline mode, payments, etc.)
- [Telegram API — Updates](../../api/bots/updates/index.md) — how the Bot API delivers updates to your bot
