# Persistence

> Save bot_data, chat_data, user_data, conversation states, and callback data across bot restarts.

## Overview

The persistence system in python-telegram-bot v22.x automatically saves and restores data dictionaries and conversation handler states. You configure a persistence backend via `ApplicationBuilder`, and the `Application` handles reading data on startup and writing changes periodically. Built-in backends include `PicklePersistence` (file-based) and `DictPersistence` (in-memory, for testing).

## Quick Usage

```python
from telegram.ext import Application, PicklePersistence

persistence = PicklePersistence(filepath="bot_data.pickle")
app = Application.builder().token("BOT_TOKEN").persistence(persistence).build()
app.run_polling()
```

## Key Classes

### BasePersistence (abstract)

> Abstract base class for all persistence implementations. Subclass this to create a custom backend.

**Methods to implement (all async):**

| Method | Returns | Description |
|---|---|---|
| `get_bot_data()` | `dict` | Load bot-wide data. |
| `get_chat_data()` | `dict[int, dict]` | Load all chat data, keyed by chat_id. |
| `get_user_data()` | `dict[int, dict]` | Load all user data, keyed by user_id. |
| `get_conversations(name)` | `dict` | Load conversation states for the handler with the given `name`. |
| `get_callback_data()` | `tuple \| None` | Load stored callback data, or `None` if not available. |
| `update_bot_data(data)` | `None` | Persist updated bot_data dict. |
| `update_chat_data(chat_id, data)` | `None` | Persist updated data for a specific chat. |
| `update_user_data(user_id, data)` | `None` | Persist updated data for a specific user. |
| `update_conversation(name, key, new_state)` | `None` | Persist a conversation state change. `key` is the conversation key tuple; `new_state` is the new state or `None` to remove. |
| `update_callback_data(data)` | `None` | Persist updated callback data. |
| `drop_chat_data(chat_id)` | `None` | Remove all persisted data for a chat. |
| `drop_user_data(user_id)` | `None` | Remove all persisted data for a user. |
| `refresh_bot_data(bot_data)` | `None` | Refresh the in-memory bot_data from the persistence store. Called before each update processing. |
| `refresh_chat_data(chat_id, chat_data)` | `None` | Refresh in-memory chat_data from the persistence store. |
| `refresh_user_data(user_id, user_data)` | `None` | Refresh in-memory user_data from the persistence store. |
| `flush()` | `None` | Force-write all in-memory data to the persistence store. Called on shutdown. |

**Constructor:**

```python
BasePersistence(
    store_data: PersistenceInput | None = None,
    update_interval: int | float = 60,
)
```

- `store_data` -- which data types to persist (default: all).
- `update_interval` -- seconds between automatic persistence writes (default: 60).

---

### PicklePersistence

> File-based persistence using Python's pickle module.

**Constructor:**

```python
PicklePersistence(
    filepath: str | Path,
    store_data: PersistenceInput | None = None,
    single_file: bool = True,
    on_flush: bool = False,
    update_interval: int | float = 60,
    context_types: ContextTypes | None = None,
)
```

| Param | Type | Default | Description |
|---|---|---|---|
| `filepath` | `str \| Path` | required | File path for the pickle file. |
| `store_data` | `PersistenceInput \| None` | `None` (all) | Which data types to persist. |
| `single_file` | `bool` | `True` | If `True`, stores everything in one file. If `False`, creates separate files per data type (e.g., `filepath_bot_data`, `filepath_chat_data`). |
| `on_flush` | `bool` | `False` | If `True`, only writes to disk on explicit `flush()` calls (e.g., on shutdown). If `False`, writes on each `update_*` call (throttled by `update_interval`). |
| `update_interval` | `int \| float` | `60` | Minimum seconds between persistence writes. |
| `context_types` | `ContextTypes \| None` | `None` | Custom context types for proper deserialization. Required if using custom `ContextTypes`. |

---

### DictPersistence

> In-memory persistence with the same interface as PicklePersistence. Useful for testing or ephemeral bots. Data is lost on restart.

**Constructor:**

```python
DictPersistence(
    store_data: PersistenceInput | None = None,
    user_data_json: str = "",
    chat_data_json: str = "",
    bot_data_json: str = "",
    conversations_json: str = "",
    callback_data_json: str = "",
    update_interval: int | float = 60,
    context_types: ContextTypes | None = None,
)
```

- All `*_json` parameters accept JSON strings to pre-populate data. Pass empty string or omit for empty initial state.

**Properties for inspecting current state:**

- `user_data_json: str` -- current user_data as JSON string.
- `chat_data_json: str` -- current chat_data as JSON string.
- `bot_data_json: str` -- current bot_data as JSON string.
- `conversations_json: str` -- current conversation states as JSON string.
- `callback_data_json: str` -- current callback data as JSON string.

---

### PersistenceInput

> Controls which data types are persisted.

**Constructor:**

```python
PersistenceInput(
    bot_data: bool = True,
    chat_data: bool = True,
    user_data: bool = True,
    callback_data: bool = True,
)
```

Pass to `PicklePersistence(store_data=...)` or `DictPersistence(store_data=...)` to selectively enable/disable persistence for each data type.

## Common Patterns

### Basic pickle persistence setup

```python
from telegram.ext import Application, PicklePersistence, PersistenceInput

# Persist only user_data and chat_data (skip bot_data and callback_data)
store = PersistenceInput(bot_data=False, callback_data=False)
persistence = PicklePersistence(filepath="data.pickle", store_data=store)

app = Application.builder().token("BOT_TOKEN").persistence(persistence).build()
app.run_polling()
```

### Persistent conversation handler

```python
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start_callback)],
    states={
        CHOOSING: [MessageHandler(filters.TEXT, choice_callback)],
        TYPING: [MessageHandler(filters.TEXT, received_callback)],
    },
    fallbacks=[CommandHandler("cancel", cancel_callback)],
    name="my_conversation",  # required for persistence
    persistent=True,          # enables persistence for this handler
)
app.add_handler(conv_handler)
```

Both `name` and `persistent=True` must be set. The `name` is used as the key in `get_conversations()`/`update_conversation()`.

### Accessing persisted data in handlers

```python
async def handler(update, context):
    # Per-user data (auto-keyed by user_id)
    context.user_data["visits"] = context.user_data.get("visits", 0) + 1

    # Per-chat data (auto-keyed by chat_id)
    context.chat_data["last_message"] = update.message.text

    # Bot-wide data (shared across all chats/users)
    context.bot_data["total_messages"] = context.bot_data.get("total_messages", 0) + 1
```

Data is automatically persisted according to the configured `update_interval`.

## Related

- [Application](application.md) -- ApplicationBuilder.persistence() setup
- [Handlers](handlers/index.md) -- ConversationHandler persistent mode
- [Errors](errors.md) -- exception handling during persistence operations
