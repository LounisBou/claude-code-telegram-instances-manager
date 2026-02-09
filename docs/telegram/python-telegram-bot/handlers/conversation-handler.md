# ConversationHandler

> Multi-step conversation flows with state machine routing, timeouts, and optional persistence.

## Overview

`ConversationHandler` implements a per-user (or per-chat) finite state machine. Entry point handlers start the conversation, state handlers process input at each step, and fallback handlers catch unmatched updates. Each callback returns the next state key (an int or object) or `ConversationHandler.END` to terminate. The conversation key is a tuple derived from `(chat_id, user_id)` by default, configurable via `per_chat`/`per_user`/`per_message`.

## Quick Usage

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

NAME, AGE = range(2)

async def start(update, context):
    await update.message.reply_text("What is your name?")
    return NAME

async def name(update, context):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("How old are you?")
    return AGE

async def age(update, context):
    context.user_data["age"] = update.message.text
    await update.message.reply_text(f"Done! {context.user_data['name']}, age {context.user_data['age']}")
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END

conv = ConversationHandler(
    entry_points=[CommandHandler("register", start)],
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
        AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
app.add_handler(conv)
```

## Key Classes

### `ConversationHandler(entry_points, states, fallbacks, ...)`

**Constructor Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `entry_points` | `list[BaseHandler]` | required | Handlers that start the conversation. |
| `states` | `dict[object, list[BaseHandler]]` | required | Maps state keys to lists of handlers active in that state. |
| `fallbacks` | `list[BaseHandler]` | required | Handlers checked when no state handler matches. |
| `allow_reentry` | `bool` | `False` | If `True`, entry_points can restart an active conversation. |
| `per_chat` | `bool` | `True` | Include `chat_id` in conversation key. |
| `per_user` | `bool` | `True` | Include `user_id` in conversation key. |
| `per_message` | `bool` | `False` | Include `message_id` in conversation key. Set `True` for per-message inline keyboard flows. |
| `conversation_timeout` | `float \| timedelta \| None` | `None` | Auto-end conversation after inactivity (seconds or timedelta). |
| `name` | `str \| None` | `None` | Identifier for this conversation. Required if `persistent=True`. |
| `persistent` | `bool` | `False` | Persist conversation state across bot restarts (requires `name` and a persistence backend). |
| `map_to_parent` | `dict[object, object] \| None` | `None` | For nested conversations — maps child states to parent states. |
| `block` | `bool` | `True` | Default blocking behavior for internal handler resolution. |

**Constants:**

| Constant | Value | Description |
|----------|-------|-------------|
| `ConversationHandler.END` | `-1` | Return to end the conversation. |
| `ConversationHandler.TIMEOUT` | `-2` | State key used in `states` dict for timeout handler. |
| `ConversationHandler.WAITING` | `-3` | Internal state indicating a non-blocking handler is running. |

**Key Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `entry_points` | `list[BaseHandler]` | Entry handlers. |
| `states` | `dict` | State-to-handlers mapping. |
| `fallbacks` | `list[BaseHandler]` | Fallback handlers. |
| `conversations` | `dict[tuple, int]` | Current state for each active conversation key. |
| `name` | `str` | Conversation name. |

**Key Methods:**

| Method | Description |
|--------|-------------|
| `check_update(update)` | Checks if update matches current state's handlers, entry_points, or fallbacks. |

## Common Patterns

### Conversation with inline keyboard states

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

CHOOSING, CONFIRM = range(2)

async def start(update, context):
    keyboard = [[
        InlineKeyboardButton("Red", callback_data="red"),
        InlineKeyboardButton("Blue", callback_data="blue"),
    ]]
    await update.message.reply_text(
        "Pick a color:", reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING

async def color_chosen(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["color"] = query.data
    keyboard = [[
        InlineKeyboardButton("Confirm", callback_data="yes"),
        InlineKeyboardButton("Cancel", callback_data="no"),
    ]]
    await query.edit_message_text(
        f"You chose {query.data}. Confirm?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return CONFIRM

async def confirm(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "yes":
        await query.edit_message_text(f"Saved: {context.user_data['color']}")
    else:
        await query.edit_message_text("Cancelled.")
    return ConversationHandler.END

conv = ConversationHandler(
    entry_points=[CommandHandler("color", start)],
    states={
        CHOOSING: [CallbackQueryHandler(color_chosen)],
        CONFIRM: [CallbackQueryHandler(confirm)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
```

### Timeout handling

```python
TYPING = 0

async def timeout_handler(update, context):
    await context.bot.send_message(
        chat_id=context.user_data.get("chat_id"),
        text="Conversation timed out."
    )

conv = ConversationHandler(
    entry_points=[CommandHandler("survey", start)],
    states={
        TYPING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input)],
        ConversationHandler.TIMEOUT: [MessageHandler(filters.ALL, timeout_handler)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    conversation_timeout=300,  # 5 minutes
)
```

### Nested conversations

```python
# Child conversation returns map_to_parent states to control parent
child_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(child_start, pattern="^start_child$")],
    states={CHILD_STATE: [MessageHandler(filters.TEXT, child_input)]},
    fallbacks=[CommandHandler("cancel", child_cancel)],
    map_to_parent={
        ConversationHandler.END: PARENT_MENU,  # child END -> parent goes to PARENT_MENU
        CHILD_DONE: PARENT_NEXT,               # custom child state -> parent state
    },
)

parent_conv = ConversationHandler(
    entry_points=[CommandHandler("start", parent_start)],
    states={
        PARENT_MENU: [child_conv],  # embed child as a handler in parent state
        PARENT_NEXT: [MessageHandler(filters.TEXT, parent_next)],
    },
    fallbacks=[CommandHandler("cancel", parent_cancel)],
)
```

## Important Notes

- Every callback in `entry_points` and `states` **must** return the next state (int/object) or `ConversationHandler.END`. Returning `None` keeps the current state.
- The conversation key defaults to `(chat_id, user_id)`. For group chats where multiple users converse independently, this is correct. For a single conversation per chat (all users share state), set `per_user=False`.
- Set `per_message=True` when using inline keyboards so each message tracks its own conversation state independently.
- Fallbacks are checked **after** state handlers. Use them for `/cancel` commands or catch-all error handling.
- With `persistent=True`, supply a `name` and configure `app.builder().persistence(...)` with a persistence backend (e.g., `PicklePersistence`).

## Related

- [command-handler.md](command-handler.md) — commonly used as entry_points and fallbacks
- [message-handler.md](message-handler.md) — commonly used in states for text input
- [callback-query-handler.md](callback-query-handler.md) — commonly used in states for inline keyboard steps
- [filters.md](filters.md) — filter system used within state handlers
- [index.md](index.md) — handler overview and routing
- [Telegram API — Interactivity](../../api/bots/interactivity/index.md) — multi-step interaction patterns in the API specification
