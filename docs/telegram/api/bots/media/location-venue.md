# Location & Venue

## sendLocation

Send a point on the map, optionally as a live location that updates over time.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| latitude | Float | Yes | Latitude of the location (-90 to 90) |
| longitude | Float | Yes | Longitude of the location (-180 to 180) |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| horizontal_accuracy | Float | No | Radius of uncertainty for the location, in meters (0-1500) |
| live_period | Integer | No | Period in seconds during which the location will be updated (60-86400), or 0x7FFFFFFF for indefinite live location |
| heading | Integer | No | Direction in which the user is moving, in degrees (1-360) |
| proximity_alert_radius | Integer | No | Maximum distance in meters for proximity alerts about approaching another chat member (1-100000) |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## editMessageLiveLocation

Edit a live location message. A location can be edited until its `live_period` expires or the live location is explicitly stopped.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| latitude | Float | Yes | New latitude (-90 to 90) |
| longitude | Float | Yes | New longitude (-180 to 180) |
| chat_id | Integer or String | No | Required if inline_message_id is not specified |
| message_id | Integer | No | Required if inline_message_id is not specified |
| inline_message_id | String | No | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| live_period | Integer | No | New live period in seconds (60-86400), or 0x7FFFFFFF for indefinite |
| horizontal_accuracy | Float | No | Radius of uncertainty in meters (0-1500) |
| heading | Integer | No | Direction of movement in degrees (1-360) |
| proximity_alert_radius | Integer | No | Maximum distance for proximity alerts in meters (1-100000) |
| reply_markup | InlineKeyboardMarkup | No | Inline keyboard |

**Returns:** Message (if sent by the bot) or True (if inline message)

---

## stopMessageLiveLocation

Stop updating a live location message.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | No | Required if inline_message_id is not specified |
| message_id | Integer | No | Required if inline_message_id is not specified |
| inline_message_id | String | No | Required if chat_id and message_id are not specified |
| business_connection_id | String | No | Unique identifier of the business connection |
| reply_markup | InlineKeyboardMarkup | No | Inline keyboard |

**Returns:** Message (if sent by the bot) or True (if inline message)

---

## sendVenue

Send a venue (named location with address).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| latitude | Float | Yes | Latitude of the venue |
| longitude | Float | Yes | Longitude of the venue |
| title | String | Yes | Name of the venue |
| address | String | Yes | Address of the venue |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| foursquare_id | String | No | Foursquare identifier of the venue |
| foursquare_type | String | No | Foursquare type of the venue |
| google_place_id | String | No | Google Places identifier of the venue |
| google_place_type | String | No | Google Places type of the venue |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## Types

### Location

Represents a point on the map.

| Field | Type | Description |
|-------|------|-------------|
| latitude | Float | Latitude as defined by the sender |
| longitude | Float | Longitude as defined by the sender |
| horizontal_accuracy | Float | Optional. Radius of uncertainty for the location, in meters (0-1500) |
| live_period | Integer | Optional. Time in seconds relative to the message send date, during which the location can be updated |
| heading | Integer | Optional. Direction in which the user is moving, in degrees (1-360) |
| proximity_alert_radius | Integer | Optional. Maximum distance for proximity alerts, in meters (1-100000) |

### Venue

Represents a venue.

| Field | Type | Description |
|-------|------|-------------|
| location | Location | Venue location (cannot be a live location) |
| title | String | Name of the venue |
| address | String | Address of the venue |
| foursquare_id | String | Optional. Foursquare identifier of the venue |
| foursquare_type | String | Optional. Foursquare type of the venue |
| google_place_id | String | Optional. Google Places identifier of the venue |
| google_place_type | String | Optional. Google Places type of the venue |

---

## Gotchas

- Live location: must call `stopMessageLiveLocation` to stop, or it auto-expires after `live_period` seconds.
- Live location with `0x7FFFFFFF` (2147483647): runs indefinitely until explicitly stopped.
- `heading` and `proximity_alert_radius` only work with live locations (`live_period` must be set).
- `foursquare_id`/`foursquare_type` and `google_place_id`/`google_place_type` are two separate venue provider systems; you can use either but not both.
