# Stickers

> Send stickers and manage sticker sets -- static, animated, video, mask, and custom emoji stickers.

## Overview

Telegram supports multiple sticker formats: static (WebP), animated (TGS/Lottie), and video (WebM). Stickers belong to `StickerSet`s and can be regular, mask, or custom emoji type. Bots can send existing stickers, create new sticker sets, and modify sets they own. Sticker sets are identified by `name` (used in URLs like `t.me/addstickers/<name>`).

## Quick Usage

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def send_sticker(update: Update, context: ContextTypes.DefaultType):
    # Send by file_id (get from a received sticker message)
    await update.message.reply_sticker(sticker="CAACAgIAAxkB...")

app = Application.builder().token("TOKEN").build()
app.add_handler(CommandHandler("sticker", send_sticker))
app.run_polling()
```

## Key Classes

### `telegram.Sticker`

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | Identifier for downloading or reusing the sticker. |
| `file_unique_id` | `str` | Unique identifier (cannot be reused to download). |
| `type` | `str` | `"regular"`, `"mask"`, or `"custom_emoji"`. |
| `width` | `int` | Sticker width. |
| `height` | `int` | Sticker height. |
| `is_animated` | `bool` | `True` for TGS animated stickers. |
| `is_video` | `bool` | `True` for WebM video stickers. |
| `thumbnail` | `PhotoSize \| None` | Sticker thumbnail. |
| `emoji` | `str \| None` | Emoji associated with the sticker. |
| `set_name` | `str \| None` | Name of the sticker set it belongs to. |
| `mask_position` | `MaskPosition \| None` | Position for mask stickers. |
| `custom_emoji_id` | `str \| None` | Unique custom emoji identifier. |
| `file_size` | `int \| None` | File size in bytes. |
| `premium_animation` | `File \| None` | Premium animation for regular stickers. |
| `needs_repainting` | `bool \| None` | `True` if the sticker must be repainted to a text color. |

---

### `telegram.StickerSet`

| Attribute | Type | Description |
|---|---|---|
| `name` | `str` | Sticker set name (used in `t.me/addstickers/<name>`). |
| `title` | `str` | Sticker set title. |
| `sticker_type` | `str` | `"regular"`, `"mask"`, or `"custom_emoji"`. |
| `stickers` | `list[Sticker]` | List of all stickers in the set. |
| `thumbnail` | `PhotoSize \| None` | Sticker set thumbnail. |

---

### `telegram.InputSticker`

Used when creating or adding stickers to a set.

```python
InputSticker(
    sticker: InputFile | str,       # File to upload or file_id
    emoji_list: list[str],          # Associated emojis (1-20)
    mask_position: MaskPosition | None = None,
    keywords: list[str] | None = None,  # Search keywords (0-20)
    format: str,                    # "static", "animated", or "video"
)
```

---

### `telegram.MaskPosition`

Defines where a mask sticker is placed on a face.

| Attribute | Type | Description |
|---|---|---|
| `point` | `str` | Face part: `"forehead"`, `"eyes"`, `"mouth"`, or `"chin"`. |
| `x_shift` | `float` | X-axis shift (-100.0 to 100.0). |
| `y_shift` | `float` | Y-axis shift (-100.0 to 100.0). |
| `scale` | `float` | Scaling coefficient (0.0 to 2.0). |

---

### Bot Methods

#### Sending

| Method | Returns | Description |
|---|---|---|
| `send_sticker(chat_id, sticker, emoji=None, disable_notification=None, protect_content=None, reply_parameters=None, reply_markup=None, message_thread_id=None, ...)` | `Message` | Send a sticker by `file_id`, URL, or file upload. |

#### Querying

| Method | Returns | Description |
|---|---|---|
| `get_sticker_set(name)` | `StickerSet` | Get a sticker set by name. |
| `get_custom_emoji_stickers(custom_emoji_ids)` | `list[Sticker]` | Get custom emoji stickers by their unique IDs. |

#### Sticker Set Management

| Method | Returns | Description |
|---|---|---|
| `create_new_sticker_set(user_id, name, title, stickers, sticker_type=None, needs_repainting=None, ...)` | `bool` | Create a new sticker set owned by `user_id`. `stickers` is `list[InputSticker]`. |
| `add_sticker_to_set(user_id, name, sticker)` | `bool` | Add a sticker to an existing set. `sticker` is `InputSticker`. |
| `set_sticker_position_in_set(sticker, position)` | `bool` | Move a sticker within its set. `sticker` is `file_id`, `position` is 0-based index. |
| `delete_sticker_from_set(sticker)` | `bool` | Remove a sticker from its set. `sticker` is `file_id`. |
| `delete_sticker_set(name)` | `bool` | Delete a sticker set created by the bot. |

#### Sticker Metadata

| Method | Returns | Description |
|---|---|---|
| `set_sticker_set_thumbnail(name, user_id, thumbnail=None, format=None)` | `bool` | Set sticker set thumbnail. |
| `set_sticker_emoji_list(sticker, emoji_list)` | `bool` | Change sticker's emoji list. |
| `set_sticker_keywords(sticker, keywords=None)` | `bool` | Change sticker's search keywords. |
| `set_sticker_mask_position(sticker, mask_position=None)` | `bool` | Change mask sticker's placement. |
| `set_custom_emoji_sticker_set_thumbnail(name, custom_emoji_id=None)` | `bool` | Set thumbnail for custom emoji set. |

## Common Patterns

### Create a new sticker set

```python
from telegram import InputSticker

async def create_set(update: Update, context: ContextTypes.DefaultType):
    user_id = update.effective_user.id
    stickers = [
        InputSticker(
            sticker=open("sticker1.webp", "rb"),
            emoji_list=["😀"],
            format="static",
        ),
    ]
    await context.bot.create_new_sticker_set(
        user_id=user_id,
        name=f"my_set_by_{context.bot.username}",
        title="My Sticker Set",
        stickers=stickers,
    )
```

### Get sticker set info and send a sticker from it

```python
async def send_from_set(update: Update, context: ContextTypes.DefaultType):
    sticker_set = await context.bot.get_sticker_set("my_set_by_mybot")
    if sticker_set.stickers:
        await update.message.reply_sticker(sticker_set.stickers[0].file_id)
```

### Handle received stickers

```python
from telegram.ext import MessageHandler, filters

async def handle_sticker(update: Update, context: ContextTypes.DefaultType):
    sticker = update.message.sticker
    info = f"Emoji: {sticker.emoji}, Set: {sticker.set_name}, Type: {sticker.type}"
    await update.message.reply_text(info)

app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
```

## Related

- [../bot.md](../bot.md) -- `Bot.send_sticker()` and all sticker set management methods
- [../handlers/message-handler.md](../handlers/message-handler.md) -- `MessageHandler` with `filters.Sticker.*`
- [../handlers/filters.md](../handlers/filters.md) -- `filters.Sticker.ALL`, `filters.Sticker.STATIC`, `filters.Sticker.ANIMATED`, `filters.Sticker.VIDEO`
- [../types/media.md](../types/media.md) -- `InputFile` for uploading sticker files
- [inline-mode.md](inline-mode.md) -- `InlineQueryResultCachedSticker` for inline sticker results
- [Telegram API — Stickers](../../api/bots/stickers/index.md) -- sticker types and set management in the API specification
