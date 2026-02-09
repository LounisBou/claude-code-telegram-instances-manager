# Dice & Animations

Send random animated results. The value is determined by Telegram servers -- the bot cannot control the outcome.

## sendDice

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| emoji | String | No | Dice emoji (default "🎲") |
| message_thread_id | Integer | No | Forum topic identifier |
| disable_notification | Boolean | No | Send silently |
| protect_content | Boolean | No | Protect from forwarding/saving |
| message_effect_id | String | No | Message effect identifier |
| reply_parameters | ReplyParameters | No | Reply configuration |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Keyboard or reply interface |

**Returns:** Message (with dice field)

## Dice (in Message)

| Field | Type | Description |
|-------|------|-------------|
| emoji | String | The emoji used |
| value | Integer | The random result value |

## Emoji Values

| Emoji | Animation | Value Range | Best Outcome |
|-------|-----------|-------------|--------------|
| 🎲 | Rolling dice | 1-6 | 6 |
| 🎯 | Throwing darts | 1-6 | 6 (bullseye) |
| 🏀 | Shooting basketball | 1-5 | 4-5 (basket made) |
| ⚽ | Kicking soccer ball | 1-5 | 3-5 (goal) |
| 🎳 | Bowling | 1-6 | 6 (strike) |
| 🎰 | Slot machine | 1-64 | 64 (jackpot: three 7s) |

## Slot Machine Value Decoding

The slot machine value (1-64) encodes three reel positions. Each reel can show one of 4 symbols (bar, grape, lemon, seven). Value 64 = three sevens (jackpot). The value maps to specific symbol combinations but the exact encoding is not officially documented.

## Gotchas

- Value is random and determined by Telegram -- bot CANNOT choose the result
- The value is known immediately in the API response, before the animation finishes on client
- Slot machine value 64 = jackpot (three 7s). Values 1-63 represent various symbol combinations.
- Only the six listed emoji are valid -- others will be rejected with an error
- Default emoji is "🎲" if not specified
- Animation takes approximately 3-4 seconds on the client
- The dice field in the returned Message contains both emoji and value

## Patterns

- Random selection: use dice value to make random choices (e.g., value 1-3 = team A, 4-6 = team B)
- Games: basketball/bowling with score tracking across rounds
- Gambling games: use slot machine for casino-style interactions (result cannot be rigged)
- Wait for animation: send follow-up message with a delay matching the animation duration
- Fair decisions: use dice for transparent, verifiable random outcomes in group chats
