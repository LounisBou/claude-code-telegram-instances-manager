# API Response Metadata

Types describing API response metadata and webhook configuration status. `ResponseParameters` appears in error responses. `WebhookInfo` is returned by `getWebhookInfo`.

## Types

### ResponseParameters

Describes additional information included in some error responses to help the caller retry.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| migrate_to_chat_id | Integer | No | The group has been migrated to a supergroup with this identifier. The bot should update its stored chat ID and retry the request with the new ID. |
| retry_after | Integer | No | Number of seconds to wait before the request can be retried. Returned when the bot is rate-limited (HTTP 429). |

### WebhookInfo

Describes the current status of a webhook. Returned by the `getWebhookInfo` method.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| url | String | Yes | Webhook URL. Empty string if webhook is not set up. |
| has_custom_certificate | Boolean | Yes | `true` if a custom certificate was provided for webhook certificate checks. |
| pending_update_count | Integer | Yes | Number of updates awaiting delivery. |
| ip_address | String | No | Currently used webhook IP address. |
| last_error_date | Integer | No | Unix timestamp of the most recent error when attempting webhook delivery. |
| last_error_message | String | No | Human-readable description of the most recent error when attempting webhook delivery. |
| last_synchronization_error_date | Integer | No | Unix timestamp of the most recent error during `setWebhook` synchronization with the remote server. |
| max_connections | Integer | No | Maximum allowed number of simultaneous HTTPS connections to the webhook. Defaults to 40. |
| allowed_updates | Array of String | No | List of update types the bot is subscribed to. Defaults to all update types except `chat_member`. |

## Gotchas

- `ResponseParameters` only appears inside error responses (when `ok` is `false`). It is never present in successful responses.
- `migrate_to_chat_id`: when a group is migrated to a supergroup, all subsequent requests using the old group ID will fail. The bot must permanently replace the old ID with the new one.
- `retry_after` is in seconds, not milliseconds. Respect this value to avoid further rate limiting.
- `WebhookInfo.url` being an empty string means no webhook is set and the bot must use `getUpdates` (long polling) to receive updates.
- `pending_update_count` can grow indefinitely if the webhook endpoint is down. Telegram retains undelivered updates for a limited time before discarding them.
- `allowed_updates` reflects what was passed to `setWebhook`. If not explicitly set, the bot receives all update types except `chat_member`.
- `last_error_date` and `last_error_message` are only populated if there has been at least one delivery error. They remain set even after a subsequent successful delivery.

## Patterns

- Check `retry_after` on HTTP 429 responses and implement a wait-and-retry loop.
- On receiving `migrate_to_chat_id`, update persistent storage with the new chat ID and re-send the failed request.
- Poll `getWebhookInfo` periodically to monitor `pending_update_count` and `last_error_message` for operational health checks.
- Use `last_error_message` to diagnose webhook delivery failures (common issues: SSL certificate errors, endpoint timeouts, non-200 responses).
