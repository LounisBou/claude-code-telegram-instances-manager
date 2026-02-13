# Bot Runner Script

The bot runner (`scripts/bot-runner.sh`) is a standalone process manager that runs the Telegram bot externally. It decouples the bot's lifecycle from any particular terminal session or automation tool, making it easy to start, restart, and stop the bot via simple file commands.

## Quick Start

```bash
./scripts/bot-runner.sh
```

The runner starts the bot in debug mode and stays in the foreground. Press **Ctrl+C** to stop.

## Usage

```bash
./scripts/bot-runner.sh              # uses config.yaml (default)
./scripts/bot-runner.sh config.yaml  # explicit config path
```

## How It Works

The runner manages the bot process and communicates through files in `.claude/heuristic-loop-state/`:

| File | Purpose |
|------|---------|
| `bot.log` | Bot stdout and stderr (truncated on each restart) |
| `bot.status` | Current state: `starting`, `running`, or `stopped` |
| `bot.pid` | Current bot process ID |
| `bot.control` | Write commands here to control the runner |

### Lifecycle

1. **Startup** — creates state directory, kills any stale bot process from a previous run, starts the bot
2. **Polling** — every 2 seconds, checks:
   - Is the bot process still alive? If not, auto-restarts it
   - Is there a command in `bot.control`? If so, executes it
3. **Shutdown** — on Ctrl+C or `stop` command, kills the bot and writes `stopped` to `bot.status`

### Environment

The runner automatically unsets SOCKS proxy environment variables (`ALL_PROXY`, `all_proxy`, `FTP_PROXY`, `ftp_proxy`, `GRPC_PROXY`, `grpc_proxy`, `RSYNC_PROXY`) while keeping `HTTP_PROXY`/`HTTPS_PROXY` intact.

## Controlling the Runner

Write commands to the control file:

```bash
# Restart the bot (kills current process, truncates log, starts fresh)
echo "restart" > .claude/heuristic-loop-state/bot.control

# Stop the bot and exit the runner
echo "stop" > .claude/heuristic-loop-state/bot.control
```

Commands are picked up within 2 seconds (the polling interval).

## Reading Bot Output

The bot's stdout and stderr are written to `bot.log`:

```bash
# Follow the log in real time
tail -f .claude/heuristic-loop-state/bot.log

# Check last 20 lines
tail -20 .claude/heuristic-loop-state/bot.log
```

The log is truncated every time the bot restarts, so it only contains output from the current run.

## Checking Status

```bash
cat .claude/heuristic-loop-state/bot.status
# Output: "running", "starting", or "stopped"
```

## Crash Recovery

If the bot process dies unexpectedly (crash, OOM, etc.), the runner detects it within 2 seconds and automatically restarts it. No manual intervention needed.

## Stale Process Handling

If the runner itself was killed without cleanup (e.g., `kill -9`), the next run detects the stale `bot.pid` file and kills the orphaned bot process before starting a fresh one.

## Usage with Claude Code (for AI agents)

The bot runner is designed to work with Claude Code skills that perform automated testing (the heuristic-loop). Instead of Claude launching the bot directly (which couples the process to Claude's session), the user starts the runner externally and Claude interacts through the file protocol:

- **Check if bot is running:** Read `.claude/heuristic-loop-state/bot.status`
- **Read console output:** Read `.claude/heuristic-loop-state/bot.log`
- **Request restart:** Write `restart` to `.claude/heuristic-loop-state/bot.control`
- **Request stop:** Write `stop` to `.claude/heuristic-loop-state/bot.control`

If the bot is not running when a test session starts, Claude should ask the user to run:

```bash
./scripts/bot-runner.sh
```
