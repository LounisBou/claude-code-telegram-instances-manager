# Payments

> Accept payments, send invoices, and handle Telegram Stars transactions within Telegram chats.

## Overview

Telegram Payments allows bots to accept payments from users via third-party payment providers or Telegram Stars (Telegram's built-in currency). The flow is: bot sends an invoice, user fills in payment details, the bot validates shipping (if applicable) and confirms the pre-checkout query, then receives a `SuccessfulPayment` notification. Telegram Stars payments skip the external provider and use Telegram's own currency.

## Quick Usage

```python
from telegram import LabeledPrice, Update
from telegram.ext import (
    Application, CommandHandler, PreCheckoutQueryHandler,
    MessageHandler, filters, ContextTypes,
)

async def send_invoice(update: Update, context: ContextTypes.DefaultType):
    await update.message.reply_invoice(
        title="Product",
        description="A great product",
        payload="product-001",
        currency="XTR",  # "XTR" for Telegram Stars
        prices=[LabeledPrice("Product", 100)],
    )

async def pre_checkout(update: Update, context: ContextTypes.DefaultType):
    await update.pre_checkout_query.answer(ok=True)

async def success(update: Update, context: ContextTypes.DefaultType):
    payment = update.message.successful_payment
    await update.message.reply_text(f"Payment received: {payment.total_amount} {payment.currency}")

app = Application.builder().token("TOKEN").build()
app.add_handler(CommandHandler("buy", send_invoice))
app.add_handler(PreCheckoutQueryHandler(pre_checkout))
app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, success))
app.run_polling()
```

## Key Classes

### Payment Flow

```
Bot sends invoice (send_invoice / reply_invoice)
    |
    v
User fills payment form
    |
    v (if flexible shipping)
ShippingQuery --> bot answers with shipping options
    |
    v
PreCheckoutQuery --> bot answers ok=True/False
    |
    v
SuccessfulPayment arrives as update.message.successful_payment
```

---

### `telegram.LabeledPrice`

```python
LabeledPrice(label: str, amount: int)
```

`amount` is in the smallest units of the currency (e.g., cents for USD, Stars for XTR). 1 Star = amount of `1` when currency is `"XTR"`.

---

### `telegram.Invoice`

Attached to messages containing an invoice.

| Attribute | Type | Description |
|---|---|---|
| `title` | `str` | Product name. |
| `description` | `str` | Product description. |
| `start_parameter` | `str` | Bot deep link parameter for generating the invoice. |
| `currency` | `str` | Three-letter ISO 4217 currency code or `"XTR"` for Stars. |
| `total_amount` | `int` | Total price in smallest units. |

---

### `telegram.SuccessfulPayment`

Received when a payment completes successfully. Available on `message.successful_payment`.

| Attribute | Type | Description |
|---|---|---|
| `currency` | `str` | Currency code. |
| `total_amount` | `int` | Total amount in smallest units. |
| `invoice_payload` | `str` | Bot-specified payload from the invoice. |
| `shipping_option_id` | `str \| None` | Identifier of the chosen shipping option. |
| `order_info` | `OrderInfo \| None` | User's order information. |
| `telegram_payment_charge_id` | `str` | Telegram payment identifier. |
| `provider_payment_charge_id` | `str` | Provider payment identifier. |

---

### `telegram.PreCheckoutQuery`

Sent just before the payment is finalized. **Must be answered within 10 seconds.**

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique query identifier. |
| `from_user` | `User` | User who sent the query. |
| `currency` | `str` | Currency code. |
| `total_amount` | `int` | Total amount in smallest units. |
| `invoice_payload` | `str` | Bot-specified payload. |
| `shipping_option_id` | `str \| None` | Chosen shipping option. |
| `order_info` | `OrderInfo \| None` | User's order info. |

| Method | Returns | Description |
|---|---|---|
| `answer(ok, error_message=None)` | `bool` | Confirm (`ok=True`) or reject (`ok=False`) the checkout. If rejecting, provide `error_message`. |

---

### `telegram.ShippingQuery`

Sent when an invoice with `is_flexible=True` needs shipping options.

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique query identifier. |
| `from_user` | `User` | User who sent the query. |
| `invoice_payload` | `str` | Bot-specified payload. |
| `shipping_address` | `ShippingAddress` | User's shipping address. |

| Method | Returns | Description |
|---|---|---|
| `answer(ok, shipping_options=None, error_message=None)` | `bool` | Provide shipping options (`ok=True`, `shipping_options=list[ShippingOption]`) or reject (`ok=False`, `error_message="reason"`). |

---

### `telegram.ShippingAddress`

| Attribute | Type |
|---|---|
| `country_code` | `str` |
| `state` | `str` |
| `city` | `str` |
| `street_line1` | `str` |
| `street_line2` | `str` |
| `post_code` | `str` |

---

### `telegram.ShippingOption`

```python
ShippingOption(id: str, title: str, prices: list[LabeledPrice])
```

---

### `telegram.OrderInfo`

| Attribute | Type |
|---|---|
| `name` | `str \| None` |
| `phone_number` | `str \| None` |
| `email` | `str \| None` |
| `shipping_address` | `ShippingAddress \| None` |

---

### `telegram.RefundedPayment`

Available on `message.refunded_payment` when a payment is refunded.

| Attribute | Type | Description |
|---|---|---|
| `currency` | `str` | Currency code (always `"XTR"` currently). |
| `total_amount` | `int` | Refunded amount in smallest units. |
| `invoice_payload` | `str` | Bot-specified payload. |
| `telegram_payment_charge_id` | `str` | Telegram payment identifier. |
| `provider_payment_charge_id` | `str \| None` | Provider payment identifier. |

---

### Bot Methods for Payments

| Method | Returns | Description |
|---|---|---|
| `send_invoice(chat_id, title, description, payload, currency, prices, provider_token=None, max_tip_amount=None, suggested_tip_amounts=None, start_parameter=None, provider_data=None, photo_url=None, photo_size=None, photo_width=None, photo_height=None, need_name=None, need_phone_number=None, need_email=None, need_shipping_address=None, send_phone_number_to_provider=None, send_email_to_provider=None, is_flexible=None, ...)` | `Message` | Send an invoice. For Stars, use `currency="XTR"` and omit `provider_token`. |
| `create_invoice_link(title, description, payload, currency, prices, ...)` | `str` | Create a payment link that can be shared anywhere. |
| `answer_shipping_query(shipping_query_id, ok, shipping_options=None, error_message=None)` | `bool` | Respond to a ShippingQuery. |
| `answer_pre_checkout_query(pre_checkout_query_id, ok, error_message=None)` | `bool` | Respond to a PreCheckoutQuery. |
| `refund_star_payment(user_id, telegram_payment_charge_id)` | `bool` | Refund a Telegram Stars payment. |
| `get_star_transactions(offset=None, limit=None)` | `StarTransactions` | Get the bot's Stars transaction history. |

---

### Telegram Stars Types

#### `telegram.StarTransaction`

| Attribute | Type | Description |
|---|---|---|
| `id` | `str` | Unique transaction identifier. |
| `amount` | `StarAmount` | Transaction amount. |
| `date` | `datetime` | Transaction date. |
| `source` | `TransactionPartner \| None` | Source of incoming transaction. |
| `receiver` | `TransactionPartner \| None` | Receiver of outgoing transaction. |

#### `telegram.StarTransactions`

| Attribute | Type |
|---|---|
| `transactions` | `list[StarTransaction]` |

#### `telegram.StarAmount`

| Attribute | Type | Description |
|---|---|---|
| `amount` | `int` | Integer amount of Stars. |
| `nanostar_amount` | `int \| None` | Fractional amount in nanostars (0-999999999). |

#### TransactionPartner Subclasses

| Class | Description |
|---|---|
| `TransactionPartnerUser` | Transaction with a user. Has `user`, `invoice_payload`, `paid_media` attributes. |
| `TransactionPartnerChat` | Transaction with a chat. |
| `TransactionPartnerFragment` | Withdrawal to Fragment. |
| `TransactionPartnerTelegramAds` | Transfer to Telegram Ads. |
| `TransactionPartnerTelegramApi` | Paid via Bot API (e.g., paid broadcasting). |
| `TransactionPartnerAffiliateProgram` | Affiliate program commission. |
| `TransactionPartnerOther` | Unknown/other transaction partner. |

## Common Patterns

### Invoice with shipping options

```python
from telegram import ShippingOption, LabeledPrice

async def send_order(update: Update, context: ContextTypes.DefaultType):
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="T-Shirt",
        description="Premium cotton t-shirt",
        payload="tshirt-order-123",
        provider_token="PROVIDER_TOKEN",
        currency="USD",
        prices=[LabeledPrice("T-Shirt", 2000)],  # $20.00
        need_shipping_address=True,
        is_flexible=True,  # triggers ShippingQuery
    )

async def handle_shipping(update: Update, context: ContextTypes.DefaultType):
    query = update.shipping_query
    options = [
        ShippingOption("standard", "Standard", [LabeledPrice("Shipping", 500)]),
        ShippingOption("express", "Express", [LabeledPrice("Shipping", 1200)]),
    ]
    await query.answer(ok=True, shipping_options=options)
```

### Telegram Stars payment with refund

```python
async def buy_stars(update: Update, context: ContextTypes.DefaultType):
    await update.message.reply_invoice(
        title="Premium Feature",
        description="Unlock premium for 30 days",
        payload="premium-30d",
        currency="XTR",
        prices=[LabeledPrice("Premium", 50)],  # 50 Stars
    )

async def refund(update: Update, context: ContextTypes.DefaultType):
    charge_id = context.args[0]  # telegram_payment_charge_id
    await context.bot.refund_star_payment(
        user_id=update.effective_user.id,
        telegram_payment_charge_id=charge_id,
    )
    await update.message.reply_text("Refund issued.")
```

### Validate pre-checkout with payload

```python
async def pre_checkout(update: Update, context: ContextTypes.DefaultType):
    query = update.pre_checkout_query
    if query.invoice_payload.startswith("tshirt-"):
        # Verify stock, validate amount, etc.
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message="Invalid order.")
```

## Related

- [../handlers/index.md](../handlers/index.md) -- `PreCheckoutQueryHandler`, `ShippingQueryHandler`, `MessageHandler` with `filters.SUCCESSFUL_PAYMENT`
- [../bot.md](../bot.md) -- `Bot.send_invoice()`, `Bot.answer_pre_checkout_query()`, `Bot.refund_star_payment()`
- [inline-mode.md](inline-mode.md) -- `InputInvoiceMessageContent` for sending invoices via inline mode
- [../types/index.md](../types/index.md) -- base types
- [Telegram API — Payments](../../api/bots/payments/index.md) -- payment flow and invoice handling in the API specification
