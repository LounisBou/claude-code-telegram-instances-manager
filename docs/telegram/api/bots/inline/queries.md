# Inline Queries

When a user types `@botusername query` in any chat, the bot receives an InlineQuery update.

## Types

### InlineQuery

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier for this query |
| from | User | Sender |
| query | String | Text of the query (up to 256 characters) |
| offset | String | Offset of results to return (for pagination) |
| chat_type | String | Type of chat where query was sent: "sender", "private", "group", "supergroup", "channel" (optional) |
| location | Location | Sender location, if geo-enabled bot (optional) |

## Methods

### answerInlineQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| inline_query_id | String | Yes | Unique identifier of the query |
| results | Array of InlineQueryResult | Yes | Array of results (max 50) |
| cache_time | Integer | No | Max seconds to cache results on server (default 300) |
| is_personal | Boolean | No | Results are specific to this user |
| next_offset | String | No | Offset for the next results page |
| button | InlineQueryResultsButton | No | Button shown above results |

**Returns:** True

### InlineQueryResultsButton

| Field | Type | Description |
|-------|------|-------------|
| text | String | Button label |
| web_app | WebAppInfo | Opens Web App (optional) |
| start_parameter | String | Deep-linking parameter for bot's /start (optional) |

### ChosenInlineResult

| Field | Type | Description |
|-------|------|-------------|
| result_id | String | Unique identifier of the chosen result |
| from | User | User who chose the result |
| location | Location | Sender location (optional) |
| inline_message_id | String | Identifier of the sent inline message (optional) |
| query | String | Query that was used to obtain the result |

## Gotchas

- **Max 50 results** per answerInlineQuery call
- **Pagination**: set next_offset and return up to 50 results; bot receives next query with that offset
- **cache_time**: set to 0 during development, higher in production
- **is_personal=true**: cache is per-user instead of global
- To edit sent inline results later, save **inline_message_id** from ChosenInlineResult
- Bot must have **inline mode enabled** via @BotFather
