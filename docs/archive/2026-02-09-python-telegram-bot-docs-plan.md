# python-telegram-bot Documentation — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create full documentation of the `python-telegram-bot` package for Claude Code reference, using progressive disclosure.

**Architecture:** Index → Topic → Detail file structure in `docs/telegram/python-telegram-bot/`. Each file follows a consistent template: Overview → Quick Usage → Key Classes (constructor + methods + attributes) → Common Patterns → Related links. Cross-references to existing `docs/telegram/api/` for Telegram API concepts.

**Tech Stack:** Markdown documentation. Source: https://docs.python-telegram-bot.org/en/stable/

---

## Task 1: Create directory structure and top-level index

**Files:**
- Create: `docs/telegram/python-telegram-bot/index.md`
- Create: `docs/telegram/python-telegram-bot/handlers/` (directory)
- Create: `docs/telegram/python-telegram-bot/types/` (directory)
- Create: `docs/telegram/python-telegram-bot/features/` (directory)

**Step 1: Create directories**

```bash
mkdir -p docs/telegram/python-telegram-bot/handlers
mkdir -p docs/telegram/python-telegram-bot/types
mkdir -p docs/telegram/python-telegram-bot/features
```

**Step 2: Write `index.md`**

```markdown
# python-telegram-bot

> Async Python wrapper for the Telegram Bot API with handler-based update routing, persistence, and job scheduling.

## Overview

`python-telegram-bot` (v22.x) provides an async interface to the Telegram Bot API. The core pattern: create an `Application`, register `Handler` objects that route incoming `Update`s to async callback functions, then run with polling or webhook.

Install: `pip install python-telegram-bot`

## Minimal Bot

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DefaultType):
    await update.message.reply_text("Hello!")

app = Application.builder().token("BOT_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

## Module Map

| File | When to read |
|------|-------------|
| [application.md](application.md) | Setting up the bot, ApplicationBuilder, lifecycle, Defaults, JobQueue |
| [bot.md](bot.md) | Sending messages, making API calls directly via Bot class |
| [handlers/](handlers/index.md) | Routing updates to callbacks — commands, messages, buttons, conversations |
| [types/](types/index.md) | Telegram data types — Message, Update, User, Chat, keyboards, media |
| [features/](features/index.md) | Inline mode, payments, games, stickers, passport, web apps |
| [persistence.md](persistence.md) | Storing conversation/user/chat data across bot restarts |
| [rate-limiting.md](rate-limiting.md) | Throttling API calls to respect Telegram rate limits |
| [request.md](request.md) | Custom HTTP request configuration (proxy, timeouts, HTTP/2) |
| [errors.md](errors.md) | Exception hierarchy and error handling |
| [constants.md](constants.md) | Library constants — ParseMode, ChatType, limits, etc. |
| [helpers.md](helpers.md) | Utility functions — deep links, mentions, markdown escaping |
```

**Step 3: Commit**

```bash
git add docs/telegram/python-telegram-bot/
git commit -m "docs: add python-telegram-bot documentation structure and index"
```

---

## Task 2: Write `application.md`

**Files:**
- Create: `docs/telegram/python-telegram-bot/application.md`

**Step 1: Write the file**

Content must cover:
- **Application** class: attributes (bot, update_queue, chat_data, user_data, bot_data, persistence, handlers, job_queue, running), core methods (run_polling, run_webhook, start, stop, add_handler, add_handlers, add_error_handler, process_update, create_task, drop_chat_data, drop_user_data)
- **ApplicationBuilder**: token(), bot(), defaults(), persistence(), concurrent_updates(), job_queue(), rate_limiter(), proxy(), connection_pool_size(), timeouts, post_init/post_stop/post_shutdown, build()
- **Defaults** class: parse_mode, disable_notification, allow_sending_without_reply, tzinfo, block, protect_content, link_preview_options
- **CallbackContext**: attributes (bot, bot_data, chat_data, user_data, args, matches, match, error, job, job_queue, application), methods (from_update, from_error, from_job)
- **ContextTypes**: constructor (context, bot_data, chat_data, user_data), DEFAULT_TYPE
- **JobQueue**: run_once, run_repeating, run_daily, run_monthly, run_custom, jobs(), get_jobs_by_name()
- Quick usage: builder pattern → add handler → run_polling
- Common patterns: setting defaults, adding error handler, using job queue

