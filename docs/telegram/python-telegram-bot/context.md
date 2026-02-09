# Callback Context and Job Queue

> Context object passed to handler callbacks, custom context types, and scheduled job execution.

## Overview

`CallbackContext` is the object that carries bot references, user/chat data, and handler-specific information into every handler and error callback. `ContextTypes` lets you swap in custom subclasses or alternative data container types for `bot_data`, `chat_data`, and `user_data`. The `JobQueue` wraps APScheduler to let you schedule one-off, repeating, daily, or monthly async callbacks -- each job callback receives its own `CallbackContext` with optional per-chat and per-user data access.

## Quick Usage

```python
from telegram import Update
from telegram.ext import ContextTypes

async def handler(update: Update, context: ContextTypes.DefaultType):
    # Send a reply via the bot
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Hi!")

    # Read/write per-user persistent data
    context.user_data["visits"] = context.user_data.get("visits", 0) + 1

    # Schedule a one-off job 30 seconds from now
    context.job_queue.run_once(callback=reminder, when=30, chat_id=update.effective_chat.id)
```

## Key Classes

### CallbackContext

> Carries context data into handler and error callbacks. Created automatically by the Application.

**Constructor:**

```python
CallbackContext(application: Application, chat_id: int | None = None, user_id: int | None = None)
```

- `application` -- the Application instance.
- `chat_id` -- optional; pre-selects which `chat_data` dict to expose.
- `user_id` -- optional; pre-selects which `user_data` dict to expose.

**Properties (always available):**

- `application: Application` -- the Application instance.
- `bot: Bot` -- shortcut for `application.bot`.
- `bot_data: dict` -- the bot-wide data dict.
- `chat_data: dict | None` -- per-chat data dict for the current chat (None if no chat in context).
- `user_data: dict | None` -- per-user data dict for the current user (None if no user in context).
- `job_queue: JobQueue | None` -- the job queue.
- `update_queue: asyncio.Queue` -- the update queue.
- `match: re.Match | None` -- first regex match (shortcut for `matches[0]`). Available when handler used a regex pattern.

**Optional attributes (set depending on handler type):**

- `args: list[str]` -- command arguments. Set by `CommandHandler` and `PrefixHandler`. E.g., `/cmd foo bar` gives `["foo", "bar"]`.
- `matches: list[re.Match]` -- all regex matches. Set by handlers with regex patterns.
- `error: Exception` -- the exception. Set in error handler callbacks.
- `job: Job` -- the job that triggered the callback. Set in `JobQueue` callbacks and error handlers for job errors.
- `coroutine: Coroutine` -- the coroutine that raised. Set in error handlers when a task created via `create_task()` fails.

**Class methods:**

- `from_update(update: Update, application: Application) -> CallbackContext` -- creates context from an update, auto-extracting chat_id and user_id.
- `from_error(update: object | None, error: Exception, application: Application, job: Job | None = None, coroutine: Coroutine | None = None) -> CallbackContext` -- creates context for error handling.
- `from_job(job: Job, application: Application) -> CallbackContext` -- creates context for a job callback.

**Methods:**

- `drop_callback_data(callback_query: CallbackQuery) -> None` -- drops stored arbitrary callback data for the given query. Only relevant when `arbitrary_callback_data` is enabled.
- `refresh_data() -> None` -- refreshes `user_data`, `chat_data`, and `bot_data` from persistence.

---

### ContextTypes

> Configures custom types for context, bot_data, chat_data, and user_data.

**Constructor:**

```python
ContextTypes(
    context: type[CallbackContext] = CallbackContext,
    bot_data: type = dict,
    chat_data: type = dict,
    user_data: type = dict,
)
```

- `context` -- custom CallbackContext subclass.
- `bot_data` -- type/factory for bot_data (must be a mutable mapping type).
- `chat_data` -- type/factory for per-chat data.
- `user_data` -- type/factory for per-user data.

**Properties:**

- `context: type[CallbackContext]`
- `bot_data: type`
- `chat_data: type`
- `user_data: type`

**Class attribute:**

- `DEFAULT_TYPE: ContextTypes` -- a pre-made instance with all defaults. Use as type hint: `context: ContextTypes.DefaultType`.

---

### JobQueue

> Schedules async callbacks using APScheduler. Requires `pip install python-telegram-bot[job-queue]`.

**Attributes:**

- `scheduler: apscheduler.schedulers.asyncio.AsyncIOScheduler` -- the underlying APScheduler instance.
- `application: Application` -- property; the associated Application.

**Methods:**

All `run_*` methods return a `Job` object. The callback signature is `async def callback(context: CallbackContext)` -- access `context.job` for the `Job` instance, `context.job.data` for custom data.

- `run_once(callback: Callable, when: float | timedelta | datetime | time, data: object = None, name: str | None = None, chat_id: int | None = None, user_id: int | None = None, job_kwargs: dict | None = None) -> Job` -- runs callback once. `when` can be seconds from now (float), a timedelta, an absolute datetime, or a time (runs today or next day).
- `run_repeating(callback: Callable, interval: float | timedelta, first: float | timedelta | datetime | time | None = None, last: float | timedelta | datetime | time | None = None, data: object = None, name: str | None = None, chat_id: int | None = None, user_id: int | None = None, job_kwargs: dict | None = None) -> Job` -- runs callback repeatedly. `first` is the first execution time; `last` is when to stop.
- `run_daily(callback: Callable, time: time, days: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6), data: object = None, name: str | None = None, chat_id: int | None = None, user_id: int | None = None, job_kwargs: dict | None = None) -> Job` -- runs callback daily at specified time. `days` uses Monday=0 through Sunday=6.
- `run_monthly(callback: Callable, when: time, day: int, data: object = None, name: str | None = None, chat_id: int | None = None, user_id: int | None = None, job_kwargs: dict | None = None) -> Job` -- runs callback monthly on the given `day` (1-31) at given time. If the day doesn't exist in a month, it runs on the last day.
- `run_custom(callback: Callable, job_kwargs: dict, data: object = None, name: str | None = None, chat_id: int | None = None, user_id: int | None = None) -> Job` -- runs callback with custom APScheduler trigger kwargs.
- `jobs() -> tuple[Job, ...]` -- returns all scheduled jobs.
- `get_jobs_by_name(name: str) -> tuple[Job, ...]` -- returns jobs matching the given name.
- `async start() -> None` -- starts the scheduler.
- `async stop(wait: bool = True) -> None` -- stops the scheduler. If `wait` is True, waits for running jobs to complete.

Note: `chat_id` and `user_id` on job methods set `context.chat_data` and `context.user_data` in the job callback, allowing jobs to access per-chat/per-user data.

## Common Patterns

### Scheduled jobs with per-chat data

```python
from datetime import time
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def set_reminder(update: Update, context: ContextTypes.DefaultType):
    chat_id = update.effective_chat.id
    context.job_queue.run_daily(
        daily_reminder,
        time=time(hour=9, minute=0),
        chat_id=chat_id,
        name=f"reminder_{chat_id}",
        data={"text": "Good morning!"},
    )
    await update.message.reply_text("Daily reminder set for 09:00 UTC.")

async def daily_reminder(context: ContextTypes.DefaultType):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text=context.job.data["text"],
    )

async def cancel_reminder(update: Update, context: ContextTypes.DefaultType):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(f"reminder_{chat_id}")
    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("Reminder cancelled.")
```

## Related

- [Application](application.md) -- application lifecycle, builder, and defaults
- [Handlers](handlers/index.md) -- routing updates to callbacks
- [Persistence](persistence.md) -- storing data across restarts
