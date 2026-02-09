# User & Chat Types

Fundamental objects representing users and chats. These types appear throughout the Telegram Bot API as return values and nested fields.

## Types

### User

Represents a Telegram user or bot.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Unique identifier for this user or bot. 64-bit integer. |
| is_bot | Boolean | Yes | `true` if this user is a bot. |
| first_name | String | Yes | User's or bot's first name. |
| last_name | String | No | User's or bot's last name. |
| username | String | No | User's or bot's username (without leading `@`). |
| language_code | String | No | IETF language tag of the user's language. |
| is_premium | Boolean | No | `true` if this user is a Telegram Premium user. |
| added_to_attachment_menu | Boolean | No | `true` if this user added the bot to their attachment menu. |
| can_join_groups | Boolean | No | `true` if the bot can be invited to groups. Returned only in `getMe`. |
| can_read_all_group_messages | Boolean | No | `true` if privacy mode is disabled for the bot. Returned only in `getMe`. |
| supports_inline_queries | Boolean | No | `true` if the bot supports inline queries. Returned only in `getMe`. |
| can_connect_to_business | Boolean | No | `true` if the bot can be connected to a Telegram Business account. Returned only in `getMe`. |
| has_main_web_app | Boolean | No | `true` if the bot has a main Web App. Returned only in `getMe`. |
| has_topics_enabled | Boolean | No | `true` if the bot has topics enabled. Returned only in `getMe`. |

### Chat

Represents a chat. This is the lightweight version returned in most contexts.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Unique identifier for this chat. 64-bit integer. |
| type | String | Yes | Type of the chat. One of: `"private"`, `"group"`, `"supergroup"`, `"channel"`. |
| title | String | No | Title of the chat (for groups, supergroups, and channels). |
| username | String | No | Username of the chat (for private chats, supergroups, and channels if available). |
| first_name | String | No | First name of the other party in a private chat. |
| last_name | String | No | Last name of the other party in a private chat. |
| is_forum | Boolean | No | `true` if the supergroup chat is a forum (has topics enabled). |
| is_direct_messages | Boolean | No | `true` if the chat is a private chat with a business account and the user is a business bot of that account. |

### ChatFullInfo

Contains full information about a chat. Returned by `getChat`. Includes all fields from Chat plus additional detail fields.

**Base fields (inherited from Chat):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | Integer | Yes | Unique identifier for this chat. 64-bit integer. |
| type | String | Yes | Type of the chat. One of: `"private"`, `"group"`, `"supergroup"`, `"channel"`. |
| title | String | No | Title of the chat (for groups, supergroups, and channels). |
| username | String | No | Username of the chat (for private chats, supergroups, and channels if available). |
| first_name | String | No | First name of the other party in a private chat. |
| last_name | String | No | Last name of the other party in a private chat. |
| is_forum | Boolean | No | `true` if the supergroup chat is a forum (has topics enabled). |
| is_direct_messages | Boolean | No | `true` if the chat is a private chat with a business account and the user is a business bot of that account. |

**Appearance fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| accent_color_id | Integer | Yes | Identifier of the accent color for the chat name and backgrounds of the chat photo, reply header, and link preview. |
| max_reaction_count | Integer | Yes | Maximum number of reactions that can be set on a message in the chat. |
| photo | ChatPhoto | No | Chat photo. |
| active_usernames | Array of String | No | List of all active chat usernames (for private chats, supergroups, and channels). |
| background_custom_emoji_id | String | No | Custom emoji identifier of the emoji chosen by the chat for the reply header and link preview background. |
| profile_accent_color_id | Integer | No | Identifier of the accent color for the chat's profile background. |
| profile_background_custom_emoji_id | String | No | Custom emoji identifier of the emoji chosen by the chat for its profile background. |
| emoji_status_custom_emoji_id | String | No | Custom emoji identifier of the chat's emoji status. |
| emoji_status_expiration_date | Integer | No | Unix timestamp when the emoji status expires. |

**Personal info fields (private chats):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| birthdate | Birthdate | No | Birthdate of the other party in a private chat. |
| personal_chat | Chat | No | The personal channel of the other party in a private chat. |
| bio | String | No | Bio of the other party in a private chat. |

**Business fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| business_intro | BusinessIntro | No | The intro of a business account in a private chat. |
| business_location | BusinessLocation | No | The location of a business account in a private chat. |
| business_opening_hours | BusinessOpeningHours | No | The opening hours of a business account in a private chat. |

