# Chat Members

Ban, unban, restrict, and promote users in groups and channels.

---

## banChatMember

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User to ban |
| until_date | Integer | No | Unix timestamp when ban is lifted. If <=60s from now or >366 days, treated as permanent. |
| revoke_messages | Boolean | No | Delete all messages from user |

**Returns:** True

---

## unbanChatMember

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User to unban |
| only_if_banned | Boolean | No | Only unban if currently banned (otherwise acts like admin removing member) |

**Returns:** True

---

## restrictChatMember

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User to restrict |
| permissions | ChatPermissions | Yes | New permissions |
| use_independent_chat_permissions | Boolean | No | Set each permission independently |
| until_date | Integer | No | Unix timestamp when restrictions are lifted |

**Returns:** True

---

## promoteChatMember

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User to promote |
| is_anonymous | Boolean | No | Admin is anonymous |
| can_manage_chat | Boolean | No | Can access chat event log, stats, members, etc. |
| can_delete_messages | Boolean | No | Can delete any message |
| can_manage_video_chats | Boolean | No | Can manage video chats |
| can_restrict_members | Boolean | No | Can restrict/ban members |
| can_promote_members | Boolean | No | Can promote other admins |
| can_change_info | Boolean | No | Can change chat info |
| can_invite_users | Boolean | No | Can invite users |
| can_post_stories | Boolean | No | Can post stories (channels) |
| can_edit_stories | Boolean | No | Can edit stories (channels) |
| can_delete_stories | Boolean | No | Can delete stories (channels) |
| can_post_messages | Boolean | No | Can post in channel |
| can_edit_messages | Boolean | No | Can edit other messages in channel |
| can_pin_messages | Boolean | No | Can pin messages |
| can_manage_topics | Boolean | No | Can manage forum topics |
| can_manage_direct_messages | Boolean | No | Can manage direct messages |

**Returns:** True

---

## setChatAdministratorCustomTitle

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | Target administrator |
| custom_title | String | Yes | New custom title (0-16 chars, emoji not allowed) |

**Returns:** True

---

## banChatSenderChat

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| sender_chat_id | Integer | Yes | Channel chat to ban |

**Returns:** True

---

## unbanChatSenderChat

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| sender_chat_id | Integer | Yes | Channel chat to unban |

**Returns:** True

---

## Types

### ChatMember variants

- **ChatMemberOwner** (status="creator"): user, is_anonymous, custom_title (optional)
- **ChatMemberAdministrator** (status="administrator"): user, can_be_edited, is_anonymous, + all permission booleans, custom_title (optional)
- **ChatMemberMember** (status="member"): user, until_date (optional)
- **ChatMemberRestricted** (status="restricted"): user, is_member, + all permission booleans, until_date
- **ChatMemberLeft** (status="left"): user
- **ChatMemberBanned** (status="kicked"): user, until_date

### ChatMemberUpdated

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat the user belongs to |
| from | User | Performer of the action |
| date | Integer | Unix timestamp of the change |
| old_chat_member | ChatMember | Previous member information |
| new_chat_member | ChatMember | New member information |
| invite_link | ChatInviteLink | Invite link used to join (optional) |
| via_chat_folder_invite_link | Boolean | True if joined via chat folder invite link (optional) |

---

## Gotchas

- `banChatMember`: in supergroups, the user must be a member. In basic groups, only works if the group has been upgraded to supergroup.
- `unbanChatMember`: without `only_if_banned=true`, this acts as an admin removing a user who was added via invite link.
- `until_date`: values <=60 seconds from now or >366 days are treated as permanent.
- `promoteChatMember`: all permission flags default to `false`. Set individual flags to `true`.
- Bot can only promote users with permissions it has itself.
- `ChatMemberUpdated`: delivered via `my_chat_member` (bot's own status) or `chat_member` (other members) updates.
- `banChatSenderChat`/`unbanChatSenderChat`: for banning/unbanning channel identities in supergroups.
