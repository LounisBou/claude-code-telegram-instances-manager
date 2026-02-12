# ---- Real captured ANSI data from Claude Code sessions ----

# Real startup status bar (captured from PTY)
REAL_STATUS_BAR_ANSI = (
    "\x1b[34mclaude-instance-manager\x1b[1C\x1b[90m│\x1b[1C"
    "\x1b[32m⎇\x1b[1Cmain\x1b[1C⇡7\x1b[1C\x1b[90m│\x1b[1C"
    "\x1b[38;5;100mUsage:\x1b[1C32%\x1b[1C███▎░░░░░░\x1b[39m"
)

# Real trust prompt (captured from untrusted folder)
REAL_TRUST_PROMPT_ANSI = (
    "\x1b[38;5;153m❯\x1b[1C\x1b[38;5;246m1.\x1b[1C"
    "\x1b[38;5;153mYes,\x1b[1CI\x1b[1Ctrust\x1b[1Cthis\x1b[1Cfolder\x1b[39m\n"
    "\x1b[3C\x1b[38;5;246m2.\x1b[1C\x1b[39mNo,\x1b[1Cexit"
)

# Real /exit command styling
REAL_EXIT_ANSI = "\x1b[38;2;177;185;249m/exit\x1b[39m"

# Real error message
REAL_ERROR_ANSI = (
    "\x1b[38;2;255;107;128m1 MCP server failed"
    "\x1b[38;2;153;153;153m ·\x1b[1C/mcp\x1b[39m"
)

# Real startup sequence with terminal modes
REAL_STARTUP_ANSI = (
    "\x1b[?2026h\r\r\n"
    "\x1b[38;5;220m────────\x1b[39m\r\r\n"
    "\x1b[1C\x1b[1mAccessing\x1b[1Cworkspace:\x1b[22m\r\r\n"
)

# Real welcome box
REAL_BOX_ANSI = (
    "\x1b[38;5;174m╭───\x1b[1CClaude\x1b[1CCode\x1b[1C"
    "\x1b[38;5;246mv2.1.37\x1b[1C"
    "\x1b[38;5;174m──────────────────────────────────────────────────────╮\x1b[39m"
)


# ---- Real captured screen data (from docs/claude-ui-patterns.md) ----

# Real IDLE screen
REAL_IDLE_SCREEN = [
    "",
    "⏺ ping",
    "",
    "────────────────────────────────────────────────────────────",
    "❯ Try \"write a test for config.py\"",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59",
]

# Real THINKING screen
REAL_THINKING_SCREEN = [
    "",
    "❯ What is 2+2?",
    "",
    "✶ Activating sleeper agents…",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59",
]

# Real STREAMING screen
REAL_STREAMING_SCREEN = [
    "",
    "❯ What is 2+2?",
    "",
    "⏺ The answer is 4.",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░ ↻ 9:59",
]

# Real TOOL_REQUEST screen (approval menu)
REAL_TOOL_REQUEST_SCREEN = [
    "",
    "────────────────────────────────",
    " Create file",
    " ../../../../tmp/test_capture.txt",
    "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
    "  1 hello",
    "╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌",
    " Do you want to create test_capture.txt?",
    " ❯ 1. Yes",
    "   2. Yes, allow all edits during this session (shift+tab)",
    "   3. No",
    "",
    " Esc to cancel · Tab to amend",
]

