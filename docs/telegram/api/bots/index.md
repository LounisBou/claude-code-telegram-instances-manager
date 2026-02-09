# Telegram Bot API Reference

## API Essentials

- **Base URL:** `https://api.telegram.org/bot<token>/METHOD_NAME`
- **HTTP methods:** GET and POST both supported
- **Parameter formats:** URL query string, application/x-www-form-urlencoded, application/json, multipart/form-data (required for file uploads)
- **Token:** obtained from [@BotFather](https://t.me/BotFather), format: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`
- **Chat/User IDs:** 64-bit integers (use int64 / long, not int32)
- **File download:** `https://api.telegram.org/file/bot<token>/<file_path>`

## Response Format

All methods return a JSON object:

| Field       | Type               | Description                                               |
|-------------|--------------------|-----------------------------------------------------------|
| ok          | Boolean            | `true` if request succeeded                               |
| result      | *varies*           | Result of the query (only when `ok` is `true`)            |
| description | String             | Human-readable error description (when `ok` is `false`)   |
| error_code  | Integer            | Error code (when `ok` is `false`)                         |
| parameters  | ResponseParameters | Additional info to help retry (when `ok` is `false`)      |

## Error Handling

| HTTP Code | Meaning                  | Action                                              |
|-----------|--------------------------|-----------------------------------------------------|
| 200       | Success                  | Parse `result`                                      |
| 400       | Bad Request              | Fix parameters or check permissions                 |
| 401       | Unauthorized             | Invalid bot token                                   |
| 403       | Forbidden                | Bot blocked by user, or lacks chat permissions      |
| 404       | Not Found                | Wrong method name                                   |
| 409       | Conflict                 | Competing getUpdates calls or webhook conflict      |
| 429       | Too Many Requests        | Rate limited — respect `retry_after` in response    |
| 500       | Internal Server Error    | Telegram server issue — retry with backoff          |

## File Size Limits

| Operation          | Limit  |
|--------------------|--------|
| Download (getFile) | 20 MB  |
| Upload (POST)      | 50 MB  |
| Upload photo       | 10 MB  |
| Upload sticker     | 512 KB (PNG), 64 KB (TGS), 256 KB (WEBM) |

## Routing

| Need to...                           | Read                         |
|--------------------------------------|------------------------------|
| Understand shared types              | [types/](types/index.md)     |
| Receive updates from Telegram        | [updates/](updates/index.md) |
| Send or manage text messages         | [messages/](messages/index.md) |
| Send photos, video, audio, files     | [media/](media/index.md)     |
| Build interactive UIs in chat        | [interactivity/](interactivity/index.md) |
| Add buttons to messages              | [keyboards/](keyboards/index.md) |
| Use inline mode (cross-chat queries) | [inline/](inline/index.md)   |
| Manage chats, groups, channels       | [chat/](chat/index.md)       |
| Configure bot settings               | [bot/](bot/index.md)         |
| Handle payments and invoices         | [payments/](payments/index.md) |
| Work with stickers                   | [stickers/](stickers/index.md) |
| Build games                          | [games/](games/index.md)     |
| Handle Telegram Passport             | [passport/](passport/index.md) |
| Business account features            | [business/](business/index.md) |
| Gifts and giveaways                  | [gifts/](gifts/index.md)     |
| Web Apps (mini apps)                 | [web-apps/](web-apps/index.md) |
| Repost stories                       | [stories/](stories/index.md) |
| Suggested posts                      | [suggested-posts/](suggested-posts/index.md) |
