# Chat Boosts

Track boost events for supergroups and channels.

---

## getUserChatBoosts

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| user_id | Integer | Yes | User identifier |

**Returns:** UserChatBoosts

---

## Types

### ChatBoostUpdated

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat that was boosted |
| boost | ChatBoost | Boost information |

### ChatBoostRemoved

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat where boost was removed |
| boost_id | String | Unique boost identifier |
| remove_date | Integer | Unix timestamp of removal |
| source | ChatBoostSource | Source of the removed boost |

### ChatBoost

| Field | Type | Description |
|-------|------|-------------|
| boost_id | String | Unique boost identifier |
| add_date | Integer | Unix timestamp boost was added |
| expiration_date | Integer | Unix timestamp boost will expire |
| source | ChatBoostSource | Source of the boost |

### ChatBoostSource variants

- **ChatBoostSourcePremium** (source="premium"): user (User)
- **ChatBoostSourceGiftCode** (source="gift_code"): user (User)
- **ChatBoostSourceGiveaway** (source="giveaway"): giveaway_message_id (Integer), user (User, optional), is_unclaimed (Boolean, optional)

### UserChatBoosts

| Field | Type | Description |
|-------|------|-------------|
| boosts | Array of ChatBoost | List of boosts by the user |

### ChatBoostAdded

| Field | Type | Description |
|-------|------|-------------|
| boost_count | Integer | Number of boosts added |

---

## Gotchas

- `chat_boost` and `removed_chat_boost` updates must be enabled in `allowed_updates`.
- Boosts unlock features: custom emoji, backgrounds, link previews in groups.
- Each Telegram Premium user provides 1 boost; higher Premium tiers give more.
- `unrestrict_boost_count` in ChatFullInfo: number of boosts needed to lift slow mode and chat permission restrictions.
