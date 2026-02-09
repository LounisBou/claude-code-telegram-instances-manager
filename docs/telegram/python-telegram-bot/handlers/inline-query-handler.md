# InlineQueryHandler

> Handles inline queries when users type `@botname query` in any chat.

## Overview

`InlineQueryHandler` processes `InlineQuery` updates triggered when a user types `@botname` followed by a query string in the Telegram message input. The handler can optionally filter by regex pattern against the query text and by chat type. The callback must respond with `await update.inline_query.answer(results)` to provide result options to the user. Inline mode must be enabled via BotFather (`/setinline`).

## Quick Usage

```python
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import InlineQueryHandler

async def inline_query(update, context):
    query = update.inline_query.query
    results = [
        InlineQueryResultArticle(
            id="1",
            title=f"Echo: {query}",
            input_message_content=InputTextMessageContent(query),
        )
    ]
    await update.inline_query.answer(results)

app.add_handler(InlineQueryHandler(inline_query))
```

## Key Classes

### `InlineQueryHandler(callback, pattern=None, block=True, chat_types=None)`

**Constructor Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `callback` | `async (Update, Context) -> None` | required | Async function called on match. |
| `pattern` | `str \| re.Pattern \| None` | `None` | Regex tested against `InlineQuery.query` via `re.match()`. If `None`, matches all inline queries. |
| `block` | `bool` | `True` | If `True`, blocks update processing until callback completes. |
| `chat_types` | `list[str] \| None` | `None` | Filter by the chat type where the inline query was sent (e.g., `["sender"]` for private, `["group", "supergroup"]`). Based on `InlineQuery.chat_type`. |

**Key Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `pattern` | `str \| re.Pattern` | The active regex pattern. |
| `chat_types` | `list[str]` | Allowed chat types. |
| `callback` | `callable` | The registered callback function. |
| `block` | `bool` | Blocking behavior. |

**Key Methods:**

| Method | Description |
|--------|-------------|
| `check_update(update)` | Returns `None` if no match, or the `re.Match` object / `True` on match. |
| `collect_additional_context(context, update, application, check_result)` | Populates `context.matches` as a single-element list with the `re.Match` object (when pattern is used). |

## Common Patterns

### Pattern-based routing

```python
async def search_handler(update, context):
    match = context.matches[0]
    search_term = match.group("term")
    # ... perform search ...
    await update.inline_query.answer(results)

app.add_handler(InlineQueryHandler(
    search_handler,
    pattern=r"^search (?P<term>.+)$"
))
```

### Paginated results with offset

```python
async def inline_query(update, context):
    query = update.inline_query.query
    offset = int(update.inline_query.offset or 0)
    page_size = 20

    all_results = get_results(query)
    page = all_results[offset:offset + page_size]

    results = [
        InlineQueryResultArticle(
            id=str(offset + i),
            title=item.title,
            input_message_content=InputTextMessageContent(item.text),
        )
        for i, item in enumerate(page)
    ]

    next_offset = str(offset + page_size) if offset + page_size < len(all_results) else ""
    await update.inline_query.answer(results, next_offset=next_offset)
```

### Cache and personalization

```python
async def inline_query(update, context):
    results = build_results(update.inline_query.query)
    await update.inline_query.answer(
        results,
        cache_time=10,         # seconds Telegram caches results (default 300)
        is_personal=True,      # per-user results (not shared across users)
    )
```

## Important Notes

- Inline mode must be enabled via BotFather's `/setinline` command.
- `answer()` must be called. Telegram shows a spinner until results are sent.
- Results are limited to 50 items per `answer()` call. Use `next_offset` for pagination.
- `pattern` uses `re.match()` (matches from start of string). Use `.*` prefix if you need `re.search()` behavior.
- `InlineQuery.query` can be empty when user types just `@botname`.
- Each result needs a unique `id` string (within the query).
- Result types: `InlineQueryResultArticle`, `InlineQueryResultPhoto`, `InlineQueryResultGif`, `InlineQueryResultVideo`, `InlineQueryResultAudio`, `InlineQueryResultDocument`, `InlineQueryResultVoice`, `InlineQueryResultLocation`, `InlineQueryResultVenue`, `InlineQueryResultContact`, `InlineQueryResultCachedPhoto`, etc.

## Related

- [other-handlers.md](other-handlers.md) — `ChosenInlineResultHandler` for tracking which result the user selected
- [callback-query-handler.md](callback-query-handler.md) — for inline keyboard buttons (different from inline queries)
- [filters.md](filters.md) — filter system (not directly used by InlineQueryHandler, but relevant for other handlers)
- [index.md](index.md) — handler overview and routing
- [Telegram API — Inline Mode](../../api/bots/inline/index.md) — inline query mechanics in the API specification
