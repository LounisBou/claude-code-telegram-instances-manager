# Reply and Preview Configuration

Types for configuring message replies and link preview behavior. Used as parameters in message-sending methods.

## Types

### ReplyParameters

Describes a reply to a message. Passed as the `reply_parameters` field in send methods.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | Integer | Yes | Identifier of the message to reply to. Must exist in the target chat. |
| chat_id | Integer or String | No | Chat identifier if the message to reply to is in a different chat. Can be chat ID (Integer) or `@channelusername` (String). Required for cross-chat replies. |
| allow_sending_without_reply | Boolean | No | If `true`, the message will be sent even if the specified replied-to message is not found. Defaults to `false`, which causes the request to fail if the target message does not exist. |
| quote | String | No | Quoted part of the message to reply to. 0-1024 characters after entity parsing. Must be an exact substring of the original message. |
| quote_parse_mode | String | No | Parse mode for the `quote` field. Supports `"Markdown"`, `"MarkdownV2"`, and `"HTML"`. |
| quote_entities | Array of MessageEntity | No | List of special entities in the quote. Overrides `quote_parse_mode` if both are provided. |
| quote_position | Integer | No | Position of the quote in the original message (byte offset in UTF-16). |
| checklist_task_id | Integer | No | Identifier of the checklist task the message is a reply to. |

### LinkPreviewOptions

Describes options for link preview generation. Passed as the `link_preview_options` field in text message methods.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| is_disabled | Boolean | No | If `true`, no link preview is generated for the message. |
| url | String | No | URL to use for the link preview. If empty, the first URL found in the message text is used. |
| prefer_small_media | Boolean | No | If `true`, the preview media is shown in a compact (small) size. Ignored if the preview media cannot be reduced in size or if `url` is not set. Mutually exclusive with `prefer_large_media`. |
| prefer_large_media | Boolean | No | If `true`, the preview media is shown in an enlarged (large) size. Ignored if the preview URL is not explicitly specified or if the media cannot be enlarged. Mutually exclusive with `prefer_small_media`. |
| show_above_text | Boolean | No | If `true`, the link preview is shown above the message text. Defaults to `false` (preview shown below text). |

## Gotchas

- `ReplyParameters.message_id` is required. To reply to a message in a different chat, you must also provide `chat_id`.
- `quote` must be an exact substring of the original message text or caption. If the text does not match, the API returns an error.
- `quote_parse_mode` and `quote_entities` are mutually exclusive. If both are provided, `quote_entities` takes precedence and `quote_parse_mode` is ignored.
- `prefer_small_media` and `prefer_large_media` are mutually exclusive. Do not set both to `true`.
- `LinkPreviewOptions.url` allows you to override which link is previewed, even if that URL does not appear in the message text.
- When `is_disabled` is `true`, all other `LinkPreviewOptions` fields are ignored.

## Patterns

- Use `allow_sending_without_reply: true` when replying to messages that may have been deleted by the time your bot responds (e.g., in moderation workflows).
- Use `quote` to highlight the specific part of the message being replied to, improving conversational clarity in groups.
- Set `is_disabled: true` on `LinkPreviewOptions` when sending URLs that should not generate previews (e.g., API endpoint URLs, internal links).
- Use `prefer_small_media` to keep link previews compact in busy group conversations.
