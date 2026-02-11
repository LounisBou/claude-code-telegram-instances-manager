# Telegram Bot API Documentation Design

## Purpose

Reference documentation for Claude Code to consult when building Telegram bots. Optimized for context window efficiency with progressive disclosure.

## Audience

Claude Code (AI agent). Guided reference format: structured by topic with brief explanations of when to use what, plus full parameter tables. No code examples.

## Progressive Disclosure (3 levels)

1. **Top index** (`index.md`) — API essentials + routing table mapping tasks to sections
2. **Section index** (`section/index.md`) — Quick reference table mapping needs to methods to files
3. **Topic file** (`section/topic.md`) — Full method/type documentation with gotchas and patterns

## Location

`docs/telegram/api/bots/`

## Scope

Full Telegram Bot API coverage (Bot API 9.3, December 2025).

## Shared Types Rule

A type goes in `types/` only if referenced by 3+ topic files. Otherwise it stays in the topic file where it's most relevant.

## Topic File Template

Methods (full parameter tables) → Types (field tables) → Gotchas → Patterns
