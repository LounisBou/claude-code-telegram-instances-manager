# Bot

> Core class for interacting with the Telegram Bot API — wraps every API method as an async Python method.

## Overview

`telegram.Bot` is the central class in python-telegram-bot that provides direct access to all Telegram Bot API methods. Every method is async and returns the corresponding Telegram type. In most handler code you should prefer the shortcut methods on `Update`/`Message` objects (e.g., `update.message.reply_text()`) which auto-fill `chat_id` and `message_thread_id`; use `Bot` directly for operations that have no shortcut or when you need to target a different chat.

## Quick Usage

```python
from telegram import Bot

bot = Bot(token="123456:ABC-DEF")

async def main():
    me = await bot.get_me()
    print(me.username)

    await bot.send_message(chat_id=12345, text="Hello!")
```

Within an `ApplicationBuilder` context the bot is available as `application.bot` or inside handlers as `context.bot`.

## Key Classes

### `telegram.Bot`

```python
Bot(
    token: str,
    base_url: str = "https://api.telegram.org/bot",
    base_file_url: str = "https://api.telegram.org/file/bot",
    request: BaseRequest | None = None,
    get_updates_request: BaseRequest | None = None,
    private_key: bytes | None = None,
    private_key_password: bytes | None = None,
    local_mode: bool = False,
)
```

**Key Parameters**

| Param | Description |
|---|---|
| `token` | Bot token from @BotFather. |
| `base_url` | Custom Bot API server URL. Change when running a local Bot API server. |
| `base_file_url` | Custom file download URL. Change alongside `base_url` for local servers. |
| `request` | Custom `BaseRequest` instance for all requests except `get_updates`. |
| `get_updates_request` | Custom `BaseRequest` instance for `get_updates` (allows separate timeout/pool config). |
| `private_key` | Private key for decrypting Telegram Passport data. |
| `local_mode` | Set `True` when using a local Bot API server; changes file handling behavior. |

**Key Properties**

| Property | Type | Description |
|---|---|---|
| `token` | `str` | The bot token. |
| `bot` | `User` | The bot's `User` object (populated after `get_me()` or `initialize()`). |
| `id` | `int` | Bot user id. |
| `username` | `str` | Bot username (without @). |
| `name` | `str` | Bot username prefixed with @ (e.g., `@MyBot`). |
| `first_name` | `str` | Bot's first name. |
| `last_name` | `str` | Bot's last name (may be empty). |
| `link` | `str` | `t.me/<username>` deep link. |
| `local_mode` | `bool` | Whether local Bot API mode is active. |

**Lifecycle Methods**

| Method | Returns | Description |
|---|---|---|
| `async initialize()` | `None` | Calls `get_me()` to populate bot info and initializes the request backend. Called automatically by `Application`. |
| `async shutdown()` | `None` | Shuts down the request backend. Called automatically by `Application`. |
| `async get_me()` | `User` | Returns basic info about the bot. |

---

### Sending Methods

All async. All accept optional keyword arguments: `read_timeout`, `write_timeout`, `connect_timeout`, `pool_timeout`, `api_kwargs`.

| Method | Returns |
|---|---|
| `send_message(chat_id, text, parse_mode=None, entities=None, disable_notification=None, protect_content=None, reply_markup=None, reply_parameters=None, message_thread_id=None, link_preview_options=None, business_connection_id=None, message_effect_id=None)` | `Message` |
| `send_photo(chat_id, photo, caption=None, parse_mode=None, ...)` | `Message` |
| `send_audio(chat_id, audio, caption=None, ...)` | `Message` |
| `send_document(chat_id, document, caption=None, ...)` | `Message` |
| `send_video(chat_id, video, caption=None, ...)` | `Message` |
| `send_voice(chat_id, voice, caption=None, ...)` | `Message` |
| `send_animation(chat_id, animation, caption=None, ...)` | `Message` |
| `send_sticker(chat_id, sticker, ...)` | `Message` |
| `send_poll(chat_id, question, options, ...)` | `Message` |
| `send_location(chat_id, latitude, longitude, ...)` | `Message` |
| `send_venue(chat_id, latitude, longitude, title, address, ...)` | `Message` |
| `send_contact(chat_id, phone_number, first_name, ...)` | `Message` |
| `send_media_group(chat_id, media, ...)` | `list[Message]` |
| `send_dice(chat_id, emoji=None, ...)` | `Message` |
| `send_chat_action(chat_id, action, ...)` | `bool` |
| `copy_message(chat_id, from_chat_id, message_id, ...)` | `MessageId` |
| `forward_message(chat_id, from_chat_id, message_id, ...)` | `Message` |

**`send_message` parameters in detail:**

- `chat_id` — `int | str`. Target chat id or `@channelusername`.
- `text` — `str`. Message text, 1-4096 characters.
- `parse_mode` — `str | None`. `"HTML"`, `"MarkdownV2"`, or `"Markdown"` (legacy).
- `entities` — `list[MessageEntity] | None`. Explicit formatting entities instead of parse_mode.
- `disable_notification` — `bool | None`. Send silently.
- `protect_content` — `bool | None`. Prevent forwarding/saving.
- `reply_markup` — `InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None`.
- `reply_parameters` — `ReplyParameters | None`. Quote/reply configuration.
- `message_thread_id` — `int | None`. Forum topic id.
- `link_preview_options` — `LinkPreviewOptions | None`. Control link preview behavior.
- `business_connection_id` — `str | None`. Send on behalf of a business account.
- `message_effect_id` — `str | None`. Trigger a message effect.

