# Games

> Send and manage HTML5 games within Telegram chats -- games are created via @BotFather and served as web pages.

## Overview

Telegram Games allow bots to send HTML5 game experiences directly into chats. Games are registered with @BotFather (not created programmatically) and referenced by `game_short_name`. The bot sends a game message, users tap to play in a webview, and scores are tracked via `set_game_score`. High score tables are built into the game message.

## Quick Usage

```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

async def send_game(update: Update, context: ContextTypes.DefaultType):
    await context.bot.send_game(
        chat_id=update.effective_chat.id,
        game_short_name="my_game",
    )

async def game_callback(update: Update, context: ContextTypes.DefaultType):
    query = update.callback_query
    await query.answer(url="https://example.com/my_game")

app = Application.builder().token("TOKEN").build()
app.add_handler(CommandHandler("game", send_game))
app.add_handler(CallbackQueryHandler(game_callback, pattern="my_game"))
app.run_polling()
```

## Key Classes

### `telegram.Game`

Represents a game. Returned in `message.game` when a game message is received.

| Attribute | Type | Description |
|---|---|---|
| `title` | `str` | Title of the game. |
| `description` | `str` | Description of the game. |
| `photo` | `list[PhotoSize]` | Photo displayed in the game message. |
| `text` | `str \| None` | Brief description or high scores embedded in the game message. |
| `text_entities` | `list[MessageEntity] \| None` | Entities in `text` (bold, links, etc.). |
| `animation` | `Animation \| None` | Animation (GIF/MPEG4) shown in the game message. |

---

### `telegram.GameHighScore`

One entry in a high score table.

| Attribute | Type | Description |
|---|---|---|
| `position` | `int` | Position in the score table (1-based). |
| `user` | `User` | The user. |
| `score` | `int` | The score. |

---

### `telegram.CallbackGame`

Empty placeholder object -- used as `callback_game` parameter on `InlineKeyboardButton` to trigger the game launch. The actual game short name is taken from the game message.

```python
InlineKeyboardButton("Play!", callback_game=CallbackGame())
```

---

### Bot Methods

| Method | Returns | Description |
|---|---|---|
| `send_game(chat_id, game_short_name, disable_notification=None, protect_content=None, reply_parameters=None, reply_markup=None, message_thread_id=None, message_effect_id=None, ...)` | `Message` | Send a game. `reply_markup` must be an `InlineKeyboardMarkup` (first button in first row can be the play button). |
| `set_game_score(user_id, score, chat_id=None, message_id=None, inline_message_id=None, force=None, disable_edit_message=None, ...)` | `Message \| bool` | Set a user's score. By default, only updates if new score is higher. Set `force=True` to overwrite. Returns `Message` for regular messages, `True` for inline messages. |
| `get_game_high_scores(user_id, chat_id=None, message_id=None, inline_message_id=None, ...)` | `list[GameHighScore]` | Get high score table. Returns scores of `user_id` and surrounding players. |

## Common Patterns

### Send game with play button

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, CallbackGame

async def send_game(update: Update, context: ContextTypes.DefaultType):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Play!", callback_game=CallbackGame())]
    ])
    await context.bot.send_game(
        chat_id=update.effective_chat.id,
        game_short_name="my_game",
        reply_markup=keyboard,
    )
```

### Set and retrieve scores

```python
# Set a score (from your game's web page callback)
await context.bot.set_game_score(
    user_id=user_id,
    score=1500,
    chat_id=chat_id,
    message_id=message_id,
)

# Get high scores around a user
scores = await context.bot.get_game_high_scores(
    user_id=user_id,
    chat_id=chat_id,
    message_id=message_id,
)
for hs in scores:
    print(f"#{hs.position}: {hs.user.first_name} - {hs.score}")
```

### Inline game result

```python
from telegram import InlineQueryResultGame

async def inline_query(update: Update, context: ContextTypes.DefaultType):
    results = [
        InlineQueryResultGame(id="1", game_short_name="my_game")
    ]
    await update.inline_query.answer(results)
```

## Related

- [../bot.md](../bot.md) -- `Bot.send_game()`, `Bot.set_game_score()`, `Bot.get_game_high_scores()`
- [../handlers/callback-query-handler.md](../handlers/callback-query-handler.md) -- handling the play button callback
- [inline-mode.md](inline-mode.md) -- `InlineQueryResultGame` for sending games via inline mode
- [../types/keyboards.md](../types/keyboards.md) -- `InlineKeyboardButton` with `callback_game`
- [Telegram API — Games](../../api/bots/games/index.md) -- game mechanics and scoring in the API specification
