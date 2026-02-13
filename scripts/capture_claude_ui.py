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

# Delay between typing text and pressing Enter.
# Prevents the TUI from treating text+Enter as a paste (multi-line input).
SUBMIT_DELAY = 0.15


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
                except pexpect.TIMEOUT:
                pass
            except pexpect.EOF:
                self.log("eof", "Child process has exited")
                break
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

    def submit(self, text, label=None):
        """Type text, then press Enter separately (like a real user).

        Sending text+Enter as a single write makes Ink treat it as a paste,
        adding the Enter as a newline in multi-line input instead of submitting.
        """
        label = label or text[:60]
        self.log("submit", label)
        if isinstance(text, str):
            text = text.encode("utf-8")
        # Step 1: type the text
        self.child.send(text)
        # Step 2: small delay so TUI processes the text
        time.sleep(SUBMIT_DELAY)
        # Step 3: press Enter to submit
        self.child.send(b"\r")

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

    def wait_for_response(self, max_wait=90, stable_for=6, snap_prefix="resp"):
        """Wait for Claude to respond. Captures streaming snapshots.

        Returns True if screen changed (response received), False if timeout.
        """
        start = time.time()
        prev = self.screen_text()
        snap_n = 0
        last_change = time.time()

        while time.time() - start < max_wait:
            self.feed(0.5)
            curr = self.screen_text()
            if curr != prev:
                snap_n += 1
                last_change = time.time()
                if snap_n <= 15:
                    self.snapshot(f"{snap_prefix}_{snap_n}")
                prev = curr
            else:
                since_change = time.time() - last_change
                if snap_n > 0 and since_change > stable_for:
                    break

        return snap_n > 0

    def wait_for_approval_and_response(self, max_wait=90, stable_for=6, snap_prefix="tool"):
        """Wait for possible tool approval prompt, approve it, wait for response."""
        start = time.time()
        prev = self.screen_text()
        approved = False
        snap_n = 0
        last_change = time.time()

        while time.time() - start < max_wait:
            self.feed(0.5)
            curr = self.screen_text()
            if curr != prev:
                snap_n += 1
                last_change = time.time()
                if snap_n <= 10:
                    self.snapshot(f"{snap_prefix}_{snap_n}")
                prev = curr
                lower = curr.lower()

                if not approved and any(k in lower for k in [
                    "[y/n]", "(y)", "allow", "approve", "permission",
                ]):
                    self.dump(f"{snap_prefix}_approval")
                    self.log("tool_approval", "detected — approving")
                    self.submit("y", label="approve tool")
                    approved = True
                    self.feed(2)
            else:
                since_change = time.time() - last_change
                if snap_n > 0 and since_change > stable_for:
                    break
                elif snap_n == 0 and (time.time() - start) > 25:
                    break

        return snap_n > 0

    def save(self, session_name):
        """Save all capture data to disk."""
        outdir = CAPTURE_DIR / session_name
        outdir.mkdir(parents=True, exist_ok=True)

        (outdir / "raw_pty.bin").write_bytes(bytes(self.raw_log))
        (outdir / "snapshots.json").write_text(
            json.dumps(self.snapshots, indent=2, ensure_ascii=False)
        )
        (outdir / "events.json").write_text(
            json.dumps(self.events, indent=2, ensure_ascii=False)
        )

        with open(outdir / "report.txt", "w") as f:
            f.write(f"Claude Code UI Capture Report\n{'=' * 50}\n")
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
            self.submit("/exit", label="/exit")
            time.sleep(3)
        except (pexpect.EOF, pexpect.TIMEOUT, OSError) as e:
            print(f"  Warning: could not send /exit to Claude: {e}")
        try:
            if self.child is not None:
                self.child.close()
        except (pexpect.ExceptionPexpect, OSError) as e:
            print(f"  Warning: could not close child process: {e}")


# ─── Smoke Test ──────────────────────────────────────────────────────

