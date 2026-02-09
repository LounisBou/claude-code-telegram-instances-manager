#!/usr/bin/env python3
"""Capture Claude Code interactive UI states for parser development.

Run from a SEPARATE terminal (not inside Claude Code):
    python scripts/capture_claude_ui.py

Automated scenario triggers all major UI states, then drops into
manual mode for edge case exploration. All raw PTY bytes and pyte
screen snapshots are saved for analysis.

Output: scripts/captures/<timestamp>/
"""

import json
import os
import select
import sys
import time
from datetime import datetime
from pathlib import Path

import pexpect
import pyte

CWD = os.path.expanduser("~/dev/claude-instance-manager")
ROWS, COLS = 40, 120
CAPTURE_DIR = Path(__file__).parent / "captures"


class CaptureSession:
    """Manages a Claude Code session with detailed UI state capture."""

    def __init__(self):
        self.screen = pyte.Screen(COLS, ROWS)
        self.stream = pyte.Stream(self.screen)
        self.child = None
        self.raw_log = bytearray()
        self.snapshots = []
        self.events = []
        self.start_time = time.time()

    def elapsed(self):
        return round(time.time() - self.start_time, 2)

    def log(self, event_type, detail=""):
        entry = {"t": self.elapsed(), "type": event_type, "detail": detail}
        self.events.append(entry)
        print(f"  [{self.elapsed():7.2f}s] {event_type}: {detail}")

    def snapshot(self, label):
        """Save current pyte screen with label."""
        lines = []
        for i, line in enumerate(self.screen.display):
            stripped = line.rstrip()
            if stripped:
                lines.append({"row": i, "text": stripped})
        snap = {
            "t": self.elapsed(),
            "label": label,
            "lines": lines,
            "raw_offset": len(self.raw_log),
        }
        self.snapshots.append(snap)
        return lines

    def dump(self, label):
        """Print + snapshot current screen."""
        lines = self.snapshot(label)
        print(f"\n  {'─' * 60}")
        print(f"  SCREEN: {label} (t={self.elapsed():.2f}s)")
        print(f"  {'─' * 60}")
        for entry in lines:
            print(f"  {entry['row']:2d}| {entry['text']}")
        if not lines:
            print("  (empty screen)")
        print(f"  {'─' * 60}\n")
        return lines

    def feed(self, seconds, poll=0.3):
        """Read PTY data for duration, feed into pyte. Returns bytes read."""
        start = time.time()
        total = 0
        while time.time() - start < seconds:
            try:
                chunk = self.child.read_nonblocking(size=16384, timeout=poll)
                if chunk:
                    self.raw_log.extend(chunk)
                    self.stream.feed(chunk.decode("utf-8", errors="replace"))
                    total += len(chunk)
            except (pexpect.TIMEOUT, pexpect.EOF):
                pass
        return total

    def wait_stable(self, max_wait=60, stable_for=6, min_wait=3):
        """Feed until screen stops changing. Returns final screen text."""
        prev = self.screen_text()
        last_change = time.time()
        start = time.time()
        changes = 0

        while time.time() - start < max_wait:
            self.feed(0.5)
            curr = self.screen_text()
            if curr != prev:
                changes += 1
                last_change = time.time()
                prev = curr

            elapsed = time.time() - start
            since_change = time.time() - last_change
            if since_change > stable_for and elapsed > min_wait:
                break

        self.log("stable", f"{changes} changes in {time.time()-start:.1f}s")
        return prev

    def screen_text(self):
        return "\n".join(self.screen.display)

    def screen_has(self, *keywords):
        """Check if any keyword appears on screen (case-insensitive)."""
        text = self.screen_text().lower()
        return any(k.lower() in text for k in keywords)

    def spawn(self):
        """Start Claude Code."""
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = os.path.expanduser("~/.claude-work")

        self.child = pexpect.spawn(
            "claude",
            args=[],
            cwd=CWD,
            encoding=None,
            timeout=300,
            dimensions=(ROWS, COLS),
            env=env,
        )
        self.log("spawn", "Claude Code started")

    def send_raw(self, data, label=None):
        """Send raw bytes."""
        self.log("send_raw", label or repr(data)[:40])
        if isinstance(data, str):
            data = data.encode("utf-8")
        self.child.send(data)

    def send_line(self, text, label=None):
        """Send text + Enter."""
        self.log("send_line", label or text[:60])
        if isinstance(text, str):
            text = text.encode("utf-8")
        self.child.sendline(text)

    def send_key(self, key_name):
        """Send special keys."""
        keys = {
            "enter": b"\r",
            "escape": b"\x1b",
            "up": b"\x1b[A",
            "down": b"\x1b[B",
            "tab": b"\t",
            "ctrl-c": b"\x03",
        }
        data = keys.get(key_name, key_name.encode("utf-8"))
        self.log("send_key", key_name)
        self.child.send(data)

    def wait_for_approval(self, max_wait=90):
        """Wait for tool approval prompt, take snapshot, approve it."""
        start = time.time()
        prev = self.screen_text()
        while time.time() - start < max_wait:
            self.feed(1)
            curr = self.screen_text()
            if curr != prev:
                prev = curr
                lower = curr.lower()
                # Tool approval patterns
                if any(k in lower for k in [
                    "[y/n]", "(y)", "allow", "approve",
                    "do you want", "permission",
                ]):
                    self.dump("tool_approval_detected")
                    self.log("tool_approval", "detected — sending Y")
                    self.send_line("y", label="approve tool")
                    self.feed(2)
                    return True

            # Check if response came without approval (auto-approved or no tool)
            elapsed = time.time() - start
            if elapsed > 20:
                self.log("no_approval", "no tool prompt seen after 20s")
                return False

        self.log("timeout", "wait_for_approval timed out")
        return False

    def save(self, session_name):
        """Save all capture data to disk."""
        outdir = CAPTURE_DIR / session_name
        outdir.mkdir(parents=True, exist_ok=True)

        # Raw PTY bytes
        (outdir / "raw_pty.bin").write_bytes(bytes(self.raw_log))

        # Snapshots
        (outdir / "snapshots.json").write_text(
            json.dumps(self.snapshots, indent=2, ensure_ascii=False)
        )

        # Events
        (outdir / "events.json").write_text(
            json.dumps(self.events, indent=2, ensure_ascii=False)
        )

        # Human-readable report
        with open(outdir / "report.txt", "w") as f:
            f.write(f"Claude Code UI Capture Report\n")
            f.write(f"{'=' * 50}\n")
            f.write(f"Session: {session_name}\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Terminal: {ROWS}x{COLS}\n")
            f.write(f"Raw bytes: {len(self.raw_log)}\n")
            f.write(f"Snapshots: {len(self.snapshots)}\n")
            f.write(f"Events: {len(self.events)}\n\n")

            f.write("EVENTS:\n")
            for ev in self.events:
                f.write(f"  [{ev['t']:7.2f}s] {ev['type']}: {ev['detail']}\n")

            f.write(f"\nSNAPSHOTS:\n")
            for snap in self.snapshots:
                f.write(f"\n--- {snap['label']} (t={snap['t']:.2f}s) ---\n")
                for entry in snap["lines"]:
                    f.write(f"  {entry['row']:2d}| {entry['text']}\n")

        print(f"\n  Saved to: {outdir}/")
        print(f"    raw_pty.bin    ({len(self.raw_log)} bytes)")
        print(f"    snapshots.json ({len(self.snapshots)} snapshots)")
        print(f"    events.json    ({len(self.events)} events)")
        print(f"    report.txt")

    def close(self):
        try:
            self.send_line("/exit", label="/exit")
            time.sleep(3)
            self.child.close()
        except Exception:
            pass


