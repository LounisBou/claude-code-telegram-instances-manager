# Inline Mode

Users can invoke the bot from ANY chat by typing @botusername followed by a query. The bot returns results displayed in a popup above the input field.

## How It Works

1. User types `@botusername query` in any chat
2. Bot receives InlineQuery update
3. Bot calls answerInlineQuery with up to 50 results
4. Results appear as cards above input field
5. User selects a result -- message is sent in that chat
6. Bot optionally receives ChosenInlineResult update

## InlineQuery

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique query identifier |
| from | User | Sender |
| query | String | Query text (up to 256 chars) |
| offset | String | Pagination offset |
| chat_type | String | Chat type: "sender", "private", "group", "supergroup", "channel" |
| location | Location | Sender location (optional, requires geo bot setting) |

## answerInlineQuery

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| inline_query_id | String | Yes | Query identifier |
| results | Array of InlineQueryResult | Yes | Results to show (max 50) |
| cache_time | Integer | No | Cache duration in seconds (default 300) |
| is_personal | Boolean | No | Per-user caching |
| next_offset | String | No | Offset for pagination |
| button | InlineQueryResultsButton | No | Button above results |

**Returns:** True

## InlineQueryResultsButton

| Field | Type | Description |
|-------|------|-------------|
| text | String | Button label |
| web_app | WebAppInfo | Opens Web App |
| start_parameter | String | Deep link parameter for private chat |

## InlineQueryResult Types

All types share these common fields:

| Field | Type | Description |
|-------|------|-------------|
| type | String | Result type |
| id | String | Unique identifier (1-64 bytes) |
| reply_markup | InlineKeyboardMarkup | Inline keyboard for the sent message (optional) |

### Available types:
- **InlineQueryResultArticle**: title, input_message_content, url, description, thumbnail_url, etc.
- **InlineQueryResultPhoto**: photo_url, thumbnail_url, photo_width, photo_height, title, description, caption
- **InlineQueryResultGif**: gif_url, thumbnail_url, gif_width, gif_height, gif_duration, title, caption
- **InlineQueryResultMpeg4Gif**: mpeg4_url, thumbnail_url, mpeg4_width, mpeg4_height, mpeg4_duration, title, caption
- **InlineQueryResultVideo**: video_url, mime_type, thumbnail_url, title, caption, video_width, video_height, video_duration, description
- **InlineQueryResultAudio**: audio_url, title, caption, performer, audio_duration
- **InlineQueryResultVoice**: voice_url, title, caption, voice_duration
- **InlineQueryResultDocument**: document_url, title, mime_type, caption, description
- **InlineQueryResultLocation**: latitude, longitude, title, horizontal_accuracy, live_period, heading, proximity_alert_radius
- **InlineQueryResultVenue**: latitude, longitude, title, address, foursquare_id, foursquare_type, google_place_id, google_place_type
- **InlineQueryResultContact**: phone_number, first_name, last_name, vcard

### Cached variants (use file_id from already uploaded files):
- InlineQueryResultCachedPhoto, InlineQueryResultCachedGif, InlineQueryResultCachedMpeg4Gif, InlineQueryResultCachedSticker, InlineQueryResultCachedDocument, InlineQueryResultCachedVideo, InlineQueryResultCachedVoice, InlineQueryResultCachedAudio

## InputMessageContent

Override what gets sent when a result is selected:

- **InputTextMessageContent**: message_text, parse_mode, entities, link_preview_options
- **InputLocationMessageContent**: latitude, longitude, horizontal_accuracy, live_period, heading, proximity_alert_radius
- **InputVenueMessageContent**: latitude, longitude, title, address, foursquare_id, foursquare_type, google_place_id, google_place_type
- **InputContactMessageContent**: phone_number, first_name, last_name, vcard
- **InputInvoiceMessageContent**: title, description, payload, provider_token, currency, prices, etc.

## ChosenInlineResult

Received when a user selects an inline result (must enable /setinlinefeedback in @BotFather):

| Field | Type | Description |
|-------|------|-------------|
| result_id | String | Identifier of the chosen result |
| from | User | User who chose the result |
| location | Location | Sender location (optional) |
| inline_message_id | String | Identifier of the sent inline message (optional) |
| query | String | The query used to obtain the result |

## Gotchas

- Must enable inline mode via @BotFather (/setinline command)
- Max 50 results per response
- Pagination: set next_offset in response, handle subsequent queries where offset matches that value
- cache_time: set to 0 during development. Default 300 seconds.
- is_personal=true: results vary per user (e.g., user-specific search results)
- Results are cached server-side -- different users may see same results if is_personal=false
- Bot can edit inline results later using inline_message_id from ChosenInlineResult
- Enable /setinlinefeedback in @BotFather to receive ChosenInlineResult updates
- inline_message_id in ChosenInlineResult: only available if the result contains reply_markup or if feedback collection is enabled
- Empty query (user just typed @botname): handle this case with default/popular results
- Result id: must be unique within a single answerInlineQuery call (1-64 bytes)

## Patterns

- Search: user types query -- bot searches database -- returns matching results
- Share: user selects content to share in another chat
- Quick actions: empty query shows recent/popular items
- Location-based: use location field for nearby results (requires geo bot setting in @BotFather)
- Paginated results: use next_offset for infinite scroll through large result sets
- Inline buttons on results: attach reply_markup for post-send interaction
