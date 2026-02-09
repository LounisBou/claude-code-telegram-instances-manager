# Reply Keyboards

Custom keyboards displayed below the message input field. The user taps a button to send its text as a message.

## Types

### ReplyKeyboardMarkup

| Field | Type | Description |
|-------|------|-------------|
| keyboard | Array of Array of KeyboardButton | Array of button rows |
| is_persistent | Boolean | Show keyboard permanently (optional, default false) |
| resize_keyboard | Boolean | Resize keyboard vertically to fit buttons (optional, default false) |
| one_time_keyboard | Boolean | Hide after button press (optional, default false) |
| input_field_placeholder | String | Placeholder text in input field when keyboard active (optional, 1-64 chars) |
| selective | Boolean | Show only to specific users in groups (optional) |

### KeyboardButton

| Field | Type | Description |
|-------|------|-------------|
| text | String | Button text. If no optional fields set, this text is sent as message when pressed. |
| request_users | KeyboardButtonRequestUsers | Pressing opens user picker (optional) |
| request_chat | KeyboardButtonRequestChat | Pressing opens chat picker (optional) |
| request_contact | Boolean | Send user's phone number (optional) |
| request_location | Boolean | Send user's current location (optional) |
| request_poll | KeyboardButtonPollType | Pressing opens poll creation dialog (optional) |
| web_app | WebAppInfo | Opens specified Web App (optional) |

### KeyboardButtonRequestUsers

| Field | Type | Description |
|-------|------|-------------|
| request_id | Integer | Identifier for this request |
| user_is_bot | Boolean | Filter: only bots or non-bots (optional) |
| user_is_premium | Boolean | Filter: only premium users (optional) |
| max_quantity | Integer | Max users to select (1-10, default 1) |
| request_name | Boolean | Request user's name (optional) |
| request_username | Boolean | Request user's username (optional) |
| request_photo | Boolean | Request user's photo (optional) |

### KeyboardButtonRequestChat

| Field | Type | Description |
|-------|------|-------------|
| request_id | Integer | Identifier for this request |
| chat_is_channel | Boolean | True for channels, false for groups/supergroups |
| chat_is_forum | Boolean | Filter: only forums (optional) |
| chat_has_username | Boolean | Filter: only chats with username (optional) |
| chat_is_created | Boolean | Filter: only chats created by user (optional) |
| user_administrator_rights | ChatAdministratorRights | Required admin rights for user (optional) |
| bot_administrator_rights | ChatAdministratorRights | Required admin rights for bot (optional) |
| bot_is_member | Boolean | Bot must be member of selected chat (optional) |
| request_title | Boolean | Request chat title (optional) |
| request_username | Boolean | Request chat username (optional) |
| request_photo | Boolean | Request chat photo (optional) |

### KeyboardButtonPollType

| Field | Type | Description |
|-------|------|-------------|
| type | String | "quiz" or "regular" to restrict type (optional) |

### ReplyKeyboardRemove

| Field | Type | Description |
|-------|------|-------------|
| remove_keyboard | Boolean | Must be True |
| selective | Boolean | Remove only for specific users (optional) |

### ForceReply

| Field | Type | Description |
|-------|------|-------------|
| force_reply | Boolean | Must be True |
| input_field_placeholder | String | Placeholder text (optional, 1-64 chars) |
| selective | Boolean | Force reply only for specific users (optional) |

## Gotchas

- **selective**: works for replies to a message or @mentioned users in groups
- **resize_keyboard=true**: almost always what you want, otherwise keyboard takes half the screen
- **one_time_keyboard**: keyboard disappears but can be re-opened via button in input field
- **request_users/request_chat**: results delivered via UsersShared/ChatShared service messages
- **ForceReply**: useful for creating step-by-step interfaces in groups (auto-quotes the bot's message)
