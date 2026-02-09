# Bot Settings

Configure bot identity, commands, descriptions, and menu button.

---

## getMe

No parameters.

**Returns:** User object with bot-specific fields: can_join_groups, can_read_all_group_messages, supports_inline_queries, can_connect_to_business, has_main_web_app, has_topics_enabled

---

## logOut

No parameters. Log out from cloud Bot API before moving to local server.

**Returns:** True

---

## close

No parameters. Close bot instance before moving from local to cloud.

**Returns:** True

---

## setMyCommands

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| commands | Array of BotCommand | Yes | List of commands (max 100) |
| scope | BotCommandScope | No | Scope for which commands are set |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

---

## deleteMyCommands

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scope | BotCommandScope | No | Scope for which commands are deleted |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

---

## getMyCommands

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| scope | BotCommandScope | No | Scope for which to return commands |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** Array of BotCommand

---

## setMyName

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | String | No | New bot name (0-64 chars). Pass empty string to remove. |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

---

## getMyName

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** BotName

---

## setMyDescription

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| description | String | No | New bot description (0-512 chars). Pass empty string to remove. |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

---

## getMyDescription

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** BotDescription

---

## setMyShortDescription

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| short_description | String | No | New short description (0-120 chars). Pass empty string to remove. |
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** True

---

## getMyShortDescription

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| language_code | String | No | Two-letter ISO 639-1 language code |

**Returns:** BotShortDescription

---

## setChatMenuButton

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer | No | Target user (default: all users) |
| menu_button | MenuButton | No | New menu button |

**Returns:** True

---

## getChatMenuButton

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer | No | Target user (default: all users) |

**Returns:** MenuButton

---

## Types

### BotCommand

| Field | Type | Description |
|-------|------|-------------|
| command | String | Text of the command (1-32 chars, lowercase a-z, 0-9, _) |
| description | String | Description of the command (1-256 chars) |

### BotCommandScope variants

| Variant | type value | Additional fields |
|---------|------------|-------------------|
| BotCommandScopeDefault | "default" | none |
| BotCommandScopeAllPrivateChats | "all_private_chats" | none |
| BotCommandScopeAllGroupChats | "all_group_chats" | none |
| BotCommandScopeAllChatAdministrators | "all_chat_administrators" | none |
| BotCommandScopeChat | "chat" | chat_id |
| BotCommandScopeChatAdministrators | "chat_administrators" | chat_id |
| BotCommandScopeChatMember | "chat_member" | chat_id, user_id |

### MenuButton variants

- **MenuButtonCommands** (type="commands"): default, shows list of commands
- **MenuButtonWebApp** (type="web_app"): text (String), web_app (WebAppInfo)
- **MenuButtonDefault** (type="default"): no special behavior

### BotName

| Field | Type | Description |
|-------|------|-------------|
| name | String | The bot's name |

### BotDescription

| Field | Type | Description |
|-------|------|-------------|
| description | String | The bot's description |

### BotShortDescription

| Field | Type | Description |
|-------|------|-------------|
| short_description | String | The bot's short description |

---

## Gotchas

- Command scope precedence: most specific scope wins (chat_member > chat > all_group_chats > default).
- `language_code`: set different commands/descriptions per language.
- Commands: must start with `/` in user interface, but the `command` field in BotCommand should NOT include `/`.
- Max 100 commands per scope.
- `setMyDescription`: shown when user opens bot for the first time ("What can this bot do?").
- `setMyShortDescription`: shown in bot sharing, chat lists, and inline mentions.
- `logOut`: wait at least 10 minutes before logging in again on another server.
- `close`: must be called before moving bot from local Bot API server to cloud.