**Step 2: Commit**

```bash
git add docs/telegram/python-telegram-bot/application.md
git commit -m "docs: add python-telegram-bot application reference"
```

---

## Task 3: Write `bot.md`

**Files:**
- Create: `docs/telegram/python-telegram-bot/bot.md`

**Step 1: Write the file**

Content must cover:
- **Bot** class constructor: token, base_url, base_file_url, request, get_updates_request, private_key, local_mode
- Key properties: token, bot, id, username, name, first_name, link, local_mode
- Sending methods: send_message, send_photo, send_audio, send_document, send_video, send_voice, send_animation, send_sticker, send_poll, send_location, send_venue, send_contact, send_media_group
- Editing methods: edit_message_text, edit_message_caption, edit_message_media, edit_message_reply_markup, delete_message
- Forwarding: forward_message, copy_message
- Chat management: get_chat, ban_chat_member, unban_chat_member, restrict_chat_member, promote_chat_member, leave_chat, set_chat_title, set_chat_description
- Updates: get_updates, set_webhook, delete_webhook
- Bot config: set_my_commands, get_my_commands, set_chat_menu_button
- Payments: send_invoice, answer_shipping_query, answer_pre_checkout_query
- Stickers: create_new_sticker_set, add_sticker_to_set
- Note: In most cases, use `update.message.reply_text()` shortcut instead of `bot.send_message()` directly
- Common patterns: sending with parse_mode, sending media, answering callback queries
- Related: link to types/messages.md, types/keyboards.md, ../api/bots/messages/sending.md

**Step 2: Commit**

```bash
git add docs/telegram/python-telegram-bot/bot.md
git commit -m "docs: add python-telegram-bot Bot class reference"
```

---

## Task 4: Write handlers index and core handler files

**Files:**
- Create: `docs/telegram/python-telegram-bot/handlers/index.md`
- Create: `docs/telegram/python-telegram-bot/handlers/command-handler.md`
- Create: `docs/telegram/python-telegram-bot/handlers/message-handler.md`
- Create: `docs/telegram/python-telegram-bot/handlers/callback-query-handler.md`

**Step 1: Write `handlers/index.md`**

Content:
- Overview of handler-based routing: Application dispatches Updates to handlers by priority (group number), first match within group wins
- Handler callback signature: `async def callback(update: Update, context: ContextTypes.DefaultType)`
- Table routing to each handler file

| File | When to read |
|------|-------------|
| command-handler.md | Handle /commands like /start, /help |
| message-handler.md | Handle messages by type or content (text, photo, etc.) |
| callback-query-handler.md | Handle inline keyboard button presses |
| conversation-handler.md | Multi-step conversation flows with states |
| inline-query-handler.md | Handle inline queries (@bot query) |
| filters.md | Filter system — select which updates a handler receives |
| other-handlers.md | All other handlers (PreCheckout, ChatMember, Poll, etc.) |

**Step 2: Write `handlers/command-handler.md`**

Content:
- CommandHandler(command, callback, filters=None, block=True, has_args=None)
- command: str or list of str, case-insensitive
- has_args: True (require args), False (no args), int (exact count), None (any)
- Context gets `context.args` as whitespace-split list
- Attributes: commands (frozenset), callback, filters, block, has_args

**Step 3: Write `handlers/message-handler.md`**

Content:
- MessageHandler(filters, callback, block=True)
- filters param is required (use filters.ALL for everything)
- Relies on filters module for routing — link to filters.md

