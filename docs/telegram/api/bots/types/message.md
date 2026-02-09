# Message Types

The Message object and related types. Message is the largest type in the API with 80+ optional fields.

## Types

### Message

Represents a message. Only fields relevant to the specific message type are populated; all others are omitted.

#### Identifiers and Metadata

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | Integer | Yes | Unique message identifier inside this chat. |
| message_thread_id | Integer | No | Unique identifier of a message thread (forum topic) the message belongs to. |
| direct_messages_topic | Boolean | No | `true` if the message is sent to the direct messages topic of a business account. |
| from | User | No | Sender of the message. Empty for messages sent to channels or for anonymous group admin messages. |
| sender_chat | Chat | No | Sender of the message when sent on behalf of a chat (e.g., channel post, anonymous group admin, or auto-forward from linked channel). |
| sender_boost_count | Integer | No | Number of boosts added by the sender of the message in a supergroup. |
| sender_business_bot | User | No | The bot that actually sent the message on behalf of the business account. |
| date | Integer | Yes | Date the message was sent (Unix timestamp). |
| business_connection_id | String | No | Unique identifier of the business connection from which the message was received. |
| chat | Chat | Yes | Chat the message belongs to. |
| is_topic_message | Boolean | No | `true` if the message was sent in a forum topic. |
| is_automatic_forward | Boolean | No | `true` if the message is an automatic forward from a linked channel to its discussion group. |
| is_from_offline | Boolean | No | `true` if the message was sent by an implicit action (e.g., a scheduled message or a forwarded message sent while the user was offline). |

#### Reply Information

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| forward_origin | MessageOrigin | No | Information about the original message for forwarded messages. |
| reply_to_message | Message | No | The original message for replies. Note: this field may itself be a reply, but the nested `reply_to_message` will not be set (max depth of 1). |
| external_reply | ExternalReplyInfo | No | Information about the message being replied to, when the reply is to a message from a different chat or forum topic. |
| quote | TextQuote | No | The quoted portion of a message that is replied to. |
| reply_to_story | Story | No | The story being replied to. |
| reply_to_checklist_task_id | Integer | No | Identifier of the checklist task the message replies to. |

#### Processing

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| via_bot | User | No | Bot through which the message was sent (inline mode). |
| edit_date | Integer | No | Date the message was last edited (Unix timestamp). |
| has_protected_content | Boolean | No | `true` if the message cannot be forwarded. |
| media_group_id | String | No | Unique identifier of a media message group (album). |
| author_signature | String | No | Signature of the post author (for messages in channels, or for anonymous group admin messages). |
| effect_id | String | No | Unique identifier of the message effect added to the message. |

#### Text and Formatting

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| text | String | No | The actual UTF-8 text of the message (for text messages). 0-4096 characters. |
| entities | Array of MessageEntity | No | Special entities in the text (usernames, URLs, bold, etc.). |
| link_preview_options | LinkPreviewOptions | No | Options used for link preview generation for the message. |
| caption | String | No | Caption for media messages. 0-1024 characters. |
| caption_entities | Array of MessageEntity | No | Special entities in the caption. |
| show_caption_above_media | Boolean | No | `true` if the caption is shown above the media. |

#### Media Content

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| animation | Animation | No | The message is an animation (GIF or H.264/MPEG-4 AVC video without sound). |
| audio | Audio | No | The message is an audio file. |
| document | Document | No | The message is a general file. |
| paid_media | PaidMediaInfo | No | The message contains paid media. |
| photo | Array of PhotoSize | No | The message is a photo. Array of available sizes. |
| sticker | Sticker | No | The message is a sticker. |
| story | Story | No | The message is a forwarded story. |
| video | Video | No | The message is a video. |
| video_note | VideoNote | No | The message is a video note (round video). |
| voice | Voice | No | The message is a voice message. |
| has_media_spoiler | Boolean | No | `true` if the media is covered by a spoiler animation. |
| paid_star_count | Integer | No | The number of Telegram Stars paid for the media. |

#### Structured Content

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| checklist | Checklist | No | The message is a checklist. |
| contact | Contact | No | The message is a shared contact. |
| dice | Dice | No | The message is a dice with a random value. |
| game | Game | No | The message is a game. |
| poll | Poll | No | The message is a native poll. |
| venue | Venue | No | The message is a venue. |
| location | Location | No | The message is a shared location (live or static). |

#### Service Messages: Chat Events

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| new_chat_members | Array of User | No | New members added to the group or supergroup. |
| left_chat_member | User | No | A member was removed from the group. |
| new_chat_title | String | No | The chat title was changed. |
| new_chat_photo | Array of PhotoSize | No | The chat photo was changed. |
| delete_chat_photo | Boolean | No | `true` if the chat photo was deleted. |
| group_chat_created | Boolean | No | `true` if the group was created. |
| supergroup_chat_created | Boolean | No | `true` if the supergroup was created. |
| channel_chat_created | Boolean | No | `true` if the channel was created. |
| message_auto_delete_timer_changed | MessageAutoDeleteTimerChanged | No | Auto-delete timer settings changed. |
| migrate_to_chat_id | Integer | No | The group was migrated to a supergroup with this identifier. |
| migrate_from_chat_id | Integer | No | The supergroup was migrated from a group with this identifier. |
| pinned_message | MaybeInaccessibleMessage | No | A message was pinned. |
| chat_background_set | ChatBackground | No | The chat background was set. |

