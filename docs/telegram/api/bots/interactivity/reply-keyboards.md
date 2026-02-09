# Reply Keyboards

Custom keyboards displayed below the message input field. Tapping a button sends its text as a regular message.

## How It Works

1. Bot sends message with ReplyKeyboardMarkup as reply_markup
2. Keyboard appears below input field
3. User taps button -- button text is sent as a regular message
4. Bot receives this as a normal Message update

## ReplyKeyboardMarkup

| Field | Type | Description |
|-------|------|-------------|
| keyboard | Array of Array of KeyboardButton | Rows of buttons |
| is_persistent | Boolean | Keep keyboard visible (default false) |
| resize_keyboard | Boolean | Fit keyboard to buttons (default false -- takes half screen) |
| one_time_keyboard | Boolean | Hide after one press (default false) |
| input_field_placeholder | String | Placeholder text (1-64 chars) |
| selective | Boolean | Show only to specific users |

## KeyboardButton

| Field | Type | Description |
|-------|------|-------------|
| text | String | Button text (sent as message if no special field set) |
| request_users | KeyboardButtonRequestUsers | Open user picker |
| request_chat | KeyboardButtonRequestChat | Open chat picker |
| request_contact | Boolean | Share user's phone number |
| request_location | Boolean | Share user's location |
| request_poll | KeyboardButtonPollType | Open poll creation |
| web_app | WebAppInfo | Open Web App |

## KeyboardButtonRequestUsers

| Field | Type | Description |
|-------|------|-------------|
| request_id | Integer | Identifier for the request |
| user_is_bot | Boolean | Filter: bots only or non-bots only |
| user_is_premium | Boolean | Filter: premium users only |
| max_quantity | Integer | Max users to select (1-10, default 1) |
| request_name | Boolean | Request user's name |
| request_username | Boolean | Request user's username |
| request_photo | Boolean | Request user's photo |

## KeyboardButtonRequestChat

| Field | Type | Description |
|-------|------|-------------|
| request_id | Integer | Identifier for the request |
| chat_is_channel | Boolean | True for channels, false for groups |
| chat_is_forum | Boolean | Filter: forum supergroups only |
| chat_has_username | Boolean | Filter: chats with username only |
| chat_is_created | Boolean | Filter: chats created by user only |
| user_administrator_rights | ChatAdministratorRights | Required user admin rights |
| bot_administrator_rights | ChatAdministratorRights | Required bot admin rights |
| bot_is_member | Boolean | Filter: bot is member of the chat |
| request_title | Boolean | Request chat title |
| request_username | Boolean | Request chat username |
| request_photo | Boolean | Request chat photo |

## KeyboardButtonPollType

| Field | Type | Description |
|-------|------|-------------|
| type | String | "regular" or "quiz" (omit for any type) |

## Removing the Keyboard

Send ReplyKeyboardRemove as reply_markup:

| Field | Type | Description |
|-------|------|-------------|
| remove_keyboard | Boolean | Must be True |
| selective | Boolean | Remove only for specific users |

## Gotchas

- ALWAYS set resize_keyboard=true unless you want the keyboard to take up half the screen
- Button text is sent as a regular message -- the bot must match it in message handler
- selective: only works when replying to a specific message or when @mentioning users
- Reply keyboards persist until explicitly removed with ReplyKeyboardRemove
- one_time_keyboard: keyboard hides but user can re-open it via button in input area
- In groups: without selective, ALL members see the keyboard
- request_contact/request_location: require user confirmation dialog
- request_users/request_chat: bot receives UsersShared/ChatShared service message

## Patterns

- Quick options: ["Yes", "No"] keyboard for simple choices
- Main menu: persistent keyboard with common actions
- Cancel: always include a "Cancel" button in multi-step flows
- Location sharing: request_location for location-dependent features
- User/chat picker: request_users or request_chat for collaborative features
