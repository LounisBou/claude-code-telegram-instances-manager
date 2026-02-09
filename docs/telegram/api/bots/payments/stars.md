# Telegram Stars

Telegram's digital currency for in-app purchases, tipping, and premium content.

## Methods

### getMyStarBalance

No parameters.

**Returns:** StarAmount

### getStarTransactions

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| offset | Integer | No | Number of transactions to skip |
| limit | Integer | No | Number of transactions to return (1-100, default 100) |

**Returns:** StarTransactions

### refundStarPayment

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| user_id | Integer | Yes | User who made the payment |
| telegram_payment_charge_id | String | Yes | Telegram payment identifier |

**Returns:** True

## Types

### StarAmount

| Field | Type | Description |
|-------|------|-------------|
| amount | Integer | Number of Telegram Stars |
| nanostar_amount | Integer | Number of 1/1000000000 fractions of a Star |

### StarTransaction

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique identifier |
| amount | Integer | Number of Telegram Stars |
| nanostar_amount | Integer | Number of 1/1000000000 fractions of a Star (optional) |
| date | Integer | Unix timestamp |
| source | TransactionPartner | Source of incoming transaction (optional) |
| receiver | TransactionPartner | Receiver of outgoing transaction (optional) |

### StarTransactions

| Field | Type | Description |
|-------|------|-------------|
| transactions | Array of StarTransaction | List of transactions |

### TransactionPartner Variants

#### TransactionPartnerUser

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "user" |
| user | User | Information about the user |
| affiliate | AffiliateInfo | Affiliate information (optional) |
| invoice_payload | String | Bot-specified invoice payload (optional) |
| subscription_period | Integer | Subscription duration in seconds (optional) |
| paid_media | Array of PaidMedia | Information about paid media (optional) |
| paid_media_payload | String | Bot-specified paid media payload (optional) |
| gift | Gift | Information about the gift (optional) |

#### TransactionPartnerChat

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "chat" |
| chat | Chat | Information about the chat |
| gift | Gift | Information about the gift (optional) |

#### TransactionPartnerAffiliateProgram

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "affiliate_program" |
| commission_per_mille | Integer | Commission amount in per mille (thousandths) |
| sponsor_user | User | Sponsor user (optional) |

#### TransactionPartnerFragment

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "fragment" |
| withdrawal_state | RevenueWithdrawalState | State of the withdrawal (optional) |

#### TransactionPartnerTelegramApi

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "telegram_api" |
| request_count | Integer | Number of successful requests that exceeded regular limits |

#### TransactionPartnerTelegramAds

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "telegram_ads" |

No additional fields.

#### TransactionPartnerOther

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "other" |

No additional fields.

### RevenueWithdrawalState Variants

#### RevenueWithdrawalStatePending

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "pending" |

#### RevenueWithdrawalStateSucceeded

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "succeeded" |
| date | Integer | Unix timestamp of withdrawal completion |
| url | String | URL to view the withdrawal |

#### RevenueWithdrawalStateFailed

| Field | Type | Description |
|-------|------|-------------|
| type | String | Always "failed" |

## Gotchas

- Telegram Stars use currency code "XTR"
- Stars are integers -- no fractional amounts at the user level (nanostars exist for internal precision)
- refundStarPayment: can only refund within 90 days of the original payment
- Bot keeps ~75% of Stars revenue after Telegram's commission
- Stars can be withdrawn to Fragment for real currency
