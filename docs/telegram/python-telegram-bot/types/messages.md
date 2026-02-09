# Message Types

> Core types for incoming updates, messages, chats, users, and text entities.

## Overview

These are the most frequently used types when building a Telegram bot. An `Update` wraps every incoming event, `Message` represents a single message in a chat, and `Chat`/`User` identify where and who. `MessageEntity` describes formatted text regions within a message.

## Quick Usage

```python
async def handler(update, context):
    user = update.effective_user
    chat = update.effective_chat
    text = update.message.text
    await update.message.reply_text(f"{user.first_name} in {chat.id}: {text}")
```

## Key Classes

### `Update`

Incoming update wrapper. Every handler callback receives an `Update` as its first argument.

**Key Attributes**

| Attribute | Type | Description |
|---|---|---|
| `update_id` | `int` | Unique update identifier. |
| `message` | `Message \| None` | New incoming message. |
| `edited_message` | `Message \| None` | Edited message. |
| `channel_post` | `Message \| None` | New channel post. |
| `edited_channel_post` | `Message \| None` | Edited channel post. |
| `callback_query` | `CallbackQuery \| None` | Incoming callback query (inline button press). |
| `inline_query` | `InlineQuery \| None` | Incoming inline query. |
| `chosen_inline_result` | `ChosenInlineResult \| None` | Result chosen by user from inline query. |
| `shipping_query` | `ShippingQuery \| None` | Incoming shipping query (payments). |
| `pre_checkout_query` | `PreCheckoutQuery \| None` | Incoming pre-checkout query (payments). |
| `poll` | `Poll \| None` | Poll state change. |
| `poll_answer` | `PollAnswer \| None` | User changed vote in a non-anonymous poll. |
| `my_chat_member` | `ChatMemberUpdated \| None` | Bot's own chat member status changed. |
| `chat_member` | `ChatMemberUpdated \| None` | A chat member's status changed. |
| `chat_join_request` | `ChatJoinRequest \| None` | User requested to join a chat. |
| `chat_boost` | `ChatBoostUpdated \| None` | Chat boost added. |
| `removed_chat_boost` | `ChatBoostRemoved \| None` | Chat boost removed. |
| `message_reaction` | `MessageReactionUpdated \| None` | Reaction to a message changed. |
| `message_reaction_count` | `MessageReactionCountUpdated \| None` | Anonymous reaction count changed. |
| `business_connection` | `BusinessConnection \| None` | Bot connected/disconnected from business account. |
| `business_message` | `Message \| None` | New message from connected business account. |
| `edited_business_message` | `Message \| None` | Edited business message. |
| `deleted_business_messages` | `BusinessMessagesDeleted \| None` | Deleted business messages. |
| `paid_media_purchased` | `PaidMediaPurchased \| None` | Paid media purchased by a user. |

**Key Properties**

| Property | Type | Description |
|---|---|---|
| `effective_message` | `Message \| None` | The message regardless of which attribute it came from (message, edited_message, channel_post, callback_query.message, etc.). |
| `effective_chat` | `Chat \| None` | The chat extracted from whichever sub-object is present. |
| `effective_user` | `User \| None` | The user who triggered this update. |
| `effective_sender` | `User \| Chat \| None` | The sender -- a User in most cases, or a Chat for anonymous channel posts. |

---

### `Message`

A message in a chat.

**Key Attributes**

