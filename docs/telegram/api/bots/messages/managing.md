# Managing Messages

Forward, copy, delete, and pin messages.

---

## forwardMessage

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| from_chat_id | Integer or String | Yes | Source chat |
| message_id | Integer | Yes | Message identifier in source chat |
| message_thread_id | Integer | No | Target forum topic |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |
| message_effect_id | String | No | Message effect |

**Returns:** Message

---

## forwardMessages (bulk)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| from_chat_id | Integer or String | Yes | Source chat |
| message_ids | Array of Integer | Yes | Message identifiers in source chat (1-100) |
| message_thread_id | Integer | No | Target forum topic |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |

**Returns:** Array of MessageId

---

## copyMessage

Like forward but without the "Forwarded from" header.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| from_chat_id | Integer or String | Yes | Source chat |
| message_id | Integer | Yes | Message identifier in source chat |
| message_thread_id | Integer | No | Target forum topic |
| caption | String | No | New caption for media, 0-1024 characters |
| parse_mode | String | No | Caption parsing mode |
| caption_entities | Array of MessageEntity | No | Special entities in caption |
| show_caption_above_media | Boolean | No | Show caption above media |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |
| message_effect_id | String | No | Message effect |
| reply_parameters | ReplyParameters | No | Reply configuration |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** MessageId

---

## copyMessages (bulk)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| from_chat_id | Integer or String | Yes | Source chat |
| message_ids | Array of Integer | Yes | Message identifiers in source chat (1-100) |
| message_thread_id | Integer | No | Target forum topic |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |
| remove_caption | Boolean | No | Remove captions from copied messages |

**Returns:** Array of MessageId

---

## deleteMessage

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Chat identifier |
| message_id | Integer | Yes | Message to delete |

**Returns:** True

---

## deleteMessages (bulk)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Chat identifier |
| message_ids | Array of Integer | Yes | Messages to delete (1-100) |

**Returns:** True

---

## pinChatMessage

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Chat identifier |
| message_id | Integer | Yes | Message to pin |
| business_connection_id | String | No | Business connection identifier |
| disable_notification | Boolean | No | Send silently (default: notifications enabled) |

**Returns:** True

---

## unpinChatMessage

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Chat identifier |
| message_id | Integer | No | Message to unpin. If omitted, unpins most recent pinned message |
| business_connection_id | String | No | Business connection identifier |

**Returns:** True

---

## unpinAllChatMessages

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Chat identifier |

**Returns:** True

---

## Gotchas

- `deleteMessage`: bot can delete its own messages anytime; other users' messages only in groups/supergroups and only within 48 hours.
- `deleteMessages`: all messages must be from the same chat, 1-100 limit.
- `forwardMessages`/`copyMessages`: messages are forwarded/copied in the order specified, max 100.
- `copyMessage` preserves media but removes "Forwarded from" attribution.
- `pinChatMessage`: in supergroups, bot needs `can_pin_messages`; in channels, `can_edit_messages`.
