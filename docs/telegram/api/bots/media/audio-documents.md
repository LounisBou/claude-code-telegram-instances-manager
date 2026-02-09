# Audio & Documents

## sendAudio

Send an audio file. For music files (MP3, M4A, etc.) -- clients display with album art and player UI. For voice messages, use sendVoice instead.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| audio | InputFile or String | Yes | Audio file to send (file_id, HTTP URL, or upload) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| caption | String | No | Audio caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption (alternative to parse_mode) |
| duration | Integer | No | Duration of the audio in seconds |
| performer | String | No | Performer of the track |
| title | String | No | Track name |
| thumbnail | InputFile or String | No | Thumbnail of the audio (JPEG only, max 200 KB, max 320px width/height) |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendDocument

Send a general file. Telegram clients handle document downloads without special UI (unlike audio or video).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| document | InputFile or String | Yes | File to send (file_id, HTTP URL, or upload) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| thumbnail | InputFile or String | No | Thumbnail of the document (JPEG only, max 200 KB, max 320px width/height) |
| caption | String | No | Document caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| disable_content_type_detection | Boolean | No | Disable automatic MIME type detection for files uploaded via multipart/form-data |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendVoice

Send a voice message. The file must be in .OGG format encoded with OPUS codec. Clients display it as a waveform with a play button.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| voice | InputFile or String | Yes | Voice message to send (.OGG with OPUS codec; file_id, HTTP URL, or upload) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| caption | String | No | Voice message caption, 0-1024 characters after entity parsing |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| duration | Integer | No | Duration of the voice message in seconds |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## Types

### Audio

Represents an audio file to be treated as music by Telegram clients.

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file, which can be used to download or reuse the file |
| file_unique_id | String | Unique identifier for this file, cannot be used to download or reuse |
| duration | Integer | Duration of the audio in seconds |
| performer | String | Optional. Performer of the audio as defined by the sender or audio tags |
| title | String | Optional. Title of the audio as defined by the sender or audio tags |
| file_name | String | Optional. Original filename |
| mime_type | String | Optional. MIME type of the file |
| file_size | Integer | Optional. File size in bytes |
| thumbnail | PhotoSize | Optional. Thumbnail of the album cover |

### Document

Represents a general file (not a photo, audio, or video).

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file |
| file_unique_id | String | Unique identifier for this file |
| thumbnail | PhotoSize | Optional. Document thumbnail as defined by the sender |
| file_name | String | Optional. Original filename |
| mime_type | String | Optional. MIME type of the file |
| file_size | Integer | Optional. File size in bytes |

### Voice

Represents a voice note.

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file |
| file_unique_id | String | Unique identifier for this file |
| duration | Integer | Duration of the audio in seconds |
| mime_type | String | Optional. MIME type of the file |
| file_size | Integer | Optional. File size in bytes |

---

## Gotchas

- `sendAudio` is for music files. Clients display it with album art, performer, and title. For general audio or voice, use `sendVoice`.
- `sendVoice` requires .OGG format with OPUS codec. Other audio formats will be sent as a document instead.
- `sendDocument` with `disable_content_type_detection=true` prevents Telegram from auto-detecting the file type. Useful when you want a video file sent as a downloadable document, not as a playable video.
- Upload size limit: 50 MB for all file types via direct upload.
- Download via URL: Telegram fetches up to 20 MB.
- `thumbnail` is only used when uploading a file directly. Ignored for file_id and URL sends.
- `performer` and `title` metadata in sendAudio: if not provided, Telegram extracts them from the audio file's ID3 tags when possible.
