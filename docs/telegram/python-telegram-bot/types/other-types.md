# Other Types

> Callback queries, polls, web apps, menu buttons, and miscellaneous interaction and UI types.

## Overview

This file covers interaction and UI types that don't fit into messages, media, or keyboards. These include CallbackQuery, Poll, WebAppInfo, MenuButton, and structural types like ReplyParameters and LinkPreviewOptions. For chat administration types (bot commands, permissions, members, invite links, forum topics), see [chat-management.md](chat-management.md).

## Quick Usage

```python
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Selected: {query.data}")
```

## Key Classes

### CallbackQuery

Incoming callback from an inline keyboard button press. Received via `update.callback_query`.

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique query identifier. |
| `from_user` | `User` | User who pressed the button. |
| `chat_instance` | `str` | Global identifier for the chat the button was in. |
| `message` | `Message \| None` | Message with the button (if available). |
| `data` | `str \| None` | Data from the `callback_data` of the button (1-64 bytes). |
| `game_short_name` | `str \| None` | Short name of a game. |
| `inline_message_id` | `str \| None` | Identifier of the inline message (if button was on an inline message). |

**Methods** (all async)

| Method | Returns | Description |
|---|---|---|
| `answer(text=None, show_alert=False, url=None, cache_time=None)` | `bool` | Acknowledge the callback. Must be called even with no notification. `show_alert=True` displays a popup instead of a toast. |
| `edit_message_text(text, ...)` | `Message` | Edit the message that had the button. |
| `edit_message_caption(caption=None, ...)` | `Message` | Edit the caption. |
| `edit_message_media(media, ...)` | `Message` | Replace the media. |
| `edit_message_reply_markup(reply_markup=None, ...)` | `Message` | Edit the inline keyboard. |
| `delete_message()` | `bool` | Delete the message. |
| `pin_message(...)` | `bool` | Pin the message. |
| `unpin_message(...)` | `bool` | Unpin the message. |

---

### Poll and PollOption

**Poll** -- a poll attached to a message.

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique poll identifier. |
| `question` | `str` | Poll question (1-300 chars). |
| `options` | `tuple[PollOption, ...]` | List of answer options. |
| `total_voter_count` | `int` | Total number of voters. |
| `is_closed` | `bool` | Whether the poll is closed. |
| `is_anonymous` | `bool` | Whether the poll is anonymous. |
| `type` | `str` | `"regular"` or `"quiz"`. |
| `allows_multiple_answers` | `bool` | Whether multiple answers are allowed. |
| `correct_option_id` | `int \| None` | 0-based index of the correct answer (quiz mode). |
| `explanation` | `str \| None` | Explanation shown after answering (quiz mode). |

**PollOption**

| Attribute | Type |
|---|---|
| `text` | `str` |
| `voter_count` | `int` |

**PollAnswer** -- a user's answer to a non-anonymous poll.

| Attribute | Type | Description |
|---|---|---|
| `poll_id` | `str` | The poll identifier. |
| `option_ids` | `tuple[int, ...]` | 0-based indices of chosen options (empty if retracted). |
| `user` | `User \| None` | The user who voted (if the poll was sent by the bot). |
| `voter_chat` | `Chat \| None` | The chat that voted (for polls in channels/anonymous admins). |

---

### WebAppInfo, WebAppData, SentWebAppMessage

**WebAppInfo** -- describes a Web App.

| Attribute | Type | Description |
|---|---|---|
| `url` | `str` | An HTTPS URL of a Web App. |

**WebAppData** -- data sent from a Web App.

| Attribute | Type |
|---|---|
| `data` | `str` |
| `button_text` | `str` |

**SentWebAppMessage** -- describes an inline message sent by a Web App.

| Attribute | Type |
|---|---|
| `inline_message_id` | `str \| None` |

---

### MenuButton and Subclasses

| Subclass | Attributes | Description |
|---|---|---|
| `MenuButtonDefault()` | -- | Default bot menu button behavior. |
| `MenuButtonCommands()` | -- | Show the bot's command list. |
| `MenuButtonWebApp(text, web_app)` | `text` (str), `web_app` (WebAppInfo) | Open a Web App. |

---

### LinkPreviewOptions

Controls link preview behavior in messages.

| Attribute | Type | Description |
|---|---|---|
| `is_disabled` | `bool \| None` | Disable link preview entirely. |
| `url` | `str \| None` | URL to preview (overrides auto-detected). |
| `prefer_small_media` | `bool \| None` | Show small preview media. |
| `prefer_large_media` | `bool \| None` | Show large preview media. |
| `show_above_text` | `bool \| None` | Show preview above message text. |

---

### ReplyParameters

Controls reply behavior when sending a message.

| Attribute | Type | Description |
|---|---|---|
| `message_id` | `int` | ID of the message to reply to. |
| `chat_id` | `int \| str \| None` | Chat containing the replied-to message (if different from target). |
| `allow_sending_without_reply` | `bool \| None` | Send even if the replied-to message is not found. |
| `quote` | `str \| None` | Quoted part of the replied-to message. |
| `quote_parse_mode` | `str \| None` | Parse mode for the quote. |
| `quote_entities` | `tuple[MessageEntity, ...] \| None` | Entities in the quote. |
| `quote_position` | `int \| None` | Position of the quote in the original message (UTF-16 offset). |

---

### LoginUrl

Used in `InlineKeyboardButton` for seamless Telegram Login.

| Attribute | Type | Description |
|---|---|---|
| `url` | `str` | Login URL. |
| `forward_text` | `str \| None` | Button text for the forwarded message. |
| `bot_username` | `str \| None` | Username of the bot for authorization. |
| `request_write_access` | `bool \| None` | Request permission to send messages to the user. |

---

### SwitchInlineQueryChosenChat

Used in `InlineKeyboardButton` to prompt the user to select a chat for inline query.

| Attribute | Type | Description |
|---|---|---|
| `query` | `str \| None` | Default inline query text. |
| `allow_user_chats` | `bool \| None` | Allow selecting private chats with users. |
| `allow_bot_chats` | `bool \| None` | Allow selecting chats with bots. |
| `allow_group_chats` | `bool \| None` | Allow selecting group chats. |
| `allow_channel_chats` | `bool \| None` | Allow selecting channel chats. |

---

### CopyTextButton

Used in `InlineKeyboardButton` to copy text to clipboard when pressed.

| Attribute | Type | Description |
|---|---|---|
| `text` | `str` | Text to copy to clipboard (1-256 chars). |

## Common Patterns

### Answer a callback query and edit the message

```python
async def button_handler(update: Update, context: ContextTypes.DefaultType):
    query = update.callback_query
    await query.answer("Processing...")  # toast notification
    await query.edit_message_text(f"Selected: {query.data}")
```

## Related

- [index.md](index.md) -- types overview and routing table
- [chat-management.md](chat-management.md) -- bot commands, chat permissions, members, invite links, forum topics
- [messages.md](messages.md) -- Update and Message types
- [keyboards.md](keyboards.md) -- InlineKeyboardButton uses LoginUrl, CopyTextButton, SwitchInlineQueryChosenChat
- [media.md](media.md) -- media types referenced by Message
- [../bot.md](../bot.md) -- Bot methods that accept/return these types
- [../handlers/callback-query-handler.md](../handlers/callback-query-handler.md) -- handling CallbackQuery
- [Telegram API — Interactivity](../../api/bots/interactivity/index.md) -- callback queries, polls, commands, and other interactive types in the API specification
