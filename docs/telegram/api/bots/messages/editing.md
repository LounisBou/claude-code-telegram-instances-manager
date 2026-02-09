# Editing Messages

## editMessageText

Edit text and game messages. Works for both regular and inline messages.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Conditional | Required if inline_message_id is not specified |
| message_id | Integer | Conditional | Required if inline_message_id is not specified |
| inline_message_id | String | Conditional | Required if chat_id and message_id are not specified |
| text | String | Yes | New text of the message, 1-4096 characters |
| business_connection_id | String | No | Unique identifier of the business connection |
| parse_mode | String | No | Text parsing mode |
| entities | Array of MessageEntity | No | Special entities in text |
| link_preview_options | LinkPreviewOptions | No | Link preview options |
| reply_markup | InlineKeyboardMarkup | No | New inline keyboard |

**Returns:** Message (for regular messages) or True (for inline messages)

---

## editMessageCaption

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Conditional | Required if inline_message_id is not specified |
| message_id | Integer | Conditional | Required if inline_message_id is not specified |
| inline_message_id | String | Conditional | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| caption | String | No | New caption, 0-1024 characters |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| show_caption_above_media | Boolean | No | Show caption above media |
| reply_markup | InlineKeyboardMarkup | No | New inline keyboard |

**Returns:** Message or True

---

## editMessageMedia

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Conditional | Required if inline_message_id is not specified |
| message_id | Integer | Conditional | Required if inline_message_id is not specified |
| inline_message_id | String | Conditional | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| media | InputMedia | Yes | New media content |
| reply_markup | InlineKeyboardMarkup | No | New inline keyboard |

**Returns:** Message or True

---

## editMessageReplyMarkup

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Conditional | Required if inline_message_id is not specified |
| message_id | Integer | Conditional | Required if inline_message_id is not specified |
| inline_message_id | String | Conditional | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| reply_markup | InlineKeyboardMarkup | No | New inline keyboard |

**Returns:** Message or True

---

## editMessageLiveLocation

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Conditional | Required if inline_message_id is not specified |
| message_id | Integer | Conditional | Required if inline_message_id is not specified |
| inline_message_id | String | Conditional | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| latitude | Float | Yes | New latitude |
| longitude | Float | Yes | New longitude |
| live_period | Integer | No | New period in seconds for live location (60-86400) or 0x7FFFFFFF for indefinite |
| horizontal_accuracy | Float | No | Accuracy radius in meters (0-1500) |
| heading | Integer | No | Direction of movement in degrees (1-360) |
| proximity_alert_radius | Integer | No | Max distance for proximity alerts in meters (1-100000) |
| reply_markup | InlineKeyboardMarkup | No | New inline keyboard |

**Returns:** Message or True

---

## stopMessageLiveLocation

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Conditional | Required if inline_message_id is not specified |
| message_id | Integer | Conditional | Required if inline_message_id is not specified |
| inline_message_id | String | Conditional | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| reply_markup | InlineKeyboardMarkup | No | New inline keyboard |

**Returns:** Message or True

---

## Gotchas

- Cannot edit a message after 48 hours (for non-inline messages).
- `editMessageText` returns 400 Bad Request if new text is identical to current text -- always check before editing.
- For inline messages, only `reply_markup` with InlineKeyboardMarkup works.
- `editMessageMedia` can change media type (e.g., photo to video).
- Live location: must be stopped explicitly or it expires after `live_period` seconds.
