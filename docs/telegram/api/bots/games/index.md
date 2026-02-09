# Games

Send HTML5 games and track high scores.

## Methods

### sendGame

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer | Yes | Target chat (must be user chat, games can't be sent to groups) |
| game_short_name | String | Yes | Short name of the game (as registered with @BotFather) |
| business_connection_id | String | No | Business connection |
| message_thread_id | Integer | No | Forum topic |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |
| message_effect_id | String | No | Message effect |
| reply_parameters | ReplyParameters | No | Reply config |
| reply_markup | InlineKeyboardMarkup | No | Must contain a button with callback_game |

**Returns:** Message

### setGameScore

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | User identifier |
| score | Integer | Yes | New score (non-negative) |
| force | Boolean | No | Set score even if lower than current |
| disable_edit_message | Boolean | No | Don't edit game message with new score |
| chat_id | Integer | Conditional | Required if inline_message_id not specified |
| message_id | Integer | Conditional | Required if inline_message_id not specified |
| inline_message_id | String | Conditional | Required if chat_id not specified |

**Returns:** Message or True

### getGameHighScores

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | Target user |
| chat_id | Integer | Conditional | Required if inline_message_id not specified |
| message_id | Integer | Conditional | Required if inline_message_id not specified |
| inline_message_id | String | Conditional | Required if chat_id not specified |

**Returns:** Array of GameHighScore

## Types

### Game

| Field | Type | Description |
|-------|------|-------------|
| title | String | Title of the game |
| description | String | Description of the game |
| photo | Array of PhotoSize | Photo displayed in game message |
| text | String | Brief description or high scores (optional) |
| text_entities | Array of MessageEntity | Special entities in text (optional) |
| animation | Animation | Animation displayed in game message (optional) |

### CallbackGame

Empty object. Used as placeholder in InlineKeyboardButton.

### GameHighScore

| Field | Type | Description |
|-------|------|-------------|
| position | Integer | Position in high score table |
| user | User | User |
| score | Integer | Score |

## Gotchas

- Game must be created via @BotFather first
- setGameScore: by default only updates if new score is higher. Use force=true to set lower scores.
- setGameScore: returns error if score is exactly the same as current
- Games are HTML5 -- the bot serves the game page via a URL configured in BotFather
- High score table shows surrounding scores for context (not just the requested user)
- callback_game button must be first button in first row of inline keyboard
