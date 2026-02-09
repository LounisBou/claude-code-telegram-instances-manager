# Shared Types

Types referenced across multiple sections of the Telegram Bot API. These are the core data structures returned in API responses and used as parameters in API methods.

## Quick Reference

| Type | Description | File |
|------|-------------|------|
| User, Chat, ChatFullInfo, ChatPhoto, ChatLocation, Birthdate | Users, chats, and chat details | [user-chat.md](user-chat.md) |
| Message, MessageId, InaccessibleMessage, MaybeInaccessibleMessage | Message object (80+ fields) and related types | [message.md](message.md) |
| MessageOriginUser, MessageOriginHiddenUser, MessageOriginChat, MessageOriginChannel | Message origin tracking for forwarded messages | [message-origin.md](message-origin.md) |
| InputFile, InputMediaPhoto, InputMediaVideo, InputMediaAnimation, InputMediaAudio, InputMediaDocument | File upload handling and media input wrappers | [input-file.md](input-file.md) |
| ReplyParameters, LinkPreviewOptions | Reply configuration and link preview behavior | [reply-parameters.md](reply-parameters.md) |
| ResponseParameters, WebhookInfo | API response metadata and webhook status | [response.md](response.md) |

## Type Conventions

- **Integer** fields for Chat and User IDs can exceed 32-bit range. Always use 64-bit integers.
- **Optional** fields are omitted from the JSON response when not applicable (not set to `null`).
- **Union types** (e.g., MaybeInaccessibleMessage) are discriminated by checking specific field values.
- **String** identifiers like `file_id` and `file_unique_id` are opaque -- do not parse or compare substrings.
