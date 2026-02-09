# Errors

> Exception hierarchy for Telegram Bot API errors -- network failures, permission issues, rate limits, and invalid requests.

## Overview

All exceptions raised by python-telegram-bot inherit from `TelegramError`. The library maps HTTP status codes and API error responses to specific exception types. Register an error handler on the `Application` to catch and handle these exceptions centrally rather than wrapping every API call in try/except.

## Quick Usage

```python
from telegram.ext import Application
import logging

logger = logging.getLogger(__name__)

async def error_handler(update, context):
    logger.error("Exception while handling update: %s", context.error)

app = Application.builder().token("BOT_TOKEN").build()
app.add_error_handler(error_handler)
```

## Exception Hierarchy

```
TelegramError (base)
+-- NetworkError
|   +-- BadRequest
|   +-- TimedOut
+-- Forbidden
+-- InvalidToken
+-- RetryAfter
+-- ChatMigrated
+-- Conflict
+-- EndPointNotFound
+-- PassportDecryptionError
```

## Exception Reference

### TelegramError

> Base exception for all telegram-related errors.

```python
TelegramError(message: str)
```

- `message` -- `str`, human-readable error description.

---

### NetworkError

> Network-level communication failure with the Telegram API.

```python
NetworkError(message: str)
```

Raised when the HTTP request itself fails (DNS resolution, connection refused, etc.). Parent of `BadRequest` and `TimedOut`.

---

### BadRequest

> Telegram rejected the request (HTTP 400). Subclass of `NetworkError`.

```python
BadRequest(message: str)
```

Common causes:
- Invalid `chat_id` or user not found.
- Message text exceeds 4096 characters.
- Invalid reply markup or inline keyboard structure.
- Message to edit not found.
- `message_id` does not exist in the chat.

---

### TimedOut

> Request exceeded the configured timeout. Subclass of `NetworkError`.

```python
TimedOut(message: str = "Timed out")
```

Raised when any of read_timeout, write_timeout, connect_timeout, or pool_timeout is exceeded. Consider increasing timeouts via `ApplicationBuilder` if this occurs frequently.

---

### Forbidden

> Bot lacks permissions for the requested action (HTTP 403).

```python
Forbidden(message: str)
```

Common causes:
- User blocked the bot (`"Forbidden: bot was blocked by the user"`).
- Bot was removed from the group.
- Bot lacks admin rights for an admin-only action.
- Bot cannot send messages in the chat.

---

### InvalidToken

> The bot token is invalid or has been revoked.

```python
InvalidToken(message: str = "Invalid token")
```

Raised during `initialize()` or the first API call if the token is malformed or revoked via BotFather.

---

### RetryAfter

> Rate limited by Telegram (HTTP 429). Wait before retrying.

```python
RetryAfter(retry_after: int | timedelta)
```

- `retry_after` -- `int` or `timedelta`, the number of seconds to wait before the next request.

Access the wait duration:
- `error.retry_after` -- the raw value passed to the constructor.

When using `AIORateLimiter` with `max_retries > 0`, these exceptions are handled automatically.

---

### ChatMigrated

> Group chat was migrated to a supergroup. Use the new chat ID.

```python
ChatMigrated(new_chat_id: int)
```

- `new_chat_id` -- `int`, the new supergroup chat ID. Update stored references to use this ID.

Handle by calling `application.migrate_chat_data(old_chat_id=old_id, new_chat_id=error.new_chat_id)` to transfer persisted chat data.

---

### Conflict

> Another bot instance is competing for updates (HTTP 409).

```python
Conflict(message: str)
```

Raised when multiple bot instances use `getUpdates` simultaneously, or when `getUpdates` is called while a webhook is active. Only one update source can be active at a time.

---

### EndPointNotFound

> The requested API endpoint does not exist.

```python
EndPointNotFound(message: str)
```

Typically indicates the Bot API server URL is misconfigured or the method name is invalid.

---

### PassportDecryptionError

> Failed to decrypt Telegram Passport data.

```python
PassportDecryptionError(message: str)
```

Raised when the bot's private key cannot decrypt passport credentials. Check that the correct private key is configured.

## Common Patterns

### Central error handler with specific exception handling

```python
from telegram import Update
from telegram.error import (
    BadRequest, Forbidden, RetryAfter, ChatMigrated, TimedOut, NetworkError
)
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DefaultType):
    error = context.error

    if isinstance(error, Forbidden):
        # User blocked the bot or bot removed from chat
        logger.info("Forbidden: %s", error.message)
    elif isinstance(error, BadRequest):
        logger.warning("Bad request: %s", error.message)
    elif isinstance(error, RetryAfter):
        logger.warning("Rate limited. Retry after %s seconds.", error.retry_after)
    elif isinstance(error, ChatMigrated):
        logger.info("Chat migrated to %s", error.new_chat_id)
    elif isinstance(error, TimedOut):
        logger.debug("Request timed out.")
    elif isinstance(error, NetworkError):
        logger.error("Network error: %s", error.message)
    else:
        logger.error("Unhandled exception: %s", error)
```

### Handling specific errors inline

```python
from telegram.error import BadRequest, Forbidden

async def send_notification(bot, chat_id, text):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Forbidden:
        # User blocked the bot -- remove from notification list
        remove_subscriber(chat_id)
    except BadRequest as e:
        if "chat not found" in str(e).lower():
            remove_subscriber(chat_id)
        else:
            raise
```

## Related

- [Application](application.md) -- add_error_handler() registration
- [Rate Limiting](rate-limiting.md) -- automatic RetryAfter handling
- [Request](request.md) -- timeout configuration to prevent TimedOut
- [Constants](constants.md) -- FloodLimit values for rate limit thresholds
- [Telegram API — Bot API Overview](../api/bots/index.md) -- error codes and response format in the API specification
