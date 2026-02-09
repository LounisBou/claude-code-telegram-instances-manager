# Message Origin Types

Describes the origin of a forwarded message. Returned in the `forward_origin` field of a Message object. The `type` field discriminates between variants.

## Types

### MessageOriginUser

The message was originally sent by a known user.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"user"` |
| date | Integer | Yes | Date the message was sent originally (Unix timestamp) |
| sender_user | User | Yes | User that sent the message originally |

### MessageOriginHiddenUser

The message was originally sent by an unknown user. This occurs when the original sender has privacy settings that hide forwarding attribution.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"hidden_user"` |
| date | Integer | Yes | Date the message was sent originally (Unix timestamp) |
| sender_user_name | String | Yes | Name of the user that sent the message originally |

### MessageOriginChat

The message was originally sent on behalf of a chat (e.g., a group or channel posting as itself).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"chat"` |
| date | Integer | Yes | Date the message was sent originally (Unix timestamp) |
| sender_chat | Chat | Yes | Chat that sent the message originally |
| author_signature | String | No | For messages originally sent by an anonymous admin, signature of the message author |

### MessageOriginChannel

The message was originally sent to a channel.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | String | Yes | Always `"channel"` |
| date | Integer | Yes | Date the message was sent originally (Unix timestamp) |
| chat | Chat | Yes | Channel chat the message was originally sent to |
| message_id | Integer | Yes | Unique message identifier inside the channel |
| author_signature | String | No | Signature of the original post author |

## Gotchas

- The `type` field is the discriminator. Always check `type` before accessing variant-specific fields.
- `MessageOriginHiddenUser` provides only a display name (`sender_user_name`), not a User object. You cannot reply to or identify the original sender programmatically.
- `MessageOriginChannel` includes a `message_id` referencing the original channel message. This ID is scoped to the channel chat, not the chat where the forward appears.
- `forward_origin` replaces the deprecated `forward_from`, `forward_from_chat`, `forward_from_message_id`, `forward_signature`, `forward_sender_name`, and `forward_date` fields.

## Patterns

- Dispatch on `forward_origin.type` to determine the variant, then access the appropriate fields.
- Use `MessageOriginChannel` to link back to the original channel post (e.g., for "view original" functionality).
- When `MessageOriginHiddenUser` is received, display the `sender_user_name` as-is since no further user data is available.