**Chat configuration fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| parent_chat | Chat | No | The parent chat of the current chat (for direct messages chats of business accounts). |
| available_reactions | Array of ReactionType | No | List of available reactions allowed in the chat. If omitted, all emoji reactions are allowed. |
| description | String | No | Description of the chat (for groups, supergroups, and channels). |
| invite_link | String | No | Primary invite link of the chat. |
| pinned_message | MaybeInaccessibleMessage | No | The most recent pinned message. |
| permissions | ChatPermissions | No | Default chat permissions for members (groups and supergroups). |
| accepted_gift_types | AcceptedGiftTypes | Yes | Information about the types of gifts accepted by the chat or the user. |
| can_send_paid_media | Boolean | No | `true` if paid media messages can be sent or forwarded to the channel chat. |
| slow_mode_delay | Integer | No | Slow mode delay in seconds for the supergroup. |
| unrestrict_boost_count | Integer | No | Minimum number of boosts required to unrestrict the supergroup. |
| message_auto_delete_time | Integer | No | Time in seconds after which messages are automatically deleted. |
| sticker_set_name | String | No | Name of the group sticker set. |
| can_set_sticker_set | Boolean | No | `true` if the bot can change the group sticker set. |
| custom_emoji_sticker_set_name | String | No | Name of the group's custom emoji sticker set. |
| linked_chat_id | Integer | No | Unique identifier of the linked chat (discussion group for channels, or linked channel for supergroups). |
| location | ChatLocation | No | Location to which the supergroup is connected (for location-based supergroups). |
| paid_message_star_count | Integer | No | The number of Telegram Stars required to send a message in the chat. |

**Privacy and moderation fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| has_private_forwards | Boolean | No | `true` if privacy settings of the other party prevent forwarding their messages. |
| has_restricted_voice_and_video_messages | Boolean | No | `true` if the privacy settings of the other party restrict sending voice and video note messages. |
| join_to_send_messages | Boolean | No | `true` if users need to join the supergroup before sending messages. |
| join_by_request | Boolean | No | `true` if new join requests need admin approval. |
| has_aggressive_anti_spam_enabled | Boolean | No | `true` if aggressive anti-spam checks are enabled in the supergroup. |
| has_hidden_members | Boolean | No | `true` if non-admins can only see the member list of admins and the bot. |
| has_protected_content | Boolean | No | `true` if messages from the chat cannot be forwarded. |
| has_visible_history | Boolean | No | `true` if new members can see the full message history. |

**Additional fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rating | UserRating | No | The rating of the user. |
| unique_gift_colors | UniqueGiftColors | No | The colors available for the unique gift backdrop. |

### ChatPhoto

Represents a chat photo.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| small_file_id | String | Yes | File identifier of the small (160x160) chat photo. Can be used to download or reuse the file. |
| small_file_unique_id | String | Yes | Unique file identifier of the small chat photo. Stable across bots, cannot be used to download. |
| big_file_id | String | Yes | File identifier of the big (640x640) chat photo. Can be used to download or reuse the file. |
| big_file_unique_id | String | Yes | Unique file identifier of the big chat photo. Stable across bots, cannot be used to download. |

### ChatLocation

Represents a location to which a chat is connected (location-based supergroups).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| location | Location | Yes | The location to which the supergroup is connected. Cannot be a live location. |
| address | String | Yes | Location address. 1-64 characters, as defined by the chat owner. |

### Birthdate

Describes the birthdate of a user.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| day | Integer | Yes | Day of the user's birthday. |
| month | Integer | Yes | Month of the user's birthday. |
| year | Integer | No | Year of the user's birthday. |

---

## Gotchas

- **64-bit IDs**: Chat and User `id` fields can exceed 32-bit integer range (2,147,483,647). Always use 64-bit integers (int64, long, BigInt) in your implementation. This is the most common source of bugs in new bot implementations.
- **`getMe`-only fields**: Several User fields (`can_join_groups`, `can_read_all_group_messages`, `supports_inline_queries`, `can_connect_to_business`, `has_main_web_app`, `has_topics_enabled`) are only returned when calling the `getMe` method. They will not appear in User objects received from updates.
- **ChatFullInfo vs Chat**: Most API responses return the lightweight `Chat` object. Only `getChat` returns `ChatFullInfo` with the complete set of fields. Do not expect fields like `bio`, `description`, `permissions`, or `pinned_message` on regular Chat objects.
- **file_id vs file_unique_id**: On ChatPhoto (and all file objects), `file_id` can be used to download or resend the file but is bot-specific and may change. `file_unique_id` is stable across bots but cannot be used to download files. Use `file_unique_id` for deduplication.
