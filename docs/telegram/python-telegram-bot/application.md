# Application System

> Core orchestration layer: Application lifecycle, builder pattern, and defaults.

## Overview

The `Application` class is the central object in python-telegram-bot v22.x. It owns the `Bot`, `Updater`, handler routing, persistence, and job queue. You never instantiate it directly -- use `Application.builder()` to get an `ApplicationBuilder`, chain configuration methods, then call `.build()`. Once built, call `run_polling()` or `run_webhook()` to start processing updates.

## Quick Usage

```python
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DefaultType):
    await update.message.reply_text("Hello!")

app = Application.builder().token("BOT_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
```

## Key Classes

### Application

> Central class that connects the bot, handlers, persistence, and job queue. Cannot be directly instantiated.

**Constructor:** Not directly callable. Use `Application.builder()` to obtain an `ApplicationBuilder`.

**Key Attributes:**

- `bot: Bot` -- the Bot instance used to make API calls
- `update_queue: asyncio.Queue` -- queue of incoming `Update` objects
- `updater: Updater` -- the Updater responsible for fetching updates (polling/webhook)
- `chat_data: MappingProxyType[int, dict]` -- read-only view of per-chat data keyed by chat_id
- `user_data: MappingProxyType[int, dict]` -- read-only view of per-user data keyed by user_id
- `bot_data: dict` -- mutable bot-wide data dict
- `persistence: BasePersistence | None` -- persistence backend (if configured)
- `handlers: dict[int, list[BaseHandler]]` -- handler groups; key is group int, value is ordered list of handlers
- `error_handlers: dict[Callable, bool]` -- registered error handlers; value is `block` flag
- `context_types: ContextTypes` -- context type configuration
- `job_queue: JobQueue | None` -- job scheduler (requires `python-telegram-bot[job-queue]`)
- `running: bool` -- property; `True` between `start()` and `stop()`

**Core Methods:**

Convenience run methods (blocking, handles signal setup and event loop):

- `run_polling(poll_interval: float = 0.0, timeout: timedelta = timedelta(seconds=10), bootstrap_retries: int = 0, allowed_updates: list[str] | None = None, drop_pending_updates: bool | None = None, close_loop: bool = True, stop_signals: tuple | None = None) -> None` -- starts polling in a blocking manner. Sets up signal handlers, calls `initialize()`, `updater.start_polling()`, `start()`, idles until stop signal, then shuts down.
- `run_webhook(listen: str = '127.0.0.1', port: int = 80, url_path: str = '', cert: str | Path | None = None, key: str | Path | None = None, bootstrap_retries: int = 0, webhook_url: str | None = None, allowed_updates: list[str] | None = None, drop_pending_updates: bool | None = None, ip_address: str | None = None, max_connections: int = 40, close_loop: bool = True, stop_signals: tuple | None = None, secret_token: str | None = None, unix: str | Path | None = None) -> None` -- starts webhook server in a blocking manner. Same lifecycle as `run_polling` but uses `updater.start_webhook()`.

Async lifecycle methods (for manual control):

- `async initialize() -> None` -- initializes bot, persistence, and job queue. Must be called before `start()`.
- `async shutdown() -> None` -- shuts down bot, persistence, and job queue. Counterpart to `initialize()`.
- `async start() -> None` -- starts processing updates from `update_queue`. Requires `initialize()` first.
- `async stop() -> None` -- stops processing updates. Call before `shutdown()`.
- `stop_running() -> None` -- signals a running `run_polling()`/`run_webhook()` to stop. Can be called from a handler.

Handler management:

- `add_handler(handler: BaseHandler, group: int = 0) -> None` -- adds a handler to the specified group. Lower group numbers are checked first. Within a group, handlers are checked in insertion order. Once a handler in a group matches, remaining handlers in that group are skipped, but higher-numbered groups still run.
- `add_handlers(handlers: list | dict, group: int = 0) -> None` -- if `handlers` is a list, adds all to `group`. If dict, keys are group ints and values are handler lists.
- `remove_handler(handler: BaseHandler, group: int = 0) -> None` -- removes handler from group.

Error handling:

- `add_error_handler(callback: Callable, block: bool = True) -> None` -- registers an error handler. Callback signature: `async def callback(update: object | None, context: CallbackContext)`. Access the exception via `context.error`.
- `remove_error_handler(callback: Callable) -> None` -- unregisters an error handler.

Update processing:

- `async process_update(update: Update) -> None` -- processes a single update through the handler chain. Called internally; useful for testing or manual update injection.
- `async process_error(update: object | None, error: Exception, job: Job | None = None, coroutine: Coroutine | None = None) -> bool` -- dispatches error to registered error handlers. Returns `True` if any error handler handled it.

Data management:

- `drop_chat_data(chat_id: int) -> None` -- removes chat_data entry for the given chat.
- `drop_user_data(user_id: int) -> None` -- removes user_data entry for the given user.
- `migrate_chat_data(message: Message | None = None, old_chat_id: int | None = None, new_chat_id: int | None = None) -> None` -- migrates chat_data from old_chat_id to new_chat_id. Can pass a `Message` that contains migration info, or explicit IDs.

Task creation:

- `create_task(coroutine: Coroutine, update: object | None = None, name: str | None = None) -> asyncio.Task` -- creates a tracked task. If it raises, the exception is routed to error handlers with the given `update` as context.

Static methods:

- `builder() -> ApplicationBuilder` -- returns a new `ApplicationBuilder` for constructing an `Application`.

---

### ApplicationBuilder

> Fluent builder for constructing an `Application`. Every setter returns `self` for chaining.

**Constructor:** Not called directly. Obtain via `Application.builder()`.

All methods below return `self` (the builder) unless noted otherwise:

**Token and bot:**

