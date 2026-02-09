# Other Handlers

> Specialized handlers for payments, membership, polls, inline results, prefix commands, and generic type matching.

## Overview

These handlers cover Telegram update types beyond messages, commands, callback queries, conversations, and inline queries. Each handler targets a specific update type. All share the standard callback signature `async def callback(update: Update, context: ContextTypes.DefaultType)` and the `block` parameter (default `True`).

## Quick Usage

```python
from telegram.ext import PreCheckoutQueryHandler

async def pre_checkout(update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)

app.add_handler(PreCheckoutQueryHandler(pre_checkout))
```

## PreCheckoutQueryHandler

Handles pre-checkout validation for Telegram Payments. Telegram sends this before charging the user. You **must** respond within 10 seconds.

```python
PreCheckoutQueryHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import PreCheckoutQueryHandler

async def pre_checkout(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload == "valid_payload":
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Invalid payment.")

app.add_handler(PreCheckoutQueryHandler(pre_checkout))
```

## ShippingQueryHandler

Handles shipping info requests during payments when flexible pricing is enabled.

```python
ShippingQueryHandler(callback, block=True)
```

**Usage:**

```python
from telegram import ShippingOption, LabeledPrice
from telegram.ext import ShippingQueryHandler

async def shipping(update, context):
    query = update.shipping_query
    options = [
        ShippingOption("standard", "Standard", [LabeledPrice("Shipping", 500)]),
        ShippingOption("express", "Express", [LabeledPrice("Shipping", 1200)]),
    ]
    await query.answer(ok=True, shipping_options=options)

app.add_handler(ShippingQueryHandler(shipping))
```

## ChatMemberHandler

Handles changes in chat membership status (joins, leaves, bans, promotions).

```python
ChatMemberHandler(callback, chat_member_types=None, block=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `chat_member_types` | `int \| None` | `ChatMemberHandler.MY_CHAT_MEMBER` (bot's own status), `ChatMemberHandler.CHAT_MEMBER` (other users), or `None` (both). |

**Constants:**

| Constant | Value | Description |
|----------|-------|-------------|
| `MY_CHAT_MEMBER` | `-1` | Bot was added/removed/promoted/demoted. |
| `CHAT_MEMBER` | `0` | A user joined/left/was banned/promoted. |

**Usage:**

```python
from telegram.ext import ChatMemberHandler

async def track_members(update, context):
    member = update.chat_member
    old = member.old_chat_member.status
    new = member.new_chat_member.status
    user = member.new_chat_member.user.full_name
    await context.bot.send_message(
        member.chat.id, f"{user}: {old} -> {new}"
    )

# Track other users' membership changes
app.add_handler(ChatMemberHandler(track_members, ChatMemberHandler.CHAT_MEMBER))

# Track bot's own status (added to / removed from chats)
app.add_handler(ChatMemberHandler(bot_status, ChatMemberHandler.MY_CHAT_MEMBER))
```

**Note:** Requires `allowed_updates=Update.ALL_TYPES` in `run_polling()` to receive `chat_member` updates.

## ChatJoinRequestHandler

Handles requests to join chats where the bot is admin and join approval is enabled.

```python
ChatJoinRequestHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import ChatJoinRequestHandler

async def handle_join(update, context):
    request = update.chat_join_request
    # Auto-approve or apply logic
    await request.approve()
    # Or: await request.decline()

app.add_handler(ChatJoinRequestHandler(handle_join))
```

## PollHandler

Handles poll status updates (when a poll is stopped or receives new votes in anonymous polls).

```python
PollHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import PollHandler

async def poll_update(update, context):
    poll = update.poll
    total = sum(o.voter_count for o in poll.options)
    results = ", ".join(f"{o.text}: {o.voter_count}" for o in poll.options)
    # Store or display: poll.id, results, total