**Step 4: Write `handlers/callback-query-handler.md`**

Content:
- CallbackQueryHandler(callback, pattern=None, game_pattern=None, block=True)
- pattern: str/regex/callable/type for matching CallbackQuery.data
- Regex matches added to context.matches
- Must call `await query.answer()` in callback
- Common pattern: inline keyboard → callback query handler

**Step 5: Commit**

```bash
git add docs/telegram/python-telegram-bot/handlers/
git commit -m "docs: add python-telegram-bot handler docs (index, command, message, callback-query)"
```

---

## Task 5: Write conversation handler, inline query handler, and other handlers

**Files:**
- Create: `docs/telegram/python-telegram-bot/handlers/conversation-handler.md`
- Create: `docs/telegram/python-telegram-bot/handlers/inline-query-handler.md`
- Create: `docs/telegram/python-telegram-bot/handlers/other-handlers.md`

**Step 1: Write `handlers/conversation-handler.md`**

Content:
- ConversationHandler(entry_points, states, fallbacks, allow_reentry=False, per_chat=True, per_user=True, per_message=False, conversation_timeout=None, name=None, persistent=False, map_to_parent=None)
- Constants: END (-1), TIMEOUT (-2), WAITING (-3)
- entry_points: list of handlers that start the conversation
- states: dict mapping state keys to handler lists
- fallbacks: handlers when no state handler matches
- Callback returns next state int, or ConversationHandler.END
- Common pattern: multi-step form with states

**Step 2: Write `handlers/inline-query-handler.md`**

Content:
- InlineQueryHandler(callback, pattern=None, block=True, chat_types=None)
- pattern: regex against InlineQuery.query
- Must call `await update.inline_query.answer(results)` in callback
- Link to features/inline-mode.md for result types

**Step 3: Write `handlers/other-handlers.md`**

Content — one section per handler:
- PreCheckoutQueryHandler(callback, block=True)
- ShippingQueryHandler(callback, block=True)
- ChatMemberHandler(callback, chat_member_types=None, block=True)
- ChatJoinRequestHandler(callback, block=True)
- PollHandler(callback, block=True)
- PollAnswerHandler(callback, block=True)
- ChosenInlineResultHandler(callback, pattern=None, block=True)
- MessageReactionHandler(callback, message_reaction_types=None, block=True)
- ChatBoostHandler(callback, chat_boost_types=None, block=True)
- BusinessConnectionHandler(callback, block=True)
- BusinessMessagesDeletedHandler(callback, block=True)
- PaidMediaPurchasedHandler(callback, block=True)
- PrefixHandler(prefix, command, callback, filters=None, block=True)
- TypeHandler(type, callback, strict=False, block=True)

**Step 4: Commit**

```bash
git add docs/telegram/python-telegram-bot/handlers/
git commit -m "docs: add conversation, inline-query, and other handler docs"
```

---

## Task 6: Write `handlers/filters.md`

**Files:**
- Create: `docs/telegram/python-telegram-bot/handlers/filters.md`

**Step 1: Write the file**

Content:
- Overview: filters select which updates a handler processes. Combine with `&` (AND), `|` (OR), `~` (NOT), `^` (XOR)
- Pre-instantiated filter constants: ALL, TEXT, PHOTO, VIDEO, AUDIO, DOCUMENT, ANIMATION, VOICE, VIDEO_NOTE, CONTACT, LOCATION, VENUE, COMMAND, REPLY, FORWARDED, CAPTION, STICKER, POLL, DICE, INVOICE, SUCCESSFUL_PAYMENT, PASSPORT_DATA, GAME, PREMIUM_USER, FORUM, STORY, etc.
- Filter classes requiring initialization: Regex(pattern), Text(strings), Caption(strings), Chat(chat_id, username), User(user_id), Entity(entity_type), CaptionEntity(entity_type), ForwardedFrom(chat_id, username), Document.FileExtension(ext), Document.MimeType(mime), Language(lang), Mention(mentions), ViaBot(bot_id)
- ChatType namespace: PRIVATE, GROUP, SUPERGROUP, CHANNEL, GROUPS
- Dice namespace: Basketball, Bowling, Darts, Football, SlotMachine
- Document namespace: ALL, Category, FileExtension, MimeType (with presets like PDF, ZIP, MP3)
- Custom filters: subclass MessageFilter or UpdateFilter, implement filter() method
- Common patterns: combining filters, negating, filtering commands in groups only

