# Media Types

> Types for photos, documents, audio, video, files, and media upload/grouping.

## Overview

Media types represent file attachments on messages. All downloadable media share `file_id` (use to re-send) and `file_unique_id` (stable across bots). The `File` object (from `bot.get_file()`) provides download methods. `InputFile` wraps data for upload, and `InputMedia*` classes are used for `send_media_group()` and `edit_message_media()`.

## Quick Usage

```python
async def handle_photo(update, context):
    largest = update.message.photo[-1]
    file = await context.bot.get_file(largest.file_id)
    await file.download_to_drive("photo.jpg")
```

## Key Classes

### `PhotoSize`

One size of a photo or thumbnail.

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier for re-sending or downloading. |
| `file_unique_id` | `str` | Unique identifier, consistent across bots (cannot be used to download). |
| `width` | `int` | Photo width in pixels. |
| `height` | `int` | Photo height in pixels. |
| `file_size` | `int \| None` | File size in bytes. |

Note: `message.photo` is a `tuple[PhotoSize, ...]` sorted by size ascending. Use `message.photo[-1]` for the largest available size.

---

### `Audio`

An audio file (treated as music by Telegram clients).

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `duration` | `int` | Duration in seconds. |
| `performer` | `str \| None` | Performer. |
| `title` | `str \| None` | Track title. |
| `file_name` | `str \| None` | Original filename. |
| `mime_type` | `str \| None` | MIME type. |
| `file_size` | `int \| None` | File size in bytes. |
| `thumbnail` | `PhotoSize \| None` | Thumbnail. |

---

### `Document`

A general file (not photo/audio/video/voice).

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `file_name` | `str \| None` | Original filename. |
| `mime_type` | `str \| None` | MIME type. |
| `file_size` | `int \| None` | File size in bytes. |
| `thumbnail` | `PhotoSize \| None` | Thumbnail. |

---

### `Video`

A video file.

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `width` | `int` | Video width. |
| `height` | `int` | Video height. |
| `duration` | `int` | Duration in seconds. |
| `file_name` | `str \| None` | Original filename. |
| `mime_type` | `str \| None` | MIME type. |
| `file_size` | `int \| None` | File size in bytes. |
| `thumbnail` | `PhotoSize \| None` | Thumbnail. |

---

### `VideoNote`

A video message (round video, up to 1 minute).

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `length` | `int` | Diameter of the video in pixels (width = height). |
| `duration` | `int` | Duration in seconds. |
| `file_size` | `int \| None` | File size in bytes. |
| `thumbnail` | `PhotoSize \| None` | Thumbnail. |

---

### `Voice`

A voice message (.ogg encoded with OPUS).

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `duration` | `int` | Duration in seconds. |
| `mime_type` | `str \| None` | MIME type. |
| `file_size` | `int \| None` | File size in bytes. |

---

### `Animation`

An animation file (GIF or H.264/MPEG-4 AVC video without sound).

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `width` | `int` | Animation width. |
| `height` | `int` | Animation height. |
| `duration` | `int` | Duration in seconds. |
| `file_name` | `str \| None` | Original filename. |
| `mime_type` | `str \| None` | MIME type. |
| `file_size` | `int \| None` | File size in bytes. |
| `thumbnail` | `PhotoSize \| None` | Thumbnail. |

---

### `Contact`

A phone contact.

| Attribute | Type | Description |
|---|---|---|
| `phone_number` | `str` | Contact's phone number. |
| `first_name` | `str` | Contact's first name. |
| `last_name` | `str \| None` | Contact's last name. |
| `user_id` | `int \| None` | Contact's Telegram user ID (if known). |
| `vcard` | `str \| None` | Additional vCard data. |

---

### `Location`

A point on the map.

| Attribute | Type | Description |
|---|---|---|
| `latitude` | `float` | Latitude. |
| `longitude` | `float` | Longitude. |
| `horizontal_accuracy` | `float \| None` | Radius of uncertainty in meters (0-1500). |
| `live_period` | `int \| None` | Time in seconds for live location updates. |
| `heading` | `int \| None` | Direction of movement in degrees (1-360). |
| `proximity_alert_radius` | `int \| None` | Maximum distance for proximity alerts in meters. |

---

### `Venue`

A venue (place with name and address).

| Attribute | Type | Description |
|---|---|---|
| `location` | `Location` | Venue location. |
| `title` | `str` | Venue name. |
| `address` | `str` | Venue address. |
| `foursquare_id` | `str \| None` | Foursquare identifier. |
| `foursquare_type` | `str \| None` | Foursquare venue type. |
| `google_place_id` | `str \| None` | Google Places identifier. |
| `google_place_type` | `str \| None` | Google Places type. |

---

### `Dice`

