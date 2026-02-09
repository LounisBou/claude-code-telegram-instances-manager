# Sending Stickers

## Methods

### sendSticker

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| sticker | InputFile or String | Yes | Sticker to send (file_id, HTTP URL .WEBP, or upload) |
| business_connection_id | String | No | Business connection |
| message_thread_id | Integer | No | Forum topic |
| emoji | String | No | Emoji associated with the sticker |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |
| message_effect_id | String | No | Message effect |
| reply_parameters | ReplyParameters | No | Reply config |
| reply_markup | Keyboard markup | No | Interface options |

**Returns:** Message

### getStickerSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | String | Yes | Name of the sticker set |

**Returns:** StickerSet

### getCustomEmojiStickers

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| custom_emoji_ids | Array of String | Yes | List of custom emoji identifiers (max 200) |

**Returns:** Array of Sticker

## Types

### Sticker

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for downloading/reusing |
| file_unique_id | String | Unique identifier |
| type | String | "regular", "mask", or "custom_emoji" |
| width | Integer | Sticker width |
| height | Integer | Sticker height |
| is_animated | Boolean | True if animated (TGS) |
| is_video | Boolean | True if video sticker (WEBM) |
| thumbnail | PhotoSize | Sticker thumbnail (optional) |
| emoji | String | Associated emoji (optional) |
| set_name | String | Sticker set name (optional) |
| premium_animation | File | Premium animation for premium stickers (optional) |
| mask_position | MaskPosition | Position for mask stickers (optional) |
| custom_emoji_id | String | Unique custom emoji identifier (optional) |
| needs_repainting | Boolean | True if must be repainted with user color (optional) |
| file_size | Integer | File size in bytes (optional) |

### StickerSet

| Field | Type | Description |
|-------|------|-------------|
| name | String | Sticker set name |
| title | String | Sticker set title |
| sticker_type | String | "regular", "mask", or "custom_emoji" |
| stickers | Array of Sticker | List of all stickers in set |
| thumbnail | PhotoSize | Set thumbnail (optional) |

### MaskPosition

| Field | Type | Description |
|-------|------|-------------|
| point | String | Face part: "forehead", "eyes", "mouth", or "chin" |
| x_shift | Float | X-axis shift (-1.0 to 1.0) |
| y_shift | Float | Y-axis shift (-1.0 to 1.0) |
| scale | Float | Mask scale |

## Gotchas

- Sticker formats: static (.WEBP, max 512KB), animated (.TGS, max 64KB), video (.WEBM, max 256KB)
- Max sticker dimensions: 512x512 for static/animated, 512x512 for video
- One side must be exactly 512px, the other <=512px
- getCustomEmojiStickers: max 200 IDs per request
