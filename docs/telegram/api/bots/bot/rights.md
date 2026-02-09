# Bot Default Administrator Rights

Configure default admin permissions requested when bot is added to groups or channels.

---

## setMyDefaultAdministratorRights

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| rights | ChatAdministratorRights | No | New default rights. Pass nothing to clear. |
| for_channels | Boolean | No | True for channel defaults, false for groups |

**Returns:** True

---

## getMyDefaultAdministratorRights

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| for_channels | Boolean | No | True for channel defaults, false for groups |

**Returns:** ChatAdministratorRights

---

## Types

### ChatAdministratorRights

| Field | Type | Description |
|-------|------|-------------|
| is_anonymous | Boolean | True if admin is anonymous |
| can_manage_chat | Boolean | Can access event log, stats, members, etc. |
| can_delete_messages | Boolean | Can delete any message |
| can_manage_video_chats | Boolean | Can manage video chats |
| can_restrict_members | Boolean | Can restrict/ban members |
| can_promote_members | Boolean | Can promote other admins |
| can_change_info | Boolean | Can change chat info |
| can_invite_users | Boolean | Can invite users |
| can_post_stories | Boolean | Can post stories (channels) |
| can_edit_stories | Boolean | Can edit stories (channels) |
| can_delete_stories | Boolean | Can delete stories (channels) |
| can_post_messages | Boolean | Can post in channel (optional, channels only) |
| can_edit_messages | Boolean | Can edit other messages (optional, channels only) |
| can_pin_messages | Boolean | Can pin messages (optional, groups only) |
| can_manage_topics | Boolean | Can manage forum topics (optional, groups only) |
| can_manage_direct_messages | Boolean | Can manage direct messages (optional) |

---

## Gotchas

- These are DEFAULT rights -- the user adding the bot can still modify them.
- Set separate defaults for groups vs channels using `for_channels` parameter.
- Bot can only grant permissions it was given by the chat owner.
- Rights set here appear in the "Add to Group/Channel" dialog.
- Clearing rights (passing no `rights` parameter) resets to no special permissions requested.
