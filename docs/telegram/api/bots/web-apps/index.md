# Web Apps

Launch mini applications within Telegram using WebApp buttons and interactions.

## Methods

### answerWebAppQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| web_app_query_id | String | Yes | Unique identifier for the query from the Web App |
| result | InlineQueryResult | Yes | Result describing the message to send |

**Returns:** SentWebAppMessage

## Types

### WebAppInfo

| Field | Type | Description |
|-------|------|-------------|
| url | String | HTTPS URL of the Web App to open |

### WebAppData

| Field | Type | Description |
|-------|------|-------------|
| data | String | Data sent from the Web App (WARNING: validate -- client can send arbitrary data) |
| button_text | String | Text of the keyboard button that opened the Web App |

### SentWebAppMessage

| Field | Type | Description |
|-------|------|-------------|
| inline_message_id | String | Identifier of the sent inline message (optional) |

## Ways to Launch Web Apps

1. **Keyboard button**: KeyboardButton with web_app field -- opens Web App, sends WebAppData back
2. **Inline button**: InlineKeyboardButton with web_app field -- opens Web App
3. **Menu button**: MenuButtonWebApp -- replaces bot menu with Web App button
4. **Inline mode**: InlineQueryResultsButton with web_app field -- opens Web App from inline results
5. **Direct link**: t.me/botusername/appname -- opens the bot's main Web App

## Gotchas

- Web App URL must be HTTPS
- WebAppData.data: NEVER trust this field -- validate and sanitize, as malicious clients can send arbitrary data
- answerWebAppQuery: used when Web App was opened from an inline query button
- Web Apps have access to user's theme colors, viewport size, and can send data back to the bot
- Main Web App: configured via @BotFather, accessible via t.me/botusername