A dice with random value.

| Attribute | Type | Description |
|---|---|---|
| `emoji` | `str` | Emoji on which the dice throw is based (dice, darts, basketball, football, bowling, slot machine). |
| `value` | `int` | Value of the dice (1-6 for dice/darts/bowling, 1-5 for basketball/football, 1-64 for slot machine). |

---

### `File`

Represents a file ready to be downloaded. Obtained via `bot.get_file(file_id)`.

| Attribute | Type | Description |
|---|---|---|
| `file_id` | `str` | File identifier. |
| `file_unique_id` | `str` | Unique file identifier. |
| `file_size` | `int \| None` | File size in bytes. |
| `file_path` | `str \| None` | File path on Telegram servers (use for download). |

**Download Methods** (all async)

| Method | Returns | Description |
|---|---|---|
| `download_to_drive(custom_path=None)` | `Path` | Download to local filesystem. Returns the file path. |
| `download_to_memory(out)` | `None` | Download into a `BytesIO` or file-like object. |
| `download_as_bytearray()` | `bytearray` | Download and return as bytearray. |

---

### `InputFile`

Wraps a file for upload. Used as the value for `photo`, `document`, `audio`, etc. parameters in send methods.

**Accepted input types:**
- `str` or `pathlib.Path` -- local file path
- File-like object (e.g., `open("file.png", "rb")`, `BytesIO`)
- `bytes` -- raw file content
- `str` (file_id) -- re-send a previously uploaded file by its `file_id`

You typically don't instantiate `InputFile` directly -- just pass the file path, bytes, or file-like object to the send method and the library wraps it automatically.

---

### `InputMedia` and Subclasses

Used for `send_media_group()` and `edit_message_media()`.

**`InputMediaPhoto`**
```python
InputMediaPhoto(
    media,                          # file_id, URL, or InputFile
    caption=None,
    parse_mode=None,
    caption_entities=None,
    show_caption_above_media=None,
    has_spoiler=None,
)
```

**`InputMediaVideo`**
```python
InputMediaVideo(
    media,
    caption=None,
    parse_mode=None,
    caption_entities=None,
    width=None,
    height=None,
    duration=None,
    supports_streaming=None,
    has_spoiler=None,
    show_caption_above_media=None,
    thumbnail=None,
)
```

**`InputMediaAnimation`**
```python
InputMediaAnimation(
    media,
    caption=None,
    parse_mode=None,
    caption_entities=None,
    width=None,
    height=None,
    duration=None,
    has_spoiler=None,
    show_caption_above_media=None,
    thumbnail=None,
)
```

**`InputMediaAudio`**
```python
InputMediaAudio(
    media,
    caption=None,
    parse_mode=None,
    caption_entities=None,
    duration=None,
    performer=None,
    title=None,
    thumbnail=None,
)
```

**`InputMediaDocument`**
```python
InputMediaDocument(
    media,
    caption=None,
    parse_mode=None,
    caption_entities=None,
    disable_content_type_detection=None,
    thumbnail=None,
)
```

For all `InputMedia*` subclasses, the `media` parameter accepts a `file_id` string (to re-use an existing file), an HTTP URL string, or file upload data (path, bytes, file-like object).

## Common Patterns

### Download a file from a message

```python
async def handle_document(update: Update, context: ContextTypes.DefaultType):
    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    path = await file.download_to_drive()  # saves to ./file_name
    await update.message.reply_text(f"Saved to {path}")
```

### Send a media group (album)

```python
from telegram import InputMediaPhoto

async def send_album(update: Update, context: ContextTypes.DefaultType):
    media = [
        InputMediaPhoto(open("photo1.jpg", "rb"), caption="First photo"),
        InputMediaPhoto(open("photo2.jpg", "rb")),
        InputMediaPhoto(open("photo3.jpg", "rb")),
    ]
    await update.message.reply_media_group(media)
```

### Get the largest photo from a message

```python
async def handle_photo(update: Update, context: ContextTypes.DefaultType):
    # message.photo is sorted by size ascending
    largest = update.message.photo[-1]
    file = await context.bot.get_file(largest.file_id)

    from io import BytesIO
    buf = BytesIO()
    await file.download_to_memory(buf)
    buf.seek(0)
    # process buf...
```

## Related

- [index.md](index.md) -- types overview and routing table
- [messages.md](messages.md) -- Message type that contains media attributes
- [keyboards.md](keyboards.md) -- keyboards sent alongside media
- [../bot.md](../bot.md) -- Bot.send_photo(), send_document(), send_media_group(), get_file(), etc.
- [../handlers/message-handler.md](../handlers/message-handler.md) -- filtering messages by media type
- [Telegram API — Media](../../api/bots/media/index.md) -- media handling in the API specification
