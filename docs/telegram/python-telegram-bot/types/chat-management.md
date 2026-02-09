# Chat Management Types

> Types for bot commands, chat permissions, membership, invite links, and forum topics.

## Overview

These types handle chat administration: defining bot commands and their visibility scopes, managing member permissions and roles, creating and revoking invite links, and organizing forum topics. They are primarily used through `Bot` methods like `set_my_commands()`, `restrict_chat_member()`, and `create_chat_invite_link()`.

## Quick Usage

```python
from telegram import BotCommand, ChatPermissions

# Define a bot command
cmd = BotCommand(command="help", description="Show help message")

# Define restrictive permissions
perms = ChatPermissions(can_send_messages=True, can_send_photos=False)
```

## Key Classes

### BotCommand and Scopes

**BotCommand** -- a bot command entry (shown in the commands menu).

| Attribute | Type | Description |
|---|---|---|
| `command` | `str` | Command text (1-32 chars, no leading `/`). |
| `description` | `str` | Description (1-256 chars). |

**BotCommandScope** subclasses (determine where commands are visible):

| Subclass | Constructor | Scope |
|---|---|---|
| `BotCommandScopeDefault()` | -- | Default, all chats |
| `BotCommandScopeAllPrivateChats()` | -- | All private chats |
| `BotCommandScopeAllGroupChats()` | -- | All group chats |
| `BotCommandScopeAllChatAdministrators()` | -- | All group admins |
| `BotCommandScopeChat(chat_id)` | `chat_id` | Specific chat |
| `BotCommandScopeChatAdministrators(chat_id)` | `chat_id` | Admins of specific chat |
| `BotCommandScopeChatMember(chat_id, user_id)` | `chat_id`, `user_id` | Specific user in specific chat |

---

### ChatPermissions

Permissions for chat members. Used in `restrict_chat_member()` and returned in `ChatFullInfo.permissions`.

| Attribute | Type |
|---|---|
| `can_send_messages` | `bool \| None` |
| `can_send_audios` | `bool \| None` |
| `can_send_documents` | `bool \| None` |
| `can_send_photos` | `bool \| None` |
| `can_send_videos` | `bool \| None` |
| `can_send_video_notes` | `bool \| None` |
| `can_send_voice_notes` | `bool \| None` |
| `can_send_polls` | `bool \| None` |
| `can_send_other_messages` | `bool \| None` |
| `can_add_web_page_previews` | `bool \| None` |
| `can_change_info` | `bool \| None` |
| `can_invite_users` | `bool \| None` |
| `can_pin_messages` | `bool \| None` |
| `can_manage_topics` | `bool \| None` |

---

### ChatMember and Subclasses

Represents a member of a chat. Abstract base with `user` and `status` attributes.

| Subclass | `status` Value | Notable Additional Attributes |
|---|---|---|
| `ChatMemberOwner` | `"creator"` | `is_anonymous`, `custom_title` |
| `ChatMemberAdministrator` | `"administrator"` | `can_be_edited`, `custom_title`, `can_manage_chat`, `can_delete_messages`, `can_manage_video_chats`, `can_restrict_members`, `can_promote_members`, `can_change_info`, `can_invite_users`, `can_post_messages`, `can_edit_messages`, `can_pin_messages`, `can_manage_topics` |
| `ChatMemberMember` | `"member"` | (no extra attributes) |
| `ChatMemberRestricted` | `"restricted"` | `is_member`, `until_date`, all `ChatPermissions` fields |
| `ChatMemberLeft` | `"left"` | (no extra attributes) |
| `ChatMemberBanned` | `"kicked"` | `until_date` |

**ChatMemberUpdated** -- sent when a chat member's status changes.

| Attribute | Type | Description |
|---|---|---|
| `chat` | `Chat` | The chat. |
| `from_user` | `User` | User who performed the action. |
| `date` | `datetime` | Date of the change. |
| `old_chat_member` | `ChatMember` | Previous status. |
| `new_chat_member` | `ChatMember` | New status. |
| `invite_link` | `ChatInviteLink \| None` | Invite link used to join. |

---

### ChatInviteLink

| Attribute | Type | Description |
|---|---|---|
| `invite_link` | `str` | The invite link URL. |
| `creator` | `User` | Link creator. |
| `creates_join_request` | `bool` | If True, users must be approved. |
| `is_primary` | `bool` | Whether this is the primary link. |
| `is_revoked` | `bool` | Whether the link has been revoked. |
| `name` | `str \| None` | Link name. |
| `expire_date` | `datetime \| None` | When the link expires. |
| `member_limit` | `int \| None` | Max number of users that can join. |

---

### ChatAdministratorRights

| Attribute | Type |
|---|---|
| `is_anonymous` | `bool` |
| `can_manage_chat` | `bool` |
| `can_delete_messages` | `bool` |
| `can_manage_video_chats` | `bool` |
| `can_restrict_members` | `bool` |
| `can_promote_members` | `bool` |
| `can_change_info` | `bool` |
| `can_invite_users` | `bool` |
| `can_post_messages` | `bool \| None` |
| `can_edit_messages` | `bool \| None` |
| `can_pin_messages` | `bool \| None` |
| `can_manage_topics` | `bool \| None` |

---

### ForumTopic

| Attribute | Type | Description |
|---|---|---|
| `message_thread_id` | `int` | Topic thread identifier. |
| `name` | `str` | Topic name. |
| `icon_color` | `int` | Color of the topic icon (RGB). |
| `icon_custom_emoji_id` | `str \| None` | Custom emoji identifier for the icon. |

## Common Patterns

### Set bot commands with scopes

```python
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats

# Commands for private chats
await bot.set_my_commands(
    [BotCommand("start", "Start the bot"),
     BotCommand("settings", "Open settings")],
    scope=BotCommandScopeAllPrivateChats(),
)

# Different commands for groups
await bot.set_my_commands(
    [BotCommand("help", "Show help"),
     BotCommand("stats", "Show group stats")],
    scope=BotCommandScopeAllGroupChats(),
)
```

### Restrict a chat member

```python
from telegram import ChatPermissions

await bot.restrict_chat_member(
    chat_id=chat_id,
    user_id=user_id,
    permissions=ChatPermissions(
        can_send_messages=True,
        can_send_photos=False,
        can_send_videos=False,
        can_send_documents=False,
    ),
)
```

## Related

- [other-types.md](other-types.md) -- callback queries, polls, web apps, menu buttons, and other interaction types
- [messages.md](messages.md) -- Update and Message types
- [../bot.md](../bot.md) -- Bot methods that accept/return these types
- [../handlers/other-handlers.md](../handlers/other-handlers.md) -- ChatMemberHandler and other handlers
