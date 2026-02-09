# Interactivity Patterns

All ways to create interactive experiences in Telegram chats.

## Quick Reference

| Pattern | Key Method(s) / Type(s) | File |
|---------|------------------------|------|
| Bot commands | setMyCommands, BotCommand | commands.md |
| Buttons with callbacks | InlineKeyboardMarkup, answerCallbackQuery | inline-keyboards.md |
| Custom keyboard below input | ReplyKeyboardMarkup | reply-keyboards.md |
| Force user text input | ForceReply | force-reply.md |
| Handle button presses | answerCallbackQuery, CallbackQuery | callback-queries.md |
| Live message editing | editMessageText | realtime-updates.md |
| Multi-page menus | editMessageText + callbacks | menus-navigation.md |
| Multi-step forms | state management + keyboards | forms-wizards.md |
| Inline queries from any chat | answerInlineQuery | inline-mode.md |
| Interactive polls & quizzes | sendPoll | polls-quizzes.md |
| Typing indicators | sendChatAction | chat-actions.md |
| Deep links with parameters | /start?param | deep-linking.md |
| Mini apps in chat | WebAppInfo | web-apps.md |
| Bot menu button | setChatMenuButton | menu-button.md |
| Random dice animations | sendDice | dice-animations.md |
| Message reactions | setMessageReaction | reactions.md |
| Visual effects on messages | message_effect_id | message-effects.md |
