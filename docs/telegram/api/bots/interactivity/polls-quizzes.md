# Polls & Quizzes

Send interactive polls that users can vote on directly in the chat.

## sendPoll

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Target chat |
| question | String | Yes | Question text (1-300 chars) |
| question_parse_mode | String | No | Parse mode for question text |
| question_entities | Array of MessageEntity | No | Special entities in question text |
| options | Array of InputPollOption | Yes | Answer options (2-10) |
| is_anonymous | Boolean | No | Anonymous poll (default true) |
| type | String | No | "regular" or "quiz" (default "regular") |
| allows_multiple_answers | Boolean | No | Multiple answers (regular only) |
| correct_option_id | Integer | No | Correct answer index, 0-based (quiz only, required for quiz) |
| explanation | String | No | Text shown after quiz answer (0-200 chars) |
| explanation_parse_mode | String | No | Parse mode for explanation |
| explanation_entities | Array of MessageEntity | No | Special entities in explanation |
| open_period | Integer | No | Auto-close after N seconds (5-600) |
| close_date | Integer | No | Unix timestamp to auto-close |
| is_closed | Boolean | No | Create already closed |
| message_thread_id | Integer | No | Forum topic identifier |
| (+ standard send params) | | | reply_markup, etc. |

**Returns:** Message

## InputPollOption

| Field | Type | Description |
|-------|------|-------------|
| text | String | Option text (1-100 chars) |
| text_parse_mode | String | Parse mode for option text |
| text_entities | Array of MessageEntity | Special entities in option text |

## stopPoll

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Integer or String | Yes | Chat identifier |
| message_id | Integer | Yes | Poll message identifier |
| business_connection_id | String | No | Business connection identifier |
| reply_markup | InlineKeyboardMarkup | No | Updated keyboard |

**Returns:** Poll

## Poll Updates

- **poll** update: poll state changed (new votes, poll closed)
- **poll_answer** update: specific user's vote changed (non-anonymous polls only)

## Poll

| Field | Type | Description |
|-------|------|-------------|
| id | String | Unique poll identifier |
| question | String | Question text |
| question_entities | Array of MessageEntity | Special entities in question (optional) |
| options | Array of PollOption | List of options |
| total_voter_count | Integer | Total number of voters |
| is_closed | Boolean | Whether the poll is closed |
| is_anonymous | Boolean | Whether the poll is anonymous |
| type | String | "regular" or "quiz" |
| allows_multiple_answers | Boolean | Whether multiple answers are allowed |
| correct_option_id | Integer | Correct answer index (quiz only, optional) |
| explanation | String | Explanation text (quiz only, optional) |
| explanation_entities | Array of MessageEntity | Special entities in explanation (optional) |
| open_period | Integer | Auto-close period in seconds (optional) |
| close_date | Integer | Auto-close Unix timestamp (optional) |

## PollOption

| Field | Type | Description |
|-------|------|-------------|
| text | String | Option text |
| text_entities | Array of MessageEntity | Special entities in text (optional) |
| voter_count | Integer | Number of voters for this option |

## PollAnswer

| Field | Type | Description |
|-------|------|-------------|
| poll_id | String | Poll identifier |
| voter_chat | Chat | Chat that voted (optional, for anonymous polls in chats) |
| user | User | User who voted (optional) |
| option_ids | Array of Integer | Chosen option indices (0-based, empty if vote retracted) |

## Gotchas

- Quiz mode: correct_option_id is required. Only one answer allowed per user.
- Regular mode: allows_multiple_answers works only for regular polls, not quiz
- Anonymous polls: you won't receive poll_answer updates (only aggregate counts via poll update)
- open_period and close_date are mutually exclusive -- use one or the other
- Closing: send stopPoll to close manually, or use open_period/close_date for auto-close
- explanation: shown after the user answers in quiz mode. Supports formatting via explanation_parse_mode.
- question_parse_mode: allows formatted question text (bold, italic, etc.)
- Poll in reply_markup: polls cannot have InlineKeyboardMarkup with callback_data (but can have url buttons)
- Retracted votes: PollAnswer with empty option_ids means the user retracted their vote

## Patterns

- Survey: regular anonymous poll with multiple options
- Quiz: quiz mode with explanation for educational content
- Quick vote: 2-option regular poll as a decision-making tool
- Timed quiz: open_period=30 for fast-paced quiz games
- Series: send multiple polls sequentially, track answers via poll_answer
- Non-anonymous feedback: is_anonymous=false to see who voted for what
