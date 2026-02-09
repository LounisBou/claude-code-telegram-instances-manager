# Inline Keyboards

Buttons attached directly to messages. Unlike reply keyboards, they don't send text -- they trigger callbacks, open URLs, switch to inline mode, etc.

## How It Works

1. Bot sends message with InlineKeyboardMarkup as reply_markup
2. User taps a button
3. Depending on button type: bot receives CallbackQuery, URL opens, inline mode activates, etc.

## InlineKeyboardMarkup

| Field | Type | Description |
|-------|------|-------------|
| inline_keyboard | Array of Array of InlineKeyboardButton | Rows of buttons |

## InlineKeyboardButton

Exactly ONE optional field must be set per button.

| Field | Type | Description |
|-------|------|-------------|
| text | String | Button label (required) |
| url | String | Opens URL when pressed |
| callback_data | String | Data sent in CallbackQuery (1-64 bytes) |
| web_app | WebAppInfo | Opens Web App |
| login_url | LoginUrl | Telegram Login button |
| switch_inline_query | String | Opens inline query in chat picker |
| switch_inline_query_current_chat | String | Opens inline query in current chat |
| switch_inline_query_chosen_chat | SwitchInlineQueryChosenChat | Opens inline query with chat filter |
| callback_game | CallbackGame | Game launch button |
| pay | Boolean | Payment button (must be first in first row) |
| copy_text | CopyTextButton | Copies text to clipboard |

## Button Types Explained

- **callback_data**: Most common. Sends data to bot, bot can edit message in response.
- **url**: Opens link in browser. Supports `tg://` protocol for Telegram-specific links.
- **web_app**: Opens mini-app inside Telegram.
- **switch_inline_query**: Prompts user to pick a chat, then pre-fills `@botname` + query text.
- **switch_inline_query_current_chat**: Inserts `@botname` + query text directly in current chat.
- **switch_inline_query_chosen_chat**: Opens inline query with filter for chat type selection.
- **login_url**: Used for Telegram Login on websites. Opens authorization confirmation dialog.
- **pay**: Creates a Pay button. MUST be first button in first row.
- **copy_text**: Copies specified text to clipboard when pressed (1-256 chars).
- **callback_game**: Launches a game. Must be first button in first row.

## SwitchInlineQueryChosenChat

| Field | Type | Description |
|-------|------|-------------|
| query | String | Default inline query text |
| allow_user_chats | Boolean | Allow private chats with users |
| allow_bot_chats | Boolean | Allow private chats with bots |
| allow_group_chats | Boolean | Allow group and supergroup chats |
| allow_channel_chats | Boolean | Allow channel chats |

## CopyTextButton

| Field | Type | Description |
|-------|------|-------------|
| text | String | Text to copy to clipboard (1-256 chars) |

## LoginUrl

| Field | Type | Description |
|-------|------|-------------|
| url | String | HTTPS URL for Telegram Login |
| forward_text | String | Button text for forwarded messages |
| bot_username | String | Username of the bot for authorization |
| request_write_access | Boolean | Request permission to message the user |

## Gotchas

- callback_data: MAX 64 BYTES. Use short codes like "p:2" not "page_number:2"
- Only ONE optional field per button -- cannot combine url + callback_data
- pay button must be the FIRST button in the FIRST row
- Buttons render in rows -- each inner array is one row
- Empty text ("") is not allowed for button text
- callback_game must be the first button in the first row

## Patterns

- Action buttons: callback_data with action prefix "del:123", "like:456"
- URL + fallback: url button for external links, callback_data for in-app actions
- Share: switch_inline_query to let users share bot content to other chats
- Clipboard: copy_text for shareable codes, referral links, etc.
