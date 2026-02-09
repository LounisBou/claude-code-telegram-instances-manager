#!/usr/bin/env python3
"""Validate classify_screen_state against real captured snapshots.

Loads snapshots from a capture session and runs each through the classifier,
reporting the detected state for every snapshot.
"""
import json
import sys
from collections import Counter
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.output_parser import classify_screen_state, ScreenState


def load_snapshots(capture_dir: str) -> list[dict]:
    """Load snapshots from a capture directory."""
    path = Path(capture_dir) / "snapshots.json"
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def snapshot_to_lines(snapshot: dict, rows: int = 40) -> list[str]:
    """Convert snapshot format to list of screen lines."""
    lines = [""] * rows
    for entry in snapshot.get("lines", []):
        row = entry["row"]
        if 0 <= row < rows:
            lines[row] = entry["text"]
    return lines


def main():
    # Find capture directory
    captures_dir = Path(__file__).parent / "captures"
    if len(sys.argv) > 1:
        capture_dir = sys.argv[1]
    else:
        # Use most recent capture
        dirs = sorted(captures_dir.iterdir())
        if not dirs:
            print("No captures found")
            sys.exit(1)
        capture_dir = str(dirs[-1])

    print(f"Validating: {capture_dir}")
    print("=" * 70)

    snapshots = load_snapshots(capture_dir)
    print(f"Total snapshots: {len(snapshots)}\n")

    state_counts: Counter = Counter()
    unknown_snapshots: list[tuple[str, list[str]]] = []
    results: list[tuple[str, str, dict]] = []

    for snap in snapshots:
        label = snap["label"]
        lines = snapshot_to_lines(snap)
        event = classify_screen_state(lines)
        state = event.state

        state_counts[state.value] += 1
        results.append((label, state.value, event.payload))

        if state == ScreenState.UNKNOWN:
            non_empty = [l for l in lines if l.strip()]
            unknown_snapshots.append((label, non_empty))

    # Print all results
    print(f"{'Label':<35} {'State':<20} {'Payload (summary)'}")
    print("-" * 70)
    for label, state, payload in results:
        # Summarize payload
        summary = ""
        if "text" in payload:
            text = payload["text"][:40]
            summary = f'text="{text}"'
        elif "options" in payload:
            summary = f'options={len(payload["options"])}'
        elif "items" in payload:
            summary = f'items={len(payload["items"])}'
        elif "count" in payload:
            summary = f'count={payload["count"]}'
        elif "tool" in payload:
            summary = f'tool={payload["tool"]}'
        elif "added" in payload:
            summary = f'+{payload["added"]}/-{payload["removed"]}'
        elif "placeholder" in payload:
            summary = f'placeholder="{payload["placeholder"][:30]}"'
        elif "raw" in payload:
            summary = f'raw="{payload["raw"][:40]}"'
        print(f"  {label:<33} {state:<20} {summary}")

    # Print summary
    print("\n" + "=" * 70)
    print("State distribution:")
    for state, count in state_counts.most_common():
        pct = count / len(snapshots) * 100
        bar = "█" * int(pct / 2)
        print(f"  {state:<20} {count:>3} ({pct:5.1f}%) {bar}")

    # Report unknowns
    if unknown_snapshots:
        print(f"\n⚠ {len(unknown_snapshots)} UNKNOWN snapshots:")
        for label, non_empty in unknown_snapshots:
            print(f"\n  --- {label} ---")
            for line in non_empty[:5]:
                print(f"    {line[:80]}")
            if len(non_empty) > 5:
                print(f"    ... ({len(non_empty) - 5} more lines)")
    else:
        print("\n✓ No UNKNOWN snapshots - all states classified!")

    # Check for expected states
    detected_states = set(state_counts.keys())
    expected = {
        "startup", "idle", "thinking", "streaming", "tool_request",
        "tool_running", "tool_result", "user_message",
    }
    missing = expected - detected_states
    if missing:
        print(f"\n⚠ Expected states NOT detected: {missing}")
    else:
        print(f"\n✓ All expected core states detected")

    print(f"\nTotal: {len(snapshots)} snapshots, {len(state_counts)} unique states")


if __name__ == "__main__":
    main()
