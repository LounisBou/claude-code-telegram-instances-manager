# Keyboard Types

> Inline keyboards (buttons attached to messages) and reply keyboards (custom keyboard below the input field).

## Overview

Telegram supports two keyboard systems: **inline keyboards** (buttons embedded in messages, triggering `CallbackQuery` or opening URLs) and **reply keyboards** (custom keyboard replacing the device keyboard, sending text when pressed). Both are passed as `reply_markup` to send/edit methods.

## Quick Usage

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Click me", callback_data="action")]
])
await update.message.reply_text("Choose:", reply_markup=keyboard)
```

## Key Classes

### `InlineKeyboardMarkup`

Inline keyboard attached to a message. Buttons trigger callback queries, open URLs, or switch inline mode.

```python
InlineKeyboardMarkup(
    inline_keyboard: list[list[InlineKeyboardButton]]
)
```

| Attribute | Type | Description |
|---|---|---|
| `inline_keyboard` | `tuple[tuple[InlineKeyboardButton, ...], ...]` | 2D structure: outer list = rows, inner list = buttons per row. |

---

### `InlineKeyboardButton`

A single button in an inline keyboard.

```python
InlineKeyboardButton(
    text: str,                                  # Button label (required)
    callback_data: str = None,                  # Data sent to bot on press (1-64 bytes)
    url: str = None,                            # URL to open
    switch_inline_query: str = None,            # Switch to inline mode in any chat
    switch_inline_query_current_chat: str = None,  # Switch to inline mode in current chat
    web_app: WebAppInfo = None,                 # Open a Web App
    login_url: LoginUrl = None,                 # Login URL for seamless auth
    pay: bool = None,                           # Payment button (must be first button)
    switch_inline_query_chosen_chat: SwitchInlineQueryChosenChat = None,
    copy_text: CopyTextButton = None,           # Copy text to clipboard on press
)
```

Exactly one optional parameter must be set alongside `text`. The most common are `callback_data` (for bot interactions) and `url` (for links).

---

### `ReplyKeyboardMarkup`

Custom keyboard displayed below the chat input field. Buttons send their `text` as a message when pressed.

```python
ReplyKeyboardMarkup(
    keyboard: list[list[KeyboardButton | str]],
    resize_keyboard: bool = None,               # Fit keyboard to button sizes (recommended True)
    one_time_keyboard: bool = None,             # Hide after one button press
    selective: bool = None,                     # Show only to specific users (in groups)
    input_field_placeholder: str = None,        # Placeholder text in input field (1-64 chars)
    is_persistent: bool = None,                 # Keep keyboard visible even after user sends a message
)
```

| Attribute | Type | Description |
|---|---|---|
| `keyboard` | `tuple[tuple[KeyboardButton, ...], ...]` | 2D structure of buttons. Strings are auto-wrapped as `KeyboardButton(text=string)`. |

---

### `KeyboardButton`

A single button in a reply keyboard.

```python
KeyboardButton(
    text: str,                          # Button text, sent as message when pressed (required)
    request_contact: bool = None,       # Send user's phone contact
    request_location: bool = None,      # Send user's current location
    request_poll: KeyboardButtonPollType = None,  # Create and send a poll
    web_app: WebAppInfo = None,         # Open a Web App
    request_users: KeyboardButtonRequestUsers = None,  # Request user selection
    request_chat: KeyboardButtonRequestChat = None,    # Request chat selection
)
```

---

### `ReplyKeyboardRemove`

Removes a previously sent reply keyboard.

```python
ReplyKeyboardRemove(
    selective: bool = None     # Remove only for specific users
)
```

The `remove_keyboard` attribute is always `True`.

---

### `ForceReply`

Forces the user's client to display a reply interface (as if they tapped the message and hit "Reply").

```python
ForceReply(
    selective: bool = None,                 # Force reply only for specific users
    input_field_placeholder: str = None,    # Placeholder text (1-64 chars)
)
```

The `force_reply` attribute is always `True`.

## Common Patterns

### Build an inline keyboard with rows

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

keyboard = InlineKeyboardMarkup([
    # Row 1: two buttons side by side
    [InlineKeyboardButton("Option A", callback_data="a"),
     InlineKeyboardButton("Option B", callback_data="b")],
    # Row 2: one wide button
    [InlineKeyboardButton("Cancel", callback_data="cancel")],
    # Row 3: URL button
    [InlineKeyboardButton("Visit Site", url="https://example.com")],
])

await update.message.reply_text("Choose:", reply_markup=keyboard)
```

### Handle inline button presses with CallbackQueryHandler

```python
from telegram.ext import CallbackQueryHandler

async def button_callback(update: Update, context: ContextTypes.DefaultType):
    query = update.callback_query
    await query.answer()  # always acknowledge first

    if query.data == "a":
        await query.edit_message_text("You chose A")
    elif query.data == "cancel":
        await query.edit_message_text("Cancelled.")

app.add_handler(CallbackQueryHandler(button_callback))
```

### Reply keyboard with resize and one-time

```python
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove

keyboard = ReplyKeyboardMarkup(
    [["Yes", "No"], ["Maybe"]],
    resize_keyboard=True,
    one_time_keyboard=True,
)
await update.message.reply_text("Do you agree?", reply_markup=keyboard)

# Later, remove the keyboard
await update.message.reply_text("Thanks!", reply_markup=ReplyKeyboardRemove())
```

## Related

- [index.md](index.md) -- types overview and routing table
- [messages.md](messages.md) -- Message.reply_markup and reply shortcut methods
- [other-types.md](other-types.md) -- CallbackQuery (handles inline button presses), WebAppInfo, LoginUrl, CopyTextButton, SwitchInlineQueryChosenChat
- [../bot.md](../bot.md) -- Bot.send_message() reply_markup parameter
- [../handlers/callback-query-handler.md](../handlers/callback-query-handler.md) -- handler for inline button callbacks
- [Telegram API — Keyboards](../../api/bots/keyboards/index.md) -- keyboard types and behavior in the API specification
