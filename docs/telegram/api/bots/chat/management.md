# Chat Management

Get information about chats and modify their settings.

---

## getChat

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat identifier or @username |

**Returns:** ChatFullInfo

---

## getChatAdministrators

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |

**Returns:** Array of ChatMember (guaranteed not to contain bots except the bot itself)

---

## getChatMemberCount

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |

**Returns:** Integer

---

## getChatMember

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | Target user |

**Returns:** ChatMember

---

## setChatTitle

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| title | String | Yes | New title (1-128 characters) |

**Returns:** True

---

## setChatDescription

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| description | String | No | New description (0-255 chars). Pass empty string to remove. |

**Returns:** True

---

## setChatPhoto

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| photo | InputFile | Yes | New photo (must be uploaded, no file_id or URL) |

**Returns:** True

---

## deleteChatPhoto

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |

**Returns:** True

---

## setChatPermissions

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| permissions | ChatPermissions | Yes | New default member permissions |
| use_independent_chat_permissions | Boolean | No | Set each permission independently |

**Returns:** True

---

## setChatStickerSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| sticker_set_name | String | Yes | Name of the sticker set |

**Returns:** True

---

## deleteChatStickerSet

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |

**Returns:** True

---

## leaveChat

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |

**Returns:** True

---

## exportChatInviteLink

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |

**Returns:** String (the new invite link; revokes the previous primary link)

---

## createChatInviteLink

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| name | String | No | Link name (0-32 chars) |
| expire_date | Integer | No | Unix timestamp when link expires |
| member_limit | Integer | No | Max users (1-99999) |
| creates_join_request | Boolean | No | Require admin approval |

**Returns:** ChatInviteLink

---

## editChatInviteLink

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| invite_link | String | Yes | The invite link to edit |
| name | String | No | Link name (0-32 chars) |
| expire_date | Integer | No | Unix timestamp when link expires |
| member_limit | Integer | No | Max users (1-99999) |
| creates_join_request | Boolean | No | Require admin approval |

**Returns:** ChatInviteLink

---

## revokeChatInviteLink

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| invite_link | String | Yes | The invite link to revoke |

**Returns:** ChatInviteLink (revoked)

---

## approveChatJoinRequest

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User to approve |

**Returns:** True

---

## declineChatJoinRequest

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User to decline |

**Returns:** True

---

## Types

### ChatPermissions

| Field | Type | Description |
|-------|------|-------------|
| can_send_messages | Boolean | Can send text messages, contacts, invoices, locations, venues (optional) |
| can_send_audios | Boolean | Can send audios (optional) |
| can_send_documents | Boolean | Can send documents (optional) |
| can_send_photos | Boolean | Can send photos (optional) |
| can_send_videos | Boolean | Can send videos (optional) |
| can_send_video_notes | Boolean | Can send video notes (optional) |
| can_send_voice_notes | Boolean | Can send voice notes (optional) |
| can_send_polls | Boolean | Can send polls (optional) |
| can_send_other_messages | Boolean | Can send stickers, GIFs, games, inline bot results (optional) |
| can_add_web_page_previews | Boolean | Can add link previews (optional) |
| can_change_info | Boolean | Can change chat title, photo, etc. (optional) |
| can_invite_users | Boolean | Can invite users (optional) |
| can_pin_messages | Boolean | Can pin messages (optional) |
| can_manage_topics | Boolean | Can manage forum topics (optional) |

### ChatInviteLink

| Field | Type | Description |
|-------|------|-------------|
| invite_link | String | The invite link |
| creator | User | Creator of the link |
| creates_join_request | Boolean | True if users joining via link need admin approval |
| is_primary | Boolean | True if the link is primary |
| is_revoked | Boolean | True if the link is revoked |
| name | String | Link name (optional) |
| expire_date | Integer | Unix timestamp when link expires (optional) |
| member_limit | Integer | Maximum number of users that can join (optional) |
| pending_join_request_count | Integer | Number of pending join requests (optional) |
| subscription_period | Integer | Subscription period in seconds (optional) |
| subscription_price | Integer | Subscription price in Telegram Stars (optional) |

### ChatJoinRequest

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat the request was sent to |
| from | User | User that sent the join request |
| user_chat_id | Integer | Identifier of the user's private chat |
| date | Integer | Unix timestamp of the request |
| bio | String | User's bio (optional) |
| invite_link | ChatInviteLink | Invite link used to send the request (optional) |

---

## Gotchas

- `exportChatInviteLink` revokes the current primary link. Use `createChatInviteLink` for additional links.
- `setChatPermissions` with `use_independent_chat_permissions=false`: media permissions are grouped. With `true`: each permission is independent.
- Bot must be admin with appropriate rights for most methods.
- `member_limit` and `creates_join_request` are mutually exclusive in invite links.
- `setChatPhoto`: the photo must be uploaded via multipart/form-data; file_id and URL are not accepted.
