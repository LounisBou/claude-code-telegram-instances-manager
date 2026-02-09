# Web Apps

> Web Apps (Mini Apps) -- embed interactive web interfaces directly inside Telegram chats via an iframe-like webview.

## Overview

Telegram Web Apps allow bots to open full web pages within the Telegram client. They can be launched from keyboard buttons, inline keyboard buttons, the bot menu button, or inline mode. The web page communicates with Telegram via a JavaScript API, and can send data back to the bot. Web Apps are specified by a URL wrapped in `WebAppInfo`.

## Quick Usage

```python
from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

async def start(update: Update, context: ContextTypes.DefaultType):
    keyboard = ReplyKeyboardMarkup([
        [KeyboardButton("Open App", web_app=WebAppInfo(url="https://example.com/app"))]
    ], resize_keyboard=True)
    await update.message.reply_text("Tap the button to open the app:", reply_markup=keyboard)

async def web_app_data(update: Update, context: ContextTypes.DefaultType):
    data = update.message.web_app_data.data
    await update.message.reply_text(f"Received: {data}")

app = Application.builder().token("TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
app.run_polling()
```

## Key Classes

### `telegram.WebAppInfo`

Describes a Web App URL.

```python
WebAppInfo(url: str)
```

| Attribute | Type | Description |
|---|---|---|
| `url` | `str` | HTTPS URL of the Web App to open. Must use HTTPS. |

---

### `telegram.WebAppData`

Data sent back from the Web App to the bot. Available on `message.web_app_data`.

| Attribute | Type | Description |
|---|---|---|
| `data` | `str` | The data (up to 4096 bytes). |
| `button_text` | `str` | Text of the `KeyboardButton` that launched the Web App. |

---

### `telegram.SentWebAppMessage`

Returned by `answer_web_app_query`.

| Attribute | Type | Description |
|---|---|---|
| `inline_message_id` | `str \| None` | Identifier of the sent inline message (can be used to edit it). |

---

### Usage Contexts

Web Apps can be launched from four places:

#### 1. Reply Keyboard Button

```python
from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

keyboard = ReplyKeyboardMarkup([
    [KeyboardButton("Open", web_app=WebAppInfo(url="https://example.com/app"))]
], resize_keyboard=True)
```

The Web App opens in a compact view. When the user submits data via `Telegram.WebApp.sendData()`, it arrives as `update.message.web_app_data`.

#### 2. Inline Keyboard Button

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Open", web_app=WebAppInfo(url="https://example.com/app"))]
])
```

Opens the Web App. Data does **not** arrive via `web_app_data` -- use other mechanisms (e.g., your own backend API or `answerWebAppQuery` from within the Web App).

#### 3. Bot Menu Button

```python
from telegram import MenuButtonWebApp, WebAppInfo

await bot.set_chat_menu_button(
    chat_id=chat_id,
    menu_button=MenuButtonWebApp(
        text="Menu",
        web_app=WebAppInfo(url="https://example.com/app"),
    ),
)
```

Replaces the default menu button (bottom-left) in the bot's chat.

#### 4. Inline Mode (via InlineQueryResultsButton)

```python
from telegram import InlineQueryResultsButton, WebAppInfo

button = InlineQueryResultsButton(
    text="Open App",
    web_app=WebAppInfo(url="https://example.com/inline-app"),
)
await update.inline_query.answer(results=[], button=button)
```

---

### Bot Methods

| Method | Returns | Description |
|---|---|---|
| `set_chat_menu_button(chat_id=None, menu_button=None)` | `bool` | Set the bot's menu button for a specific chat or the default. `menu_button` can be `MenuButtonWebApp`, `MenuButtonCommands`, or `MenuButtonDefault`. |
| `get_chat_menu_button(chat_id=None)` | `MenuButton` | Get the current menu button configuration. |
| `answer_web_app_query(web_app_query_id, result)` | `SentWebAppMessage` | Send an inline result on behalf of a Web App. `result` is an `InlineQueryResult`. Used when Web App was opened from inline mode. |

---

### Menu Button Types

| Class | Params | Description |
|---|---|---|
| `MenuButtonWebApp` | `text: str, web_app: WebAppInfo` | Menu button that opens a Web App. |
| `MenuButtonCommands` | (none) | Default menu button showing the command list. |
| `MenuButtonDefault` | (none) | No custom menu button (Telegram decides). |

## Common Patterns

### Reply keyboard with Web App data handling

```python
from telegram import KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

async def start(update: Update, context: ContextTypes.DefaultType):
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("Pick Color", web_app=WebAppInfo(url="https://example.com/color-picker"))]],
        resize_keyboard=True,
    )
    await update.message.reply_text("Choose a color:", reply_markup=keyboard)

async def handle_webapp_data(update: Update, context: ContextTypes.DefaultType):
    import json
    data = json.loads(update.message.web_app_data.data)
    color = data.get("color")
    await update.message.reply_text(f"You picked: {color}")

app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))
```

### Set menu button globally vs per-chat

```python
from telegram import MenuButtonWebApp, MenuButtonDefault, WebAppInfo

# Set for a specific chat
await context.bot.set_chat_menu_button(
    chat_id=12345,
    menu_button=MenuButtonWebApp(text="Dashboard", web_app=WebAppInfo(url="https://example.com/dashboard")),
)

# Set global default
await context.bot.set_chat_menu_button(
    menu_button=MenuButtonWebApp(text="App", web_app=WebAppInfo(url="https://example.com/app")),
)

# Reset to default
await context.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
```

### Answer a Web App inline query

```python
from telegram import InlineQueryResultArticle, InputTextMessageContent

async def answer_webapp(web_app_query_id: str, text: str):
    result = InlineQueryResultArticle(
        id="1",
        title="Result",
        input_message_content=InputTextMessageContent(text),
    )
    sent = await bot.answer_web_app_query(
        web_app_query_id=web_app_query_id,
        result=result,
    )
    # sent.inline_message_id can be used to edit the message later
```

## Related

- [../bot.md](../bot.md) -- `Bot.set_chat_menu_button()`, `Bot.answer_web_app_query()`
- [../types/keyboards.md](../types/keyboards.md) -- `KeyboardButton`, `InlineKeyboardButton` with `web_app` param
- [../handlers/message-handler.md](../handlers/message-handler.md) -- `MessageHandler` with `filters.StatusUpdate.WEB_APP_DATA`
- [../handlers/filters.md](../handlers/filters.md) -- `filters.StatusUpdate.WEB_APP_DATA`
- [inline-mode.md](inline-mode.md) -- `InlineQueryResultsButton` with `web_app` for inline Web Apps
- [../types/index.md](../types/index.md) -- `WebAppInfo` in the type hierarchy
- [Telegram API — Web Apps](../../api/bots/web-apps/index.md) -- Web Apps (Mini Apps) in the API specification