**Step 2: Commit**

```bash
git add docs/telegram/python-telegram-bot/handlers/filters.md
git commit -m "docs: add python-telegram-bot filters reference"
```

---

## Task 7: Write types index and core type files

**Files:**
- Create: `docs/telegram/python-telegram-bot/types/index.md`
- Create: `docs/telegram/python-telegram-bot/types/messages.md`
- Create: `docs/telegram/python-telegram-bot/types/media.md`
- Create: `docs/telegram/python-telegram-bot/types/keyboards.md`
- Create: `docs/telegram/python-telegram-bot/types/other-types.md`

**Step 1: Write `types/index.md`**

Routing table:
| File | When to read |
|------|-------------|
| messages.md | Update, Message, Chat, ChatFullInfo, User, MessageEntity |
| media.md | PhotoSize, Document, Audio, Video, Voice, Animation, etc. |
| keyboards.md | InlineKeyboardMarkup/Button, ReplyKeyboardMarkup, ForceReply |
| other-types.md | Location, Contact, Venue, Poll, Dice, File, InputFile, BotCommand, WebAppInfo |

Note: all types extend `TelegramObject` which provides `to_dict()`, `to_json()`, `from_json()`.

**Step 2: Write `types/messages.md`**

Key classes:
- **Update**: update_id, message, edited_message, channel_post, callback_query, inline_query, chosen_inline_result, shipping_query, pre_checkout_query, poll, poll_answer, chat_member, chat_join_request, effective_message (property), effective_chat (property), effective_user (property)
- **Message**: message_id, date, chat, from_user, text, entities, caption, photo, document, audio, video, voice, animation, reply_to_message, reply_markup. Shortcut methods: reply_text(), reply_photo(), reply_document(), reply_html(), reply_markdown_v2(), forward(), copy(), delete(), edit_text(), pin(), unpin()
- **Chat**: id, type, title, username, first_name, last_name
- **ChatFullInfo**: extends Chat with bio, description, invite_link, permissions, etc.
- **User**: id, is_bot, first_name, last_name, username, language_code. Methods: mention_html(), mention_markdown_v2(), get_profile_photos()
- **MessageEntity**: type, offset, length, url, user, language. Types: mention, hashtag, cashtag, bot_command, url, email, phone_number, bold, italic, underline, strikethrough, spoiler, code, pre, text_link, text_mention, custom_emoji

**Step 3: Write `types/media.md`**

Key classes: PhotoSize, Audio, Document, Video, VideoNote, Voice, Animation, Contact, Location, Venue, Dice, File, InputFile, InputMedia (Photo, Video, Animation, Audio, Document), InputPaidMedia (Photo, Video)

**Step 4: Write `types/keyboards.md`**

Key classes:
- **InlineKeyboardMarkup**: inline_keyboard (list of list of InlineKeyboardButton)
- **InlineKeyboardButton**: text, callback_data, url, switch_inline_query, switch_inline_query_current_chat, web_app, login_url, pay, copy_text
- **ReplyKeyboardMarkup**: keyboard, resize_keyboard, one_time_keyboard, selective, input_field_placeholder, is_persistent
- **KeyboardButton**: text, request_contact, request_location, request_poll, web_app, request_users, request_chat
- **ReplyKeyboardRemove**: remove_keyboard=True, selective
- **ForceReply**: force_reply=True, selective, input_field_placeholder

**Step 5: Write `types/other-types.md`**

