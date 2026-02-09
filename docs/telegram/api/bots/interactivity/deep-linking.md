# Deep Linking

Open bots with preset parameters using special URLs. Enables referral tracking, feature activation, and context-aware bot starts.

## URL Formats

| Format | Purpose |
|--------|---------|
| `https://t.me/botusername?start=PARAMETER` | Open private chat with bot |
| `https://t.me/botusername?startgroup=PARAMETER` | Add bot to a group |
| `https://t.me/botusername?startchannel` | Add bot to a channel |
| `tg://resolve?domain=botusername&start=PARAMETER` | tg:// protocol variant |
| `tg://resolve?domain=botusername&startgroup=PARAMETER` | tg:// protocol variant for groups |

## How It Works

### Private Chat (?start=)

1. User opens `https://t.me/botusername?start=ref123`
2. Telegram opens bot chat and shows START button
3. User presses START
4. Bot receives Message with text `/start ref123`
5. Bot parses the parameter after `/start `

### Group (?startgroup=)

1. User opens `https://t.me/botusername?startgroup=setup`
2. User selects a group to add the bot to
3. Bot is added to the group
4. Bot receives Message with text `/start@botusername setup`

### Channel (?startchannel)

1. User opens `https://t.me/botusername?startchannel`
2. User selects a channel to add the bot to
3. Bot is added as channel administrator

## Parameter Rules

- Allowed characters: `A-Z`, `a-z`, `0-9`, `_`, `-`
- Length: 1-64 characters
- Case-sensitive
- For groups: delivered as `/start@botname PARAMETER`

## Gotchas

- Parameter is part of the /start message text, space-separated: "/start payload"
- If user already has a chat with the bot, they still need to press START button
- startgroup: user selects a group to add the bot to, then bot receives the parameter
- Parameters are NOT encrypted -- don't put secrets in them
- URL must use t.me domain or tg:// protocol
- Only /start command supports deep linking -- other commands cannot receive URL parameters
- Deep link parameters are visible in the URL -- do not encode sensitive information
- Maximum parameter length is 64 characters -- use a reference ID for longer data

## Patterns

- Referral tracking: `/start ref_user123` -- track who referred the new user
- Feature activation: `/start feature_premium` -- unlock specific feature or show specific content
- Resource linking: `/start doc_456` -- show specific document/item
- Authentication: `/start auth_TOKEN` -- complete login flow from external website
- Group onboarding: `?startgroup=setup` -- bot joins group and runs initial setup
- Campaign tracking: `/start campaign_summer2024` -- track marketing campaign effectiveness
- Invite codes: `/start invite_ABC` -- validate and apply invitation