- `token(token: str)` -- bot token from BotFather. Mutually exclusive with `bot()`.
- `bot(bot: Bot)` -- use a pre-configured Bot instance. Mutually exclusive with `token()`.
- `base_url(base_url: str)` -- custom Bot API server base URL (default: Telegram's servers).
- `base_file_url(base_file_url: str)` -- custom file download base URL.
- `local_mode(local_mode: bool)` -- enable local Bot API server mode.
- `private_key(private_key: bytes, password: bytes | None = None)` -- RSA private key for decrypting Telegram Passport data.

**Behavior:**

- `defaults(defaults: Defaults)` -- set default values for parse_mode, etc.
- `concurrent_updates(concurrent_updates: bool | int)` -- `True` to process updates concurrently (default: `False`). Pass an `int` to set the semaphore limit.
- `arbitrary_callback_data(callback_data: bool | int)` -- enable storing arbitrary data in callback buttons. Pass `True` (1024 entry cache) or an `int` for custom cache size.
- `context_types(context_types: ContextTypes)` -- custom context types.

**Persistence and scheduling:**

- `persistence(persistence: BasePersistence)` -- set persistence backend.
- `job_queue(job_queue: JobQueue)` -- set a custom JobQueue instance.

**Networking:**

- `proxy(proxy: str | httpx.Proxy | httpx.URL)` -- proxy URL for API requests.
- `get_updates_proxy(proxy: str | httpx.Proxy | httpx.URL)` -- proxy URL specifically for `getUpdates` calls.
- `connection_pool_size(connection_pool_size: int = 256)` -- max connections for API requests.
- `get_updates_connection_pool_size(get_updates_connection_pool_size: int = 1)` -- max connections for getUpdates.
- `connect_timeout(connect_timeout: float = 5.0)` -- connection timeout in seconds.
- `read_timeout(read_timeout: float = 5.0)` -- read timeout in seconds.
- `write_timeout(write_timeout: float = 5.0)` -- write timeout in seconds.
- `pool_timeout(pool_timeout: float = 1.0)` -- timeout for acquiring a connection from the pool.
- `media_write_timeout(media_write_timeout: float = 20.0)` -- write timeout for media uploads.
- `http_version(http_version: str)` -- HTTP version string, e.g. `"2"` for HTTP/2. Default `"1.1"`.
- `rate_limiter(rate_limiter: BaseRateLimiter)` -- set a rate limiter for API calls.

**Lifecycle callbacks:**

- `post_init(callback: Callable[[Application], Coroutine])` -- async callback run after `initialize()`. Use for setup that needs the bot (e.g., setting commands).
- `post_stop(callback: Callable[[Application], Coroutine])` -- async callback run after `stop()`.
- `post_shutdown(callback: Callable[[Application], Coroutine])` -- async callback run after `shutdown()`.

**Advanced:**

- `updater(updater: Updater | None)` -- set a custom Updater, or `None` to disable.
- `update_queue(update_queue: asyncio.Queue)` -- provide a custom update queue.
- `application_class(application_class: type, kwargs: dict | None = None)` -- use a custom Application subclass.

**Build:**

- `build() -> Application` -- constructs and returns the `Application`. Raises `RuntimeError` if required parameters (e.g., token) are missing.

---

### Defaults

> Default values applied to all Bot API calls. Pass to `ApplicationBuilder.defaults()`.

**Constructor:**

```python
Defaults(
    parse_mode: str | None = None,
    disable_notification: bool | None = None,
    allow_sending_without_reply: bool | None = None,
    tzinfo: datetime.tzinfo = UTC,
    block: bool = True,
    protect_content: bool | None = None,
    link_preview_options: LinkPreviewOptions | None = None,
    do_quote: bool | None = None,
)
```

- `parse_mode` -- default parse mode for all messages (`"HTML"`, `"MarkdownV2"`, `"Markdown"`).
- `disable_notification` -- send messages silently by default.
- `allow_sending_without_reply` -- send even if the replied-to message is not found.
- `tzinfo` -- timezone for `JobQueue` scheduling. Defaults to UTC.
- `block` -- default `block` parameter for handlers. When `True` (default), handlers run sequentially; when `False`, they run as concurrent tasks.
- `protect_content` -- protect messages from forwarding/saving by default.
- `link_preview_options` -- default link preview behavior for outgoing messages.
- `do_quote` -- whether `Message.reply_text()` etc. quote the original message by default.

## Common Patterns

### Custom defaults and post_init setup

```python
from telegram.ext import Application, Defaults
from telegram.constants import ParseMode

defaults = Defaults(parse_mode=ParseMode.HTML, protect_content=True)

async def post_init(app: Application):
    await app.bot.set_my_commands([("start", "Start the bot"), ("help", "Get help")])

app = (
    Application.builder()
    .token("BOT_TOKEN")
    .defaults(defaults)
    .post_init(post_init)
    .build()
)
app.run_polling()
```

### Manual lifecycle (no run_polling)

```python
import asyncio
from telegram.ext import Application

async def main():
    app = Application.builder().token("BOT_TOKEN").build()
    async with app:  # calls initialize() on enter, shutdown() on exit
        await app.start()
        # custom logic here; process updates manually or run other async code
        await asyncio.sleep(3600)
        await app.stop()

asyncio.run(main())
```

## Related

- [Callback Context and Job Queue](context.md) -- context object, custom context types, and scheduled jobs
- [Bot class](bot.md) -- sending messages and making API calls
- [Handlers](handlers/index.md) -- routing updates to callbacks
- [Persistence](persistence.md) -- storing data across restarts
- [Errors](errors.md) -- exception hierarchy and error handling
- [Telegram API -- Updates](../api/bots/updates/index.md) -- underlying update model