| Attribute | Type | Description |
|---|---|---|
| `message_id` | `int` | Unique message identifier within the chat. |
| `date` | `datetime` | Date the message was sent (UTC). |
| `chat` | `Chat` | Chat the message belongs to. |
| `from_user` | `User \| None` | Sender (None for channel posts). |
| `text` | `str \| None` | Text content (for text messages). |
| `entities` | `tuple[MessageEntity, ...] \| None` | Formatting entities in text. |
| `caption` | `str \| None` | Caption for media messages. |
| `caption_entities` | `tuple[MessageEntity, ...] \| None` | Formatting entities in caption. |
| `photo` | `tuple[PhotoSize, ...] \| None` | Available photo sizes (sorted by size ascending; use `[-1]` for largest). |
| `document` | `Document \| None` | Attached document. |
| `audio` | `Audio \| None` | Attached audio file. |
| `video` | `Video \| None` | Attached video. |
| `voice` | `Voice \| None` | Attached voice message. |
| `animation` | `Animation \| None` | Attached animation (GIF). |
| `sticker` | `Sticker \| None` | Attached sticker. |
| `reply_to_message` | `Message \| None` | The message this is a reply to. |
| `reply_markup` | `InlineKeyboardMarkup \| None` | Inline keyboard attached to the message. |
| `forward_origin` | `MessageOrigin \| None` | Info about the original message if forwarded. |
| `message_thread_id` | `int \| None` | Forum topic thread id. |
| `link_preview_options` | `LinkPreviewOptions \| None` | Link preview settings. |

**Key Property**

- `effective_attachment` -- returns the media attachment (PhotoSize tuple, Document, Audio, Video, etc.) if any, else `None`.

**Shortcut Methods** (all async)

| Method | Returns | Description |
|---|---|---|
| `reply_text(text, **kwargs)` | `Message` | Send text reply to same chat. Auto-fills `chat_id`. |
| `reply_photo(photo, **kwargs)` | `Message` | Send photo reply. |
| `reply_document(document, **kwargs)` | `Message` | Send document reply. |
| `reply_html(text, **kwargs)` | `Message` | Reply with `parse_mode="HTML"`. |
| `reply_markdown_v2(text, **kwargs)` | `Message` | Reply with `parse_mode="MarkdownV2"`. |
| `reply_media_group(media, **kwargs)` | `list[Message]` | Send media group reply. |
| `forward(chat_id, **kwargs)` | `Message` | Forward this message to another chat. |
| `copy(chat_id, **kwargs)` | `MessageId` | Copy this message to another chat (without "Forwarded from" header). |
| `delete(**kwargs)` | `bool` | Delete this message. |
| `edit_text(text, **kwargs)` | `Message` | Edit this message's text. |
| `edit_caption(caption=None, **kwargs)` | `Message` | Edit this message's caption. |
| `edit_media(media, **kwargs)` | `Message` | Edit this message's media. |
| `edit_reply_markup(reply_markup=None, **kwargs)` | `Message` | Edit this message's inline keyboard. |
| `pin(**kwargs)` | `bool` | Pin this message in the chat. |
| `unpin(**kwargs)` | `bool` | Unpin this message. |
| `get_url()` | `str \| None` | Get a URL link to this message (works for supergroups/channels). |

---

### `Chat`

Basic chat information. Present on every `Message`.

**Key Attributes**

| Attribute | Type | Description |
|---|---|---|
| `id` | `int` | Unique chat identifier. |
| `type` | `str` | One of `"private"`, `"group"`, `"supergroup"`, `"channel"`. |
| `title` | `str \| None` | Chat title (groups, supergroups, channels). |
| `username` | `str \| None` | Chat username (if set). |
| `first_name` | `str \| None` | First name (private chats). |
| `last_name` | `str \| None` | Last name (private chats). |

---

### `ChatFullInfo`

Extended chat information returned by `bot.get_chat(chat_id)`. Extends `Chat` with additional fields.

**Additional Attributes** (beyond Chat)

| Attribute | Type |
|---|---|
| `bio` | `str \| None` |
| `description` | `str \| None` |
| `invite_link` | `str \| None` |
| `permissions` | `ChatPermissions \| None` |
| `photo` | `ChatPhoto \| None` |
| `pinned_message` | `Message \| None` |
| `active_usernames` | `tuple[str, ...] \| None` |
| `available_reactions` | `tuple[ReactionType, ...] \| None` |

---

### `User`

A Telegram user or bot.

**Key Attributes**

| Attribute | Type | Description |
|---|---|---|
| `id` | `int` | Unique user identifier. |
| `is_bot` | `bool` | True if this user is a bot. |
| `first_name` | `str` | User's first name. |
| `last_name` | `str \| None` | User's last name. |
| `username` | `str \| None` | Username (without @). |
| `language_code` | `str \| None` | IETF language tag of the user's client. |
| `is_premium` | `bool \| None` | True if user has Telegram Premium. |

