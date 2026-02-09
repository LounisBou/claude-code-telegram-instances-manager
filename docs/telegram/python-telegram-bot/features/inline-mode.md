# Inline Mode

> Let users invoke the bot from any chat by typing `@botusername query` -- the bot returns a list of results displayed as a popup.

## Overview

Inline mode allows users to query a bot directly from the text input field in any chat. The bot receives an `InlineQuery` update, processes it, and returns a list of `InlineQueryResult` objects. The user picks one, and Telegram sends the corresponding content into the chat. Enable inline mode via @BotFather before use.

## Quick Usage

```python
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import Application, InlineQueryHandler, ContextTypes

async def inline_query(update: Update, context: ContextTypes.DefaultType):
    results = [
        InlineQueryResultArticle(
            id="1",
            title="Hello",
            input_message_content=InputTextMessageContent("Hello, world!"),
        )
    ]
    await update.inline_query.answer(results)

app = Application.builder().token("TOKEN").build()
app.add_handler(InlineQueryHandler(inline_query))
app.run_polling()
```

## Key Classes

### `telegram.InlineQuery`

Represents an incoming inline query.

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique query identifier. |
| `from_user` | `User` | Sender of the query. |
| `query` | `str` | Text of the query (up to 256 characters). |
| `offset` | `str` | Offset for pagination (empty string if none). |
| `chat_type` | `str \| None` | Type of chat the query was sent from: `"sender"`, `"private"`, `"group"`, `"supergroup"`, `"channel"`. |
| `location` | `Location \| None` | Sender location (only for bots requesting location). |

**Key Methods**

| Method | Returns | Description |
|---|---|---|
| `answer(results, cache_time=300, is_personal=None, next_offset=None, button=None)` | `bool` | Send results back. `results` is `list[InlineQueryResult]` (max 50). `next_offset` enables pagination. `button` adds a button above results. |

---

### InlineQueryResult Types

All require `id: str`. Two families: **URL-based** (fetch content from a URL) and **Cached** (use `file_id` already on Telegram servers).

#### URL-based Results

| Class | Required Params | Description |
|---|---|---|
| `InlineQueryResultArticle` | `id, title, input_message_content` | Generic result with a title. Optional: `reply_markup`, `url`, `description`, `thumbnail_url`, `thumbnail_width`, `thumbnail_height`. |
| `InlineQueryResultPhoto` | `id, photo_url, thumbnail_url` | Photo from URL. Optional: `photo_width`, `photo_height`, `title`, `description`, `caption`, `parse_mode`, `reply_markup`, `input_message_content`. |
| `InlineQueryResultGif` | `id, gif_url, thumbnail_url` | Animated GIF. Optional: `gif_width`, `gif_height`, `gif_duration`, `title`, `caption`, `parse_mode`, `reply_markup`, `input_message_content`. |
| `InlineQueryResultMpeg4Gif` | `id, mpeg4_url, thumbnail_url` | MPEG4 animation. Optional: `mpeg4_width`, `mpeg4_height`, `mpeg4_duration`, `title`, `caption`, `parse_mode`, `reply_markup`, `input_message_content`. |
| `InlineQueryResultVideo` | `id, video_url, mime_type, thumbnail_url, title` | Video. Optional: `caption`, `video_width`, `video_height`, `video_duration`, `description`, `parse_mode`, `reply_markup`, `input_message_content`. |
| `InlineQueryResultAudio` | `id, audio_url, title` | Audio file. Optional: `caption`, `performer`, `audio_duration`, `parse_mode`, `reply_markup`, `input_message_content`. |
| `InlineQueryResultVoice` | `id, voice_url, title` | Voice message. Optional: `caption`, `voice_duration`, `parse_mode`, `reply_markup`, `input_message_content`. |
| `InlineQueryResultDocument` | `id, document_url, title, mime_type` | Document file. Optional: `caption`, `description`, `parse_mode`, `reply_markup`, `input_message_content`, `thumbnail_url`, `thumbnail_width`, `thumbnail_height`. |
| `InlineQueryResultLocation` | `id, latitude, longitude, title` | Location. Optional: `horizontal_accuracy`, `live_period`, `heading`, `proximity_alert_radius`, `reply_markup`, `input_message_content`, `thumbnail_url`. |
| `InlineQueryResultVenue` | `id, latitude, longitude, title, address` | Venue. Optional: `foursquare_id`, `foursquare_type`, `google_place_id`, `google_place_type`, `reply_markup`, `input_message_content`, `thumbnail_url`. |
| `InlineQueryResultContact` | `id, phone_number, first_name` | Contact. Optional: `last_name`, `vcard`, `reply_markup`, `input_message_content`, `thumbnail_url`. |
| `InlineQueryResultGame` | `id, game_short_name` | Game. Optional: `reply_markup`. |

#### Cached Results (use `file_id` from Telegram servers)