# ─── Automated Scenario ─────────────────────────────────────────────

def run_automated(s):
    """Run the automated capture scenario."""

    # ── Step 1: Startup ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 1/8: Startup                       │")
    print("└──────────────────────────────────────────┘")
    s.feed(12)
    s.dump("startup_raw")

    # ── Step 2: Trust prompt ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 2/8: Trust Prompt                   │")
    print("└──────────────────────────────────────────┘")
    if s.screen_has("trust", "Yes, I trust", "trust this folder"):
        s.dump("trust_prompt")
        s.send_raw(b"\r", label="confirm trust (\\r)")
        s.feed(10)
        s.dump("after_trust")
    else:
        s.log("skip", "no trust prompt detected")

    # Wait for fully ready
    s.wait_stable(max_wait=20, stable_for=4)
    s.dump("ready_state")

    # ── Step 3: Idle state ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 3/8: Idle State (prompt + status)   │")
    print("└──────────────────────────────────────────┘")
    s.dump("idle_state")

    # ── Step 4: Simple question (streaming) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 4/8: Simple Question (streaming)    │")
    print("└──────────────────────────────────────────┘")
    s.send_line("What is 2+2? Reply with just the number, nothing else.")

    # Capture streaming with frequent snapshots
    start = time.time()
    prev = s.screen_text()
    snap_n = 0
    while time.time() - start < 60:
        s.feed(0.3)
        curr = s.screen_text()
        if curr != prev:
            snap_n += 1
            # Capture first 15 screen changes to see streaming progression
            if snap_n <= 15:
                s.snapshot(f"streaming_{snap_n}")
            prev = curr
        else:
            # If stable for 6s after at least one change, we're done
            if snap_n > 0:
                s.feed(5)
                if s.screen_text() == curr:
                    break

    s.dump("simple_response_final")

    # ── Step 5: File read (tool approval) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 5/8: File Read (tool approval)      │")
    print("└──────────────────────────────────────────┘")
    s.send_line("Read the file pyproject.toml and tell me the project name only.")

    # Watch for tool approval or direct response
    start = time.time()
    prev = s.screen_text()
    approved = False
    snap_n = 0
    while time.time() - start < 90:
        s.feed(0.5)
        curr = s.screen_text()
        if curr != prev:
            snap_n += 1
            if snap_n <= 10:
                s.snapshot(f"tool_read_{snap_n}")
            prev = curr
            lower = curr.lower()

            # Check for tool approval
            if not approved and any(k in lower for k in [
                "[y/n]", "(y)", "allow", "approve", "permission",
            ]):
                s.dump("file_read_approval")
                s.send_line("y", label="approve file read")
                approved = True
                s.feed(2)
                s.snapshot("after_approve_file_read")
        else:
            elapsed = time.time() - start
            if elapsed > 15 and snap_n > 0:
                s.feed(5)
                if s.screen_text() == curr:
                    break

    s.dump("file_read_final")

    # ── Step 6: Bash command (spinner/execution) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 6/8: Bash Command (spinner)         │")
    print("└──────────────────────────────────────────┘")
    s.send_line("Run this bash command: echo 'capture_test_ok'. Show only the output.")

    start = time.time()
    prev = s.screen_text()
    approved = False
    snap_n = 0
    while time.time() - start < 90:
        s.feed(0.5)
        curr = s.screen_text()
        if curr != prev:
            snap_n += 1
            if snap_n <= 10:
                s.snapshot(f"bash_{snap_n}")
            prev = curr
            lower = curr.lower()

            if not approved and any(k in lower for k in [
                "[y/n]", "(y)", "allow", "approve", "permission",
            ]):
                s.dump("bash_approval")
                s.send_line("y", label="approve bash")
                approved = True
                s.feed(2)
                s.snapshot("after_approve_bash")
        else:
            elapsed = time.time() - start
            if elapsed > 15 and snap_n > 0:
                s.feed(5)
                if s.screen_text() == curr:
                    break

    s.dump("bash_final")

    # ── Step 7: Follow-up (prompt reappearance + status bar) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 7/8: Follow-up (prompt + status)    │")
    print("└──────────────────────────────────────────┘")
    s.send_line("Say 'done'.")
    s.wait_stable(max_wait=45, stable_for=6)
    s.dump("followup_final")

    # ── Step 8: Status bar detail ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 8/8: Status Bar Detail              │")
    print("└──────────────────────────────────────────┘")
    # Just a detailed dump with focus on the status bar line
    lines = s.dump("status_bar_detail")
    for entry in lines:
        if "│" in entry["text"] and ("%" in entry["text"] or "usage" in entry["text"].lower()):
            s.log("status_bar", entry["text"])

    print("\n  ✓ Automated scenario complete.")


