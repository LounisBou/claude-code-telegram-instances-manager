# Event Handlers

> Handlers for reactions, boosts, and business account events.

## Overview

These handlers cover newer Telegram features introduced for richer user interactions and business integrations. They handle message reactions, channel boost events, business account connections, business message deletions, and paid media purchases. All share the standard callback signature `async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE)` and the `block` parameter (default `True`).

## Quick Usage

```python
from telegram.ext import MessageReactionHandler

async def reaction_update(update, context):
    r = update.message_reaction
    new_reactions = r.new_reaction
    await context.bot.send_message(r.chat.id, f"Reaction changed on message {r.message_id}")

app.add_handler(MessageReactionHandler(reaction_update))
```

## MessageReactionHandler

Handles message reaction updates (added/removed reactions).

```python
MessageReactionHandler(callback, message_reaction_types=None, block=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `message_reaction_types` | `int \| None` | `MessageReactionHandler.MESSAGE_REACTION` (individual), `MessageReactionHandler.MESSAGE_REACTION_COUNT` (anonymous count), or `None` (both). |

**Constants:**

| Constant | Description |
|----------|-------------|
| `MESSAGE_REACTION` | Individual user reaction updates (shows who reacted). |
| `MESSAGE_REACTION_COUNT` | Anonymous reaction count updates. |

**Usage:**

```python
from telegram.ext import MessageReactionHandler

async def reaction_update(update, context):
    if update.message_reaction:
        r = update.message_reaction
        new_reactions = r.new_reaction  # list of ReactionType
        old_reactions = r.old_reaction
    elif update.message_reaction_count:
        r = update.message_reaction_count
        reactions = r.reactions  # list of ReactionCount

app.add_handler(MessageReactionHandler(reaction_update))
```

## ChatBoostHandler

Handles chat boost and boost removal events.

```python
ChatBoostHandler(callback, chat_boost_types=None, block=True)
```

| Param | Type | Description |
|-------|------|-------------|
| `chat_boost_types` | `int \| None` | `ChatBoostHandler.CHAT_BOOST` (new boost), `ChatBoostHandler.REMOVED_CHAT_BOOST` (removed), or `None` (both). |

**Usage:**

```python
from telegram.ext import ChatBoostHandler

async def boost_event(update, context):
    if update.chat_boost:
        boost = update.chat_boost.boost
        source = boost.source  # ChatBoostSource
    elif update.removed_chat_boost:
        removed = update.removed_chat_boost

app.add_handler(ChatBoostHandler(boost_event))
```

## BusinessConnectionHandler

Handles updates about the bot's connection to a Telegram Business account.

```python
BusinessConnectionHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import BusinessConnectionHandler

async def business_connection(update, context):
    conn = update.business_connection
    user_id = conn.user.id
    is_enabled = conn.is_enabled
    can_reply = conn.can_reply

app.add_handler(BusinessConnectionHandler(business_connection))
```

## BusinessMessagesDeletedHandler

Handles notifications about messages deleted in a business account chat.

```python
BusinessMessagesDeletedHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import BusinessMessagesDeletedHandler

async def biz_messages_deleted(update, context):
    deleted = update.deleted_business_messages
    chat_id = deleted.chat.id
    message_ids = deleted.message_ids
    connection_id = deleted.business_connection_id

app.add_handler(BusinessMessagesDeletedHandler(biz_messages_deleted))
```

## PaidMediaPurchasedHandler

Handles paid media purchase events.

```python
PaidMediaPurchasedHandler(callback, block=True)
```

**Usage:**

```python
from telegram.ext import PaidMediaPurchasedHandler

async def paid_media(update, context):
    purchase = update.purchased_paid_media
    from_user = purchase.from_user
    payload = purchase.paid_media_payload

app.add_handler(PaidMediaPurchasedHandler(paid_media))
```

## Common Patterns

### Track reactions per message

```python
from telegram.ext import MessageReactionHandler

async def track_reactions(update, context):
    if update.message_reaction:
        r = update.message_reaction
        key = f"reactions_{r.chat.id}_{r.message_id}"
        context.bot_data.setdefault(key, [])
        for reaction in r.new_reaction:
            context.bot_data[key].append({
                "user": r.user.id,
                "emoji": reaction.emoji,
            })

app.add_handler(MessageReactionHandler(track_reactions, MessageReactionHandler.MESSAGE_REACTION))
```

### Log business account connections

```python
from telegram.ext import BusinessConnectionHandler

async def log_business(update, context):
    conn = update.business_connection
    status = "connected" if conn.is_enabled else "disconnected"
    print(f"Business {status}: user {conn.user.id}, can_reply={conn.can_reply}")

app.add_handler(BusinessConnectionHandler(log_business))
```

## Related

- [other-handlers.md](other-handlers.md) — payments, membership, polls, inline results, prefix commands, and generic type matching
- [index.md](index.md) — handler overview and routing
- [callback-query-handler.md](callback-query-handler.md) — inline keyboard button presses
