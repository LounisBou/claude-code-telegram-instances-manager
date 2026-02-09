# Callback Queries

When a user presses an InlineKeyboardButton with callback_data, the bot receives a CallbackQuery update.

## How It Works

1. User presses inline button with callback_data
2. Bot receives CallbackQuery with: query id, user, message, callback data
3. Bot MUST call answerCallbackQuery to dismiss loading spinner
4. Bot optionally edits the message, shows notification, or takes action

## CallbackQuery

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for this query |
| from | User | User who pressed the button |
| message | MaybeInaccessibleMessage | Message the button was on (optional) |
| inline_message_id | String | Identifier if inline message (optional) |
| chat_instance | String | Global chat identifier |
| data | String | Data from callback_data (optional, 1-64 bytes) |
| game_short_name | String | Short name of Game (optional) |

### MaybeInaccessibleMessage

This is either a Message (accessible, date > 0) or an InaccessibleMessage (date = 0). When the message is inaccessible (older than ~48 hours), only the message_id, chat, and date fields are available -- you cannot read its content or edit it.

## answerCallbackQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| callback_query_id | String | Yes | Unique identifier of the query |
| text | String | No | Notification text (0-200 chars) |
| show_alert | Boolean | No | Show alert dialog instead of toast notification |
| url | String | No | URL to open (games or t.me links) |
| cache_time | Integer | No | Seconds to cache result on client (default 0) |

**Returns:** True

## Gotchas

- ALWAYS call answerCallbackQuery -- even with no text. Without it, the button shows infinite loading spinner.
- callback_data limit: 64 bytes. Use compact encoding.
- message field can be InaccessibleMessage (date=0) if message is older than ~48 hours -- you cannot edit it
- show_alert=true: user must dismiss the popup. show_alert=false: small toast at top of screen.
- cache_time: client won't send duplicate queries for this button during cache period
- Multiple rapid button presses: each generates a separate CallbackQuery
- inline_message_id is set INSTEAD of message when the button is on an inline message
- data field may be absent if the button was a game button (game_short_name is set instead)

## Patterns

- Route by prefix: parse callback_data like "action:id" -- split on ":" -- route to handler
- Acknowledge + edit: answer callback with empty text, then edit message to show result
- Confirmation dialog: show_alert=true with "Are you sure?" text (but user can only dismiss, not confirm/cancel -- use inline buttons for real confirmation)
- Debounce: use cache_time to prevent accidental double-taps
- Stale state detection: always validate that the action is still valid before executing
