# Photos & Videos

## sendPhoto

Send a photo to a chat.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| photo | InputFile or String | Yes | Photo to send (file_id, HTTP URL, or upload) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| caption | String | No | Photo caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption (alternative to parse_mode) |
| show_caption_above_media | Boolean | No | Show caption above the photo instead of below |
| has_spoiler | Boolean | No | Cover photo with a spoiler animation |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendVideo

Send a video to a chat. Telegram clients support MPEG4 videos (other formats may be sent as Document).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| video | InputFile or String | Yes | Video to send (file_id, HTTP URL, or upload) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| duration | Integer | No | Duration of the video in seconds |
| width | Integer | No | Video width |
| height | Integer | No | Video height |
| thumbnail | InputFile or String | No | Thumbnail of the video (JPEG only, max 200 KB, max 320px width/height) |
| cover | InputFile or String | No | Cover for the video in the message. Ignored if thumbnail is not set or set to file_id/URL |
| start_timestamp | Integer | No | Timestamp in seconds from which the video cover should start playing |
| caption | String | No | Video caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| show_caption_above_media | Boolean | No | Show caption above the video instead of below |
| has_spoiler | Boolean | No | Cover video with a spoiler animation |
| supports_streaming | Boolean | No | Pass True if the video is suitable for streaming |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendAnimation

Send an animation (GIF or soundless H.264/MPEG-4 AVC video).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| animation | InputFile or String | Yes | Animation to send (file_id, HTTP URL, or upload) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| duration | Integer | No | Duration of the animation in seconds |
| width | Integer | No | Animation width |
| height | Integer | No | Animation height |
| thumbnail | InputFile or String | No | Thumbnail of the animation (JPEG only, max 200 KB, max 320px width/height) |
| caption | String | No | Animation caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| show_caption_above_media | Boolean | No | Show caption above the animation instead of below |
| has_spoiler | Boolean | No | Cover animation with a spoiler animation |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendVideoNote

Send a video note (round video message, max 1 minute).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| video_note | InputFile or String | Yes | Video note to send (file_id or upload; HTTP URLs not supported) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| duration | Integer | No | Duration of the video in seconds |
| length | Integer | No | Video width and height (diameter of the circular video) |
| thumbnail | InputFile or String | No | Thumbnail of the video note (JPEG only, max 200 KB, max 320px width/height) |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## Types

### PhotoSize

Represents one size of a photo or a file/sticker thumbnail.

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file, which can be used to download or reuse the file |
| file_unique_id | String | Unique identifier for this file, cannot be used to download or reuse |
| width | Integer | Photo width |
| height | Integer | Photo height |
| file_size | Integer | Optional. File size in bytes |

### Video

Represents a video file.

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file |
| file_unique_id | String | Unique identifier for this file |
| width | Integer | Video width as defined by the sender |
| height | Integer | Video height as defined by the sender |
| duration | Integer | Duration of the video in seconds |
| thumbnail | PhotoSize | Optional. Video thumbnail |
| cover | Array of PhotoSize | Optional. Available sizes of the cover of the video in the message |
| start_timestamp | Integer | Optional. Timestamp in seconds from which the video starts playing |
| file_name | String | Optional. Original filename |
| mime_type | String | Optional. MIME type of the file |
| file_size | Integer | Optional. File size in bytes |

### Animation

Represents an animation file (GIF or H.264/MPEG-4 AVC video without sound).

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file |
| file_unique_id | String | Unique identifier for this file |
| width | Integer | Video width as defined by the sender |
| height | Integer | Video height as defined by the sender |
| duration | Integer | Duration of the video in seconds |
| thumbnail | PhotoSize | Optional. Animation thumbnail |
| file_name | String | Optional. Original filename |
| mime_type | String | Optional. MIME type of the file |
| file_size | Integer | Optional. File size in bytes |

### VideoNote

Represents a video message (round video).

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file |
| file_unique_id | String | Unique identifier for this file |
| length | Integer | Video width and height (diameter of the video message) |
| duration | Integer | Duration of the video in seconds |
| thumbnail | PhotoSize | Optional. Video thumbnail |
| file_size | Integer | Optional. File size in bytes |

---

## Gotchas

- Photos: Telegram generates multiple PhotoSize objects at different resolutions. The last element in the array is the highest resolution.
- Photo file size limit: 10 MB.
- Video/animation via URL: Telegram downloads up to 20 MB.
- VideoNote: always square (length = width = height), maximum 1 minute duration.
- VideoNote does not support HTTP URL sends -- only file_id and direct upload.
- `has_spoiler`: available for sendPhoto, sendVideo, and sendAnimation.
- `thumbnail`: must be JPEG format, max 200 KB, max 320px width/height. Ignored when sending by file_id or URL.
- `show_caption_above_media`: available for sendPhoto, sendVideo, and sendAnimation.
