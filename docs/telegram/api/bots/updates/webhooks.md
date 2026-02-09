# Webhooks

## setWebhook

Specifies a URL to receive incoming updates via an outgoing webhook. Whenever there is an update for the bot, Telegram sends an HTTPS POST request to the specified URL.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| url | String | Yes | HTTPS URL to send updates to. Use empty string to remove. |
| certificate | InputFile | No | Upload public key certificate for self-signed certificates |
| ip_address | String | No | Fixed IP address for sending webhook requests instead of DNS |
| max_connections | Integer | No | Max simultaneous HTTPS connections for update delivery (1-100, default 40) |
| allowed_updates | Array of String | No | Update types to receive |
| drop_pending_updates | Boolean | No | Drop all pending updates |
| secret_token | String | No | Secret token sent in X-Telegram-Bot-Api-Secret-Token header (1-256 chars, A-Za-z0-9_-) |

**Returns:** True on success.

---

## deleteWebhook

Removes the webhook integration. Use this to switch back to getUpdates.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| drop_pending_updates | Boolean | No | Drop all pending updates |

**Returns:** True on success.

---

## getWebhookInfo

Returns current webhook status. No parameters required.

**Returns:** WebhookInfo

---

## WebhookInfo Type

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| url | String | Yes | Webhook URL, empty string if not set |
| has_custom_certificate | Boolean | Yes | True if custom certificate was provided |
| pending_update_count | Integer | Yes | Number of updates awaiting delivery |
| ip_address | String | No | Currently used webhook IP address |
| last_error_date | Integer | No | Unix time of most recent delivery error |
| last_error_message | String | No | Error description in human-readable format |
| last_synchronization_error_date | Integer | No | Unix time of most recent error that happened while delivering an update via webhook synchronization |
| max_connections | Integer | No | Maximum allowed simultaneous HTTPS connections for update delivery |
| allowed_updates | Array of String | No | List of subscribed update types |

---

## Gotchas

- Webhook URL must be HTTPS. Self-signed certificates are allowed if you upload the public key via the `certificate` parameter.
- Telegram retries failed deliveries with increasing delays.
- If the webhook returns a non-2xx HTTP status too many times, it gets automatically disabled.
- `secret_token`: always validate the `X-Telegram-Bot-Api-Secret-Token` header to prevent spoofed requests.
- Supported ports: 443, 80, 88, 8443.
- Webhook response: you can reply directly with a method as JSON in the webhook response body. Only one method per response is allowed, and only methods that return Message or Boolean are supported.
- 409 Conflict error means getUpdates is being called while a webhook is active.

---

## Patterns

- **Webhook response trick:** Return a sendMessage JSON body directly in the webhook HTTP response to save an extra API call.
- **Use secret_token for production deployments.** Without it, anyone who discovers your webhook URL can send fake updates.
- **Use ip_address when your DNS might change but your IP is stable.** This avoids delivery interruptions during DNS propagation.
