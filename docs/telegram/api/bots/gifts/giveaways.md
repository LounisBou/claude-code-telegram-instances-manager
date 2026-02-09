# Giveaways

Giveaways allow channel/group owners to distribute prizes to random subscribers.

## Types

### Giveaway

| Field | Type | Description |
|-------|------|-------------|
| chats | Array of Chat | Chats user must join to participate |
| winners_selection_date | Integer | Unix timestamp for winner selection |
| winner_count | Integer | Number of winners |
| only_new_members | Boolean | Only users who joined after start (optional) |
| has_public_winners | Boolean | Winners are publicly visible (optional) |
| prize_description | String | Additional prize text (optional) |
| country_codes | Array of String | ISO country codes for eligibility (optional) |
| prize_star_count | Integer | Telegram Stars to distribute (optional) |
| premium_subscription_month_count | Integer | Months of Premium subscription prize (optional) |

### GiveawayCreated

| Field | Type | Description |
|-------|------|-------------|
| prize_star_count | Integer | Stars being distributed (optional) |

### GiveawayWinners

| Field | Type | Description |
|-------|------|-------------|
| chat | Chat | Chat that created the giveaway |
| giveaway_message_id | Integer | Message ID of the giveaway |
| winners_selection_date | Integer | When winners were selected |
| winner_count | Integer | Total number of winners |
| winners | Array of User | List of winners (up to 100) |
| additional_chat_count | Integer | Number of other participating chats (optional) |
| prize_star_count | Integer | Stars distributed (optional) |
| premium_subscription_month_count | Integer | Months of Premium won (optional) |
| unclaimed_prize_count | Integer | Prizes not yet claimed (optional) |
| only_new_members | Boolean | Restricted to new members (optional) |
| was_refunded | Boolean | Giveaway was cancelled and refunded (optional) |
| prize_description | String | Additional prize description (optional) |

### GiveawayCompleted

| Field | Type | Description |
|-------|------|-------------|
| winner_count | Integer | Total number of winners |
| unclaimed_prize_count | Integer | Unclaimed prizes (optional) |
| giveaway_message | Message | Original giveaway message (optional) |
| is_star_giveaway | Boolean | True if Stars giveaway (optional) |

## Gotchas

- Giveaways are created by channel/group owners through the Telegram client, not via Bot API
- Bot receives giveaway events as service messages
- winners list contains up to 100 users; use winner_count for the actual total
- Prizes can be Premium subscriptions or Telegram Stars
- was_refunded in GiveawayWinners: giveaway was cancelled and payment returned
