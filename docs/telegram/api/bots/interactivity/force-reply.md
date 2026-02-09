# Force Reply

Forces the user's Telegram client to display a reply interface, as if they manually selected the bot's message and tapped "Reply."

## How It Works

1. Bot sends message with ForceReply as reply_markup
2. User's input field shows "Reply to [bot message]"
3. User types response -- sent as a reply to the bot's message
4. Bot receives Message with reply_to_message pointing to the original

## ForceReply

| Field | Type | Description |
|-------|------|-------------|
| force_reply | Boolean | Must be True |
| input_field_placeholder | String | Placeholder text in input (1-64 chars, optional) |
| selective | Boolean | Force reply only for specific users (optional) |

## Gotchas

- Main use case: collecting text input in groups without inline keyboards
- selective: works when replying to a specific message or @mentioning users
- The reply interface can be dismissed by the user
- ForceReply does NOT prevent the user from sending a non-reply message
- In private chats, ForceReply is less useful (user is already talking to the bot)
- ForceReply is a one-shot mechanism -- it only triggers once, not persistently

## Patterns

- Form input in groups: bot asks "What's your name?" with ForceReply -- user replies -- bot gets reply_to_message to match context
- Sequential input: send ForceReply after each question in a multi-step form
- Use input_field_placeholder to hint at expected format: "Enter your email..."
- Combine with selective=true in groups to target only the relevant user
