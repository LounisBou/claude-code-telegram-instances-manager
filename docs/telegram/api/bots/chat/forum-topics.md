# Forum Topics

Manage topics in forum-enabled supergroups and private chats.

---

## createForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup identifier |
| name | String | Yes | Topic name (1-128 chars) |
| icon_color | Integer | No | RGB color for topic icon |
| icon_custom_emoji_id | String | No | Custom emoji for topic icon |

**Returns:** ForumTopic

---

## editForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |
| message_thread_id | Integer | Yes | Topic identifier |
| name | String | No | New name (1-128 chars) |
| icon_custom_emoji_id | String | No | New icon. Pass empty string to remove. |

**Returns:** True

---

## closeForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |
| message_thread_id | Integer | Yes | Topic identifier |

**Returns:** True

---

## reopenForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |
| message_thread_id | Integer | Yes | Topic identifier |

**Returns:** True

---

## deleteForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |
| message_thread_id | Integer | Yes | Topic identifier |

**Returns:** True

---

## unpinAllForumTopicMessages

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |
| message_thread_id | Integer | Yes | Topic identifier |

**Returns:** True

---

## editGeneralForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |
| name | String | Yes | New name for the General topic (1-128 chars) |

**Returns:** True

---

## closeGeneralForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |

**Returns:** True

---

## reopenGeneralForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |

**Returns:** True

---

## hideGeneralForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |

**Returns:** True

---

## unhideGeneralForumTopic

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Forum supergroup |

**Returns:** True

---

## getForumTopicIconStickers

No parameters.

**Returns:** Array of Sticker (available custom emoji for topic icons)

---

## Types

### ForumTopic

| Field | Type | Description |
|-------|------|-------------|
| message_thread_id | Integer | Topic identifier |
| name | String | Topic name |
| icon_color | Integer | RGB color of topic icon |
| icon_custom_emoji_id | String | Custom emoji identifier (optional) |

### ForumTopicCreated

| Field | Type | Description |
|-------|------|-------------|
| name | String | Topic name |
| icon_color | Integer | RGB color of topic icon |
| icon_custom_emoji_id | String | Custom emoji identifier (optional) |

### ForumTopicEdited

| Field | Type | Description |
|-------|------|-------------|
| name | String | New topic name (optional) |
| icon_custom_emoji_id | String | New custom emoji identifier (optional) |

### ForumTopicClosed

No fields. Service message indicating the topic was closed.

### ForumTopicReopened

No fields. Service message indicating the topic was reopened.

---

## Gotchas

- `message_thread_id` is used to send messages to a specific topic (via the `message_thread_id` parameter in send methods).
- General topic: the default topic. Can be hidden/unhidden, closed/reopened, renamed.
- `icon_color`: limited to specific RGB values (Telegram predefined set).
- `deleteForumTopic`: deletes the topic AND all its messages.
- Private chats: forum topics are supported in private chats (Bot API 9.3+).
- Bot needs `can_manage_topics` permission.
- `editForumTopic`: at least one of `name` or `icon_custom_emoji_id` must be provided.
