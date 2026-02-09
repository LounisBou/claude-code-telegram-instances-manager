# Claude Code UI Patterns Reference

> Captured from real Claude Code v2.1.37 interactive sessions via pyte terminal emulator.
> Source: `scripts/captures/capture_20260209_175144/` (576KB raw PTY, 161 snapshots)

## Screen Layout

Claude Code uses an Ink/React TUI with this general layout:

```
Row 0-4:   Logo + version + model info (startup only, scrolls away)
Row N:     Conversation history (user messages + Claude responses)
Row N+1:   Separator ────────────
Row N+2:   ❯ (input prompt with optional placeholder)
Row N+3:   Separator ────────────
Row N+4:   Status bar (project │ branch │ Usage: N%)
Row N+5:   Extra status (diff stats, background task count)
```

## Unicode Markers

| Character | Unicode | Name | Meaning |
|---|---|---|---|
| `❯` | U+276F | Heavy right-pointing angle | User input prompt |
| `⏺` | U+23FA | Black circle for record | Claude response / tool header |
| `⎿` | U+23BF | Dentistry symbol | Tool output connector |
| `◻` | U+25FB | White medium square | TODO: pending task |
| `◼` | U+25FC | Black medium square | TODO: in-progress task |
| `✔` | U+2714 | Heavy check mark | TODO: completed task |
| `✶` | U+2736 | Six pointed black star | Thinking indicator |
| `✳` | U+2733 | Eight spoked asterisk | Thinking indicator |
| `✻` | U+273B | Teardrop-spoked asterisk | Thinking indicator |
| `✽` | U+273D | Heavy teardrop-spoked pinwheel | Thinking indicator |
| `✢` | U+2722 | Four teardrop-spoked asterisk | Thinking indicator |
| `·` | U+00B7 | Middle dot | Minimal thinking indicator |
| `⎇` | U+2387 | Alternative key symbol | Git branch marker |
| `⇡` | U+21E1 | Upwards dashed arrow | Commits ahead |
| `╌` | U+254C | Box drawings light double dash | File diff delimiter |
| `├` | U+251C | Box drawings light | Agent tree connector |
| `│` | U+2502 | Box drawings light vertical | Tree/status separator |
| `└` | U+2514 | Box drawings light up and right | Agent tree end |

## Screen States

### 1. STARTUP

```
 0| uuuu
 1|            Claude Code v2.1.37
 2|  ▐▛███▜▌   Opus 4.6 · Claude Max
 3| ▝▜█████▛▘  ~/dev/claude-instance-manager
 4|   ▘▘ ▝▝    Opus 4.6 is here · ...
 6|   General tip: Leave code cleaner than found
```

**Detection:** Logo block chars (`▐▛▜▌▝▘█`) on rows 0-4, "Claude Code v" text.

### 2. IDLE

```
 8| ────────────────────────────
 9| ❯ Try "write a test for config.py"
10| ────────────────────────────
11|   claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59
```

**Detection:** `❯` prompt line between two separators, status bar below. Placeholder text after `❯` (e.g. `Try "write a test for..."` or `read src/output_parser.py`).

### 3. THINKING

```
✶ Activating sleeper agents…
✳ Deploying robot army…
✻ Deploying robot army… (thought for 1s)
✽ Fixing error handling in close()…
· Assimilating human knowledge…
✳ Fixing wait_for_approval_and_response logic…
✶ Enslaving smart toasters… (running stop hook)
```

**Detection:** Line starts with thinking star chars (`✶✳✻✽✢·`) followed by humorous text ending with `…`. May include timing `(thought for Ns)` or hook info `(running stop hook)`.

**Thinking stars regex:** `^[✶✳✻✽✢·]\s+.+…`

### 4. STREAMING (Claude Response)

```
⏺ ping
⏺ The project name is claude-instance-manager.
⏺ Files in src/ (excluding __pycache__):
⏺ Done. Created /tmp/test_capture.txt with content "hello".
⏺ 60-second timer launched in the background.
```

**Detection:** Line starts with `⏺` followed by text content.

