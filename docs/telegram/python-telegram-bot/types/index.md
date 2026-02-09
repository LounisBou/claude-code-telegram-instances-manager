# Types

> Telegram data types -- all extend TelegramObject and mirror the Telegram Bot API type hierarchy.

## Overview

Every type in `python-telegram-bot` inherits from `TelegramObject`, which provides `to_dict()`, `to_json()`, and the class method `de_json(data, bot)` for deserialization. Types are immutable dataclass-like objects that map 1:1 to the Telegram Bot API types. You rarely construct them manually -- they arrive via `Update` objects or are returned from `Bot` methods.

## TelegramObject Base

All types inherit these methods:

| Method | Returns | Description |
|---|---|---|
| `to_dict()` | `dict` | Serialize to dictionary. |
| `to_json()` | `str` | Serialize to JSON string. |
| `de_json(data, bot)` | `cls` | Class method. Deserialize from dict + bot instance. |
| `de_list(data, bot)` | `list[cls]` | Class method. Deserialize a list of dicts. |

## Routing Table

| File | When to read |
|------|-------------|
| [messages.md](messages.md) | Update, Message, Chat, ChatFullInfo, User, MessageEntity, MessageOrigin |
| [media.md](media.md) | PhotoSize, Document, Audio, Video, Voice, Animation, File, InputFile, InputMedia* |
| [keyboards.md](keyboards.md) | InlineKeyboardMarkup/Button, ReplyKeyboardMarkup/Button, ReplyKeyboardRemove, ForceReply |
| [other-types.md](other-types.md) | CallbackQuery, Poll, WebAppInfo, MenuButton, LinkPreviewOptions, ReplyParameters |
| [chat-management.md](chat-management.md) | BotCommand, ChatPermissions, ChatMember, ChatInviteLink, ForumTopic |

## Related

- [../bot.md](../bot.md) -- Bot methods that return these types
- [../handlers/index.md](../handlers/index.md) -- handlers that route Updates to callbacks
- [../application.md](../application.md) -- Application setup and lifecycle
- [Telegram API — Types](../../api/bots/types/index.md) -- type definitions in the API specification