| Class | Required Params |
|---|---|
| `InlineQueryResultCachedPhoto` | `id, photo_file_id` |
| `InlineQueryResultCachedGif` | `id, gif_file_id` |
| `InlineQueryResultCachedMpeg4Gif` | `id, mpeg4_file_id` |
| `InlineQueryResultCachedVideo` | `id, video_file_id, title` |
| `InlineQueryResultCachedAudio` | `id, audio_file_id` |
| `InlineQueryResultCachedVoice` | `id, voice_file_id, title` |
| `InlineQueryResultCachedDocument` | `id, document_file_id, title` |
| `InlineQueryResultCachedSticker` | `id, sticker_file_id` |

All cached variants accept optional: `caption`, `parse_mode`, `reply_markup`, `input_message_content` (except CachedSticker which only accepts `reply_markup` and `input_message_content`).

---

### InputMessageContent Types

Define message content when the user selects an inline result. Used in `input_message_content` parameter.

| Class | Required Params | Description |
|---|---|---|
| `InputTextMessageContent` | `message_text` | Text message. Optional: `parse_mode`, `entities`, `link_preview_options`. |
| `InputLocationMessageContent` | `latitude, longitude` | Location. Optional: `horizontal_accuracy`, `live_period`, `heading`, `proximity_alert_radius`. |
| `InputVenueMessageContent` | `latitude, longitude, title, address` | Venue. Optional: `foursquare_id`, `foursquare_type`, `google_place_id`, `google_place_type`. |
| `InputContactMessageContent` | `phone_number, first_name` | Contact. Optional: `last_name`, `vcard`. |
| `InputInvoiceMessageContent` | `title, description, payload, currency, prices` | Invoice (for payments via inline mode). Additional params mirror `send_invoice`. |

---

### `telegram.InlineQueryResultsButton`

Button shown above inline query results.

| Attribute | Type | Description |
|---|---|---|
| `text` | `str` | Button label text. |
| `web_app` | `WebAppInfo \| None` | Opens a Web App when pressed. |
| `start_parameter` | `str \| None` | Deep link parameter -- pressing button starts private chat with bot with this parameter. |

---

### `telegram.ChosenInlineResult`

Sent when a user selects an inline result (requires feedback collection enabled via @BotFather).

| Attribute | Type | Description |
|---|---|---|
| `result_id` | `str` | The unique identifier of the chosen result. |
| `from_user` | `User` | The user who chose the result. |
| `query` | `str` | The query that was used to obtain the result. |
| `location` | `Location \| None` | Sender location (if requested). |
| `inline_message_id` | `str \| None` | Identifier of the sent inline message (for editing via Bot methods). |

---

### `telegram.PreparedInlineMessage`

Describes an inline message to be sent by a user of a Mini App.

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique identifier of the prepared message. |
| `expiration_date` | `datetime` | Expiration date of the prepared message. |

## Common Patterns

### Paginated inline results

```python
import uuid

async def inline_query(update: Update, context: ContextTypes.DefaultType):
    query = update.inline_query.query
    offset = int(update.inline_query.offset) if update.inline_query.offset else 0
    page_size = 20

    # Fetch items[offset:offset+page_size] from your data source
    items = get_items(query, offset, page_size)

    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=item.title,
            input_message_content=InputTextMessageContent(item.text),
        )
        for item in items
    ]

    next_offset = str(offset + page_size) if len(items) == page_size else ""
    await update.inline_query.answer(results, next_offset=next_offset)
```

### Inline result with keyboard and formatting

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def inline_query(update: Update, context: ContextTypes.DefaultType):
    results = [
        InlineQueryResultArticle(
            id="1",
            title="Formatted Result",
            description="Tap to send formatted message",
            input_message_content=InputTextMessageContent(
                message_text="<b>Bold</b> and <i>italic</i>",
                parse_mode="HTML",
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Visit", url="https://example.com")]
            ]),
        )
    ]
    await update.inline_query.answer(results, cache_time=60, is_personal=True)
```

### Handling chosen inline results

```python
from telegram.ext import ChosenInlineResultHandler

async def chosen_result(update: Update, context: ContextTypes.DefaultType):
    result = update.chosen_inline_result
    # result.inline_message_id can be used to edit the sent message later
    await context.bot.edit_message_text(
        inline_message_id=result.inline_message_id,
        text=f"You chose: {result.result_id}",
    )

app.add_handler(ChosenInlineResultHandler(chosen_result))
```

## Related

- [../handlers/index.md](../handlers/index.md) -- `InlineQueryHandler`, `ChosenInlineResultHandler`
- [../bot.md](../bot.md) -- `Bot.answer_inline_query()` (low-level equivalent of `InlineQuery.answer()`)
- [../types/keyboards.md](../types/keyboards.md) -- `InlineKeyboardMarkup` used in result `reply_markup`
- [payments.md](payments.md) -- `InputInvoiceMessageContent` for inline payments
- [games.md](games.md) -- `InlineQueryResultGame` for inline game results
- [web-apps.md](web-apps.md) -- `InlineQueryResultsButton` can open a Web App
- [Telegram API — Inline Mode](../../api/bots/inline/index.md) -- inline query mechanics in the API specification
