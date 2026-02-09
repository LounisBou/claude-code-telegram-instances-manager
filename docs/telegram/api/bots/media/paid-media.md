# Paid Media

## sendPaidMedia

Send paid media that requires Telegram Stars to view. Users must pay the specified number of Stars before they can access the content.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| star_count | Integer | Yes | Number of Telegram Stars the user must pay to view the media (1-2500) |
| media | Array of InputPaidMedia | Yes | Array of paid media to send (1-10 items) |
| business_connection_id | String | No | Unique identifier of the business connection |
| payload | String | No | Bot-defined payload, 0-128 bytes. Not visible to the user; use to identify purchases in purchased_paid_media updates |
| caption | String | No | Media caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| show_caption_above_media | Boolean | No | Show caption above the media instead of below |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup | No | Inline keyboard attached to the message |

**Returns:** Message

---

## Types

### PaidMediaInfo

Describes the paid media added to a message.

| Field | Type | Description |
|-------|------|-------------|
| star_count | Integer | Number of Telegram Stars that must be paid to unlock the media |
| paid_media | Array of PaidMedia | Information about the paid media |

### PaidMedia

One of the following types, distinguished by the `type` field:

#### PaidMediaPreview

Shown to users before they purchase the media.

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "preview" |
| width | Integer | Optional. Media width as defined by the sender |
| height | Integer | Optional. Media height as defined by the sender |
| duration | Integer | Optional. Duration of the media in seconds |

#### PaidMediaPhoto

Shown to users after they purchase the media (photo content).

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "photo" |
| photo | Array of PhotoSize | The photo |

#### PaidMediaVideo

Shown to users after they purchase the media (video content).

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "video" |
| video | Video | The video |

### InputPaidMedia

One of the following types for specifying paid media to send:

#### InputPaidMediaPhoto

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "photo" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |

#### InputPaidMediaVideo

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "video" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |
| thumbnail | InputFile or String | Optional. Thumbnail (JPEG only, max 200 KB, max 320px width/height) |
| width | Integer | Optional. Video width |
| height | Integer | Optional. Video height |
| duration | Integer | Optional. Video duration in seconds |
| supports_streaming | Boolean | Optional. Pass True if the video is suitable for streaming |

### PaidMediaPurchased

Contains information about a paid media purchase. Received via the `purchased_paid_media` update.

| Field | Type | Description |
|-------|------|-------------|
| from | User | User who purchased the media |
| paid_media_payload | String | Bot-specified payload from the original sendPaidMedia call |

---

## Gotchas

- Star count range: 1-2500 Telegram Stars per message.
- 1-10 media items per sendPaidMedia call.
- `payload`: use this field to identify which content was purchased when you receive the `purchased_paid_media` update. It is not visible to the user.
- Only `InlineKeyboardMarkup` is supported for `reply_markup` (not ReplyKeyboardMarkup or other types).
- Before purchase, users see `PaidMediaPreview` (blurred/placeholder). After purchase, the actual `PaidMediaPhoto` or `PaidMediaVideo` is revealed.
- The bot must be an administrator in the channel or group to send paid media.