def run_smoke_test(s):
    """Quick test: submit one message, verify Claude responds.

    Returns True if working, False if submission is broken.
    """
    print("\n┌──────────────────────────────────────────┐")
    print("│  SMOKE TEST: Verifying submission works   │")
    print("└──────────────────────────────────────────┘")

    # Record screen before sending
    before = s.screen_text()
    before_lines = set(line.rstrip() for line in s.screen.display)
    before_usage_line = None
    for line in s.screen.display:
        if "Usage:" in line:
            before_usage_line = line.rstrip()

    s.submit("Say just the word 'ping'.")

    # Wait up to 45s for screen to change significantly
    # "significantly" = new lines appear that weren't in the input area
    start = time.time()
    got_response = False
    while time.time() - start < 45:
        s.feed(1)
        curr = s.screen_text()
        if curr == before:
            continue

        # Check for signs of a real response:
        # 1. Usage % changed (means tokens were consumed)
        # 2. New content appeared beyond the input line
        # 3. The input line was replaced by response text
        for line in s.screen.display:
            stripped = line.rstrip()
            if not stripped:
                continue
            low = stripped.lower()
            # Response text containing "ping" or "pong"
            if "ping" in low and "❯" not in stripped:
                got_response = True
                break
            # Any line that looks like Claude's response (not input, not UI)
            if stripped and "❯" not in stripped and "───" not in stripped and "│" not in stripped and "▐" not in stripped and "▝" not in stripped and "▘" not in stripped:
                # Check if it's a new line not in the startup screen
                if stripped not in before_lines:
                    got_response = True
                    break

        # Also check if usage changed
        for line in s.screen.display:
            if "Usage:" in line and before_usage_line and line.rstrip() != before_usage_line:
                got_response = True
                break

        if got_response:
            break

    s.dump("smoke_test_result")

    if got_response:
        print("  ✓ SMOKE TEST PASSED: Claude responded!")
        s.log("smoke_test", "PASSED")
        # Wait for full response to settle
        s.wait_stable(max_wait=30, stable_for=5)
        return True
    else:
        print("  ✗ SMOKE TEST FAILED: No response detected after 45s.")
        print("    Messages may not be submitting correctly.")
        print("    Check the screen dump above for clues.")
        s.log("smoke_test", "FAILED")
        return False


# ─── Automated Scenario ─────────────────────────────────────────────

def run_automated(s):
    """Run the full automated capture scenario (steps 1-5)."""

    # ── Step 1: File read (tool approval) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 1/5: File Read (tool approval)      │")
    print("└──────────────────────────────────────────┘")
    s.submit("Read the file pyproject.toml and tell me the project name only.")
    s.wait_for_approval_and_response(snap_prefix="tool_read")
    s.dump("file_read_final")

    # ── Step 2: Bash command (spinner/execution) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 2/5: Bash Command (spinner)         │")
    print("└──────────────────────────────────────────┘")
    s.submit("Run this bash command: echo 'capture_test_ok'. Show only the output.")
    s.wait_for_approval_and_response(snap_prefix="bash")
    s.dump("bash_final")

    # ── Step 3: Follow-up (prompt reappearance) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 3/5: Follow-up (prompt reappear)    │")
    print("└──────────────────────────────────────────┘")
    s.submit("Say 'done'.")
    s.wait_for_response(snap_prefix="followup")
    s.dump("followup_final")

    # ── Step 4: Status bar ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 4/5: Status Bar Detail              │")
    print("└──────────────────────────────────────────┘")
    lines = s.dump("status_bar_detail")
    for entry in lines:
        if "│" in entry["text"] and ("%" in entry["text"] or "usage" in entry["text"].lower()):
            s.log("status_bar", entry["text"])

    # ── Step 5: Longer response (streaming) ──
    print("\n┌──────────────────────────────────────────┐")
    print("│  Step 5/5: Longer response (streaming)    │")
    print("└──────────────────────────────────────────┘")
    s.submit("List the files in src/ directory. Use the Read tool or Bash, your choice.")
    s.wait_for_approval_and_response(max_wait=120, snap_prefix="long")
    s.dump("long_response_final")

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

    while True:
        s.feed(0.5)

        print("\n  manual> ", end="", flush=True)
        try:
            while True:
                ready, _, _ = select.select([sys.stdin], [], [], 1.0)
                if ready:
                    break
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
            s.submit(user_input)
            # Wait for response
            s.wait_for_approval_and_response(
                max_wait=120, snap_prefix=f"manual_{manual_snap_n}"
            )
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

        # ── Startup ──
        print("\n┌──────────────────────────────────────────┐")
        print("│  Startup                                 │")
        print("└──────────────────────────────────────────┘")
        s.feed(12)
        s.dump("startup_raw")

        # Handle trust prompt
        if s.screen_has("trust", "Yes, I trust", "trust this folder"):
            s.dump("trust_prompt")
            s.send_raw(b"\r", label="confirm trust (\\r)")
            s.feed(10)
            s.dump("after_trust")

        s.wait_stable(max_wait=20, stable_for=4)
        s.dump("idle_state")

        # ── Smoke test before running full scenario ──
        if not run_smoke_test(s):
            print("\n  ⚠ Smoke test failed. Skipping automated scenario.")
            print("    Dropping into manual mode so you can debug.")
            run_manual(s)
        else:
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
