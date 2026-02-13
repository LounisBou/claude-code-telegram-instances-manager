# Bot Runner Script — Design

## Problem

The heuristic-loop skill currently launches the bot app directly via `Bash` with `run_in_background: true`. This couples the app lifecycle to Claude's session:
- Task ID is lost on `/clear`
- Claude needs process management permissions (PTY, signals)
- No way to start the app independently for manual testing

## Solution

A **runner script** that owns the bot process, with a **file-based control protocol** for Claude to request restarts.

## Architecture

```
┌──────────────┐       writes        ┌──────────────────┐
│  Claude Skill │  ──────────────►   │  bot.control      │
│  (read-only   │                    │  ("restart")      │
│   process ctrl)│                    └────────┬─────────┘
│               │                             │ polls
│               │       reads                 ▼
│               │  ◄──────────────   ┌──────────────────┐
│               │                    │  bot-runner.sh    │
│               │  ◄──── reads ───── │  (owns process)  │
│               │     bot.log        │                   │
│               │     bot.status     │  python -m src... │
└──────────────┘                    └──────────────────┘
```

### File Protocol

All files live in `.claude/heuristic-loop-state/`:

| File | Writer | Reader | Purpose |
|------|--------|--------|---------|
| `bot.log` | Runner (app stdout/stderr) | Claude | Console output for debugging |
| `bot.status` | Runner | Claude | Current state: `starting`, `running`, `stopped` |
| `bot.pid` | Runner | Runner | Internal PID tracking |
| `bot.control` | Claude | Runner | Commands: `restart`, `stop` |

## Runner Script (`scripts/bot-runner.sh`)

### Usage

```bash
./scripts/bot-runner.sh              # uses config.yaml
./scripts/bot-runner.sh config.yaml  # explicit config
```

Runs in the foreground (Ctrl+C to stop). The bot is a background child process.

### Behavior

1. **Start**: launches `env -u ALL_PROXY -u all_proxy -u FTP_PROXY -u ftp_proxy -u GRPC_PROXY -u grpc_proxy -u RSYNC_PROXY python -m src.main config.yaml --debug`, redirects stdout+stderr to `bot.log`, writes PID to `bot.pid`, writes `running` to `bot.status`

2. **Control polling**: every 2 seconds, checks `bot.control` for commands:
   - `restart` → kills current process, truncates log, starts fresh
   - `stop` → kills process, writes `stopped`, exits

3. **Crash recovery**: if the bot process dies unexpectedly, detects via PID check and auto-restarts

4. **Cleanup**: on SIGINT/SIGTERM, kills bot, writes `stopped`, removes stale files

5. **Log truncation**: clears `bot.log` on every (re)start

### Pseudocode

```bash
#!/usr/bin/env bash
set -euo pipefail

STATE_DIR=".claude/heuristic-loop-state"
CONFIG="${1:-config.yaml}"
POLL_INTERVAL=2
UNSET_VARS=(ALL_PROXY all_proxy FTP_PROXY ftp_proxy GRPC_PROXY grpc_proxy RSYNC_PROXY)

mkdir -p "$STATE_DIR"

trap cleanup EXIT INT TERM

start_bot() {
    echo "starting" > bot.status
    : > bot.log  # truncate
    env -u SOCKS_VARS... python -m src.main "$CONFIG" --debug >> bot.log 2>&1 &
    echo $! > bot.pid
    echo "running" > bot.status
}

kill_bot() {
    kill $(cat bot.pid) 2>/dev/null; wait ... || true
    rm -f bot.pid
}

cleanup() {
    kill_bot
    echo "stopped" > bot.status
    rm -f bot.pid bot.control
}

# Initial start
rm -f bot.control
start_bot

# Main loop
while true; do
    sleep $POLL_INTERVAL

    # Check if bot is alive
    if ! kill -0 $(cat bot.pid) 2>/dev/null; then
        start_bot  # crash recovery
    fi

    # Check for commands
    if [ -f bot.control ]; then
        cmd=$(cat bot.control)
        rm -f bot.control
        case $cmd in
            restart) kill_bot; start_bot ;;
            stop) exit 0 ;;
        esac
    fi
done
```

## Skill Changes

### `heuristic-loop:test-and-gather` — Step 1

**Before:** Runs `python -m src.main config.yaml --debug` with `run_in_background: true`. Uses `TaskOutput` to read console.

**After:**
- Check `bot.status`. If `running`, proceed.
- If missing or `stopped`, tell user: "Start the runner: `./scripts/bot-runner.sh`"
- Read console logs via `Read` tool on `bot.log`
- Remove all `TaskOutput` references

### `heuristic-loop:verify-one` — Step 5

**Before:** `TaskStop` + new `Bash` background task.

**After:**
- Write `restart` to `bot.control`
- Poll `bot.status` every 2-3s until `running` (timeout ~15s)
- Wait a few more seconds for Telegram registration
- Read `bot.log` to confirm startup message

### `heuristic-loop:fix-one` — No changes

### `heuristic-loop` (orchestrator) — Minor update

Add note in startup protocol that the runner script must be running externally.

## Implementation Tasks

1. Create `scripts/bot-runner.sh` with the behavior described above
2. Update `heuristic-loop:test-and-gather/SKILL.md` — replace app launch with status check + log file reading
3. Update `heuristic-loop:verify-one/SKILL.md` — replace TaskStop/restart with control file protocol
4. Update `heuristic-loop/SKILL.md` — add runner prerequisite to startup protocol
5. Add `.claude/heuristic-loop-state/bot.*` to `.gitignore`
