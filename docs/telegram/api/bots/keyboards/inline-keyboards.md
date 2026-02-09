# Inline Keyboards

Buttons attached directly to messages. Unlike reply keyboards, pressing these does NOT send a message -- they trigger callbacks, open URLs, etc.

## Types

### InlineKeyboardMarkup

| Field | Type | Description |
|-------|------|-------------|
| inline_keyboard | Array of Array of InlineKeyboardButton | Array of button rows |

### InlineKeyboardButton

Exactly one of the optional fields must be set.

| Field | Type | Description |
|-------|------|-------------|
| text | String | Button label text |
| url | String | HTTP/HTTPS/tg:// URL to open (optional) |
| callback_data | String | Data sent to bot in CallbackQuery (1-64 bytes) (optional) |
| web_app | WebAppInfo | Opens a Web App (optional) |
| login_url | LoginUrl | Auto-login URL for Telegram Login (optional) |
| switch_inline_query | String | Prompts user to select chat and inserts bot's username + this string in input field (optional) |
| switch_inline_query_current_chat | String | Inserts bot's username + this string in current chat's input field (optional) |
| switch_inline_query_chosen_chat | SwitchInlineQueryChosenChat | Prompts user to select chat with filters (optional) |
| callback_game | CallbackGame | Description of game to launch (optional) |
| pay | Boolean | True for Pay button (must be first button in first row) (optional) |
| copy_text | CopyTextButton | Copies specified text to clipboard (optional) |

### LoginUrl

| Field | Type | Description |
|-------|------|-------------|
| url | String | HTTPS URL for Telegram Login |
| forward_text | String | New text for the button when forwarded (optional) |
| bot_username | String | Username of bot for login (optional) |
| request_write_access | Boolean | Request permission to message user (optional) |

### SwitchInlineQueryChosenChat

| Field | Type | Description |
|-------|------|-------------|
| query | String | Default inline query text (optional) |
| allow_user_chats | Boolean | Allow selecting private chats with users (optional) |
| allow_bot_chats | Boolean | Allow selecting private chats with bots (optional) |
| allow_group_chats | Boolean | Allow selecting group and supergroup chats (optional) |
| allow_channel_chats | Boolean | Allow selecting channel chats (optional) |

### CopyTextButton

| Field | Type | Description |
|-------|------|-------------|
| text | String | Text to copy to clipboard (1-256 chars) |

### CallbackQuery

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for this query |
| from | User | User who pressed the button |
| message | MaybeInaccessibleMessage | Message with the callback button (optional) |
| inline_message_id | String | Identifier of the inline message (optional) |
| chat_instance | String | Global identifier for the chat (optional) |
| data | String | Data from callback_data field (optional) |
| game_short_name | String | Short name of Game to return (optional) |

## Methods

### answerCallbackQuery

Must be called after receiving a CallbackQuery. Stops the loading spinner on the button.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| callback_query_id | String | Yes | Unique identifier of the query to answer |
| text | String | No | Notification text (0-200 chars). Shown as toast or alert. |
| show_alert | Boolean | No | If true, shows alert dialog instead of toast |
| url | String | No | URL to open (for game buttons or t.me links) |
| cache_time | Integer | No | Max seconds to cache the result on client (default 0) |

**Returns:** True

## Gotchas

- **callback_data max**: 64 bytes -- use short codes, not full data
- **ALWAYS call answerCallbackQuery**, even with no text, to dismiss the loading spinner
- **CallbackQuery.message** can be InaccessibleMessage if the message is too old (>48h) -- check date field
- **pay button**: must be FIRST button in FIRST row
- **Only one optional field** per InlineKeyboardButton -- you cannot combine url + callback_data

## Patterns

- **Navigation**: use callback_data with prefixes like "page:2", "menu:settings" and route in handler
- **Confirmation**: send message with "Confirm" / "Cancel" inline buttons, handle via callback_data
- **Toggle**: edit the message and keyboard to reflect new state after callback
