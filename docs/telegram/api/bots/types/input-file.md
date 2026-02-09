# File Upload Handling

Types for sending files to the Telegram Bot API. Files can be sent via reuse (`file_id`), URL, or direct upload. `InputMedia` variants wrap media files with metadata for use in methods that accept grouped media.

## Types

### InputFile

Represents the contents of a file to be uploaded. There are three ways to send files:

**Method 1: file_id (reuse existing file)**

Pass a `file_id` as a String to send a file that already exists on Telegram servers. No re-upload required. Every file object in the API (PhotoSize, Audio, Document, etc.) contains a `file_id`.

**Method 2: HTTP URL**

Pass an HTTP URL as a String. Telegram will download the file from the specified URL. Size limits: 5 MB for photos, 20 MB for all other file types.

**Method 3: multipart/form-data upload**

Upload the file directly using `multipart/form-data` encoding with the POST method. This is the only method that supports sending new files from disk.

| Sending Method | Value | Max Size | Notes |
|---------------|-------|----------|-------|
| file_id | String (existing file identifier) | N/A (already on server) | No re-upload. Can be used across chats. `file_id` is unique per bot. |
| HTTP URL | String (https://...) | 5 MB photos, 20 MB other | Telegram downloads the file. Must be publicly accessible. |
| multipart upload | File binary via multipart/form-data | 50 MB general, 10 MB photos | Direct upload from the calling application. |

### InputMediaPhoto

Represents a photo to be sent as part of a media group.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"photo"` |
| media | String | Yes | File to send. Pass a `file_id`, an HTTP URL, or `attach://<file_attach_name>` for multipart upload. |
| caption | String | No | Caption for the photo. 0-1024 characters after entity parsing. |
| parse_mode | String | No | Parse mode for the caption: `"Markdown"`, `"MarkdownV2"`, or `"HTML"`. |
| caption_entities | Array of MessageEntity | No | List of special entities in the caption. Overrides `parse_mode`. |
| show_caption_above_media | Boolean | No | If `true`, the caption is shown above the photo. |
| has_spoiler | Boolean | No | If `true`, the photo is covered with a spoiler animation. |

### InputMediaVideo

Represents a video to be sent as part of a media group.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"video"` |
| media | String | Yes | File to send. Pass a `file_id`, an HTTP URL, or `attach://<file_attach_name>` for multipart upload. |
| thumbnail | InputFile or String | No | Thumbnail of the video. Can be uploaded via multipart or passed as `file_id`/URL. Should be JPEG, max 200 kB, ideally 320x320 px. |
| caption | String | No | Caption for the video. 0-1024 characters after entity parsing. |
| parse_mode | String | No | Parse mode for the caption: `"Markdown"`, `"MarkdownV2"`, or `"HTML"`. |
| caption_entities | Array of MessageEntity | No | List of special entities in the caption. Overrides `parse_mode`. |
| show_caption_above_media | Boolean | No | If `true`, the caption is shown above the video. |
| width | Integer | No | Video width. |
| height | Integer | No | Video height. |
| duration | Integer | No | Video duration in seconds. |
| supports_streaming | Boolean | No | If `true`, the video is suitable for streaming. |
| has_spoiler | Boolean | No | If `true`, the video is covered with a spoiler animation. |

### InputMediaAnimation

Represents an animation (GIF or H.264/MPEG-4 AVC video without sound) to be sent as part of a media group.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"animation"` |
| media | String | Yes | File to send. Pass a `file_id`, an HTTP URL, or `attach://<file_attach_name>` for multipart upload. |
| thumbnail | InputFile or String | No | Thumbnail of the animation. Should be JPEG, max 200 kB, ideally 320x320 px. |
| caption | String | No | Caption for the animation. 0-1024 characters after entity parsing. |
| parse_mode | String | No | Parse mode for the caption: `"Markdown"`, `"MarkdownV2"`, or `"HTML"`. |
| caption_entities | Array of MessageEntity | No | List of special entities in the caption. Overrides `parse_mode`. |
| show_caption_above_media | Boolean | No | If `true`, the caption is shown above the animation. |
| width | Integer | No | Animation width. |
| height | Integer | No | Animation height. |
| duration | Integer | No | Animation duration in seconds. |
| has_spoiler | Boolean | No | If `true`, the animation is covered with a spoiler animation. |

### InputMediaAudio

Represents an audio file to be sent as part of a media group.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"audio"` |
| media | String | Yes | File to send. Pass a `file_id`, an HTTP URL, or `attach://<file_attach_name>` for multipart upload. |
| thumbnail | InputFile or String | No | Thumbnail of the audio file. Should be JPEG, max 200 kB, ideally 320x320 px. |
| caption | String | No | Caption for the audio. 0-1024 characters after entity parsing. |
| parse_mode | String | No | Parse mode for the caption: `"Markdown"`, `"MarkdownV2"`, or `"HTML"`. |
| caption_entities | Array of MessageEntity | No | List of special entities in the caption. Overrides `parse_mode`. |
| duration | Integer | No | Duration of the audio in seconds. |
| performer | String | No | Performer of the audio. |
| title | String | No | Title of the audio. |

### InputMediaDocument

Represents a general file to be sent as part of a media group.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"document"` |
| media | String | Yes | File to send. Pass a `file_id`, an HTTP URL, or `attach://<file_attach_name>` for multipart upload. |
| thumbnail | InputFile or String | No | Thumbnail of the file. Should be JPEG, max 200 kB, ideally 320x320 px. Thumbnails cannot be reused via `file_id`; they must be uploaded. |
| caption | String | No | Caption for the document. 0-1024 characters after entity parsing. |
| parse_mode | String | No | Parse mode for the caption: `"Markdown"`, `"MarkdownV2"`, or `"HTML"`. |
| caption_entities | Array of MessageEntity | No | List of special entities in the caption. Overrides `parse_mode`. |
| disable_content_type_detection | Boolean | No | If `true`, disables automatic server-side content type detection for files uploaded via multipart. |

## Gotchas

- `file_id` values are unique per bot. A `file_id` obtained by one bot cannot be used by another bot.
- `file_id` values may change over time and should not be persisted as permanent identifiers. Use `file_unique_id` for stable cross-bot identification.
- HTTP URL downloads are performed by Telegram servers, not by the bot. The URL must be publicly reachable from Telegram's infrastructure.
- HTTP URL downloads have stricter size limits (5 MB photos, 20 MB other) compared to multipart uploads (10 MB photos, 50 MB general).
- For `attach://<file_attach_name>` references in InputMedia, the corresponding file must be included in the same multipart request with the field name `<file_attach_name>`.
- Thumbnails for InputMedia types must be uploaded directly (multipart) -- they cannot reference a `file_id`.
- `parse_mode` and `caption_entities` are mutually exclusive. If both are provided, `caption_entities` takes precedence.
- `InputMediaAnimation` cannot be mixed with other InputMedia types in `sendMediaGroup`. A media group must contain only photos and videos, only audios, or only documents.
- `disable_content_type_detection` on `InputMediaDocument` only affects multipart uploads. It has no effect on `file_id` or URL sends.

## Patterns

- Use `file_id` reuse whenever possible to avoid re-uploading files and to reduce bandwidth.
- For media groups (`sendMediaGroup`), build an array of InputMedia objects. Only the first item's caption is displayed as the group caption.
- When uploading multiple new files in one request, use `attach://<name>` in the `media` field and include each file as a separate multipart field with the corresponding `<name>`.
- Use `file_unique_id` (available on all file objects) for deduplication and cross-reference, since it is consistent across bots.
