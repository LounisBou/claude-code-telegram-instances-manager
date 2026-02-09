# Message Effects

Add visual effects (animations) when sending messages. Effects play once when the recipient opens the message.

## How It Works

1. Include message_effect_id parameter when sending a message
2. The effect animation plays when the recipient first sees the message
3. The effect is stored in the message's effect_id field

## Parameter

| Parameter | Type | Description |
|-----------|------|-------------|
| message_effect_id | String | Unique identifier of the message effect to apply |

## Supported Methods

The message_effect_id parameter is available on these send methods:

- sendMessage
- sendPhoto
- sendVideo
- sendAnimation
- sendAudio
- sendDocument
- sendVoice
- sendVideoNote
- sendSticker
- sendLocation
- sendVenue
- sendContact
- sendDice
- sendPoll
- sendInvoice
- forwardMessage
- copyMessage

## Effect IDs

Known effect IDs (these are Telegram-internal identifiers):

| Effect | ID |
|--------|----|
| Fire | 5104841245755180586 |
| Thumbs up | 5107584321108051014 |
| Thumbs down | 5104858069142078462 |
| Heart | 5159385139981059251 |
| Party/Confetti | 5046509860389126442 |
| Poop | 5046589136895476101 |

Note: Effect IDs may change or expand over time. These are not officially documented in the Bot API specification.

## Message.effect_id

| Field | Type | Description |
|-------|------|-------------|
| effect_id | String | Unique identifier of the message effect applied (optional) |

This field is present in the Message object when an effect was applied.

## Gotchas

- Effect IDs are not comprehensively documented in the Bot API -- they are obtained from the Telegram client or community sources
- Effects play ONCE when the message first appears on screen
- Not all clients support effects -- they are silently ignored on unsupported clients
- Effects are cosmetic only -- they do not affect message content or behavior
- The effect_id field in Message stores the applied effect after sending
- There is no API method to list available effects
- Invalid effect IDs may be silently ignored or cause an error

## Patterns

- Celebrations: add confetti/party effect to congratulatory messages
- Emphasis: use fire effect to draw attention to important messages
- Feedback: use thumbs up/down effects for approval or rejection
- Fun interactions: add visual flair to casual bot interactions
