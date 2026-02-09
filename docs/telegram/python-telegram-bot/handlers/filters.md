# Filters

> Composable predicates that narrow which updates a handler processes, accessed via `telegram.ext.filters`.

## Overview

Filters determine whether a handler's callback fires for a given update. They are passed to handlers like `MessageHandler(filters.TEXT, callback)`. Filters compose with bitwise operators (`&`, `|`, `~`, `^`) to build complex matching logic without writing custom code.

Import: `from telegram.ext import filters`

## Quick Usage

```python
from telegram.ext import MessageHandler, filters

# Text messages that are not commands
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# Photos or videos in private chats
app.add_handler(MessageHandler(
    (filters.PHOTO | filters.VIDEO) & filters.ChatType.PRIVATE,
    handle_media,
))
```

## Filter Operators

| Operator | Meaning | Example |
|----------|---------|---------|
| `&` | AND -- both must pass | `filters.TEXT & filters.Entity("url")` |
| `\|` | OR -- either passes | `filters.AUDIO \| filters.VIDEO` |
| `~` | NOT -- invert | `~filters.COMMAND` |
| `^` | XOR -- exactly one passes | `filters.PHOTO ^ filters.CAPTION` |

Operators return new filter objects, so they can be stored and reused:

```python
MEDIA_PRIVATE = (filters.PHOTO | filters.VIDEO) & filters.ChatType.PRIVATE
app.add_handler(MessageHandler(MEDIA_PRIVATE, handler))
```

## Pre-instantiated Filter Constants

Use these directly without calling them. They are ready-made instances on the `filters` module.

| Constant | Matches messages with... |
|----------|------------------------|
| `ALL` | Any message (always True) |
| `ANIMATION` | An animation (GIF) |
| `ATTACHMENT` | Any attachment |
| `AUDIO` | An audio file |
| `BOOST_ADDED` | A chat boost added service message |
| `CAPTION` | A caption on media |
| `COMMAND` | A bot command (text starting with `/`) |
| `CONTACT` | A shared contact |
| `EFFECT_ID` | A message effect id |
| `FORUM` | Messages in a forum (supergroup with topics) |
| `FORWARDED` | A forwarded message |
| `GAME` | A game |
| `GIVEAWAY` | A giveaway |
| `GIVEAWAY_WINNERS` | Giveaway winners |
| `HAS_MEDIA_SPOILER` | A media spoiler |
| `HAS_PROTECTED_CONTENT` | Protected (non-forwardable) content |
| `INVOICE` | An invoice (payment) |
| `IS_AUTOMATIC_FORWARD` | An auto-forwarded channel post |
| `IS_FROM_OFFLINE` | A message sent while the user was offline |
| `IS_TOPIC_MESSAGE` | A message in a forum topic |
| `LOCATION` | A location |
| `PAID_MEDIA` | Paid media content |
| `PASSPORT_DATA` | Telegram Passport data |
| `PHOTO` | A photo |
| `POLL` | A poll |
| `PREMIUM_USER` | A Telegram Premium user |
| `REPLY` | A reply to another message |
| `SENDER_BOOST_COUNT` | A sender boost count |
| `STORY` | A story |
| `SUCCESSFUL_PAYMENT` | A successful payment confirmation |
| `TEXT` | Text content (including commands) |
| `USER` | A non-anonymous, non-channel sender |
| `USER_ATTACHMENT` | A user attachment menu interaction |
| `VENUE` | A venue |
| `VIA_BOT` | A message sent via an inline bot |
| `VIDEO` | A video |
| `VIDEO_NOTE` | A video note (round video) |
| `VOICE` | A voice message |

## Filter Classes

These require instantiation with arguments.

### `Regex(pattern)`

Matches `message.text` against a regex pattern. All `re.Match` objects are stored in `context.matches`.

```python
app.add_handler(MessageHandler(
    filters.Regex(r"https?://\S+"),
    handle_urls,
))

async def handle_urls(update, context):
    for match in context.matches:
        print(match.group(0))
```

### `Text(strings)`

Exact text match against a set of strings.

```python
filters.Text(["yes", "no", "maybe"])
```

### `Caption(strings)`

Exact caption match against a set of strings.

```python
filters.Caption(["sunset", "sunrise"])
```

### `CaptionRegex(pattern)`

Regex match on `message.caption`. Matches stored in `context.matches`.

```python
filters.CaptionRegex(r"#\w+")
```

### `Chat(chat_id=None, username=None, allow_empty=False)`

Filter by specific chat(s). Accepts a single value or collection.

```python
filters.Chat(chat_id=[-1001234567890])
filters.Chat(username="mychannel")
```

When `allow_empty=True`, the filter passes all messages until a chat is added at runtime via `filter.add_chat_ids()` or `filter.remove_chat_ids()`.

### `User(user_id=None, username=None, allow_empty=False)`

Filter by specific user(s). Same interface as `Chat`.

```python
filters.User(user_id=123456)
filters.User(username=["alice", "bob"])
```

### `Entity(entity_type)`

Filter messages containing a specific `MessageEntity` type.

