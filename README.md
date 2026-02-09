# Claude Instance Manager

A Telegram bot that proxies Claude Code CLI sessions, mirroring the full terminal experience through Telegram with interactive tool approvals, multi-session support, and real-time output streaming.

## Features

- **Rich terminal mirroring** — Claude Code output is parsed via a pyte virtual terminal and streamed to Telegram in real time
- **Interactive tool approvals** — file writes, command execution, and other tool uses are forwarded as inline keyboards for explicit user confirmation
- **Multi-session management** — run up to 3 concurrent Claude sessions across different projects
- **Project auto-discovery** — scans a root directory for projects containing `.git` or `.claude` markers
- **File uploads** — send documents and photos via Telegram, automatically saved to the active project directory
- **Git integration** — view current branch and PR info for any active session
- **Debug mode** — verbose logging with PyDevMate for troubleshooting

## Quick Start

```bash
git clone https://github.com/lounisbou/claude-instance-manager.git
cd claude-instance-manager
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Create a `config.yaml` (see [Installation](docs/installation.md#configuration) for all options):

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"
  authorized_users: [YOUR_TELEGRAM_USER_ID]

projects:
  root: "/path/to/your/projects"
```

Run:

```bash
python -m src.main config.yaml
```

## Commands

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

## Documentation

- [Architecture](docs/architecture.md) — system design, module responsibilities, and data flow
- [Installation](docs/installation.md) — prerequisites, configuration, systemd deployment
- [Usage](docs/usage.md) — commands, session lifecycle, file uploads, multi-session management

## License

[MIT](LICENSE)
