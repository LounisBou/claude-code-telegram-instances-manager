# Menu Button

Configure the button shown in the bot's chat input area (replaces the default "/" commands menu).

## setChatMenuButton

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer | No | Target user's private chat (default: all users) |
| menu_button | MenuButton | No | New menu button (default: MenuButtonDefault) |

**Returns:** True

## getChatMenuButton

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer | No | Target user's private chat (default: all users) |

**Returns:** MenuButton

## MenuButton Variants

### MenuButtonCommands

| Field | Type | Description |
|-------|------|-------------|
| type | String | "commands" |

Shows the default commands menu (list of BotCommands set via setMyCommands).

### MenuButtonWebApp

| Field | Type | Description |
|-------|------|-------------|
| type | String | "web_app" |
| text | String | Button label shown in the input area |
| web_app | WebAppInfo | URL to open when button is pressed |

Opens a Web App in a bottom sheet (can be expanded to full screen).

### MenuButtonDefault

| Field | Type | Description |
|-------|------|-------------|
| type | String | "default" |

No special menu button. Uses Telegram's default behavior (which varies by client and may show a commands button if commands are set).

## Gotchas

- Per-user customization: pass chat_id to set different menu buttons for different users
- Without chat_id: sets the default menu button for ALL users
- MenuButtonWebApp: the text field is the button label shown in the input area (not the Web App title)
- Default behavior without any configuration: shows commands list button if commands are set
- Web App menu button: opens the Web App in a bottom sheet
- Only works in private chats with the bot (not in groups)

## Patterns

- Main app: set MenuButtonWebApp to make the Web App the primary interface
- Contextual: set different menu buttons per user based on their role or state
- Fallback: use MenuButtonCommands for users who prefer command-based interaction
- Onboarding: show MenuButtonWebApp for new users, switch to MenuButtonCommands for experienced users