```python
filters.Entity("url")       # contains a URL
filters.Entity("bold")      # contains bold text
filters.Entity("mention")   # contains an @mention
```

Common entity types: `"mention"`, `"hashtag"`, `"cashtag"`, `"bot_command"`, `"url"`, `"email"`, `"phone_number"`, `"bold"`, `"italic"`, `"underline"`, `"strikethrough"`, `"spoiler"`, `"code"`, `"pre"`, `"text_link"`, `"text_mention"`, `"custom_emoji"`.

### `CaptionEntity(entity_type)`

Same as `Entity` but checks `message.caption_entities`.

```python
filters.CaptionEntity("url")
```

### `ForwardedFrom(chat_id=None, username=None, allow_empty=False)`

Filter by the original sender of a forwarded message.

```python
filters.ForwardedFrom(chat_id=123456)
filters.ForwardedFrom(username="newschannel")
```

### `Language(lang)`

Filter by user's `language_code` in their Telegram profile. Accepts a single string or collection.

```python
filters.Language("en")
filters.Language(["en", "fr", "de"])
```

### `Mention(mentions)`

Filter messages that mention specific users or chats. Accepts `int` (user id), `str` (username without @), or `ChatMember`/`User` objects.

```python
filters.Mention(mentions=[123456, "mybot"])
```

### `ViaBot(bot_id=None, username=None, allow_empty=False)`

Filter messages sent via a specific inline bot.

```python
filters.ViaBot(username="gif")
```

## Namespace Filters

### `ChatType`

| Filter | Matches |
|--------|---------|
| `filters.ChatType.PRIVATE` | Private (DM) chats |
| `filters.ChatType.GROUP` | Group chats |
| `filters.ChatType.SUPERGROUP` | Supergroup chats |
| `filters.ChatType.CHANNEL` | Channel posts |
| `filters.ChatType.GROUPS` | Group OR Supergroup (shortcut) |

### `Dice`

Filter by dice emoji type.

| Filter | Emoji |
|--------|-------|
| `filters.Dice.BASKETBALL` | Basketball |
| `filters.Dice.BOWLING` | Bowling |
| `filters.Dice.DARTS` | Darts |
| `filters.Dice.DICE` | Dice |
| `filters.Dice.FOOTBALL` | Football |
| `filters.Dice.SLOT_MACHINE` | Slot machine |

### `Document`

| Filter | Matches |
|--------|---------|
| `filters.Document.ALL` | Any document |
| `filters.Document.Category(category)` | Documents by MIME category (e.g., `"audio"`, `"image"`) |
| `filters.Document.FileExtension(file_extension)` | By file extension, **without the dot** (e.g., `"pdf"`, `"csv"`) |
| `filters.Document.MimeType(mime_type)` | By exact MIME type (e.g., `"application/pdf"`) |

Prebuilt MIME type shortcuts: `Document.APK`, `Document.DOC`, `Document.DOCX`, `Document.EXE`, `Document.GIF`, `Document.JPG`, `Document.MP3`, `Document.MP4`, `Document.PDF`, `Document.PY`, `Document.SVG`, `Document.TXT`, `Document.WAV`, `Document.XML`, `Document.ZIP`.

```python
# PDFs only
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

# Any spreadsheet by extension
app.add_handler(MessageHandler(
    filters.Document.FileExtension("xlsx") | filters.Document.FileExtension("csv"),
    handle_spreadsheet,
))
```

## Custom Filters

Subclass `MessageFilter` (checks `message`) or `UpdateFilter` (checks the entire `update`). Implement the `filter()` method returning `bool`.

### MessageFilter

```python
class ContainsHello(filters.MessageFilter):
    def filter(self, message):
        return bool(message.text and "hello" in message.text.lower())

app.add_handler(MessageHandler(ContainsHello(), handle_hello))
```

### UpdateFilter

```python
class HasCallbackFromAdmin(filters.UpdateFilter):
    def filter(self, update):
        return (
            update.callback_query is not None
            and update.callback_query.from_user.id in ADMIN_IDS
        )
```

Set `self.data_filter = True` in `__init__` if your filter adds data to `context` (like `Regex` does with `context.matches`). Override `filter()` to return a dict of data instead of `bool`; the dict values are merged into `context`.

## Common Patterns

### Text messages excluding commands

```python
MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
```

### Photos in private chats only

```python
MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_private_photo)
```

### Messages from a specific user

```python
MessageHandler(filters.User(user_id=123456), handle_vip)
```

### Documents by file extension

```python
MessageHandler(filters.Document.FileExtension("pdf"), handle_pdf)
```

### Regex with match extraction

```python
MessageHandler(filters.Regex(r"order\s+#?(\d+)"), handle_order)

async def handle_order(update, context):
    order_id = context.matches[0].group(1)
```

## Related

- [Message Handler](message-handler.md) -- primary consumer of filters
- [Command Handler](command-handler.md) -- also accepts optional filters
- [Handlers Overview](index.md) -- handler routing system
- [Telegram API -- Updates](../../api/bots/updates/index.md)