---

### Editing Methods

| Method | Returns |
|---|---|
| `edit_message_text(text, chat_id=None, message_id=None, inline_message_id=None, parse_mode=None, reply_markup=None, ...)` | `Message` |
| `edit_message_caption(chat_id=None, message_id=None, inline_message_id=None, caption=None, ...)` | `Message` |
| `edit_message_media(media, chat_id=None, message_id=None, inline_message_id=None, reply_markup=None, ...)` | `Message` |
| `edit_message_reply_markup(chat_id=None, message_id=None, inline_message_id=None, reply_markup=None, ...)` | `Message` |
| `delete_message(chat_id, message_id, ...)` | `bool` |
| `delete_messages(chat_id, message_ids, ...)` | `bool` |

For inline messages, pass `inline_message_id` instead of `chat_id`+`message_id`. When editing inline messages the return type is `bool` (`True`), not `Message`.

---

### Chat Management

| Method | Returns |
|---|---|
| `get_chat(chat_id)` | `ChatFullInfo` |
| `get_chat_member(chat_id, user_id)` | `ChatMember` |
| `get_chat_member_count(chat_id)` | `int` |
| `ban_chat_member(chat_id, user_id, until_date=None, revoke_messages=None)` | `bool` |
| `unban_chat_member(chat_id, user_id, only_if_banned=None)` | `bool` |
| `restrict_chat_member(chat_id, user_id, permissions, until_date=None)` | `bool` |
| `promote_chat_member(chat_id, user_id, can_change_info=None, can_post_messages=None, ...)` | `bool` |
| `leave_chat(chat_id)` | `bool` |
| `set_chat_title(chat_id, title)` | `bool` |
| `set_chat_description(chat_id, description)` | `bool` |
| `export_chat_invite_link(chat_id)` | `str` |

---

### Updates / Webhooks

| Method | Returns |
|---|---|
| `get_updates(offset=None, limit=None, timeout=None, allowed_updates=None)` | `list[Update]` |
| `set_webhook(url, certificate=None, max_connections=None, allowed_updates=None, ip_address=None, drop_pending_updates=None, secret_token=None)` | `bool` |
| `delete_webhook(drop_pending_updates=None)` | `bool` |
| `get_webhook_info()` | `WebhookInfo` |

---

### Bot Configuration

| Method | Returns |
|---|---|
| `set_my_commands(commands, scope=None, language_code=None)` | `bool` |
| `get_my_commands(scope=None, language_code=None)` | `list[BotCommand]` |
| `delete_my_commands(scope=None, language_code=None)` | `bool` |
| `get_me()` | `User` |

---

### Callback Queries

```python
async answer_callback_query(
    callback_query_id: str,
    text: str | None = None,
    show_alert: bool = False,
    url: str | None = None,
    cache_time: int | None = None,
) -> bool
```

---

### Inline Queries

```python
async answer_inline_query(
    inline_query_id: str,
    results: list[InlineQueryResult],
    cache_time: int | None = None,
    is_personal: bool | None = None,
    next_offset: str | None = None,
    button: InlineQueryResultsButton | None = None,
) -> bool
```

---

### Payments

| Method | Returns |
|---|---|
| `send_invoice(chat_id, title, description, payload, currency, prices, ...)` | `Message` |
| `answer_shipping_query(shipping_query_id, ok, shipping_options=None, error_message=None)` | `bool` |
| `answer_pre_checkout_query(pre_checkout_query_id, ok, error_message=None)` | `bool` |

## Common Patterns

### Send a formatted message with an inline keyboard

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Yes", callback_data="yes"),
     InlineKeyboardButton("No", callback_data="no")],
])

await bot.send_message(
    chat_id=chat_id,
    text="<b>Confirm?</b>",
    parse_mode="HTML",
    reply_markup=keyboard,
)
```

### Edit a message after a callback query

```python
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # acknowledge the callback (shortcut for answer_callback_query)

    await query.edit_message_text(text=f"You selected: {query.data}")
```

### Prefer shortcut methods in handlers

```python
# Preferred -- auto-fills chat_id and message_thread_id
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

# Equivalent but more verbose
async def echo_verbose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=update.message.text,
    )
```

> **Guideline:** In handler callbacks, prefer shortcut methods on `Update`/`Message` objects (e.g., `update.message.reply_text()`, `query.answer()`, `query.edit_message_text()`) over calling `context.bot.<method>()` directly. The shortcuts auto-fill `chat_id` and `message_thread_id`.

## Related

- [Application](application.md)
- [Types -- Messages](types/messages.md)
- [Types -- Keyboards](types/keyboards.md)
- [Types -- Media](types/media.md)
- [Telegram API -- Sending Messages](../api/bots/messages/sending.md)
- [Telegram API -- Media](../api/bots/media/index.md)
