# Business Features

Handle connections to Telegram Business accounts, allowing bots to manage messages on behalf of business users.

## Types

### BusinessConnection

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique connection identifier |
| user | User | Business account owner |
| user_chat_id | Integer | Identifier of the private chat with the business user |
| date | Integer | Unix timestamp of connection |
| can_reply | Boolean | Whether bot can send messages to the business chat |
| is_enabled | Boolean | Whether connection is active |

### BusinessIntro

| Field | Type | Description |
|-------|------|-------------|
| title | String | Title of the business intro (optional) |
| message | String | Message of the business intro (optional) |
| sticker | Sticker | Sticker of the business intro (optional) |

### BusinessLocation

| Field | Type | Description |
|-------|------|-------------|
| address | String | Business address |
| location | Location | Business geographic location (optional) |

### BusinessOpeningHours

| Field | Type | Description |
|-------|------|-------------|
| time_zone_name | String | IANA time zone identifier |
| opening_hours | Array of BusinessOpeningHoursInterval | List of opening periods |

### BusinessOpeningHoursInterval

| Field | Type | Description |
|-------|------|-------------|
| opening_minute | Integer | Start time as minutes from midnight (0-7*24*60) |
| closing_minute | Integer | End time as minutes from midnight (0-8*24*60) |

### BusinessMessagesDeleted

| Field | Type | Description |
|-------|------|-------------|
| business_connection_id | String | Connection identifier |
| chat | Chat | Chat in the business account |
| message_ids | Array of Integer | Identifiers of deleted messages |

## Gotchas

- business_connection update: received when a user connects/disconnects their business account
- business_message / edited_business_message: messages from the business account's chats
- Use business_connection_id parameter in send methods to send messages on behalf of the business
- Bot can only reply if can_reply is true in the BusinessConnection
- opening_minute/closing_minute: span across days. E.g., Monday 9:00 = 0*24*60+9*60 = 540, Tuesday 18:00 = 1*24*60+18*60 = 2520