### 5. USER MESSAGE

```
❯ What is 2+2? Reply with just the number, nothing else.
❯ Read the file pyproject.toml and tell me the project name only.
❯ Create a file /tmp/test_capture.txt with the content "hello"
```

**Detection:** Line starts with `❯` followed by user text (NOT between separators — that's IDLE placeholder).

### 6. TOOL_REQUEST (Selection Menu)

```
────────────────────────────────
 Create file
 ../../../../tmp/test_capture.txt
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
  1 hello
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Do you want to create test_capture.txt?
 ❯ 1. Yes
   2. Yes, allow all edits during this session (shift+tab)
   3. No

 Esc to cancel · Tab to amend
```

**Detection:** Selection menu pattern:
- `❯ 1. <option>` (selected, with `❯` prefix)
- `  N. <option>` (unselected, indented)
- `Esc to cancel` hint line
- Preceded by question `Do you want to...?`
- May include file diff between `╌╌╌` delimiters

**Approval options (always 3):**
1. `Yes`
2. `Yes, allow all edits during this session (shift+tab)`
3. `No`

### 7. TOOL_RUNNING

```
  Bash(echo 'capture_test_ok')
  ⎿  Running…

  Bash(git status)
  ⎿  Waiting…

⏺ Write(/tmp/test_capture.txt)
  ⎿  Running PreToolUse hooks…

⏺ Update(scripts/capture_claude_ui.py)
  ⎿  Running PreToolUse hooks…
```

**Detection:** Tool header format: `Bash(command)`, `Write(path)`, `Update(path)`, `Read N file`. Followed by `⎿  Running…` or `⎿  Waiting…` or `⎿  Running PreToolUse hooks…`.

**Tool header patterns:**
- `Bash(<command>)` — bash execution
- `Write(<path>)` — file creation
- `Update(<path>)` — file edit
- `Read N file (ctrl+o to expand)` — file read (collapsed)
- `Searched for N pattern (ctrl+o to expand)` — glob search (collapsed)
- `Reading N file… (ctrl+o to expand)` — reading in progress

### 8. TOOL_RESULT

```
⏺ ⎿  Running…
     capture_test_ok

  ⎿  Added 4 lines, removed 1 line
       91  self.raw_log.extend(chunk)
       92  ...
       94 -  except (pexpect.TIMEOUT, pexpect.EOF):
       94 +  except pexpect.TIMEOUT:

─────… +7 lines (ctrl+o to expand)──────
```

**Detection:**
- `⎿  Added N lines, removed M lines` — diff summary
- Line numbers with `+`/`-` markers for additions/removals
- `+N lines (ctrl+o to expand)` — collapsed long output
- Indented output under tool header

### 9. BACKGROUND_TASK

```
     Runn    in the background (↓ to manage)
```

Status bar shows:
```
  1 bash · 1 file +194 -192
```

**Detection:** `in the background` text with `↓ to manage` or `shift+↑ to manage` hint. Background task count appears in extra status line below status bar.

### 10. PARALLEL_AGENTS

```
⏺ 4 agents launched (ctrl+o to expand)
   ├─ pr-review-toolkit:code-reviewer (Code review of PR changes)
   │  ⎿  Running in the background (shift+↑ to manage)
   ├─ pr-review-toolkit:silent-failure-hunter (Silent failure hunting in changes)
   │  ⎿  Running in the background (shift+↑ to manage)
   ├─ pr-review-toolkit:code-simplifier (Code simplification review)
   │  ⎿  Running in the background (shift+↑ to manage)
   └─ pr-review-toolkit:comment-analyzer (Comment accuracy analysis)
      ⎿  Running in the background (shift+↑ to manage)
```

Agent completion:
```
⏺ Agent "Code simplification review" completed
⏺ Code review is done. 2 of 4 agents complete.
```

Status bar:
```
  4 local agents · 1 file +194 -192
  2 local agents · 1 file +194 -192   (decreases as agents complete)
```

**Detection:**
- `N agents launched (ctrl+o to expand)` — agent summary
- Tree connectors `├─`, `│`, `└─` for agent list
- `Running in the background (shift+↑ to manage)` per agent
- `Agent "name" completed` — completion notification
- `N local agents` in status area

### 11. TODO_LIST

```
  5 tasks (2 done, 1 in progress, 2 open) · ctrl+t to hide tasks
  ◼ Fix substring-vs-set check in smoke test
  ◻ Fix stale docstring "steps 1-8" to "steps 1-5"
  ✔ Separate pexpect.EOF from TIMEOUT in feed()
  ✔ Replace bare except Exception: pass in close()
  ✔ Remove dead since_last variable
```

**Detection:**
- Header: `N tasks (M done, K open)` or `N tasks (M done, P in progress, K open) · ctrl+t to hide tasks`
- `◻` (U+25FB) = pending task
- `◼` (U+25FC) = in-progress task
- `✔` (U+2714) = completed task
- `ctrl+t to hide tasks` hint

### 12. STATUS_BAR

```
  claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 7% ▊░░░░░░░░░ ↻ 10:00
```

Extra status line (below main status bar):
```
  1 bash · 1 file +194 -192
  4 local agents · 1 file +194 -192
  1 file +194 -192
```

**Detection:** `<project> │ ⎇ <branch> ⇡<N> │ Usage: <N>%`

**Components:**
- Project name
- Branch with optional `*` (dirty)
- Commits ahead `⇡N`
- Usage percentage with progress bar (`▉░░░░░░░░░`)
- Timer `↻ M:SS`
- Optional: `N MCP server failed · /mcp`

**Extra status (optional):**
- `N bash` — background bash tasks
- `N local agents` — parallel agents running
- `N file +A -D` — file change stats

### 13. FILE_DIFF (inside TOOL_REQUEST)

```
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
  1 hello
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌

  372  # ─── Automated Scenario ───
  375 -    """Run the full automated capture scenario (steps 1-8)."""
  375 +    """Run the full automated capture scenario (steps 1-5)."""
```

**Detection:** Content between `╌╌╌` (U+254C) delimiters. Line numbers with optional `+`/`-` markers.

### 14. TABLE

```
┌─────┬───────────────────────┬─────────────────┐
│  #  │         Task          │ Validation Word │
├─────┼───────────────────────┼─────────────────┤
│ 1   │ Some task...          │ alpha           │
└─────┴───────────────────────┴─────────────────┘
```

**Detection:** Standard box-drawing characters for table borders.

## Screen Artifacts

The pyte terminal emulator produces rendering artifacts when Claude Code redraws parts of the screen. Common patterns:

1. **Overlapping text:** Two different content layers merged on the same line
   - Example: `✶─Deploying robot army…ept─Exception:─pass─in─close()───`
   - Cause: thinking indicator drawn over previous content

2. **Glitch characters:** `──...──��` or `─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────`
   - Cause: partial ANSI sequence rendering

3. **Line bleeding:** Content from one logical section appearing on another line
   - Example: `⏺ capture_test_ok              ind the code and/or conversation`
   - Cause: overlapping screen updates

**Handling strategy:** These artifacts are cosmetic noise. The parser should:
- Identify "clean" lines (no artifact overlap) vs "dirty" lines
- Use the primary content markers (`⏺`, `❯`, `◻`, `✔`, etc.) to identify line purpose
- Strip trailing artifact text after detecting the primary content

## Key Interactions

### Submitting Input
- Text must be sent separately from Enter key (`\r`)
- Sending text+Enter together triggers paste/multi-line mode
- Use `child.send(text)` → `sleep(0.15)` → `child.send(b"\r")`

### Trust Prompt
- Auto-handled by sending `\r` (confirms default selection)

### Tool Approval
- Selection menu with `❯ 1. Yes` pre-selected
- Send `\r` to confirm default selection
- Three options: Yes / Yes all session / No

### Collapsed Sections
- `(ctrl+o to expand)` — expandable sections
- `+N lines (ctrl+o to expand)` — truncated output
- `N agents launched (ctrl+o to expand)` — agent list
