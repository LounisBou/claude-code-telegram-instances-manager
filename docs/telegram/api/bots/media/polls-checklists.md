# Polls & Checklists

## sendPoll

Send a native poll.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| question | String | Yes | Poll question, 1-300 characters |
| options | Array of InputPollOption | Yes | List of 2-10 answer options |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| question_parse_mode | String | No | Parsing mode for the question text |
| question_entities | Array of MessageEntity | No | Special entities in the question text |
| is_anonymous | Boolean | No | True if the poll is anonymous (default: True) |
| type | String | No | Poll type: "regular" (default) or "quiz" |
| allows_multiple_answers | Boolean | No | True if the poll allows multiple answers (regular polls only) |
| correct_option_id | Integer | No | 0-based index of the correct answer option (required for quiz polls) |
| explanation | String | No | Text shown when a user chooses an incorrect answer in quiz mode, 0-200 characters |
| explanation_parse_mode | String | No | Parsing mode for the explanation text |
| explanation_entities | Array of MessageEntity | No | Special entities in the explanation text |
| open_period | Integer | No | Time in seconds the poll will be active after creation (5-600). Cannot be used with close_date |
| close_date | Integer | No | Unix timestamp when the poll will be automatically closed. Cannot be used with open_period |
| is_closed | Boolean | No | Pass True to create the poll in an already-closed state (useful for previews) |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## stopPoll

Stop a poll that was sent by the bot.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Identifier of the target chat |
| message_id | Integer | Yes | Identifier of the original poll message |
| business_connection_id | String | No | Unique identifier of the business connection |
| reply_markup | InlineKeyboardMarkup | No | Inline keyboard |

**Returns:** Poll

---

## sendChecklist

Send a checklist.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Unique identifier for target chat or username (@channelusername) |
| checklist | InputChecklist | Yes | Checklist to send |
| business_connection_id | String | No | Unique identifier of the business connection |
| message_thread_id | Integer | No | Unique identifier for the target message thread (topic) in forums |
| disable_notification | Boolean | No | Send message silently (no notification sound) |
| protect_content | Boolean | No | Protect message content from forwarding and saving |
| allow_paid_broadcast | Boolean | No | Allow sending to paid subscribers of the channel |
| message_effect_id | String | No | Unique identifier of the message effect to apply |
| reply_parameters | ReplyParameters | No | Description of the message to reply to |
| reply_markup | InlineKeyboardMarkup or ReplyKeyboardMarkup or ReplyKeyboardRemove or ForceReply | No | Additional interface options |

**Returns:** Message

---

## Types

### Poll

Contains information about a poll.

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique poll identifier |
| question | String | Poll question, 1-300 characters |
| question_entities | Array of MessageEntity | Optional. Special entities in the question |
| options | Array of PollOption | List of poll options |
| total_voter_count | Integer | Total number of users that voted in the poll |
| is_closed | Boolean | True if the poll is closed |
| is_anonymous | Boolean | True if the poll is anonymous |
| type | String | Poll type: "regular" or "quiz" |
| allows_multiple_answers | Boolean | True if the poll allows multiple answers |
| correct_option_id | Integer | Optional. 0-based index of the correct answer (quiz polls only) |
| explanation | String | Optional. Text shown when a user chooses an incorrect answer (quiz polls) |
| explanation_entities | Array of MessageEntity | Optional. Special entities in the explanation |
| open_period | Integer | Optional. Amount of time in seconds the poll will be active |
| close_date | Integer | Optional. Unix timestamp when the poll will be automatically closed |

### PollOption

Contains information about one answer option in a poll.

| Field | Type | Description |
|-------|------|-------------|
| text | String | Option text, 1-100 characters |
| text_entities | Array of MessageEntity | Optional. Special entities in the option text |
| voter_count | Integer | Number of users that voted for this option |

### InputPollOption

Contains information about one answer option in a poll to be sent.

| Field | Type | Description |
|-------|------|-------------|
| text | String | Option text, 1-100 characters |
| text_parse_mode | String | Optional. Parsing mode for the text |
| text_entities | Array of MessageEntity | Optional. Special entities in the text |

### PollAnswer

Represents an answer of a user in a non-anonymous poll.

| Field | Type | Description |
|-------|------|-------------|
| poll_id | String | Unique poll identifier |
| voter_chat | Chat | Optional. The chat that changed the answer (for chat-level votes) |
| user | User | Optional. The user that changed the answer (for user-level votes) |
| option_ids | Array of Integer | 0-based identifiers of the chosen answer options (may be empty if vote was retracted) |

### Checklist

Contains information about a checklist.

| Field | Type | Description |
|-------|------|-------------|
| title | String | Checklist title |
| tasks | Array of ChecklistTask | List of tasks in the checklist |
| others_can_add_tasks | Boolean | True if other chat members can add tasks |
| others_can_toggle_tasks | Boolean | True if other chat members can toggle task completion |

### ChecklistTask

Represents a task in a checklist.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Task identifier within the checklist |
| text | String | Task text |
| text_entities | Array of MessageEntity | Optional. Special entities in the task text |
| is_completed | Boolean | True if the task has been marked as completed |

### InputChecklist

Represents a checklist to be sent.

| Field | Type | Description |
|-------|------|-------------|
| title | String | Checklist title, 1-255 characters |
| tasks | Array of InputChecklistTask | List of 1-30 tasks |
| others_can_add_tasks | Boolean | Optional. True to allow other chat members to add tasks |
| others_can_toggle_tasks | Boolean | Optional. True to allow other chat members to toggle task completion |

### InputChecklistTask

Represents a task in a checklist to be sent.

| Field | Type | Description |
|-------|------|-------------|
| text | String | Task text, 1-500 characters |
| text_parse_mode | String | Optional. Parsing mode for the task text |
| text_entities | Array of MessageEntity | Optional. Special entities in the task text |

---

## Gotchas

- Quiz polls: `correct_option_id` is required when `type` is "quiz".
- `allows_multiple_answers` only works with regular polls, not quiz polls.
- `open_period` and `close_date` are mutually exclusive -- use one or the other.
- Checklist tasks can be toggled by any chat member if `others_can_toggle_tasks` is True.
- PollAnswer: the `voter_chat` field is present when a chat (e.g., a channel) votes, while `user` is present when a user votes. At least one is always present.
