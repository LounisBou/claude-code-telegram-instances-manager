# Invoices & Checkout

Send payment invoices and handle the checkout flow.

## Payment Flow

1. Bot sends invoice via sendInvoice or createInvoiceLink
2. User fills payment form and confirms
3. Bot receives ShippingQuery (if shipping required) → answerShippingQuery
4. Bot receives PreCheckoutQuery → answerPreCheckoutQuery (must respond within 10 seconds)
5. If approved, Telegram processes payment → bot receives SuccessfulPayment in message

## Methods

### sendInvoice

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| title | String | Yes | Product name (1-32 chars) |
| description | String | Yes | Product description (1-255 chars) |
| payload | String | Yes | Bot-defined invoice payload (1-128 bytes) |
| provider_token | String | No | Payment provider token (empty string or omit for Telegram Stars) |
| currency | String | Yes | Three-letter ISO 4217 currency code, or "XTR" for Telegram Stars |
| prices | Array of LabeledPrice | Yes | Price breakdown (total must be positive) |
| message_thread_id | Integer | No | Forum topic identifier |
| max_tip_amount | Integer | No | Max tip amount in smallest currency units |
| suggested_tip_amounts | Array of Integer | No | Suggested tip amounts (max 4 values, ascending) |
| start_parameter | String | No | Deep-linking parameter for URL generation |
| provider_data | String | No | JSON data about invoice for payment provider |
| photo_url | String | No | URL of product photo |
| photo_size | Integer | No | Photo size in bytes |
| photo_width | Integer | No | Photo width |
| photo_height | Integer | No | Photo height |
| need_name | Boolean | No | Request user's full name |
| need_phone_number | Boolean | No | Request user's phone number |
| need_email | Boolean | No | Request user's email |
| need_shipping_address | Boolean | No | Request shipping address |
| send_phone_number_to_provider | Boolean | No | Forward phone to provider |
| send_email_to_provider | Boolean | No | Forward email to provider |
| is_flexible | Boolean | No | True if final price depends on shipping method |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding |
| message_effect_id | String | No | Message effect |
| reply_parameters | ReplyParameters | No | Reply config |
| reply_markup | InlineKeyboardMarkup | No | Inline keyboard (pay button auto-added as first button) |

**Returns:** Message

### createInvoiceLink

Same parameters as sendInvoice except: no chat_id, message_thread_id, disable_notification, protect_content, message_effect_id, reply_parameters, reply_markup. Plus subscription_period (opt, 2592000 for 30-day subscriptions).

**Returns:** String (the invoice link)

### answerShippingQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| shipping_query_id | String | Yes | Query identifier |
| ok | Boolean | Yes | True if delivery is possible |
| shipping_options | Array of ShippingOption | Conditional | Available shipping options (required if ok=true) |
| error_message | String | Conditional | Error message (required if ok=false) |

**Returns:** True

### answerPreCheckoutQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| pre_checkout_query_id | String | Yes | Query identifier |
| ok | Boolean | Yes | True to confirm order |
| error_message | String | Conditional | Error message (required if ok=false) |

**Returns:** True

## Types

### LabeledPrice

| Field | Type | Description |
|-------|------|-------------|
| label | String | Price portion label |
| amount | Integer | Price in smallest currency units (e.g., cents for USD) |

### Invoice

| Field | Type | Description |
|-------|------|-------------|
| title | String | Product name |
| description | String | Product description |
| start_parameter | String | Unique deep-linking parameter |
| currency | String | Currency code |
| total_amount | Integer | Total price in smallest units |

### ShippingAddress

| Field | Type | Description |
|-------|------|-------------|
| country_code | String | Two-letter ISO 3166-1 alpha-2 country code |
| state | String | State, if applicable |
| city | String | City |
| street_line1 | String | First line of the address |
| street_line2 | String | Second line of the address |
| post_code | String | Address post code |

### OrderInfo

| Field | Type | Description |
|-------|------|-------------|
| name | String | User name (optional) |
| phone_number | String | User phone number (optional) |
| email | String | User email (optional) |
| shipping_address | ShippingAddress | User shipping address (optional) |

### ShippingOption

| Field | Type | Description |
|-------|------|-------------|
| id | String | Shipping option identifier |
| title | String | Option title |
| prices | Array of LabeledPrice | Price breakdown for this option |

### ShippingQuery

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique query identifier |
| from | User | User who sent the query |
| invoice_payload | String | Bot-specified invoice payload |
| shipping_address | ShippingAddress | User-specified shipping address |

### PreCheckoutQuery

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique query identifier |
| from | User | User who sent the query |
| currency | String | Three-letter ISO 4217 currency code |
| total_amount | Integer | Total price in smallest currency units |
| invoice_payload | String | Bot-specified invoice payload |
| shipping_option_id | String | Identifier of chosen shipping option (optional) |
| order_info | OrderInfo | Order information provided by the user (optional) |

### SuccessfulPayment

| Field | Type | Description |
|-------|------|-------------|
| currency | String | Three-letter ISO 4217 currency code |
| total_amount | Integer | Total price in smallest currency units |
| invoice_payload | String | Bot-specified invoice payload |
| subscription_expiration_date | Integer | Unix timestamp when subscription expires (optional) |
| is_recurring | Boolean | True if payment is recurring (optional) |
| is_first_recurring | Boolean | True if this is the first recurring payment (optional) |
| shipping_option_id | String | Identifier of chosen shipping option (optional) |
| order_info | OrderInfo | Order information provided by the user (optional) |
| telegram_payment_charge_id | String | Telegram payment identifier |
| provider_payment_charge_id | String | Provider payment identifier |

### RefundedPayment

| Field | Type | Description |
|-------|------|-------------|
| currency | String | Three-letter ISO 4217 currency code |
| total_amount | Integer | Total price in smallest currency units |
| invoice_payload | String | Bot-specified invoice payload |
| telegram_payment_charge_id | String | Telegram payment identifier |
| provider_payment_charge_id | String | Provider payment identifier (optional) |

## Gotchas

- **answerPreCheckoutQuery**: MUST respond within 10 seconds, otherwise payment is cancelled
- **currency "XTR"**: use for Telegram Stars payments. provider_token must be empty/omitted.
- **prices**: amount is in SMALLEST currency units. $10.00 = amount: 1000
- **Pay button**: automatically inserted as first button in first row of inline keyboard
- **payload**: use to identify which product/service was purchased. Keep ≤128 bytes.
- **is_flexible**: if true, you MUST handle ShippingQuery updates
- **Subscriptions**: use subscription_period=2592000 for monthly subscriptions