#### Service Messages: Forum Topics

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| forum_topic_created | ForumTopicCreated | No | A forum topic was created. |
| forum_topic_edited | ForumTopicEdited | No | A forum topic was edited. |
| forum_topic_closed | ForumTopicClosed | No | A forum topic was closed. |
| forum_topic_reopened | ForumTopicReopened | No | A forum topic was reopened. |
| general_forum_topic_hidden | GeneralForumTopicHidden | No | The "General" topic was hidden. |
| general_forum_topic_unhidden | GeneralForumTopicUnhidden | No | The "General" topic was unhidden. |

#### Service Messages: Boosts and Giveaways

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| boost_added | ChatBoostAdded | No | A user boosted the chat. |
| giveaway_created | GiveawayCreated | No | A scheduled giveaway was created. |
| giveaway | Giveaway | No | The message is a scheduled giveaway. |
| giveaway_winners | GiveawayWinners | No | A giveaway with public winners was completed. |
| giveaway_completed | GiveawayCompleted | No | A giveaway without public winners was completed. |

#### Service Messages: Video Chat

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| video_chat_scheduled | VideoChatScheduled | No | A video chat is scheduled. |
| video_chat_started | VideoChatStarted | No | A video chat started. |
| video_chat_ended | VideoChatEnded | No | A video chat ended. |
| video_chat_participants_invited | VideoChatParticipantsInvited | No | New members were invited to a video chat. |

#### Service Messages: Other

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| web_app_data | WebAppData | No | Data sent by a Web App. |
| write_access_allowed | WriteAccessAllowed | No | The user allowed the bot to write messages. |
| proximity_alert_triggered | ProximityAlertTriggered | No | A user in a live location share triggered a proximity alert. |
| connected_website | String | No | The domain name of the website the user logged in to using Telegram Login. |

#### Payments and Sharing

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| invoice | Invoice | No | The message is an invoice for a payment. |
| successful_payment | SuccessfulPayment | No | A payment was completed successfully. |
| refunded_payment | RefundedPayment | No | A payment was refunded. |
| users_shared | UsersShared | No | Users were shared with the bot. |
| chat_shared | ChatShared | No | A chat was shared with the bot. |
| gift | Gift | No | A gift was sent or received. |
| unique_gift | UniqueGift | No | A unique gift was sent or received. |

#### UI

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| reply_markup | InlineKeyboardMarkup | No | Inline keyboard attached to the message. |

### MessageId

Represents a unique message identifier.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message_id | Integer | Yes | Unique message identifier. |

### InaccessibleMessage

Describes a message that was deleted or is otherwise inaccessible to the bot.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| chat | Chat | Yes | Chat the message originally belonged to. |
| message_id | Integer | Yes | Unique message identifier inside the chat. |
| date | Integer | Yes | Always `0`. Indicates the message is inaccessible. |

### MaybeInaccessibleMessage

Union type. Either a Message or an InaccessibleMessage. Discriminate by checking the `date` field: if `date` is `0`, it is an InaccessibleMessage; otherwise it is a Message.

---

## Gotchas

- **Message field sparsity**: The Message object has 80+ optional fields, but only a handful are populated for any given message. A text message will have `text` and `entities` but not `photo`, `video`, etc. Always check for field presence before access.
- **MaybeInaccessibleMessage discrimination**: When you receive a `MaybeInaccessibleMessage` (e.g., in `pinned_message` or `reply_to_message`), check the `date` field first. If `date == 0`, the message is inaccessible and only `chat` and `message_id` are available.
- **`from` field absence**: The `from` field is empty for messages sent to channels and for anonymous group admin messages. Use `sender_chat` in those cases.
- **`reply_to_message` depth limit**: The `reply_to_message` field nests at most one level. If message A replies to message B which replies to message C, then A's `reply_to_message` is B, but B's `reply_to_message` will not be set.
- **Chat type migration**: When a group migrates to a supergroup, `migrate_to_chat_id` and `migrate_from_chat_id` service messages are sent. The bot must update its stored chat ID. The old group ID becomes permanently invalid.

## Patterns

- Determine message content type by checking which content field is present: `text` for text messages, `photo` for photos, `document` for files, etc. Only one content type field is present per message (except `caption` which accompanies media).
- Use `sender_chat` for attribution when `from` is absent (channel posts, anonymous admins).
- For forwarded messages, read `forward_origin` to determine the original source. See [message-origin.md](message-origin.md) for the variant types.
- When handling `MaybeInaccessibleMessage`, branch on `date == 0` to decide whether full message data is available.
