# Usage Guide

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start`, `/new` | Select a project and start a new Claude session |
| `/sessions` | List active sessions with switch/kill buttons |
| `/exit` | Kill the current active session |
| `/history` | Show recent session history |
| `/git` | Show git branch and PR info for active session |
| `/context` | Request context usage info from Claude |
| `/download <path>` | Download a file from the server |
| `/update_claude` | Update the Claude Code CLI |

## Session Lifecycle

A session follows a simple flow: **select project -> chat -> exit**.

1. Use `/start` to see a list of available projects.
2. Tap a project button to spawn a new Claude Code session attached to that project directory.
3. Type messages in the Telegram chat -- they are forwarded directly to the Claude CLI process.
4. Claude's responses are streamed back to Telegram in real time.
5. Use `/exit` to terminate the current session when you are done.

## File Uploads

You can send documents or photos directly in the Telegram chat. Uploaded files are saved to a temporary session directory (under `/tmp/claude/`), and the Claude process is notified of the new file so it can reference or process it.

## Multi-Session Management

Each user can run up to **3 concurrent sessions**, each tied to a different project.

- Use `/sessions` to view all your active sessions. The currently active session is marked with `*`.
- Tap **Switch** to change your active session to a different one.
- Tap **Kill** to terminate a session you no longer need.

Any message you type is sent to whichever session is currently active.

## Git Info

Use `/git` to display the current git branch and any associated pull request information for the active session's project. This is useful for keeping track of which branch Claude is working on.

## Context Usage

Use `/context` to ask Claude for its current context window usage. This helps you monitor how much of the conversation budget has been consumed in the active session.
