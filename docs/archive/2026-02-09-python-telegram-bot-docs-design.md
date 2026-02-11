# python-telegram-bot Documentation Design

## Goal

Full documentation of the `python-telegram-bot` Python package for Claude Code consumption, using progressive disclosure (Index → Topic → Detail).

Location: `docs/telegram/python-telegram-bot/`

## Target Audience

Claude Code — AI coding assistant that needs to quickly find correct classes, methods, and patterns when building Telegram bots.

## Directory Structure

```
docs/telegram/python-telegram-bot/
├── index.md                     # Top-level router — what the library is, module map
├── application.md               # Application, ApplicationBuilder, lifecycle
├── bot.md                       # Bot class — sending messages, API calls
├── handlers/
│   ├── index.md                 # Handler overview, how routing works, handler list
│   ├── command-handler.md
│   ├── message-handler.md
│   ├── callback-query-handler.md
│   ├── conversation-handler.md
│   ├── inline-query-handler.md
│   ├── other-handlers.md        # PreCheckout, ShippingQuery, ChatMember, etc.
│   └── filters.md               # Filter system used by handlers
├── types/
│   ├── index.md                 # Type overview, common patterns
│   ├── messages.md              # Message, Update, Chat, User
│   ├── media.md                 # PhotoSize, Document, Audio, Video, etc.
│   ├── keyboards.md             # InlineKeyboardMarkup, ReplyKeyboardMarkup, etc.
│   └── other-types.md           # Location, Contact, Venue, etc.
├── features/
│   ├── index.md                 # Feature modules overview
│   ├── inline-mode.md
│   ├── payments.md
│   ├── games.md
│   ├── stickers.md
│   ├── passport.md
│   └── web-apps.md
├── persistence.md               # Persistence system
├── rate-limiting.md             # Rate limiter classes
├── request.md                   # HTTPXRequest, custom request classes
├── errors.md                    # Error/exception hierarchy
├── constants.md                 # Library constants
└── helpers.md                   # Helper utilities
```

## File Content Template

Each file follows a consistent format:

```markdown
# [Topic Name]

> One-line description of what this module/class does.

## Overview
2-3 sentences: what it is, when to use it, how it fits in the library.

## Quick Usage
Minimal code showing the most common usage pattern (5-10 lines).

## Key Classes / Functions

### ClassName
> One-line purpose.

**Constructor:**
`ClassName(param1: Type = default, param2: Type = default, ...)`

- `param1` — what it does
- `param2` — what it does

**Key Methods:**
- `method_name(params) -> ReturnType` — what it does

**Key Attributes:**
- `attr_name: Type` — what it is

## Common Patterns
2-3 short snippets showing typical combinations.

## Related
- Links to related topic files within the docs
- Link to corresponding Telegram Bot API section in docs/telegram/api
```

## Index File Strategy

Top-level `index.md` routes Claude to the right file via a table:

| File | When to read |
|------|-------------|
| application.md | Setting up the bot, lifecycle, builder pattern |
| bot.md | Sending messages, making API calls directly |
| handlers/ | Routing updates to callbacks (commands, messages, buttons) |
| types/ | Telegram data types (Message, User, Chat, keyboards) |
| features/ | Inline mode, payments, games, stickers, passport, web apps |
| persistence.md | Storing conversation/user data across restarts |
| ... | ... |

Sub-index files follow the same pattern.

## Cross-Referencing

- Each file links to corresponding `docs/telegram/api` sections for underlying Telegram concepts
- Type files document only the Python class interface, not Telegram API semantics
- Related section at bottom of each file includes cross-links

## Detail Level

Usage + key API signatures. Minimal code examples — enough for Claude to write correct code, not tutorial-style.

## Source

Official docs: https://docs.python-telegram-bot.org/en/stable/
