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
