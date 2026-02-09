# Managing Sticker Sets

## Methods

### uploadStickerFile

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | User identifier of sticker set owner |
| sticker | InputFile | Yes | Sticker file (.WEBP, .PNG, .TGS, or .WEBM) |
| sticker_format | String | Yes | "static", "animated", or "video" |

**Returns:** File

### createNewStickerSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | User who will own the sticker set |
| name | String | Yes | Set name (1-64 chars, must end with _by_\<bot_username\>) |
| title | String | Yes | Set title (1-64 chars) |
| stickers | Array of InputSticker | Yes | Stickers to add (1-50) |
| sticker_type | String | No | "regular" (default), "mask", or "custom_emoji" |
| needs_repainting | Boolean | No | True for adaptive custom emoji |

**Returns:** True

### addStickerToSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | Set owner |
| name | String | Yes | Set name |
| sticker | InputSticker | Yes | Sticker to add |

**Returns:** True

### setStickerPositionInSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sticker | String | Yes | File identifier of the sticker |
| position | Integer | Yes | New position in the set (0-based) |

**Returns:** True

### deleteStickerFromSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sticker | String | Yes | File identifier of the sticker |

**Returns:** True

### replaceStickerInSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | Set owner |
| name | String | Yes | Set name |
| old_sticker | String | Yes | File identifier of the sticker to replace |
| sticker | InputSticker | Yes | New sticker data |

**Returns:** True

### setStickerSetThumbnail

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | Set owner |
| name | String | Yes | Set name |
| thumbnail | InputFile or String | No | Thumbnail image (omit to remove) |
| format | String | Yes | "static", "animated", or "video" |

**Returns:** True

### setCustomEmojiStickerSetThumbnail

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | String | Yes | Set name |
| custom_emoji_id | String | No | Custom emoji identifier for thumbnail (omit to remove) |

**Returns:** True

### setStickerSetTitle

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | String | Yes | Set name |
| title | String | Yes | New set title (1-64 chars) |

**Returns:** True

### deleteStickerSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | String | Yes | Set name |

**Returns:** True

### setStickerEmojiList

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sticker | String | Yes | File identifier of the sticker |
| emoji_list | Array of String | Yes | List of 1-20 emoji associated with the sticker |

**Returns:** True

### setStickerKeywords

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sticker | String | Yes | File identifier of the sticker |
| keywords | Array of String | No | Search keywords (max 20, each max 64 chars) |

**Returns:** True

### setStickerMaskPosition

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| sticker | String | Yes | File identifier of the sticker |
| mask_position | MaskPosition | No | Position for mask placement (omit to remove) |

**Returns:** True

## Types

### InputSticker

| Field | Type | Description |
|-------|------|-------------|
| sticker | InputFile or String | The sticker file |
| format | String | "static", "animated", or "video" |
| emoji_list | Array of String | List of 1-20 emoji associated with the sticker |
| mask_position | MaskPosition | Position for mask stickers (optional) |
| keywords | Array of String | Search keywords, max 20, each max 64 chars (optional) |

## Gotchas

- Set name MUST end with \_by\_\<bot_username\>
- Max 120 stickers per regular/mask set, 200 per custom emoji set
- All stickers in a set must be the same type (regular/mask/custom_emoji)
- uploadStickerFile: only needed for sticker formats that require pre-upload
- User who creates the set becomes the permanent owner
