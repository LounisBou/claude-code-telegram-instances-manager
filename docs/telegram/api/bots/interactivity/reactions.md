# Message Reactions

Set emoji reactions on messages.

## setMessageReaction

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| message_id | Integer | Yes | Target message |
| reaction | Array of ReactionType | No | Reactions to set (empty array to remove all) |
| is_big | Boolean | No | Show larger reaction animation |

**Returns:** True

## ReactionType Variants

### ReactionTypeEmoji

| Field | Type | Description |
|-------|------|-------------|
| type | String | "emoji" |
| emoji | String | Emoji reaction (must be from allowed set) |

### ReactionTypeCustomEmoji

| Field | Type | Description |
|-------|------|-------------|
| type | String | "custom_emoji" |
| custom_emoji_id | String | Custom emoji identifier |

### ReactionTypePaid

| Field | Type | Description |
|-------|------|-------------|
| type | String | "paid" |

## Reaction Updates

Bot must include "message_reaction" and/or "message_reaction_count" in allowed_updates to receive these.

### message_reaction Update

Received when a specific user changes their reaction on a message (non-anonymous reactions).

### MessageReactionUpdated

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat containing the message |
| message_id | Integer | Message that was reacted to |
| user | User | User who changed the reaction (optional) |
| actor_chat | Chat | Chat on behalf of which the reaction was changed (optional) |
| date | Integer | Date of the change (Unix timestamp) |
| old_reaction | Array of ReactionType | Previous reactions |
| new_reaction | Array of ReactionType | New reactions |

### message_reaction_count Update

Received when reactions on a message with anonymous reactions are changed.

### MessageReactionCountUpdated

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat containing the message |
| message_id | Integer | Message identifier |
| date | Integer | Date of the change (Unix timestamp) |
| reactions | Array of ReactionCount | Current reaction counts |

### ReactionCount

| Field | Type | Description |
|-------|------|-------------|
| type | ReactionType | Reaction type |
| total_count | Integer | Number of times this reaction was used |

## Gotchas

- Bot can only set reactions available in the chat (check available_reactions in ChatFullInfo via getChat)
- Custom emoji reactions require Telegram Premium in the chat
- Passing empty reaction array removes the bot's reactions
- is_big: only shows the larger animation once; subsequent views show normal size
- message_reaction update: only received if explicitly enabled in allowed_updates
- message_reaction_count update: only for messages with anonymous reactions
- max_reaction_count in ChatFullInfo: maximum number of different reactions per message in this chat
- Bot can set multiple reactions on the same message simultaneously
- Each call to setMessageReaction replaces ALL of the bot's previous reactions on that message

## Patterns

- Acknowledgment: react with thumbs-up or checkmark to confirm receipt of a message
- Status indicator: react with hourglass while processing, then change to checkmark when done
- Feedback: react with thumbs-up/thumbs-down based on analysis or validation result
- Read receipts: react to indicate the bot has seen and processed the message