Key classes: Location, Contact, Venue, Poll, PollOption, PollAnswer, Dice, File, InputFile, BotCommand, BotCommandScope*, WebAppInfo, WebAppData, ChatInviteLink, ChatPermissions, ChatAdministratorRights, ChatPhoto, ChatMember*, ForumTopic*, MenuButton*, LinkPreviewOptions, ReplyParameters, CallbackQuery (answer method), LoginUrl, SwitchInlineQueryChosenChat

**Step 6: Commit**

```bash
git add docs/telegram/python-telegram-bot/types/
git commit -m "docs: add python-telegram-bot type reference docs"
```

---

## Task 8: Write features index and inline-mode, payments

**Files:**
- Create: `docs/telegram/python-telegram-bot/features/index.md`
- Create: `docs/telegram/python-telegram-bot/features/inline-mode.md`
- Create: `docs/telegram/python-telegram-bot/features/payments.md`

**Step 1: Write `features/index.md`**

Routing table for feature modules.

**Step 2: Write `features/inline-mode.md`**

Content:
- InlineQuery: id, from_user, query, offset, chat_type. Method: answer(results, cache_time, is_personal, next_offset, button)
- Result types: InlineQueryResultArticle, Photo, Gif, Mpeg4Gif, Video, Audio, Voice, Document, Location, Venue, Contact, Game
- Cached variants: InlineQueryResultCached* (Photo, Gif, Mpeg4Gif, Video, Audio, Voice, Document, Sticker)
- InputMessageContent types: InputTextMessageContent, InputLocationMessageContent, InputVenueMessageContent, InputContactMessageContent, InputInvoiceMessageContent
- InlineQueryResultsButton: text, web_app, start_parameter
- ChosenInlineResult: result_id, from_user, query, location, inline_message_id

**Step 3: Write `features/payments.md`**

Content:
- Payment flow: send_invoice → ShippingQuery → PreCheckoutQuery → SuccessfulPayment
- Invoice, LabeledPrice, ShippingAddress, ShippingOption, OrderInfo
- Bot methods: send_invoice, answer_shipping_query, answer_pre_checkout_query
- Star transactions: StarTransaction, StarTransactions, TransactionPartner*
- Handlers: PreCheckoutQueryHandler, ShippingQueryHandler
- RefundedPayment

**Step 4: Commit**

```bash
git add docs/telegram/python-telegram-bot/features/
git commit -m "docs: add inline-mode and payments feature docs"
```

---

## Task 9: Write games, stickers, passport, web-apps

**Files:**
- Create: `docs/telegram/python-telegram-bot/features/games.md`
- Create: `docs/telegram/python-telegram-bot/features/stickers.md`
- Create: `docs/telegram/python-telegram-bot/features/passport.md`
- Create: `docs/telegram/python-telegram-bot/features/web-apps.md`

**Step 1: Write `features/games.md`**

Content: Game, GameHighScore, CallbackGame. Bot methods: send_game, set_game_score, get_game_high_scores.

**Step 2: Write `features/stickers.md`**

Content: Sticker, StickerSet, InputSticker, MaskPosition. Bot methods: send_sticker, get_sticker_set, create_new_sticker_set, add_sticker_to_set, delete_sticker_from_set, set_sticker_position_in_set, set_sticker_set_thumbnail.

**Step 3: Write `features/passport.md`**

Content: PassportData, EncryptedPassportElement, EncryptedCredentials, Credentials, PersonalDetails, ResidentialAddress, IdDocumentData, PassportFile. Error types for validation feedback.

**Step 4: Write `features/web-apps.md`**

Content: WebAppInfo, WebAppData, SentWebAppMessage. MenuButtonWebApp. KeyboardButton with web_app. InlineKeyboardButton with web_app.

**Step 5: Commit**

```bash
git add docs/telegram/python-telegram-bot/features/
git commit -m "docs: add games, stickers, passport, web-apps feature docs"
```

---

