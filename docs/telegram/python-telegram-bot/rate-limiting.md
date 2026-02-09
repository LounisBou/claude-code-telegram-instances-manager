# Rate Limiting

> Throttle outgoing Bot API calls to respect Telegram's rate limits (30 msgs/sec overall, 20 msgs/min per group).

## Overview

Telegram enforces rate limits on bot API calls: approximately 30 messages per second globally, 20 messages per minute per group/channel, and 1 message per second per individual chat. The rate limiting module transparently queues and delays outgoing requests to stay within these limits. Wire it up via `ApplicationBuilder` and all `Bot` method calls are automatically throttled.

**Requires:** `pip install "python-telegram-bot[rate-limiter]"` (installs the `aiolimiter` dependency).

## Quick Usage

```python
from telegram.ext import Application, AIORateLimiter

app = (
    Application.builder()
    .token("BOT_TOKEN")
    .rate_limiter(AIORateLimiter())
    .build()
)
app.run_polling()
```

## Key Classes

### BaseRateLimiter (abstract)

> Abstract base class for rate limiter implementations. Subclass this to create a custom rate limiter.

**Methods to implement (all async):**

| Method | Description |
|---|---|
| `initialize()` | Called on application startup. Set up any resources. |
| `shutdown()` | Called on application shutdown. Clean up resources. |
| `process_request(callback, args, kwargs, endpoint, data, rate_limit_args)` | Called for every outgoing API request. Apply rate limiting logic, then call `callback(*args, **kwargs)` to execute the actual request. |

**`process_request` parameters:**

- `callback` -- the actual API call coroutine to invoke after rate limiting.
- `args` -- positional arguments for the callback.
- `kwargs` -- keyword arguments for the callback.
- `endpoint` -- `str`, the Bot API method name (e.g., `"sendMessage"`).
- `data` -- `dict[str, ...]`, the request payload. Contains `chat_id` when applicable (useful for per-chat limiting).
- `rate_limit_args` -- `dict[str, ...]` or `None`, custom rate limit arguments passed via `do_api_request`. Allows per-call rate limit overrides.

---

### AIORateLimiter

> Built-in rate limiter using `aiolimiter.AsyncLimiter`. Handles both global and per-group/channel limits.

**Constructor:**

```python
AIORateLimiter(
    overall_max_rate: float = 30,
    overall_time_period: float = 1,
    group_max_rate: float = 20,
    group_time_period: float = 60,
    max_retries: int = 0,
)
```

| Param | Type | Default | Description |
|---|---|---|---|
| `overall_max_rate` | `float` | `30` | Maximum number of requests per `overall_time_period` for the entire bot. |
| `overall_time_period` | `float` | `1` | Time window in seconds for the overall rate limit. |
| `group_max_rate` | `float` | `20` | Maximum requests per `group_time_period` for each group/supergroup/channel. |
| `group_time_period` | `float` | `60` | Time window in seconds for the per-group rate limit. |
| `max_retries` | `int` | `0` | Number of retry attempts when a `RetryAfter` exception is raised by Telegram. Retries wait for the duration specified in the exception. |

**Behavior:**

- Every outgoing request passes through the overall limiter (30/sec by default).
- Requests targeting a group or channel chat additionally pass through a per-chat limiter (20/min by default).
- Private chats are only subject to the overall limit.
- When `max_retries > 0`, a `RetryAfter` error from Telegram triggers an automatic wait-and-retry cycle.

## Common Patterns

### Conservative rate limiting for high-traffic bots

```python
from telegram.ext import Application, AIORateLimiter

limiter = AIORateLimiter(
    overall_max_rate=25,       # stay below the 30/s hard limit
    overall_time_period=1,
    group_max_rate=15,         # stay below the 20/min per-group limit
    group_time_period=60,
    max_retries=3,             # auto-retry on 429 errors
)

app = (
    Application.builder()
    .token("BOT_TOKEN")
    .rate_limiter(limiter)
    .build()
)
```

### Combining rate limiting with concurrent updates

```python
app = (
    Application.builder()
    .token("BOT_TOKEN")
    .rate_limiter(AIORateLimiter())
    .concurrent_updates(True)
    .build()
)
```

When `concurrent_updates` is enabled, multiple handlers may attempt to send messages simultaneously. The rate limiter ensures these concurrent sends remain within Telegram's limits.

## Related

- [Application](application.md) -- ApplicationBuilder.rate_limiter() configuration
- [Errors](errors.md) -- RetryAfter exception details
- [Request](request.md) -- HTTP-level configuration (timeouts, proxies)
- [Constants](constants.md) -- FloodLimit constants for Telegram rate limits
