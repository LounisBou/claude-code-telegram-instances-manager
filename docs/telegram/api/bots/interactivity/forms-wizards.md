# Forms & Wizards

Collect multi-step user input through conversation flow, using state management to track progress.

## How It Works

1. Bot sends first question (with ForceReply or reply keyboard)
2. User responds -- bot stores answer and sends next question
3. Repeat until all fields collected
4. Bot shows summary and confirmation

## State Management Approaches

The bot must track which step each user is on:

- **In-memory dict**: `user_states[user_id] = {"step": "email", "name": "John"}`
- **Database**: store conversation state per user in persistent storage
- **callback_data**: encode minimal state in button data (limited by 64-byte max)
- **Redis/cache**: fast ephemeral storage with TTL for automatic cleanup

## Input Collection Methods

1. **Free text**: ForceReply or just wait for next message -- flexible but needs validation
2. **Reply keyboard**: predefined options -- user picks one -- text is sent as message
3. **Inline keyboard**: callback_data -- structured, no text parsing needed
4. **Mixed**: inline keyboard for choices, ForceReply for free text fields

## Step-by-Step Flow

### Step Tracking

For each user, maintain:
- Current step identifier (e.g., "name", "email", "confirm")
- Collected data so far (e.g., {"name": "John", "email": "john@example.com"})
- Timestamp of last interaction (for timeout handling)

### Advancing Steps

On each user message:
1. Look up user's current step
2. Validate input for current step
3. If valid: store value, determine next step, send next question
4. If invalid: re-send current question with error message

### Completion

After last step:
1. Show summary of all collected data
2. Present "Confirm" / "Edit" / "Cancel" options
3. On confirm: process the data
4. On edit: jump back to specific step
5. On cancel: clear state

## Cancellation

Always provide a way to abort:

- "Cancel" button in reply keyboard
- "Cancel" inline button in each step
- /cancel command handler
- Automatic timeout after period of inactivity

## Validation

After each step:
- Validate input format (email, phone, number range, date, etc.)
- If invalid: re-ask with error message, don't advance step
- If valid: store value, advance to next step
- Consider allowing "back" to go to previous step

## Gotchas

- State persistence: in-memory state is lost on restart. Use database for production.
- Group chats: use reply_to_message or ForceReply with selective=true to avoid cross-talk between users
- Timeout: user may abandon the form. Set a timeout and cleanup state.
- Concurrent forms: user might start a new form before finishing the current one. Handle gracefully (either cancel old form or block new one).
- Privacy: don't store sensitive data (passwords, payment info) in bot state longer than needed
- Message order: in rare cases, messages may arrive out of order. Use reply_to_message to match responses.
- Bot restart: all in-memory state is lost. Users mid-form will need to start over unless state is persisted.

## Patterns

- Linear wizard: step1 -- step2 -- step3 -- confirm -- submit
- Editable form: show summary with "Edit name", "Edit email" inline buttons to jump to specific steps
- Optional fields: "Skip" button alongside input request
- Progressive disclosure: show only relevant follow-up questions based on previous answers
- Confirmation: show all collected data, ask "Is this correct?" before final action
- Default values: pre-fill fields and let user change or accept
- Back navigation: "Back" button to return to previous step without losing data