## Task 10: Write standalone reference files

**Files:**
- Create: `docs/telegram/python-telegram-bot/persistence.md`
- Create: `docs/telegram/python-telegram-bot/rate-limiting.md`
- Create: `docs/telegram/python-telegram-bot/request.md`
- Create: `docs/telegram/python-telegram-bot/errors.md`
- Create: `docs/telegram/python-telegram-bot/constants.md`
- Create: `docs/telegram/python-telegram-bot/helpers.md`

**Step 1: Write `persistence.md`**

Content:
- BasePersistence (abstract): methods to implement (get/update/drop user_data, chat_data, bot_data, conversations, callback_data)
- PicklePersistence(filepath, store_data=None, single_file=True, on_flush=False, update_interval=60, context_types=None)
- DictPersistence: in-memory, same interface
- PersistenceInput: configure which data types to persist
- Wire up: ApplicationBuilder().persistence(PicklePersistence("data.pickle"))

**Step 2: Write `rate-limiting.md`**

Content:
- BaseRateLimiter (abstract): initialize(), shutdown(), process_request()
- AIORateLimiter(overall_max_rate=30, overall_time_period=1, group_max_rate=20, group_time_period=60, max_retries=0)
- Requires: `pip install "python-telegram-bot[rate-limiter]"`
- Wire up: ApplicationBuilder().rate_limiter(AIORateLimiter())

**Step 3: Write `request.md`**

Content:
- HTTPXRequest(connection_pool_size=256, read_timeout=5.0, write_timeout=5.0, connect_timeout=5.0, pool_timeout=1.0, http_version='1.1', proxy=None, media_write_timeout=20.0, httpx_kwargs=None)
- BaseRequest (abstract): initialize(), shutdown(), do_request()
- Usually configured via ApplicationBuilder timeout/proxy methods, not directly

**Step 4: Write `errors.md`**

Content — exception hierarchy:
- TelegramError (base)
  - NetworkError → BadRequest, TimedOut
  - Forbidden
  - InvalidToken
  - RetryAfter(retry_after: int|timedelta)
  - ChatMigrated(new_chat_id: int)
  - Conflict
  - EndPointNotFound
  - PassportDecryptionError
- Error handling pattern: add_error_handler on Application

**Step 5: Write `constants.md`**

Content — key constant classes:
- ParseMode: HTML, MARKDOWN, MARKDOWN_V2
- ChatType: PRIVATE, GROUP, SUPERGROUP, CHANNEL, SENDER
- ChatMemberStatus: OWNER, ADMINISTRATOR, MEMBER, RESTRICTED, LEFT, BANNED
- ChatAction: TYPING, UPLOAD_PHOTO, UPLOAD_VIDEO, RECORD_VIDEO, etc.
- MessageLimit, FileSizeLimit, ChatLimit, etc.
- BOT_API_VERSION

**Step 6: Write `helpers.md`**

Content:
- create_deep_linked_url(bot_username, payload=None, group=False) → str
- effective_message_type(entity) → str | None
- escape_markdown(text, version=1, entity_type=None) → str
- mention_html(user_id, name) → str
- mention_markdown(user_id, name, version=1) → str

**Step 7: Commit**

```bash
git add docs/telegram/python-telegram-bot/
git commit -m "docs: add persistence, rate-limiting, request, errors, constants, helpers docs"
```

---

## Task 11: Final review and cross-link verification

**Step 1: Verify all files exist**

```bash
find docs/telegram/python-telegram-bot -name "*.md" | sort
```

Expected: 25 files.

**Step 2: Verify all internal links resolve**

Check that every `[text](path.md)` link in every file points to an existing file.

**Step 3: Verify cross-references to `docs/telegram/api/`**

Spot-check that linked API docs exist.

**Step 4: Final commit if any fixes needed**

```bash
git add docs/telegram/python-telegram-bot/
git commit -m "docs: fix cross-links in python-telegram-bot docs"
```
