# Chat Actions

Show typing indicators and upload progress to let users know the bot is working.

## sendChatAction

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| action | String | Yes | Type of action (see below) |
| message_thread_id | Integer | No | Forum topic identifier |
| business_connection_id | String | No | Business connection identifier |

**Returns:** True

## Valid Actions

| Action | Indicator Shown |
|--------|----------------|
| typing | "Bot is typing..." |
| upload_photo | "Bot is sending a photo..." |
| record_video | "Bot is recording video..." |
| upload_video | "Bot is sending a video..." |
| record_voice | "Bot is recording voice..." |
| upload_voice | "Bot is sending a voice message..." |
| upload_document | "Bot is sending a document..." |
| choose_sticker | "Bot is choosing a sticker..." |
| find_location | "Bot is finding a location..." |
| record_video_note | "Bot is recording a video note..." |
| upload_video_note | "Bot is sending a video note..." |

## Gotchas

- Action automatically disappears after 5 seconds or when a message is sent
- Must be re-sent every 5 seconds for long operations
- Match the action to what you're doing: use "typing" when generating text, "upload_photo" when processing an image
- Actions are per-chat, not per-user in group chats
- No "processing" or "thinking" generic action -- use "typing" as the default
- Sending a message in the chat automatically cancels the action indicator
- Invalid action strings are silently ignored (no error returned)

## Patterns

- Long processing: loop sending "typing" every 4 seconds until done
- File preparation: send "upload_document" while generating/downloading a file
- Honest indicators: use the action that matches the actual operation
- Pre-response: send "typing" immediately when receiving a message that will take time to process
