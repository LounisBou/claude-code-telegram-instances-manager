# Bot Commands

Commands are the primary way users interact with bots. They appear in the bot menu and can be typed manually.

## How It Works

1. User types `/command` or `/command@botname` or selects from menu
2. Bot receives a Message update with text starting with `/`
3. The `entities` array contains a `bot_command` entity at offset 0

## Setting Up Commands

### setMyCommands

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| commands | Array of BotCommand | Yes | List of commands (max 100) |
| scope | BotCommandScope | No | Scope for these commands |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

### BotCommand

| Field | Type | Description |
|-------|------|-------------|
| command | String | Command text without `/` (1-32 chars, a-z, 0-9, _) |
| description | String | Description shown in menu (1-256 chars) |

### BotCommandScope (precedence order, most specific wins)

1. **BotCommandScopeChatMember** (chat_id + user_id) -- specific user in specific chat
2. **BotCommandScopeChat** (chat_id) -- specific chat
3. **BotCommandScopeChatAdministrators** (chat_id) -- admins in specific chat
4. **BotCommandScopeAllChatAdministrators** -- all admins in all groups
5. **BotCommandScopeAllGroupChats** -- all groups
6. **BotCommandScopeAllPrivateChats** -- all private chats
7. **BotCommandScopeDefault** -- default fallback

### deleteMyCommands

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scope | BotCommandScope | No | Scope to delete commands for |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

### getMyCommands

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scope | BotCommandScope | No | Scope to get commands for |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** Array of BotCommand

## Gotchas

- Commands must be lowercase a-z, 0-9, underscore only
- Command text does NOT include the `/` prefix
- In groups: commands can include bot username suffix `/command@botname`
- Scope precedence: more specific scopes override less specific ones
- Use language_code to show different commands to users in different languages
- deleteMyCommands and getMyCommands share the same scope/language_code params

## Patterns

- Set different commands for private chats vs groups vs admins
- Use language_code for localized command lists
- Common commands: /start, /help, /settings, /cancel
