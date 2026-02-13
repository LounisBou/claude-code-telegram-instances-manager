# Bot Runner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Decouple the bot's process lifecycle from Claude's session by introducing an external runner script with file-based control protocol.

**Architecture:** A bash wrapper script (`scripts/bot-runner.sh`) manages the bot process, writing output to a log file and polling a control file for commands. Claude skills only interact through plain files — reading `bot.log`/`bot.status` and writing `bot.control`.

**Tech Stack:** Bash, existing Python bot (`python -m src.main`)

**Design doc:** `docs/plans/2026-02-13-bot-runner-design.md`

---

### Task 1: Create the runner script

**Files:**
- Create: `scripts/bot-runner.sh`

**Step 1: Create `scripts/bot-runner.sh`**

```bash
#!/usr/bin/env bash
# bot-runner.sh — Manages the bot process lifecycle externally.
#
# Usage:
#   ./scripts/bot-runner.sh              # uses config.yaml
#   ./scripts/bot-runner.sh config.yaml  # explicit config
#
# Control:
#   Write commands to .claude/heuristic-loop-state/bot.control:
#     "restart" — stop + start the bot
#     "stop"    — stop the bot and exit the runner
#
# Files written (all in .claude/heuristic-loop-state/):
#   bot.log     — app stdout+stderr (truncated on each restart)
#   bot.status  — current state: "starting", "running", "stopped"
#   bot.pid     — current bot PID
#   bot.control — read by this script for commands (deleted after processing)

set -euo pipefail

STATE_DIR=".claude/heuristic-loop-state"
LOG_FILE="$STATE_DIR/bot.log"
PID_FILE="$STATE_DIR/bot.pid"
CONTROL_FILE="$STATE_DIR/bot.control"
STATUS_FILE="$STATE_DIR/bot.status"
CONFIG="${1:-config.yaml}"
POLL_INTERVAL=2

# SOCKS proxy vars to unset (HTTP_PROXY/HTTPS_PROXY are kept)
UNSET_VARS=(ALL_PROXY all_proxy FTP_PROXY ftp_proxy GRPC_PROXY grpc_proxy RSYNC_PROXY)

BOT_PID=""

mkdir -p "$STATE_DIR"

kill_bot() {
    if [ -n "$BOT_PID" ] && kill -0 "$BOT_PID" 2>/dev/null; then
        echo "[runner] Stopping bot (PID: $BOT_PID)..."
        kill "$BOT_PID" 2>/dev/null || true
        wait "$BOT_PID" 2>/dev/null || true
    fi
    BOT_PID=""
    rm -f "$PID_FILE"
}

start_bot() {
    echo "starting" > "$STATUS_FILE"
    : > "$LOG_FILE"  # truncate log

    # Build env -u flags
    local env_args=()
    for var in "${UNSET_VARS[@]}"; do
        env_args+=(-u "$var")
    done

    env "${env_args[@]}" python -m src.main "$CONFIG" --debug >> "$LOG_FILE" 2>&1 &
    BOT_PID=$!
    echo "$BOT_PID" > "$PID_FILE"
    echo "running" > "$STATUS_FILE"
    echo "[runner] Bot started (PID: $BOT_PID)"
}

cleanup() {
    echo "[runner] Shutting down..."
    kill_bot
    echo "stopped" > "$STATUS_FILE"
    rm -f "$PID_FILE" "$CONTROL_FILE"
    exit 0
}

trap cleanup EXIT INT TERM

# Remove stale control file from previous run
rm -f "$CONTROL_FILE"

# Initial start
start_bot

# Main loop: poll for commands and monitor process health
while true; do
    sleep "$POLL_INTERVAL"

    # Check if bot process is still alive
    if [ -n "$BOT_PID" ] && ! kill -0 "$BOT_PID" 2>/dev/null; then
        echo "[runner] Bot process died unexpectedly, restarting..."
        BOT_PID=""
        start_bot
    fi

    # Check for control commands
    if [ -f "$CONTROL_FILE" ]; then
        cmd=$(cat "$CONTROL_FILE")
        rm -f "$CONTROL_FILE"

        case "$cmd" in
            restart)
                echo "[runner] Restart requested"
                kill_bot
                start_bot
                ;;
            stop)
                echo "[runner] Stop requested"
                exit 0  # cleanup trap handles the rest
                ;;
            *)
                echo "[runner] Unknown command: $cmd"
                ;;
        esac
    fi
done
```

**Step 2: Make it executable**

Run: `chmod +x scripts/bot-runner.sh`

**Step 3: Manually test the script**

Run: `./scripts/bot-runner.sh` in a terminal. Verify:
- Bot starts and output appears in `.claude/heuristic-loop-state/bot.log`
- `bot.status` reads `running`
- `bot.pid` contains a valid PID

Test restart: `echo "restart" > .claude/heuristic-loop-state/bot.control`
- Bot stops and restarts
- `bot.log` is truncated (old output gone)

Test stop: `echo "stop" > .claude/heuristic-loop-state/bot.control`
- Bot stops, runner exits
- `bot.status` reads `stopped`

Test Ctrl+C:
- Bot stops, `bot.status` reads `stopped`

**Step 4: Commit**

```bash
git add scripts/bot-runner.sh
git commit -m 'feat: add bot-runner.sh — external process manager with file-based control'
```

---

### Task 2: Update test-and-gather skill — replace app launch with status check

