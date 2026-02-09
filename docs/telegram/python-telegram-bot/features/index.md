# Features

> Specialized Telegram Bot API features -- inline mode, payments, games, stickers, passport, and web apps.

## Overview

These docs cover the higher-level Telegram Bot API features beyond basic messaging. Each feature has its own set of types, bot methods, and handlers. Most require additional setup via @BotFather (e.g., enabling inline mode, creating games, configuring payments).

## Routing Table

| File | When to read |
|------|-------------|
| [inline-mode.md](inline-mode.md) | Inline queries -- user types `@bot query` in any chat |
| [payments.md](payments.md) | Accepting payments, invoices, Telegram Stars |
| [games.md](games.md) | HTML5 games in Telegram |
| [stickers.md](stickers.md) | Sending and managing sticker sets |
| [passport.md](passport.md) | Telegram Passport -- identity verification |
| [web-apps.md](web-apps.md) | Web Apps (Mini Apps) -- embedded web interfaces |

## Related

- [../index.md](../index.md) -- python-telegram-bot top-level reference
- [../bot.md](../bot.md) -- Bot methods (many feature-specific methods listed there)
- [../handlers/index.md](../handlers/index.md) -- handler routing for feature-related updates
- [../types/index.md](../types/index.md) -- base types used across features
- [Telegram API — Bot API Overview](../../api/bots/index.md) -- complete Bot API reference and feature overview
