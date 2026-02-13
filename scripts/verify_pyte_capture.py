#!/usr/bin/env python3
"""Verify that pyte + pexpect can capture Claude Code interactive output.

Run this from a SEPARATE terminal (not inside Claude Code):
    python scripts/verify_pyte_capture.py

It spawns Claude Code, sends a question, captures the response via pyte,
and prints the reconstructed screen showing the actual LLM response.
"""

import os
import sys
import time

import pexpect
import pyte

CWD = os.path.expanduser("~/dev/claude-instance-manager")
ROWS, COLS = 40, 120


def main():
    print("=== pyte + pexpect Claude Code Verification ===")
    print(f"Terminal size: {ROWS}x{COLS}")
    print(f"Working dir: {CWD}")
    print()

    # Set up pyte terminal emulator
    screen = pyte.Screen(COLS, ROWS)
    stream = pyte.Stream(screen)

    # Spawn Claude Code
    print("[1] Spawning Claude Code...")
    env = os.environ.copy()

    child = pexpect.spawn(
        "claude",
        args=[],
        cwd=CWD,
        encoding=None,
        timeout=300,
        dimensions=(ROWS, COLS),
        env=env,
    )

    def feed_and_wait(seconds):
        """Read PTY data and feed into pyte for given duration."""
        start = time.time()
        total_bytes = 0
        while time.time() - start < seconds:
            try:
                chunk = child.read_nonblocking(size=16384, timeout=1)
                if chunk:
                    stream.feed(chunk.decode("utf-8", errors="replace"))
                    total_bytes += len(chunk)
            except (pexpect.TIMEOUT, pexpect.EOF):
                pass
        return total_bytes

    def dump_screen(label):
        """Print non-empty screen lines."""
        print(f"\n  --- {label} ---")
        for i, line in enumerate(screen.display):
            stripped = line.rstrip()
            if stripped:
                print(f"  {i:2d}| {stripped}")
        print()

    # Wait for startup
    print("[2] Waiting for startup (20s)...")
    feed_and_wait(20)
    dump_screen("After startup")

    # Handle trust prompt if present
    screen_text = "\n".join(screen.display)
    if "trust this folder" in screen_text.lower() or "Yes, I trust" in screen_text:
        print("[2b] Trust prompt detected, sending Enter (raw \\r)...")
        child.send(b"\r")  # Raw carriage return for Ink/React TUI
        feed_and_wait(15)
        dump_screen("After trust confirmation")

        # If still showing trust prompt, try sending \n
        screen_text = "\n".join(screen.display)
        if "trust this folder" in screen_text.lower():
            print("[2c] Still on trust prompt, trying \\n...")
            child.send(b"\n")
            feed_and_wait(10)
            dump_screen("After \\n")

    # Send a simple question
    print("[3] Sending: 'What is 2+2? Reply just the number'")
    child.sendline(b"What is 2+2? Reply just the number")

    # Wait patiently for response
    print("[4] Waiting for response (up to 120s)...")
    prev_text = "\n".join(screen.display)
    last_change = time.time()
    start = time.time()

    while time.time() - start < 120:
        feed_and_wait(2)
        current_text = "\n".join(screen.display)
        if current_text != prev_text:
            last_change = time.time()
            prev_text = current_text
            elapsed = int(time.time() - start)
            print(f"    Screen updated at {elapsed}s...")

        # If no changes for 10s after we've seen at least some updates, we're done
        if time.time() - last_change > 10 and time.time() - start > 15:
            break

    dump_screen("After response")

    # Check if we got a response
    content_lines = []
    for line in screen.display:
        stripped = line.rstrip()
        if stripped and "───" not in stripped and "│" not in stripped and "❯" not in stripped:
            content_lines.append(stripped)

    print("=" * 60)
    if any("4" in line for line in content_lines):
        print("  SUCCESS: Response '4' found on screen!")
    else:
        print("  Content lines found:")
        for line in content_lines:
            print(f"    {line}")
    print("=" * 60)

    # Exit
    print("\n[5] Sending /exit...")
    child.sendline(b"/exit")
    time.sleep(5)
    try:
        child.close()
    except Exception:
        pass

    print("\nDone!")


if __name__ == "__main__":
    main()
