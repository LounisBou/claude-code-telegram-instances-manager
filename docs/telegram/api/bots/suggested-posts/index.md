# Suggested Posts

Approve or decline suggested posts in business channels.

## Methods

### approveSuggestedPost

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| business_connection_id | String | Yes | Identifier of the business connection |
| message_id | Integer | Yes | Identifier of the suggested post message |

**Returns:** True

### declineSuggestedPost

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| business_connection_id | String | Yes | Identifier of the business connection |
| message_id | Integer | Yes | Identifier of the suggested post message |
| decline_reason | String | No | Reason for declining |

**Returns:** True

## Types

### SuggestedPostInfo (in Message)

| Field | Type | Description |
|-------|------|-------------|
| suggest_date | Integer | Suggested publish date (Unix timestamp) |
| suggest_star_count | Integer | Stars offered for the post |

## Service Message Types

- **SuggestedPostApproved**: suggested post was approved
- **SuggestedPostApprovalFailed**: approval failed (e.g., channel deleted)
- **SuggestedPostDeclined**: suggested post was declined
- **SuggestedPostPaid**: payment for suggested post received
- **SuggestedPostRefunded**: payment for suggested post refunded

## Gotchas

- Suggested posts are part of the Business features -- require business_connection_id
- Bot must be connected to the business account to manage suggested posts
- Suggested posts appear with suggested_post_info field in the Message object
- decline_reason: optional but recommended for user experience