**Files:**
- Modify: `.claude/skills/heuristic-loop:test-and-gather/SKILL.md`

This task changes three sections:
1. Evidence action counter — remove `TaskOutput` reference
2. Step 1 — replace direct launch with status file check
3. Step 6 — replace `TaskOutput` console reading with `Read` on bot.log

**Step 1: Update evidence action counter (line 31)**

Replace:
```
- `TaskOutput` (console log reads)
```

With:
```
- `Read` on `bot.log` (console log reads)
```

**Step 2: Replace Step 1 "Start the App" (lines 75-81)**

Replace the entire Step 1 section:

```markdown
### 1. Start the App (If Not Running)

```bash
python -m src.main config.yaml --debug
```

Run with `run_in_background: true`. Save the task ID for reading console logs later.
```

With:

```markdown
### 1. Confirm the App Is Running

Check `.claude/heuristic-loop-state/bot.status`:
- If it reads `running` → proceed to Step 2
- If it doesn't exist or reads `stopped` → tell the user: **"Start the runner first: `./scripts/bot-runner.sh`"** and wait

The runner script manages the bot process externally. Console output goes to `.claude/heuristic-loop-state/bot.log`.
```

**Step 3: Update Step 6 console reading (line 133)**

Replace:
```
**Console second** (`TaskOutput` with `block=false` on saved task ID): Look for `ERROR`/`WARNING`, tracebacks, unexpected state transitions, timestamp gaps.
```

With:
```
**Console second** (`Read` on `.claude/heuristic-loop-state/bot.log`, focus on the last ~50 lines): Look for `ERROR`/`WARNING`, tracebacks, unexpected state transitions, timestamp gaps.
```

**Step 4: Commit**

```bash
git add .claude/skills/heuristic-loop:test-and-gather/SKILL.md
git commit -m 'docs: update test-and-gather skill to use bot.log instead of TaskOutput'
```

---

### Task 3: Update verify-one skill — replace TaskStop/restart with control file

**Files:**
- Modify: `.claude/skills/heuristic-loop:verify-one/SKILL.md`

**Step 1: Replace Step 5 "Restart the App" (lines 112-123)**

Replace:

```markdown
### 5. Restart the App

```bash
# Stop current instance
# (use TaskStop on the background task ID)

# Restart
python -m src.main config.yaml --debug
# (run_in_background: true, save new task ID)
```

Wait for "Bot is running" in logs.
```

With:

```markdown
### 5. Restart the App

Request a restart via the runner's control file:

```bash
echo "restart" > .claude/heuristic-loop-state/bot.control
```

Then poll `.claude/heuristic-loop-state/bot.status` every 2-3 seconds until it reads `running` (timeout after ~15 seconds).

After status shows `running`, wait ~5 more seconds for the bot to register with Telegram, then read the last lines of `.claude/heuristic-loop-state/bot.log` to confirm the bot started successfully.
```

**Step 2: Update Step 6 console log checking (line 132)**

In Section 6 "Live Re-Test via Telegram", step 4 says "Check console logs for any new errors/warnings". This is fine as-is — the skill already reads console via whatever method is current. But add clarity by replacing line 132:

```
4. Check console logs for any new errors/warnings
```

With:

```
4. Check `.claude/heuristic-loop-state/bot.log` for any new errors/warnings
```

**Step 3: Commit**

```bash
git add .claude/skills/heuristic-loop:verify-one/SKILL.md
git commit -m 'docs: update verify-one skill to use control file for app restart'
```

---

### Task 4: Update orchestrator skill — add runner prerequisite

**Files:**
- Modify: `.claude/skills/heuristic-loop/SKILL.md`

**Step 1: Add runner prerequisite to Startup Protocol (after line 86)**

In the "Startup Protocol" section, add a step 0 before the existing check. Replace:

```
1. Check if .claude/heuristic-loop-state/state.md exists
```

With:

```
0. Verify the bot runner is active:
   Read .claude/heuristic-loop-state/bot.status
   → "running": proceed
   → Missing or "stopped": tell user: "Start the runner: ./scripts/bot-runner.sh"
      Wait for user confirmation before continuing.
1. Check if .claude/heuristic-loop-state/state.md exists
```

**Step 2: Commit**

```bash
git add .claude/skills/heuristic-loop/SKILL.md
git commit -m 'docs: add runner prerequisite to heuristic-loop orchestrator startup'
```

---

### Task 5: End-to-end validation

**Step 1: Start the runner in a terminal**

```bash
./scripts/bot-runner.sh
```

Verify `bot.status` reads `running` and `bot.log` has output.

**Step 2: Test restart from Claude's perspective**

```bash
echo "restart" > .claude/heuristic-loop-state/bot.control
sleep 5
cat .claude/heuristic-loop-state/bot.status   # should say "running"
cat .claude/heuristic-loop-state/bot.log       # should have fresh startup logs
```

**Step 3: Test stop**

```bash
echo "stop" > .claude/heuristic-loop-state/bot.control
sleep 3
cat .claude/heuristic-loop-state/bot.status   # should say "stopped"
```

**Step 4: Review all skill files for stale references**

Search all four SKILL.md files for `TaskOutput`, `TaskStop`, `run_in_background`, `task ID`. There should be zero matches.

Run:
```bash
grep -rn "TaskOutput\|TaskStop\|run_in_background\|task ID\|task_id" .claude/skills/heuristic-loop*/SKILL.md
```

Expected: no output (no matches).
