# Gifts

Send virtual gifts to users and retrieve gift lists.

## Methods

### sendGift

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | Recipient user identifier |
| gift_id | String | Yes | Gift identifier to send |
| text | String | No | Accompanying text message (0-255 chars) |
| text_parse_mode | String | No | Text formatting mode |
| text_entities | Array of MessageEntity | No | Text entities |
| pay_for_upgrade | Boolean | No | Pay to upgrade gift to unique |

**Returns:** True

### getUserGifts

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | Target user identifier |
| offset | String | No | Offset for pagination |
| limit | Integer | No | Max gifts to return (1-100, default 100) |

**Returns:** UserGifts

### getChatGifts

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat identifier |
| offset | String | No | Offset for pagination |
| limit | Integer | No | Max gifts to return (1-100, default 100) |

**Returns:** ChatGifts

### getAvailableGifts

No parameters. Returns Gifts (list of available gifts to send).

## Types

### Gift

| Field | Type | Description |
|-------|------|-------------|
| id | String | Gift unique identifier |
| sticker | Sticker | Visual representation of the gift |
| star_count | Integer | Price in Telegram Stars |
| total_count | Integer | Total number of this gift available (optional) |
| remaining_count | Integer | Remaining available (optional) |

### GiftInfo

| Field | Type | Description |
|-------|------|-------------|
| gift | Gift | The gift object |
| owned_gift_id | String | Unique identifier of the owned gift (optional) |
| sender_user | User | User who sent the gift (optional) |
| send_date | Integer | Unix timestamp when gift was sent (optional) |
| text | String | Accompanying text (optional) |
| text_entities | Array of MessageEntity | Text entities (optional) |
| is_private | Boolean | True if sender chose to be anonymous (optional) |
| is_saved | Boolean | True if gift is saved to profile (optional) |
| can_be_upgraded | Boolean | True if can be upgraded to unique (optional) |
| was_refunded | Boolean | True if Stars were refunded (optional) |
| convert_star_count | Integer | Stars received if gift is sold (optional) |
| prepaid_upgrade_star_count | Integer | Stars paid to upgrade (optional) |
| upgrade_star_count | Integer | Cost to upgrade to unique (optional) |

### UniqueGift

| Field | Type | Description |
|-------|------|-------------|
| base_name | String | Base name of the gift |
| name | String | Unique name of the gift |
| number | Integer | Serial number |
| model | UniqueGiftModel | Model of the gift |
| symbol | UniqueGiftSymbol | Symbol of the gift |
| backdrop | UniqueGiftBackdrop | Backdrop of the gift |

### OwnedGiftRegular / OwnedGiftUnique

Variants for gifts the user owns. Regular includes gift, sender_user, send_date, text fields. Unique includes gift details plus trading information.

### AcceptedGiftTypes

| Field | Type | Description |
|-------|------|-------------|
| unlimited_gifts | Boolean | Accepts unlimited gifts |
| limited_gifts | Boolean | Accepts limited gifts |
| unique_gifts | Boolean | Accepts unique gifts |
| premium_subscription | Boolean | Accepts premium subscription gifts |

## Gotchas

- Gifts cost Telegram Stars to send
- Limited edition gifts have total_count and remaining_count
- Unique gifts: upgraded versions of regular gifts with serial numbers
- Gift appears as a service message in the chat (gift field in Message)
- getUserGifts: returns gifts visible on user's profile (user may hide some)
