# Web Apps (Interactive)

Launch full interactive mini-applications within Telegram, capable of rich UI that goes beyond buttons and text.

## Launch Methods

| Method | Where it Appears | How to Set Up |
|--------|-----------------|---------------|
| Keyboard button | Reply keyboard | KeyboardButton with web_app field |
| Inline button | Attached to message | InlineKeyboardButton with web_app field |
| Menu button | Bot menu (hamburger) | setChatMenuButton with MenuButtonWebApp |
| Inline results button | Above inline results | InlineQueryResultsButton with web_app field |
| Direct link | t.me/botusername/appname | Configure main Web App in @BotFather |
| Attachment menu | Chat attachment menu | Configure via @BotFather |

## WebAppInfo

| Field | Type | Description |
|-------|------|-------------|
| url | String | HTTPS URL of the Web App |

## Data Exchange

### Keyboard Button Launch

- Web App sends data back via `Telegram.WebApp.sendData(data)`
- Bot receives a Message update containing a WebAppData service message
- This is a one-shot data transfer -- Web App closes after sendData

### Inline Button Launch

- No automatic data channel to the bot
- Web App communicates with its own backend via standard HTTP requests
- Or closes silently without sending data

### Inline Mode Launch

- Use answerWebAppQuery to send a result back to the chat from the Web App
- Web App calls its backend, backend calls answerWebAppQuery

## answerWebAppQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| web_app_query_id | String | Yes | Identifier from the Web App |
| result | InlineQueryResult | Yes | Result to send to the chat |

**Returns:** SentWebAppMessage

## SentWebAppMessage

| Field | Type | Description |
|-------|------|-------------|
| inline_message_id | String | Identifier of the sent inline message (optional) |

## WebAppData

| Field | Type | Description |
|-------|------|-------------|
| data | String | Data from the Web App (up to 4096 bytes) |
| button_text | String | Text of the keyboard button that opened the app |

## Client-Side API (Telegram.WebApp)

Key properties and methods available in the Web App JavaScript context:

- **initData**: raw init data string (validate on server with bot token)
- **initDataUnsafe**: parsed init data (user, chat, etc.) -- DO NOT trust without server validation
- **colorScheme**: "light" or "dark"
- **themeParams**: theme colors matching user's Telegram theme
- **viewportHeight** / **viewportStableHeight**: available viewport dimensions
- **isExpanded**: whether app is expanded to full height
- **sendData(data)**: send data to bot and close (keyboard button launch only)
- **ready()**: signal that the app is ready to be displayed
- **expand()**: expand to full height
- **close()**: close the Web App
- **MainButton**: configurable main button at bottom of Web App
- **BackButton**: back button in Web App header
- **HapticFeedback**: haptic feedback methods
- **showPopup(params)**: show native popup dialog
- **showAlert(message)**: show native alert
- **showConfirm(message)**: show native confirm dialog

## Gotchas

- URL must be HTTPS
- NEVER trust WebAppData.data -- treat it as untrusted user input, validate on server
- Web Apps have access to user theme colors, viewport size, haptic feedback
- Web App can expand to full screen via expand()
- Web Apps can interact with the bot's backend via standard HTTP requests
- Telegram.WebApp.initData contains user info -- validate hash with bot token on your server
- sendData() only works when the Web App was opened from a keyboard button
- Data limit for sendData: 4096 bytes
- Web App must call ready() to signal it has loaded; otherwise Telegram shows loading indicator

## Patterns

- Complex forms: Web App for rich input (date pickers, maps, file upload) -- send result via sendData
- Dashboard: persistent Web App via menu button for analytics/settings
- E-commerce: product catalog as Web App, checkout via Telegram Payments
- Games: HTML5 games with rich graphics beyond what inline games support
- Authentication: use initData for seamless user authentication on your backend