app.add_handler(PollHandler(poll_update))
```

## PollAnswerHandler

Handles individual poll answer submissions (non-anonymous polls only).

```python
PollAnswerHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import PollAnswerHandler

async def poll_answer(update, context):
    answer = update.poll_answer
    user_id = answer.user.id
    poll_id = answer.poll_id
    option_ids = answer.option_ids  # list of selected option indices
    # Empty option_ids means user retracted their vote

app.add_handler(PollAnswerHandler(poll_answer))
```

## ChosenInlineResultHandler

Handles notifications when a user selects an inline query result. Requires feedback collection enabled via BotFather (`/setinlinefeedback`).

```python
ChosenInlineResultHandler(callback, pattern=None, block=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `pattern` | `str \| re.Pattern \| None` | Regex against `ChosenInlineResult.result_id`. Matches added to `context.matches`. |

**Usage:**

```python
from telegram.ext import ChosenInlineResultHandler

async def result_chosen(update, context):
    result = update.chosen_inline_result
    result_id = result.result_id
    query = result.query
    user = result.from_user.id
    # Track which result was chosen for analytics

app.add_handler(ChosenInlineResultHandler(result_chosen))
```

## PrefixHandler

Handles messages starting with a custom prefix character (like `!`, `.`, `#`) instead of `/`.

```python
PrefixHandler(prefix, command, callback, filters=None, block=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `prefix` | `str \| Collection[str]` | Prefix character(s), e.g., `"!"` or `["!", "."]`. |
| `command` | `str \| Collection[str]` | Command name(s) after the prefix. |
| `filters` | `BaseFilter \| None` | Additional filter. |

**Usage:**

```python
from telegram.ext import PrefixHandler

async def handle_ban(update, context):
    # Matches "!ban user123" or ".ban user123"
    args = context.args  # ["user123"]
    await update.message.reply_text(f"Banning: {args}")

app.add_handler(PrefixHandler(["!", "."], "ban", handle_ban))
```

**Note:** `context.args` works the same as `CommandHandler` — whitespace-split list of arguments after the prefix+command.

## TypeHandler

Generic handler that matches updates by Python type. Useful for custom update types or catch-all processing.

```python
TypeHandler(type, callback, strict=False, block=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `type` | `type` | The Python type to match against. |
| `strict` | `bool` | If `True`, requires exact type match (`type(update) is type`). If `False` (default), uses `isinstance()`. |

**Usage:**

```python
from telegram import Update
from telegram.ext import TypeHandler

async def log_all(update, context):
    # Logs every single update, regardless of type
    print(f"Update: {update.update_id}")

app.add_handler(TypeHandler(Update, log_all), group=1)
```

## Common Patterns

### Auto-approve chat join requests

```python
from telegram.ext import ChatJoinRequestHandler

async def auto_approve(update, context):
    await update.chat_join_request.approve()

app.add_handler(ChatJoinRequestHandler(auto_approve))
```

### Log all updates with TypeHandler

```python
from telegram import Update
from telegram.ext import TypeHandler

async def log_all(update, context):
    print(f"Update {update.update_id}: {update.to_dict()}")

app.add_handler(TypeHandler(Update, log_all), group=1)
```

## Related

- [event-handlers.md](event-handlers.md) — reactions, boosts, and business account event handlers
- [command-handler.md](command-handler.md) — standard `/command` handling
- [message-handler.md](message-handler.md) — message-based handling with filters
- [callback-query-handler.md](callback-query-handler.md) — inline keyboard button presses
- [inline-query-handler.md](inline-query-handler.md) — inline query handling (pairs with ChosenInlineResultHandler)
- [conversation-handler.md](conversation-handler.md) — multi-step flows using any of these handlers
- [index.md](index.md) — handler overview and routing
- [Telegram API — Payments](../../api/bots/payments/index.md) — payment flow and pre-checkout queries in the API specification
- [Telegram API — Chat](../../api/bots/chat/index.md) — chat membership and management in the API specification
