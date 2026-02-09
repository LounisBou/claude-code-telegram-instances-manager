# Files

Upload, download, and reference files on Telegram servers.

## getFile

Get basic info about a file and prepare it for downloading. The file can then be downloaded via the returned `file_path`. The link is guaranteed to be valid for at least 1 hour.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file_id | String | Yes | File identifier from any file-containing type (Photo, Video, Audio, Document, etc.) |

**Returns:** File

**Download URL format:** `https://api.telegram.org/file/bot<token>/<file_path>`

---

## Types

### File

Represents a file ready to be downloaded.

| Field | Type | Description |
|-------|------|-------------|
| file_id | String | Identifier for this file, which can be used to download or reuse the file |
| file_unique_id | String | Unique identifier for this file. Cannot be used to download or reuse the file |
| file_size | Integer | Optional. File size in bytes. Can be bigger than 2^31 for very large files |
| file_path | String | Optional. File path. Use the download URL format above to get the file |

### InputFile

There are three ways to send files (photos, stickers, audio, media, etc.):

**1. file_id (String)**

Reuse a file already stored on Telegram servers. Pass the `file_id` from any received file object (e.g., `message.photo[0].file_id`). No size limits. The file is not re-uploaded.

**2. HTTP URL (String)**

Provide a public HTTP URL for Telegram to download the file. Telegram servers download the file.

- Photo URLs: max 5 MB
- Other file URLs: max 20 MB

**3. Upload (multipart/form-data)**

Upload a new file directly via multipart/form-data POST. Attach the file under the parameter name (e.g., `photo`, `document`, `video`).

- All file types: max 10 MB for photos, 50 MB for other files

---

## InputMedia Variants

Used with `sendMediaGroup` and `editMessageMedia` to specify media content.

### InputMediaPhoto

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "photo" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |
| caption | String | Optional. Caption, 0-1024 characters |
| parse_mode | String | Optional. Caption parsing mode |
| caption_entities | Array of MessageEntity | Optional. Special entities in caption |
| show_caption_above_media | Boolean | Optional. Show caption above the media |
| has_spoiler | Boolean | Optional. Cover with spoiler animation |

### InputMediaVideo

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "video" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |
| thumbnail | InputFile or String | Optional. Thumbnail (JPEG only, max 200 KB, max 320px width/height) |
| cover | InputFile or String | Optional. Cover for the video in the message |
| start_timestamp | Integer | Optional. Timestamp in seconds from which the cover should start playing |
| caption | String | Optional. Caption, 0-1024 characters |
| parse_mode | String | Optional. Caption parsing mode |
| caption_entities | Array of MessageEntity | Optional. Special entities in caption |
| show_caption_above_media | Boolean | Optional. Show caption above the media |
| width | Integer | Optional. Video width |
| height | Integer | Optional. Video height |
| duration | Integer | Optional. Video duration in seconds |
| supports_streaming | Boolean | Optional. True if suitable for streaming |
| has_spoiler | Boolean | Optional. Cover with spoiler animation |

### InputMediaAnimation

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "animation" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |
| thumbnail | InputFile or String | Optional. Thumbnail (JPEG only, max 200 KB, max 320px width/height) |
| caption | String | Optional. Caption, 0-1024 characters |
| parse_mode | String | Optional. Caption parsing mode |
| caption_entities | Array of MessageEntity | Optional. Special entities in caption |
| show_caption_above_media | Boolean | Optional. Show caption above the media |
| width | Integer | Optional. Animation width |
| height | Integer | Optional. Animation height |
| duration | Integer | Optional. Animation duration in seconds |
| has_spoiler | Boolean | Optional. Cover with spoiler animation |

### InputMediaAudio

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "audio" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |
| thumbnail | InputFile or String | Optional. Thumbnail (JPEG only, max 200 KB, max 320px width/height) |
| caption | String | Optional. Caption, 0-1024 characters |
| parse_mode | String | Optional. Caption parsing mode |
| caption_entities | Array of MessageEntity | Optional. Special entities in caption |
| duration | Integer | Optional. Audio duration in seconds |
| performer | String | Optional. Performer of the audio |
| title | String | Optional. Title of the audio |

### InputMediaDocument

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "document" |
| media | String | File to send (file_id, HTTP URL, or attach://file_name for multipart upload) |
| thumbnail | InputFile or String | Optional. Thumbnail (JPEG only, max 200 KB, max 320px width/height) |
| caption | String | Optional. Caption, 0-1024 characters |
| parse_mode | String | Optional. Caption parsing mode |
| caption_entities | Array of MessageEntity | Optional. Special entities in caption |
| disable_content_type_detection | Boolean | Optional. Disable automatic MIME type detection for uploaded files |

---

## sendMediaGroup

Send a group of photos, videos, documents, or audios as an album. Documents and audio files can only be grouped with items of the same type.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| media | Array of InputMedia | Yes | Array of media to send (2-10 items). Must be InputMediaAudio, InputMediaDocument, InputMediaPhoto, or InputMediaVideo |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |

**Returns:** Array of Message

Note: `reply_markup` is NOT supported for sendMediaGroup.

---

## Gotchas

- `file_id` vs `file_unique_id`: only `file_id` can be used to download or reuse a file. `file_unique_id` is for deduplication across bots and cannot be used as a file reference.
- `getFile` returns a temporary `file_path` -- the download link expires after at least 1 hour.
- Download limit via `getFile`: 20 MB maximum file size.
- Upload limit via multipart POST: 10 MB for photos, 50 MB for other files.
- URL download limit: 5 MB for photos, 20 MB for other files.
- `file_id` is specific to each bot. A `file_id` from one bot cannot be used by another bot. However, `file_unique_id` is the same across all bots.
- `sendMediaGroup`: requires 2-10 items. Photos and videos can be mixed together. Audio files can only be grouped with other audio files. Documents can only be grouped with other documents.
- `sendMediaGroup` does not support `reply_markup` -- no inline keyboard or reply keyboard can be attached to media groups.
- When uploading files via InputMedia and attaching them via multipart/form-data, use `attach://field_name` as the `media` value and include the actual file as a separate multipart field with the corresponding field name.
- A `file_id` obtained from a message in one chat can be reused to send the same file to any other chat, without re-uploading.
