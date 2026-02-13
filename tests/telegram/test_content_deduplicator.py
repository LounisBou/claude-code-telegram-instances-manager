"""Tests for ContentDeduplicator."""

from __future__ import annotations

from src.telegram.output_state import ContentDeduplicator


class TestContentDeduplicatorInit:
    """ContentDeduplicator starts with empty state."""

    def test_initial_state_empty(self):
        d = ContentDeduplicator()
        assert d.sent_lines == set()
        assert d.thinking_snapshot == set()


class TestSeedFromDisplay:
    """seed_from_display populates sent_lines from screen content."""

    def test_seeds_non_blank_lines(self):
        d = ContentDeduplicator()
        d.seed_from_display(["Hello", "  ", "World", ""])
        assert d.sent_lines == {"Hello", "World"}

    def test_strips_whitespace(self):
        d = ContentDeduplicator()
        d.seed_from_display(["  Hello  ", "\tWorld\t"])
        assert "Hello" in d.sent_lines
        assert "World" in d.sent_lines

    def test_accumulates_across_calls(self):
        d = ContentDeduplicator()
        d.seed_from_display(["Line 1"])
        d.seed_from_display(["Line 2"])
        assert d.sent_lines == {"Line 1", "Line 2"}


class TestSnapshotChrome:
    """snapshot_chrome only captures UI chrome lines, not content."""

    def test_captures_separator(self):
        d = ContentDeduplicator()
        d.snapshot_chrome(["────────────────────"])
        assert "────────────────────" in d.thinking_snapshot

    def test_excludes_content_lines(self):
        d = ContentDeduplicator()
        d.snapshot_chrome(["Hello world", "────────────────────"])
        assert "Hello world" not in d.thinking_snapshot
        assert "────────────────────" in d.thinking_snapshot

    def test_replaces_previous_snapshot(self):
        d = ContentDeduplicator()
        d.snapshot_chrome(["────────────────────"])
        d.snapshot_chrome(["━━━━━━━━━━━━━━━━━━━━"])
        assert "────────────────────" not in d.thinking_snapshot
        assert "━━━━━━━━━━━━━━━━━━━━" in d.thinking_snapshot


class TestClear:
    """clear() resets both sent_lines and thinking_snapshot."""

    def test_clears_everything(self):
        d = ContentDeduplicator()
        d.sent_lines.add("line")
        d.thinking_snapshot.add("chrome")
        d.clear()
        assert d.sent_lines == set()
        assert d.thinking_snapshot == set()


class TestFilterNew:
    """filter_new returns only unsent lines."""

    def test_all_new_lines_pass_through(self):
        d = ContentDeduplicator()
        result = d.filter_new("Hello\nWorld")
        assert result == "Hello\nWorld"

    def test_already_sent_lines_filtered(self):
        d = ContentDeduplicator()
        d.sent_lines.add("Hello")
        result = d.filter_new("Hello\nWorld")
        assert "World" in result
        assert "Hello" not in result

    def test_blank_lines_preserved(self):
        d = ContentDeduplicator()
        d.sent_lines.add("Hello")
        result = d.filter_new("Hello\n\nWorld")
        assert "World" in result

    def test_records_lines_as_sent(self):
        d = ContentDeduplicator()
        d.filter_new("Hello\nWorld")
        assert "Hello" in d.sent_lines
        assert "World" in d.sent_lines

    def test_repeated_lines_within_same_content_preserved(self):
        """Multiple identical lines in one response (e.g. 'return False')."""
        d = ContentDeduplicator()
        result = d.filter_new("return False\nsome code\nreturn False")
        assert result.count("return False") == 2

    def test_snapshot_subtracted_when_use_snapshot_true(self):
        d = ContentDeduplicator()
        d.thinking_snapshot.add("chrome line")
        result = d.filter_new("chrome line\nReal content", use_snapshot=True)
        assert "chrome line" not in result
        assert "Real content" in result

    def test_snapshot_ignored_when_use_snapshot_false(self):
        d = ContentDeduplicator()
        d.thinking_snapshot.add("chrome line")
        result = d.filter_new("chrome line\nReal content", use_snapshot=False)
        assert "chrome line" in result

    def test_returns_empty_string_when_all_filtered(self):
        d = ContentDeduplicator()
        d.sent_lines.add("Only line")
        result = d.filter_new("Only line")
        assert result == ""

    def test_dedents_result(self):
        d = ContentDeduplicator()
        result = d.filter_new("    Hello\n    World")
        assert result == "Hello\nWorld"