# ─── Manual Mode ─────────────────────────────────────────────────────

def run_manual(s):
    """Interactive mode: user types commands, screen changes are captured."""
    print("\n┌──────────────────────────────────────────┐")
    print("│  Manual Mode                             │")
    print("│                                          │")
    print("│  Type text to send to Claude             │")
    print("│  /snap   — force a screen snapshot       │")
    print("│  /dump   — print current screen          │")
    print("│  /raw    — show last 500 raw bytes (hex) │")
    print("│  /quit   — save captures and exit        │")
    print("│  /enter  — send raw Enter (\\r)           │")
    print("│  /up     — send arrow up                 │")
    print("│  /down   — send arrow down               │")
    print("│  /esc    — send Escape                   │")
    print("│  /ctrl-c — send Ctrl-C                   │")
    print("└──────────────────────────────────────────┘")

    manual_snap_n = 0

    # Background reader: keep feeding PTY data between user inputs
    while True:
        # Read any pending PTY data
        s.feed(0.5)

        # Check for user input (non-blocking)
        print("\n  manual> ", end="", flush=True)
        try:
            # Wait for user input with timeout so we keep reading PTY
            while True:
                ready, _, _ = select.select([sys.stdin], [], [], 1.0)
                if ready:
                    break
                # Keep reading PTY data while waiting for user
                s.feed(0.3)

            user_input = sys.stdin.readline().strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input == "/quit":
            break
        elif user_input == "/snap":
            manual_snap_n += 1
            s.dump(f"manual_snap_{manual_snap_n}")
        elif user_input == "/dump":
            s.dump("manual_dump")
        elif user_input == "/raw":
            tail = bytes(s.raw_log[-500:])
            print(f"\n  Last {len(tail)} raw bytes:")
            print(f"  {tail.hex()}")
            print(f"  Decoded: {tail.decode('utf-8', errors='replace')}")
        elif user_input == "/enter":
            s.send_raw(b"\r", label="manual Enter")
            s.feed(2)
            s.dump("after_manual_enter")
        elif user_input == "/up":
            s.send_key("up")
            s.feed(1)
            s.dump("after_up")
        elif user_input == "/down":
            s.send_key("down")
            s.feed(1)
            s.dump("after_down")
        elif user_input == "/esc":
            s.send_key("escape")
            s.feed(1)
            s.dump("after_esc")
        elif user_input == "/ctrl-c":
            s.send_key("ctrl-c")
            s.feed(2)
            s.dump("after_ctrl_c")
        else:
            s.send_line(user_input)
            # Capture response with streaming snapshots
            start = time.time()
            prev = s.screen_text()
            snap_n = 0
            while time.time() - start < 120:
                s.feed(0.5)
                curr = s.screen_text()
                if curr != prev:
                    snap_n += 1
                    if snap_n <= 10:
                        s.snapshot(f"manual_response_{manual_snap_n}_{snap_n}")
                    prev = curr
                    lower = curr.lower()
                    # Auto-detect approval prompts
                    if any(k in lower for k in ["[y/n]", "(y)", "allow", "approve"]):
                        s.dump("manual_approval_detected")
                        print("  ⚠ Tool approval detected! Type 'y' or 'n':")
                        break
                else:
                    elapsed = time.time() - start
                    if elapsed > 8 and snap_n > 0:
                        s.feed(4)
                        if s.screen_text() == curr:
                            break

            manual_snap_n += 1
            s.dump(f"manual_result_{manual_snap_n}")


# ─── Main ────────────────────────────────────────────────────────────

def main():
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  Claude Code UI Capture Tool                         ║")
    print("║  Run from a SEPARATE terminal, NOT inside Claude     ║")
    print("╚═══════════════════════════════════════════════════════╝\n")

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    session_name = datetime.now().strftime("capture_%Y%m%d_%H%M%S")
    print(f"  Session:  {session_name}")
    print(f"  Output:   {CAPTURE_DIR / session_name}/")
    print(f"  Terminal: {ROWS}x{COLS}")
    print(f"  CWD:      {CWD}\n")

    s = CaptureSession()

    try:
        s.spawn()
        run_automated(s)
        run_manual(s)
    except KeyboardInterrupt:
        print("\n\n  Interrupted.")
    except Exception as e:
        print(f"\n  Error: {e}")
        s.log("error", str(e))
        import traceback
        traceback.print_exc()
    finally:
        print("\n  Saving captures...")
        s.dump("final_state")
        s.save(session_name)
        s.close()
        print(f"\n  Done! Report: {CAPTURE_DIR / session_name}/report.txt")


if __name__ == "__main__":
    main()
