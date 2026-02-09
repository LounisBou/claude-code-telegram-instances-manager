# Polling (getUpdates)

## getUpdates

Receives incoming updates using long polling. Returns Array of Update.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| offset | Integer | No | Identifier of the first update to return. Must be greater by one than the highest update_id previously received. Negative offset counts from the end. |
| limit | Integer | No | Max number of updates to retrieve (1-100, default 100) |
| timeout | Integer | No | Timeout in seconds for long polling (0 = short polling, recommended: 30+) |
| allowed_updates | Array of String | No | List of update types to receive. Specify empty list to receive all except chat_member. |

**Returns:** Array of Update

---

## Update Type

Each Update contains exactly one of the optional fields below, plus the required `update_id`.

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| update_id | Integer | Yes | Unique identifier for this update. Monotonically increasing. |
| message | Message | No | New incoming message of any kind (text, photo, sticker, etc.) |
| edited_message | Message | No | A message that was edited by the user |
| channel_post | Message | No | New incoming channel post of any kind |
| edited_channel_post | Message | No | A channel post that was edited |
| business_connection | BusinessConnection | No | The bot was connected to or disconnected from a business account |
| business_message | Message | No | New message from a connected business account |
| edited_business_message | Message | No | Edited message from a connected business account |
| deleted_business_messages | BusinessMessagesDeleted | No | Messages deleted from a connected business account |
| message_reaction | MessageReactionUpdated | No | A reaction to a message was changed by a user |
| message_reaction_count | MessageReactionCountUpdated | No | Reactions to a message with anonymous reactions were changed |
| inline_query | InlineQuery | No | New incoming inline query |
| chosen_inline_result | ChosenInlineResult | No | Result of an inline query chosen by user and sent to chat partner |
| callback_query | CallbackQuery | No | New incoming callback query (from inline keyboard button) |
| shipping_query | ShippingQuery | No | New incoming shipping query (payments) |
| pre_checkout_query | PreCheckoutQuery | No | New incoming pre-checkout query (payments, must answer within 10 seconds) |
| purchased_paid_media | PaidMediaPurchased | No | A user purchased paid media with a non-empty payload |
| poll | Poll | No | New poll state (bots receive updates only for stopped polls and polls sent by the bot) |
| poll_answer | PollAnswer | No | A user changed their answer in a non-anonymous poll |
| my_chat_member | ChatMemberUpdated | No | The bot's own chat member status was updated |
| chat_member | ChatMemberUpdated | No | A chat member's status was updated (requires explicit opt-in via allowed_updates) |
| chat_join_request | ChatJoinRequest | No | A request to join a chat has been sent |
| chat_boost | ChatBoostUpdated | No | A chat boost was added or changed |
| removed_chat_boost | ChatBoostRemoved | No | A chat boost was removed |

---

## Gotchas

- Only ONE of the optional fields will be present in any given Update object.
- After processing updates, set `offset = update_id + 1` to acknowledge receipt. Unacknowledged updates will be re-delivered.
- If `timeout > 0`, this is long polling -- the connection stays open until an update arrives or the timeout expires.
- Cannot use getUpdates while a webhook is active. Call deleteWebhook first.
- `allowed_updates`: if not specified, the previous setting is used. The default receives all update types except `chat_member`.
