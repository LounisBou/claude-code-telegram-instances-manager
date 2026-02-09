# Contact & Dice

## sendContact

Send a phone contact.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| phone_number | String | Yes | Contact's phone number |
| first_name | String | Yes | Contact's first name |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| last_name | String | No | Contact's last name |
| vcard | String | No | Additional vCard data, 0-2048 bytes |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## sendDice

Send an animated emoji that displays a random value.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| emoji | String | No | Emoji on which the dice throw animation is based (see table below; default: dice) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

**Valid emoji values:**

| Emoji | Animation | Value Range |
|-------|-----------|-------------|
| (dice) | Dice | 1-6 |
| (darts) | Darts | 1-6 |
| (basketball) | Basketball | 1-5 |
| (soccer) | Soccer/Football | 1-5 |
| (bowling) | Bowling | 1-6 |
| (slot machine) | Slot Machine | 1-64 |

---

## Types

### Contact

Represents a phone contact.

| Field | Type | Description |
|-------|------|-------------|
| phone_number | String | Contact's phone number |
| first_name | String | Contact's first name |
| last_name | String | Optional. Contact's last name |
| user_id | Integer | Optional. Contact's user identifier in Telegram |
| vcard | String | Optional. Additional vCard data |

### Dice

Represents an animated emoji that displays a random value.

| Field | Type | Description |
|-------|------|-------------|
| emoji | String | Emoji on which the dice throw animation is based |
| value | Integer | Value of the dice (see sendDice emoji table for ranges) |

---

## Gotchas

- `sendDice`: the value is random and determined by Telegram servers -- the bot cannot control the result.
