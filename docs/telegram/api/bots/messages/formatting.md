# Message Formatting

Three parse modes: **MarkdownV2** (recommended), **HTML**, **Markdown** (legacy, avoid).

---

## MarkdownV2

| Entity | Syntax |
|--------|--------|
| Bold | `*bold text*` |
| Italic | `_italic text_` |
| Underline | `__underline__` |
| Strikethrough | `~strikethrough~` |
| Spoiler | `\|\|spoiler\|\|` |
| Bold italic | `*_bold italic_*` |
| Inline code | `` `inline code` `` |
| Pre-formatted | ` ```language\npre-formatted\n``` ` |
| Text link | `[text](url)` |
| Text mention | `[text](tg://user?id=123456)` |
| Custom emoji | `![emoji](tg://emoji?id=5368324170671202286)` |
| Blockquote | `>blockquote` (each line prefixed with >) |
| Expandable blockquote | `**>expandable blockquote\|\|` |

**Escaping in MarkdownV2**: These characters must be escaped with `\` when used outside special syntax:

`_`, `*`, `[`, `]`, `(`, `)`, `~`, `` ` ``, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`

---

## HTML

| Entity | Tag |
|--------|-----|
| Bold | `<b>` or `<strong>` |
| Italic | `<i>` or `<em>` |
| Underline | `<u>` or `<ins>` |
| Strikethrough | `<s>` or `<strike>` or `<del>` |
| Spoiler | `<tg-spoiler>` or `<span class="tg-spoiler">` |
| Inline code | `<code>` |
| Pre-formatted | `<pre>` or `<pre><code class="language-python">` |
| Text link | `<a href="url">text</a>` |
| Text mention | `<a href="tg://user?id=123456">text</a>` |
| Custom emoji | `<tg-emoji emoji-id="5368324170671202286">emoji</tg-emoji>` |
| Blockquote | `<blockquote>` |
| Expandable blockquote | `<blockquote expandable>` |

---

## MessageEntity

| Field | Type | Description |
|-------|------|-------------|
| type | String | Type of entity (see entity types below) |
| offset | Integer | Offset in UTF-16 code units to start of entity |
| length | Integer | Length of entity in UTF-16 code units |
| url | String | For "text_link" only -- URL to open |
| user | User | For "text_mention" only -- mentioned user |
| language | String | For "pre" only -- programming language |
| custom_emoji_id | String | For "custom_emoji" only -- unique identifier |

**Entity type values**: mention, hashtag, cashtag, bot_command, url, email, phone_number, bold, italic, underline, strikethrough, spoiler, blockquote, expandable_blockquote, code, pre, text_link, text_mention, custom_emoji

---

## Gotchas

- MarkdownV2 escaping is the #1 source of errors -- escape ALL special chars outside of formatting syntax.
- UTF-16 code units: emoji and some characters count as 2 units. `offset`/`length` use UTF-16, not byte or character offsets.
- HTML: only the tags listed above are supported. All other HTML tags are stripped.
- Nesting: bold, italic, underline, strikethrough can be nested. Blockquotes cannot contain other blockquotes.
- Legacy Markdown mode exists but has many quirks -- always use MarkdownV2 or HTML instead.
- `entities` parameter: alternative to `parse_mode`, lets you specify entities programmatically with exact offsets.
