# CallbackQueryHandler

> Handles inline keyboard button presses by matching `CallbackQuery.data` against patterns.

## Overview

`CallbackQueryHandler` processes presses on `InlineKeyboardButton` buttons that carry `callback_data`. It can match all callback queries, or filter by string/regex pattern, callable, or type. Regex matches are accessible via `context.matches`. Every callback **must** call `await query.answer()` — Telegram requires acknowledgement within ~30 seconds or the button shows a loading spinner.

## Quick Usage

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler

async def button_pressed(update, context):
    query = update.callback_query
    await query.answer()  # REQUIRED — acknowledge the press
    await query.edit_message_text(f"You chose: {query.data}")

app.add_handler(CallbackQueryHandler(button_pressed))
```

## Key Classes

### `CallbackQueryHandler(callback, pattern=None, game_pattern=None, block=True)`

**Constructor Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `callback` | `async (Update, Context) -> None` | required | Async function called on match. |
| `pattern` | `str \| re.Pattern \| callable \| type \| None` | `None` | Tested against `CallbackQuery.data`. Strings/regex use `re.match()`. Callables receive `data` and return truthy/falsy. |
| `game_pattern` | `str \| re.Pattern \| None` | `None` | Tested against `CallbackQuery.game_short_name` via `re.match()`. |
| `block` | `bool` | `True` | If `True`, blocks update processing until callback completes. |

If neither `pattern` nor `game_pattern` is set, the handler matches **all** callback queries.

**Key Attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `pattern` | `str \| re.Pattern \| callable \| type` | The active data pattern. |
| `game_pattern` | `str \| re.Pattern` | The active game pattern. |
| `callback` | `callable` | The registered callback function. |
| `block` | `bool` | Blocking behavior. |

**Key Methods:**

| Method | Description |
|--------|-------------|
| `check_update(update)` | Returns `None` if no match, or the match result (re.Match or callable return). |
| `collect_additional_context(context, update, application, check_result)` | Populates `context.matches` as a single-element list containing the `re.Match` object. |

## Common Patterns

### Send keyboard, then handle presses

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def show_menu(update, context):
    keyboard = [
        [InlineKeyboardButton("Option A", callback_data="choice_a"),
         InlineKeyboardButton("Option B", callback_data="choice_b")],
    ]
    await update.message.reply_text(
        "Choose:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_choice(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Selected: {query.data}")

app.add_handler(CommandHandler("menu", show_menu))
app.add_handler(CallbackQueryHandler(handle_choice, pattern=r"^choice_"))
```

### Regex pattern with capture groups

```python
import re

async def handle_action(update, context):
    query = update.callback_query
    await query.answer()
    match = context.matches[0]  # re.Match object
    action = match.group("action")
    item_id = match.group("id")
    await query.edit_message_text(f"Action: {action}, ID: {item_id}")

app.add_handler(CallbackQueryHandler(
    handle_action,
    pattern=re.compile(r"^(?P<action>delete|edit)_(?P<id>\d+)$")
))
```

### Answer with alert or toast

```python
async def handle_query(update, context):
    query = update.callback_query
    # Toast notification (brief popup):
    await query.answer(text="Saved!")
    # Or modal alert (user must dismiss):
    # await query.answer(text="Are you sure?", show_alert=True)
```

## Important Notes

- `query.answer()` must be called in every callback. Failure to answer causes a persistent loading indicator on the button.
- `pattern` uses `re.match()` (matches from start of string), not `re.search()`. Use `^` and `$` for exactness.
- `callback_data` is limited to 1-64 bytes by Telegram. For larger payloads, store data in `context.user_data` or a database and pass only an ID in the callback data.
- `query.edit_message_text()` / `query.edit_message_reply_markup()` modify the message the button was on.
- `query.message` is the message containing the button. `query.from_user` is who pressed it.

## Related

- [command-handler.md](command-handler.md) — often used to send the initial keyboard
- [conversation-handler.md](conversation-handler.md) — use CallbackQueryHandler inside conversation states
- [inline-query-handler.md](inline-query-handler.md) — for inline mode (different from inline keyboards)
- [index.md](index.md) — handler overview and routing
- [Telegram API — Interactivity](../../api/bots/interactivity/index.md) — callback queries and interactive patterns in the API specification
