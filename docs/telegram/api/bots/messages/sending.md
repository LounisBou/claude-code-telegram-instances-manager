# Sending Messages

## sendMessage

Send text messages to a chat.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| text | String | Yes | Text of the message, 1-4096 characters after entity parsing |
| business_connection_id | String | No | Unique identifier of the business connection for business bot messages |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| parse_mode | String | No | "MarkdownV2", "HTML", or "Markdown" (legacy) |
| entities | Array of MessageEntity | No | List of special entities in message text (alternative to parse_mode) |
| link_preview_options | LinkPreviewOptions | No | Link preview generation options |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendMessageDraft

Allows partial messages to be streamed to a user while being generated. Useful for bots that use AI to generate responses.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat identifier |
| text | String | Yes | Text content of the draft message |
| business_connection_id | String | No | Business connection identifier |
| message_thread_id | Integer | No | Target message thread (topic) identifier |
| parse_mode | String | No | Text parsing mode |
| entities | Array of MessageEntity | No | Special entities in text |
| link_preview_options | LinkPreviewOptions | No | Link preview generation options |
| reply_parameters | ReplyParameters | No | Reply configuration |

**Returns:** MessageId

---

## Gotchas

- Text limit is 4096 characters AFTER entity parsing.
- `reply_markup` accepts 4 different types -- only one at a time.
- `sendMessageDraft`: the message appears as "being typed" and can be updated incrementally; useful for streaming AI responses.
- `parse_mode` and `entities` are mutually exclusive -- use one or the other.
- To mention a user without a username, use `parse_mode=HTML` with `<a href="tg://user?id=123456">name</a>`.
