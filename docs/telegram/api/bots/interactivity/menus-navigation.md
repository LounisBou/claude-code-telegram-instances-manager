# Menus & Navigation

Build multi-page menus, paginated lists, and nested navigation using inline keyboards and message editing.

## How It Works

1. Bot sends a message with inline keyboard (menu options)
2. User taps a button -- bot receives CallbackQuery
3. Bot edits the message text AND keyboard to show new "page"
4. Repeat -- each button press navigates to a different view

## Core Methods Used

### editMessageText (with reply_markup)

Updates both message text and keyboard in a single call. See realtime-updates.md for full parameter table.

Key parameters for menu navigation:
- chat_id + message_id: identify the menu message
- text: new page content
- reply_markup: new InlineKeyboardMarkup with updated buttons

### answerCallbackQuery

Must be called for every button press. See callback-queries.md for full parameter table.

## Pagination Pattern

For lists longer than one screen:

- Show items 1-10 with "Previous" and "Next" buttons
- callback_data encoding: "page:1", "page:2", etc.
- On callback: edit message with items for that page, update keyboard
- Disable or hide "Previous" on first page, "Next" on last page
- Optionally show page indicator: "Page 2 of 5"

## Nested Menu Pattern

For hierarchical settings/options:

- Main menu -- Category -- Sub-option
- callback_data encoding: "m:main", "m:settings", "m:s:notif"
- Always include a "Back" button to return to parent menu
- On callback: edit message text to show current menu, update keyboard buttons

## Breadcrumb Pattern

Show navigation path in message text:

- "Settings > Notifications > Sound"
- Helps user understand current location in menu hierarchy
- Update breadcrumb text with each navigation step

## callback_data Size Management

64 bytes max. Strategies:

- Short prefixes: "m:" for menu, "p:" for page, "s:" for settings
- Numeric IDs: "m:3" not "menu:notifications"
- State encoding: "s:n:1" = settings > notifications > page 1
- If you need more than 64 bytes, store state server-side and use a short reference ID

## Gotchas

- editMessageText + reply_markup: both update atomically in a single API call -- always update both together
- Stale callbacks: user may press buttons on old menus. Always validate current state.
- callback_data 64-byte limit: plan data format carefully. Use short codes.
- Empty keyboard: pass InlineKeyboardMarkup with empty inline_keyboard array to remove all buttons
- Message text must change: if only keyboard changes, use editMessageReplyMarkup instead
- "message is not modified" error: occurs when both text and keyboard are identical to current state
- 48-hour message age limit: older messages cannot be edited

## Patterns

- Breadcrumb in text: "Settings > Notifications > Sound" to show current location
- Confirm/Cancel: final screen with "Confirm" / "Cancel" buttons before taking action
- Item detail: list view -- tap item -- show details with "Back to list" button
- Dynamic buttons: change button text to show selected state: "* Option A" / "Option B"
- Grid layout: multiple buttons per row for compact option display
- Close button: include a "Close" button that deletes the menu message or removes buttons
