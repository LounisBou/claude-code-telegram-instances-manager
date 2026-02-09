# Constants

> Library constants for parse modes, chat types, message limits, rate limits, and Telegram entity enumerations.

## Overview

The `telegram.constants` module provides typed constant classes for all Telegram Bot API enumerations and limits. Use these instead of raw strings or magic numbers to ensure correctness and get IDE autocompletion. All constant classes use string or integer values that match the Telegram Bot API specification.

## Quick Usage

```python
from telegram.constants import ParseMode, ChatAction, MessageLimit

await bot.send_message(chat_id=chat_id, text="<b>Hello</b>", parse_mode=ParseMode.HTML)
await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
```

## Constant Classes

### ParseMode

> Text formatting modes for messages and captions.

| Constant | Value |
|---|---|
| `ParseMode.HTML` | `"HTML"` |
| `ParseMode.MARKDOWN` | `"Markdown"` |
| `ParseMode.MARKDOWN_V2` | `"MarkdownV2"` |

Prefer `HTML` or `MARKDOWN_V2`. `MARKDOWN` is legacy and has escaping issues.

---

### ChatType

> Types of Telegram chats.

| Constant | Value |
|---|---|
| `ChatType.PRIVATE` | `"private"` |
| `ChatType.GROUP` | `"group"` |
| `ChatType.SUPERGROUP` | `"supergroup"` |
| `ChatType.CHANNEL` | `"channel"` |
| `ChatType.SENDER` | `"sender"` |

---

### ChatMemberStatus

> Possible statuses of a chat member.

| Constant | Value |
|---|---|
| `ChatMemberStatus.OWNER` | `"creator"` |
| `ChatMemberStatus.ADMINISTRATOR` | `"administrator"` |
| `ChatMemberStatus.MEMBER` | `"member"` |
| `ChatMemberStatus.RESTRICTED` | `"restricted"` |
| `ChatMemberStatus.LEFT` | `"left"` |
| `ChatMemberStatus.BANNED` | `"kicked"` |

---

### ChatAction

> Actions to broadcast via `send_chat_action()`. Displayed as "typing...", "sending photo...", etc.

| Constant | Value |
|---|---|
| `ChatAction.TYPING` | `"typing"` |
| `ChatAction.UPLOAD_PHOTO` | `"upload_photo"` |
| `ChatAction.UPLOAD_VIDEO` | `"upload_video"` |
| `ChatAction.RECORD_VIDEO` | `"record_video"` |
| `ChatAction.UPLOAD_VOICE` | `"upload_voice"` |
| `ChatAction.UPLOAD_DOCUMENT` | `"upload_document"` |
| `ChatAction.CHOOSE_STICKER` | `"choose_sticker"` |
| `ChatAction.FIND_LOCATION` | `"find_location"` |
| `ChatAction.RECORD_VOICE` | `"record_voice"` |
| `ChatAction.RECORD_VIDEO_NOTE` | `"record_video_note"` |
| `ChatAction.UPLOAD_VIDEO_NOTE` | `"upload_video_note"` |

---

### MessageEntityType

> Types of special entities in messages (formatting, links, mentions).

| Constant | Value |
|---|---|
| `MessageEntityType.MENTION` | `"mention"` |
| `MessageEntityType.HASHTAG` | `"hashtag"` |
| `MessageEntityType.CASHTAG` | `"cashtag"` |
| `MessageEntityType.BOT_COMMAND` | `"bot_command"` |
| `MessageEntityType.URL` | `"url"` |
| `MessageEntityType.EMAIL` | `"email"` |
| `MessageEntityType.PHONE_NUMBER` | `"phone_number"` |
| `MessageEntityType.BOLD` | `"bold"` |
| `MessageEntityType.ITALIC` | `"italic"` |
| `MessageEntityType.UNDERLINE` | `"underline"` |
| `MessageEntityType.STRIKETHROUGH` | `"strikethrough"` |
| `MessageEntityType.SPOILER` | `"spoiler"` |
| `MessageEntityType.BLOCKQUOTE` | `"blockquote"` |
| `MessageEntityType.EXPANDABLE_BLOCKQUOTE` | `"expandable_blockquote"` |
| `MessageEntityType.CODE` | `"code"` |
| `MessageEntityType.PRE` | `"pre"` |
| `MessageEntityType.TEXT_LINK` | `"text_link"` |
| `MessageEntityType.TEXT_MENTION` | `"text_mention"` |
| `MessageEntityType.CUSTOM_EMOJI` | `"custom_emoji"` |

---

### UpdateType

> Types of updates the bot can receive. Used with `allowed_updates` parameter.