# Real TOOL_RUNNING screen
REAL_TOOL_RUNNING_SCREEN = [
    "",
    "  Bash(echo 'capture_test_ok')",
    "  ⎿  Running…",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real TOOL_RESULT screen
REAL_TOOL_RESULT_SCREEN = [
    "",
    "  ⎿  Added 4 lines, removed 1 line",
    "       91  self.raw_log.extend(chunk)",
    "       92  ...",
    "       94 -  except (pexpect.TIMEOUT, pexpect.EOF):",
    "       94 +  except pexpect.TIMEOUT:",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real TODO_LIST screen
REAL_TODO_LIST_SCREEN = [
    "  5 tasks (2 done, 1 in progress, 2 open) · ctrl+t to hide tasks",
    "  ◼ Fix substring-vs-set check in smoke test",
    "  ◻ Fix stale docstring \"steps 1-8\" to \"steps 1-5\"",
    "  ✔ Separate pexpect.EOF from TIMEOUT in feed()",
    "  ✔ Replace bare except Exception: pass in close()",
    "  ✔ Remove dead since_last variable",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real PARALLEL_AGENTS screen
REAL_PARALLEL_AGENTS_SCREEN = [
    "⏺ 4 agents launched (ctrl+o to expand)",
    "   ├─ pr-review-toolkit:code-reviewer (Code review of PR changes)",
    "   │  ⎿  Running in the background (shift+↑ to manage)",
    "   ├─ pr-review-toolkit:silent-failure-hunter (Silent failure hunting)",
    "   │  ⎿  Running in the background (shift+↑ to manage)",
    "   ├─ pr-review-toolkit:code-simplifier (Code simplification review)",
    "   │  ⎿  Running in the background (shift+↑ to manage)",
    "   └─ pr-review-toolkit:comment-analyzer (Comment accuracy analysis)",
    "      ⎿  Running in the background (shift+↑ to manage)",
    "",
    "  4 local agents · 1 file +194 -192",
]

# Real BACKGROUND_TASK screen
REAL_BACKGROUND_SCREEN = [
    "",
    "⏺ 60-second timer launched.",
    "     Running in the background (↓ to manage)",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
    "  1 bash · 1 file +194 -192",
]

# Real STARTUP screen
REAL_STARTUP_SCREEN = [
    " uuuu",
    "            Claude Code v2.1.37",
    "  ▐▛███▜▌   Opus 4.6 · Claude Max",
    " ▝▜█████▛▘  ~/dev/claude-instance-manager",
    "   ▘▘ ▝▝    Opus 4.6 is here · ...",
    "",
    "   General tip: Leave code cleaner than found",
]

# Real USER_MESSAGE screen (no separators around ❯)
REAL_USER_MESSAGE_SCREEN = [
    "",
    "❯ What is 2+2? Reply with just the number, nothing else.",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real ERROR screen
REAL_ERROR_SCREEN = [
    "",
    "1 MCP server failed · /mcp",
    "",
    "────────────────────────────────────────────────────────────",
    "  claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░",
]

# Real AUTH_REQUIRED screen (OAuth login prompt — captured from PTY)
REAL_AUTH_SCREEN = [
    "Welcome to Claude Code v2.1.39",
    "…………………………………………………………………………………………………………………………………………………………",
    "     *                                       █████▓▓░",
    "                                 *         ███▓░     ░░",
    "            ░░░░░░                        ███▓░",
    "    ░░░   ░░░░░░░░░░                      ███▓░",
    "   ░░░░░░░░░░░░░░░░░░░    *                ██▓░░      ▓",
    "                                             ░▓▓███▓▓░",
    " *                                 ░░░░",
    "                                 ░░░░░░░░",
    "                               ░░░░░░░░░░░░░░░░",
    "       █████████                                        *",
    "      ██▄█████▄██                        *",
    "       █████████      *",
    "…………………█ █   █ █………………………………………………………………………………………………………………",
    " Browser didn't open? Use the url below to sign in (c to copy)",
    "https://claude.ai/oauth/authorize?code=true&client_id=9d1c250a-e61b-44d9-88ed-59",
    "44d1962f5e&response_type=code&redirect_uri=https%3A%2F%2Fplatform.claude.com%2Fo",
    "auth%2Fcode%2Fcallback&scope=org%3Acreate_api_key+user%3Aprofile+user%3Ainferenc",
    "e+user%3Asessions%3Aclaude_code+user%3Amcp_servers&code_challenge=RhdVCCckU39dk3",
    "KQT4iXsBHHgRbBDWI9tXJb4NW2dVk&code_challenge_method=S256&state=8QGJojlAQLBWdoLUZ",
    "o_k2lSWq2HuQGuISNnbsMcr8Oc",
    " Paste code here if prompted >",
]
