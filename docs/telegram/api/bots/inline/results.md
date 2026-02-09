# Inline Query Results

All result types that can be returned by answerInlineQuery.

## Result Variants

All variants share: type (String), id (String, unique, 1-64 bytes), reply_markup (InlineKeyboardMarkup, opt)

### Fresh content (bot provides URL/file)

| Variant | Represents | Key Fields |
|---------|-----------|------------|
| InlineQueryResultArticle | Text article | title, input_message_content, url (opt), description (opt), thumbnail_url (opt) |
| InlineQueryResultPhoto | Photo via URL | photo_url, thumbnail_url, photo_width (opt), photo_height (opt), title (opt), description (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultGif | GIF via URL | gif_url, thumbnail_url, gif_width (opt), gif_height (opt), gif_duration (opt), title (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultMpeg4Gif | MP4 animation via URL | mpeg4_url, thumbnail_url, mpeg4_width (opt), mpeg4_height (opt), mpeg4_duration (opt), title (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultVideo | Video via URL | video_url, mime_type, thumbnail_url, title, video_width (opt), video_height (opt), video_duration (opt), description (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultAudio | Audio via URL | audio_url, title, caption (opt), performer (opt), audio_duration (opt), input_message_content (opt) |
| InlineQueryResultVoice | Voice via URL | voice_url, title, caption (opt), voice_duration (opt), input_message_content (opt) |
| InlineQueryResultDocument | Document via URL | document_url, title, mime_type, caption (opt), description (opt), input_message_content (opt) |
| InlineQueryResultLocation | Location | latitude, longitude, title, horizontal_accuracy (opt), live_period (opt), heading (opt), proximity_alert_radius (opt), input_message_content (opt) |
| InlineQueryResultVenue | Venue | latitude, longitude, title, address, foursquare_id (opt), foursquare_type (opt), google_place_id (opt), google_place_type (opt), input_message_content (opt) |
| InlineQueryResultContact | Contact | phone_number, first_name, last_name (opt), vcard (opt), input_message_content (opt) |
| InlineQueryResultGame | Game | game_short_name |

### Cached content (file already on Telegram servers)

| Variant | Key Fields |
|---------|------------|
| InlineQueryResultCachedPhoto | photo_file_id, title (opt), description (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultCachedGif | gif_file_id, title (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultCachedMpeg4Gif | mpeg4_file_id, title (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultCachedSticker | sticker_file_id, input_message_content (opt) |
| InlineQueryResultCachedDocument | document_file_id, title, description (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultCachedVideo | video_file_id, title, description (opt), caption (opt), input_message_content (opt) |
| InlineQueryResultCachedVoice | voice_file_id, title, caption (opt), input_message_content (opt) |
| InlineQueryResultCachedAudio | audio_file_id, caption (opt), input_message_content (opt) |

## InputMessageContent Variants

Override the content of the message sent when result is selected.

### InputTextMessageContent

| Field | Type | Description |
|-------|------|-------------|
| message_text | String | Text of the message (1-4096 chars) |
| parse_mode | String | Formatting mode (optional) |
| entities | Array of MessageEntity | Special entities (optional) |
| link_preview_options | LinkPreviewOptions | Link preview settings (optional) |

### InputLocationMessageContent

| Field | Type | Description |
|-------|------|-------------|
| latitude | Float | Latitude of the location |
| longitude | Float | Longitude of the location |
| horizontal_accuracy | Float | Radius of uncertainty in meters (0-1500) (optional) |
| live_period | Integer | Period in seconds during which location can be updated (60-86400) or 0x7FFFFFFF for indefinite (optional) |
| heading | Integer | Direction of movement in degrees (1-360) (optional) |
| proximity_alert_radius | Integer | Max distance in meters for proximity alerts (optional) |

### InputVenueMessageContent

| Field | Type | Description |
|-------|------|-------------|
| latitude | Float | Latitude of the venue |
| longitude | Float | Longitude of the venue |
| title | String | Name of the venue |
| address | String | Address of the venue |
| foursquare_id | String | Foursquare identifier (optional) |
| foursquare_type | String | Foursquare type (optional) |
| google_place_id | String | Google Places identifier (optional) |
| google_place_type | String | Google Places type (optional) |

### InputContactMessageContent

| Field | Type | Description |
|-------|------|-------------|
| phone_number | String | Contact's phone number |
| first_name | String | Contact's first name |
| last_name | String | Contact's last name (optional) |
| vcard | String | Additional vCard data (optional) |

### InputInvoiceMessageContent

| Field | Type | Description |
|-------|------|-------------|
| title | String | Product name (1-32 chars) |
| description | String | Product description (1-255 chars) |
| payload | String | Bot-defined invoice payload (1-128 bytes) |
| provider_token | String | Payment provider token (optional) |
| currency | String | Three-letter ISO 4217 currency code |
| prices | Array of LabeledPrice | Price breakdown |
| max_tip_amount | Integer | Max tip amount in smallest currency units (optional) |
| suggested_tip_amounts | Array of Integer | Suggested tip amounts (optional) |
| provider_data | String | JSON data for the payment provider (optional) |
| photo_url | String | Product photo URL (optional) |
| photo_size | Integer | Photo size in bytes (optional) |
| photo_width | Integer | Photo width (optional) |
| photo_height | Integer | Photo height (optional) |
| need_name | Boolean | Request user's full name (optional) |
| need_phone_number | Boolean | Request user's phone number (optional) |
| need_email | Boolean | Request user's email (optional) |
| need_shipping_address | Boolean | Request user's shipping address (optional) |
| send_phone_number_to_provider | Boolean | Send phone number to provider (optional) |
| send_email_to_provider | Boolean | Send email to provider (optional) |
| is_flexible | Boolean | Final price depends on shipping method (optional) |

## Gotchas

- **Result id** must be unique within the query response (1-64 bytes)
- **Fresh vs Cached**: use Cached variants when you have a file_id from a previous upload; use fresh variants when providing URLs
- **input_message_content**: overrides default behavior. Without it, the result sends its native type (photo sends photo, etc.)
- **InlineQueryResultArticle**: requires input_message_content (it has no default content to send)
- **thumbnail_url**: highly recommended for visual results, improves user experience
- **document mime_type**: must be "application/pdf" or "application/zip" for InlineQueryResultDocument