**Key Methods**

| Method | Returns | Description |
|---|---|---|
| `mention_html(name=None)` | `str` | HTML `<a>` tag mention. Uses `name` or `first_name` as display text. |
| `mention_markdown_v2(name=None)` | `str` | MarkdownV2 mention link. |
| `get_profile_photos(**kwargs)` | `UserProfilePhotos` | Fetch user's profile photos. |

**Key Properties**

| Property | Type | Description |
|---|---|---|
| `link` | `str` | `t.me/<username>` deep link. |
| `full_name` | `str` | `first_name` + `last_name` (if present). |

---

### `MessageEntity`

Describes a special entity in a message text (bold, link, mention, etc.).

**Key Attributes**

| Attribute | Type | Description |
|---|---|---|
| `type` | `str` | Entity type (see list below). |
| `offset` | `int` | Offset in UTF-16 code units. |
| `length` | `int` | Length in UTF-16 code units. |
| `url` | `str \| None` | For `"text_link"` -- the URL. |
| `user` | `User \| None` | For `"text_mention"` -- the mentioned user. |
| `language` | `str \| None` | For `"pre"` -- programming language. |
| `custom_emoji_id` | `str \| None` | For `"custom_emoji"` -- unique emoji identifier. |

**Entity Types**: `"mention"`, `"hashtag"`, `"cashtag"`, `"bot_command"`, `"url"`, `"email"`, `"phone_number"`, `"bold"`, `"italic"`, `"underline"`, `"strikethrough"`, `"spoiler"`, `"blockquote"`, `"expandable_blockquote"`, `"code"`, `"pre"`, `"text_link"`, `"text_mention"`, `"custom_emoji"`

**Key Method**

- `extract_from(text) -> str` -- Extract the entity's text from the full message text string.

---

### `MessageOrigin` and Subclasses

Information about the origin of a forwarded message. Abstract base class with four concrete subclasses.

| Subclass | Key Attributes |
|---|---|
| `MessageOriginUser` | `sender_user` (User), `date` (datetime) |
| `MessageOriginChat` | `sender_chat` (Chat), `author_signature` (str\|None), `date` |
| `MessageOriginChannel` | `chat` (Chat), `message_id` (int), `author_signature` (str\|None), `date` |
| `MessageOriginHiddenUser` | `sender_user_name` (str), `date` |

## Common Patterns

### Access the message and user from any update type

```python
async def handler(update: Update, context: ContextTypes.DefaultType):
    # Works regardless of whether it's a message, edited_message, channel_post, etc.
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message

    if message and message.text:
        await message.reply_text(f"You said: {message.text}")
```

### Parse entities from a message

```python
async def handle_message(update: Update, context: ContextTypes.DefaultType):
    message = update.message
    if not message.entities:
        return

    for entity in message.entities:
        if entity.type == "url":
            url = entity.extract_from(message.text)
            await message.reply_text(f"Found URL: {url}")
        elif entity.type == "text_link":
            await message.reply_text(f"Found link: {entity.url}")
        elif entity.type == "mention":
            username = entity.extract_from(message.text)  # includes @
            await message.reply_text(f"Mentioned: {username}")
```

### Mention a user with HTML formatting

```python
async def greet(update: Update, context: ContextTypes.DefaultType):
    user = update.effective_user
    await update.message.reply_html(
        f"Hello {user.mention_html()}! Your ID is {user.id}."
    )
```

## Related

- [index.md](index.md) -- types overview and routing table
- [media.md](media.md) -- media types referenced by Message (PhotoSize, Document, etc.)
- [keyboards.md](keyboards.md) -- keyboard markup types used in reply_markup
- [other-types.md](other-types.md) -- CallbackQuery, Poll, ChatMember, etc.
- [../bot.md](../bot.md) -- Bot methods that send/edit/delete messages
- [../handlers/index.md](../handlers/index.md) -- handlers that route Updates
- [Telegram API — Types](../../api/bots/types/index.md) -- type definitions in the API specification
