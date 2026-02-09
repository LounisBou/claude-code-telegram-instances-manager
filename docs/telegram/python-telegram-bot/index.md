# python-telegram-bot

> Async Python wrapper for the Telegram Bot API with handler-based update routing, persistence, and job scheduling.

## Overview

`python-telegram-bot` (v22.x) provides an async interface to the Telegram Bot API. The core pattern: create an `Application`, register `Handler` objects that route incoming `Update`s to async callback functions, then run with polling or webhook.

Install: `pip install python-telegram-bot`

## Minimal Bot

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DefaultType):
    await update.message.reply_text("Hello!")

app = Application.builder().token("BOT_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

## Module Map

| File | When to read |
|------|-------------|
| [application.md](application.md) | Setting up the bot, ApplicationBuilder, lifecycle, Defaults |
| [context.md](context.md) | CallbackContext, ContextTypes, JobQueue scheduling |
| [bot.md](bot.md) | Sending messages, making API calls directly via Bot class |
| [handlers/](handlers/index.md) | Routing updates to callbacks — commands, messages, buttons, conversations |
| [types/](types/index.md) | Telegram data types — Message, Update, User, Chat, keyboards, media |
| [features/](features/index.md) | Inline mode, payments, games, stickers, passport, web apps |
| [persistence.md](persistence.md) | Storing conversation/user/chat data across bot restarts |
| [rate-limiting.md](rate-limiting.md) | Throttling API calls to respect Telegram rate limits |
| [request.md](request.md) | Custom HTTP request configuration (proxy, timeouts, HTTP/2) |
| [errors.md](errors.md) | Exception hierarchy and error handling |
| [constants.md](constants.md) | Library constants — ParseMode, ChatType, limits, etc. |
| [helpers.md](helpers.md) | Utility functions — deep links, mentions, markdown escaping |

## Related

- [../api/bots/index.md](../api/bots/index.md) -- Telegram Bot API Reference
