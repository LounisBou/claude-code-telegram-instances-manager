# Stories

Repost stories from users.

## Methods

### repostStory

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat to repost in |
| from_chat_id | Integer or String | Yes | Identifier of the chat that originally posted the story |
| story_id | Integer | Yes | Identifier of the story to repost |

**Returns:** Story

## Types

### Story

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat that posted the story |
| id | Integer | Unique story identifier |

## Gotchas

- repostStory: reposts a story to a channel chat
- Story content is not accessible via Bot API -- only metadata
- Stories appear as service messages in some contexts
