# Installation

## Prerequisites

- **Python 3.11+**
- **Claude Code CLI** installed and authenticated (`claude` available in your PATH)
- **Telegram bot token** obtained from [BotFather](https://t.me/BotFather)

## Clone and Install

```bash
git clone https://github.com/lounisbou/claude-instance-manager.git
cd claude-instance-manager
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Create a `config.yaml` file at the project root with the following fields:

```yaml
telegram:
  bot_token: "YOUR_BOT_TOKEN"           # Telegram bot token from BotFather
  authorized_users: [YOUR_TELEGRAM_USER_ID]  # List of allowed Telegram user IDs

projects:
  root: "/path/to/your/projects"        # Root directory to scan for projects
  scan_depth: 1                         # How many levels deep to scan for projects

sessions:
  max_per_user: 3                       # Maximum concurrent Claude sessions per user
  output_debounce_ms: 500               # Debounce interval for output forwarding (ms)
  output_max_buffer: 2000               # Maximum output buffer size (characters)

claude:
  command: "claude"                     # Path or name of the Claude Code CLI binary
  default_args: []                      # Default arguments passed to every Claude invocation
  update_command: "claude update"       # Command used to update Claude Code CLI

database:
  path: "data/sessions.db"             # Path to the SQLite database file

debug:
  enabled: false                        # Enable debug logging
```

## Running the Bot

Start the bot with:

```bash
python -m src.main config.yaml
```

### Debug Mode

For verbose logging, use the `--debug` flag:

```bash
python -m src.main config.yaml --debug
```

## Systemd Deployment

A systemd unit file is provided at `systemd/claude-bot.service` for running the bot as a background service. Refer to that file for setup instructions.

## Development Setup

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest --cov=src -q
```
