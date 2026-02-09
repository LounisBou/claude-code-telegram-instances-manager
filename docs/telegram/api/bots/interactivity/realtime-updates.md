# Real-time Message Updates

Edit messages in place to create live-updating displays: progress bars, status indicators, counters, loading animations.

## How It Works

1. Bot sends initial message with sendMessage -- stores message_id
2. Bot calls editMessageText repeatedly to update content
3. Each edit replaces the previous text/markup

## Key Methods

### editMessageText

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes* | Chat identifier |
| message_id | Integer | Yes* | Message to edit |
| inline_message_id | String | Yes* | For inline messages |
| text | String | Yes | New text content |
| business_connection_id | String | No | Business connection identifier |
| parse_mode | String | No | Formatting mode |
| entities | Array of MessageEntity | No | Special entities in text |
| link_preview_options | LinkPreviewOptions | No | Link preview settings |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

*Either chat_id + message_id OR inline_message_id must be provided.

**Returns:** Message (or True for inline messages)

### editMessageCaption

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes* | Chat identifier |
| message_id | Integer | Yes* | Message to edit |
| inline_message_id | String | Yes* | For inline messages |
| caption | String | No | New caption |
| parse_mode | String | No | Formatting mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| show_caption_above_media | Boolean | No | Show caption above media |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

**Returns:** Message (or True for inline messages)

### editMessageMedia

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes* | Chat identifier |
| message_id | Integer | Yes* | Message to edit |
| inline_message_id | String | Yes* | For inline messages |
| media | InputMedia | Yes | New media content |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

**Returns:** Message (or True for inline messages)

### editMessageReplyMarkup

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes* | Chat identifier |
| message_id | Integer | Yes* | Message to edit |
| inline_message_id | String | Yes* | For inline messages |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

**Returns:** Message (or True for inline messages)

### editMessageLiveLocation

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes* | Chat identifier |
| message_id | Integer | Yes* | Message to edit |
| inline_message_id | String | Yes* | For inline messages |
| latitude | Float | Yes | New latitude |
| longitude | Float | Yes | New longitude |
| live_period | Integer | No | New live period |
| horizontal_accuracy | Float | No | Accuracy radius (0-1500 meters) |
| heading | Integer | No | Direction of movement (1-360 degrees) |
| proximity_alert_radius | Integer | No | Proximity alert distance |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

**Returns:** Message (or True for inline messages)

### stopMessageLiveLocation

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes* | Chat identifier |
| message_id | Integer | Yes* | Message to edit |
| inline_message_id | String | Yes* | For inline messages |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

**Returns:** Message (or True for inline messages)

## Text-Based Progress Bar Pattern

Build a progress bar using Unicode block characters:
- Use full block and light shade characters to show progress
- Format: `[XXXXXXXX....] 65%`
- Edit the message each time progress changes

## Live Counter Pattern

Show a counter that updates in real-time:
- Send initial "Processing: 0/100"
- Edit to "Processing: 15/100", "Processing: 42/100", etc.
- Final edit: "Complete! 100/100 items processed"

## Status Indicator Pattern

Show current operation status with sequential edits:
- "Downloading file..."
- "Processing data..."
- "Done! File saved."

## Gotchas

- **Rate limit**: approximately 30 edits per minute per chat, approximately 20 edits per minute per message in group chats. More frequent edits will get 429 Too Many Requests.
- **Identical content**: editMessageText returns 400 "message is not modified" if text+markup are identical. Always check before editing.
- **48-hour limit**: messages older than ~48 hours cannot be edited (non-inline messages).
- **Inline messages**: use inline_message_id instead of chat_id + message_id. Cannot use both.
- **No diff**: each edit replaces the ENTIRE message text. You must send the full content each time.
- **Flickering**: very rapid edits may cause visual flickering on some clients. Space edits at least 1 second apart.
- **editMessageReplyMarkup**: use this when only the keyboard changes, not the text -- avoids "message is not modified" error.

## Patterns

- Progress bar: send message -- loop with editMessageText updating bar -- final edit with result
- Status + buttons: combine editMessageText + updated InlineKeyboardMarkup to change both text and buttons atomically
- Countdown: edit message periodically with remaining time (respect rate limits)
- Live location: use sendLocation with live_period, then editMessageLiveLocation to update position