| Constant | Value |
|---|---|
| `UpdateType.MESSAGE` | `"message"` |
| `UpdateType.EDITED_MESSAGE` | `"edited_message"` |
| `UpdateType.CHANNEL_POST` | `"channel_post"` |
| `UpdateType.EDITED_CHANNEL_POST` | `"edited_channel_post"` |
| `UpdateType.INLINE_QUERY` | `"inline_query"` |
| `UpdateType.CHOSEN_INLINE_RESULT` | `"chosen_inline_result"` |
| `UpdateType.CALLBACK_QUERY` | `"callback_query"` |
| `UpdateType.SHIPPING_QUERY` | `"shipping_query"` |
| `UpdateType.PRE_CHECKOUT_QUERY` | `"pre_checkout_query"` |
| `UpdateType.POLL` | `"poll"` |
| `UpdateType.POLL_ANSWER` | `"poll_answer"` |
| `UpdateType.MY_CHAT_MEMBER` | `"my_chat_member"` |
| `UpdateType.CHAT_MEMBER` | `"chat_member"` |
| `UpdateType.CHAT_JOIN_REQUEST` | `"chat_join_request"` |
| `UpdateType.MESSAGE_REACTION` | `"message_reaction"` |
| `UpdateType.MESSAGE_REACTION_COUNT` | `"message_reaction_count"` |
| `UpdateType.CHAT_BOOST` | `"chat_boost"` |
| `UpdateType.REMOVED_CHAT_BOOST` | `"removed_chat_boost"` |

---

### StickerType

> Types of stickers.

| Constant | Value |
|---|---|
| `StickerType.REGULAR` | `"regular"` |
| `StickerType.MASK` | `"mask"` |
| `StickerType.CUSTOM_EMOJI` | `"custom_emoji"` |

---

### DiceEmoji

> Emoji for the `send_dice()` method, each with different animations.

| Constant | Value |
|---|---|
| `DiceEmoji.DICE` | `"\U0001f3b2"` |
| `DiceEmoji.DARTS` | `"\U0001f3af"` |
| `DiceEmoji.BASKETBALL` | `"\U0001f3c0"` |
| `DiceEmoji.FOOTBALL` | `"\u26bd"` |
| `DiceEmoji.BOWLING` | `"\U0001f3b3"` |
| `DiceEmoji.SLOT_MACHINE` | `"\U0001f3b0"` |

---

### FloodLimit

> Telegram's rate limit thresholds.

| Constant | Value | Description |
|---|---|---|
| `FloodLimit.MESSAGES_PER_SECOND` | `30` | Global max messages per second. |
| `FloodLimit.MESSAGES_PER_MINUTE_PER_GROUP` | `20` | Max messages per minute per group/supergroup. |
| `FloodLimit.MESSAGES_PER_SECOND_PER_CHAT` | `1` | Max messages per second per individual chat. |

---

### MessageLimit

> Telegram message size constraints.

| Constant | Value | Description |
|---|---|---|
| `MessageLimit.MAX_TEXT_LENGTH` | `4096` | Maximum characters in a text message. |
| `MessageLimit.CAPTION_LENGTH` | `1024` | Maximum characters in a media caption. |

---

### FileSizeLimit

> File size constraints for uploads and downloads.

| Constant | Value | Description |
|---|---|---|
| `FileSizeLimit.FILESIZE_DOWNLOAD` | `20_971_520` | Max download size (~20 MB). |
| `FileSizeLimit.FILESIZE_UPLOAD` | `52_428_800` | Max upload size (~50 MB). |
| `FileSizeLimit.PHOTOSIZE_UPLOAD` | `10_485_760` | Max photo upload size (~10 MB). |

---

### Bot API Version

| Constant | Value | Description |
|---|---|---|
| `BOT_API_VERSION` | `"9.3"` | Bot API version string. |
| `BOT_API_VERSION_INFO` | `(9, 3)` | Bot API version as a named tuple. |

## Common Patterns

### Using ParseMode with Defaults

```python
from telegram.ext import Application, Defaults
from telegram.constants import ParseMode

defaults = Defaults(parse_mode=ParseMode.HTML)
app = Application.builder().token("BOT_TOKEN").defaults(defaults).build()

# All messages now default to HTML parsing
await context.bot.send_message(chat_id=cid, text="<b>bold</b> and <i>italic</i>")
```

### Checking chat type in handlers

```python
from telegram.constants import ChatType

async def handler(update, context):
    if update.effective_chat.type == ChatType.PRIVATE:
        await update.message.reply_text("This is a private chat.")
    elif update.effective_chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        await update.message.reply_text("This is a group chat.")
```

### Filtering allowed updates

```python
from telegram.constants import UpdateType

app.run_polling(
    allowed_updates=[UpdateType.MESSAGE, UpdateType.CALLBACK_QUERY]
)
```

## Related

- [Application](application.md) -- Defaults class for setting default parse_mode
- [Bot](bot.md) -- API methods that use these constants
- [Helpers](helpers.md) -- escape_markdown for safe formatting
- [Rate Limiting](rate-limiting.md) -- FloodLimit values in practice
- [Errors](errors.md) -- RetryAfter raised when FloodLimit is exceeded
- [Telegram API — Formatting](../api/bots/messages/formatting.md) -- ParseMode options in the API specification
- [Telegram API — Updates](../api/bots/updates/index.md) -- UpdateType values in the API specification
