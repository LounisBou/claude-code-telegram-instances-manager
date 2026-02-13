from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.parsing.terminal_emulator import CharSpan
from src.parsing.screen_classifier import classify_screen_state
from src.parsing.ui_patterns import (
    CHROME_CATEGORIES,
    ScreenEvent, TerminalView, classify_text_line,
)
from src.telegram.output import poll_output
from src.telegram.output_pipeline import (
    dedent_attr_lines,
    filter_response_attr,
    find_last_prompt,
    lstrip_n_chars,
    strip_marker_from_spans,
)


class TestContentDedup:
    """Regression: screen scroll must not cause duplicate content in Telegram."""

    def _run_dedup(self, content: str, sent: set[str]) -> tuple[str, set[str]]:
        """Run the dedup logic from poll_output and return (deduped, updated_sent).

        Mirrors the two-pass approach: first pass filters against pre-existing
        sent set (without modifying it), second pass records all lines as sent.
        """
        from src.telegram.formatter import reflow_text

        new_lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
            elif stripped not in sent:
                new_lines.append(line)
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped:
                sent.add(stripped)
        if new_lines:
            return reflow_text("\n".join(new_lines)), sent
        return "", sent

    def test_first_content_passes_through(self):
        """First time content is seen, it should pass through entirely."""
        content = "Hello world\nThis is a test"
        result, sent = self._run_dedup(content, set())
        assert "Hello world" in result
        assert "This is a test" in result
        assert "Hello world" in sent
        assert "This is a test" in sent

    def test_duplicate_lines_filtered(self):
        """Lines already in sent set must be filtered out."""
        sent = {"Hello world", "This is a test"}
        content = "Hello world\nThis is a test\nNew content here"
        result, sent = self._run_dedup(content, sent)
        assert "Hello world" not in result
        assert "This is a test" not in result
        assert "New content here" in result

    def test_all_duplicates_returns_empty(self):
        """If all lines are duplicates, result should be empty."""
        sent = {"Line one", "Line two"}
        content = "Line one\nLine two"
        result, _ = self._run_dedup(content, sent)
        assert result == ""

    def test_empty_lines_ignored_in_dedup(self):
        """Blank lines should not be added to the sent set."""
        content = "Hello\n\nWorld"
        result, sent = self._run_dedup(content, set())
        assert "" not in sent
        assert "Hello" in sent
        assert "World" in sent

    def test_whitespace_stripped_for_dedup(self):
        """Lines with leading/trailing whitespace should dedup against stripped version."""
        sent = {"Hello world"}
        content = "  Hello world  "
        result, _ = self._run_dedup(content, sent)
        assert result == ""

    def test_partial_overlap_keeps_new(self):
        """Mixed old and new content: only new lines should appear."""
        sent = {"Already seen line"}
        content = "Already seen line\nBrand new line\nAnother new one"
        result, sent = self._run_dedup(content, sent)
        assert "Already seen line" not in result
        assert "Brand new line" in result
        assert "Another new one" in result
        assert "Brand new line" in sent
        assert "Another new one" in sent

    def test_repeated_lines_within_response_preserved(self):
        """Regression: identical lines within the same response must not be deduped.

        Code responses often contain repeated lines like 'return False' or
        'return True' at multiple points. These must all be preserved.
        """
        content = (
            "def is_prime(n):\n"
            "    if n < 2:\n"
            "        return False\n"
            "    if n % 2 == 0:\n"
            "        return False\n"
            "    return True"
        )
        result, sent = self._run_dedup(content, set())
        assert result.count("return False") == 2
        assert "return True" in result

    def test_repeated_lines_still_dedup_across_responses(self):
        """Repeated lines from a PREVIOUS response must still be deduped."""
        sent = {"return False", "return True"}
        content = (
            "def is_prime(n):\n"
            "    if n < 2:\n"
            "        return False\n"
            "    return True"
        )
        result, _ = self._run_dedup(content, sent)
        assert "return False" not in result
        assert "return True" not in result
        assert "def is_prime(n):" in result
        assert "if n < 2:" in result

    def test_blank_lines_preserved_between_paragraphs(self):
        """Regression: blank lines between paragraphs must survive dedup."""
        content = "First paragraph\n\nSecond paragraph"
        result, sent = self._run_dedup(content, set())
        assert "First paragraph" in result
        assert "Second paragraph" in result
        # The blank line separator must be preserved
        assert "\n\n" in result or result.count("\n") >= 2

    def test_blank_lines_preserved_after_partial_dedup(self):
        """Blank lines must survive even when some lines are deduped."""
        sent = {"First paragraph"}
        content = "First paragraph\n\nSecond paragraph"
        result, sent = self._run_dedup(content, sent)
        assert "First paragraph" not in result
        assert "Second paragraph" in result


class TestBuildApp:
    """Tests for build_app wiring."""

    def test_builds_app_with_handlers(self, tmp_path):
        """build_app must return a valid Application."""
        import yaml

        from src.main import build_app

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "telegram": {
                        "bot_token": "fake-token",
                        "authorized_users": [111],
                    },
                    "projects": {"root": "/tmp"},
                }
            )
        )
        app = build_app(str(config_file))
        assert app is not None

    def test_debug_flags_propagate_to_config(self, tmp_path):
        """Debug flags must propagate through to config dataclass."""
        import yaml

        from src.main import build_app

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "telegram": {
                        "bot_token": "fake-token",
                        "authorized_users": [111],
                    },
                    "projects": {"root": "/tmp"},
                }
            )
        )
        app = build_app(str(config_file), debug=True, trace=True, verbose=True)
        assert app is not None
        assert app.bot_data["config"].debug.enabled is True
        assert app.bot_data["config"].debug.trace is True
        assert app.bot_data["config"].debug.verbose is True


class TestDedentAfterDedup:
    """Regression: artifact lines at indent 0 prevent textwrap.dedent in
    extract_content.  After dedup removes the artifact, the remaining lines
    still carry the unwanted terminal margin.  poll_output must re-dedent
    after dedup to strip this residual margin.

    Bug trigger: pyte display line 0 contains ``'u'`` (0-indent artifact).
    extract_content includes it, dedent is a no-op (min indent 0).  Dedup
    then removes ``'u'`` (was in thinking snapshot), but the code lines
    keep their 2-space terminal margin.
    """

    def test_dedent_removes_residual_margin_after_dedup(self):
        """Simulates the poll_output pipeline: extract_content → dedup → dedent."""
        import textwrap

        # Lines as they come from extract_content when a 0-indent artifact
        # was present during dedent (making dedent a no-op).
        content_with_margin = "\n".join([
            "u",
            "  def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      if n <= 1:",
            "          return n",
            "      return fibonacci(n - 1) + fibonacci(n - 2)",
        ])
        # Simulate dedup removing the 'u' artifact
        deduped_lines = [
            "  def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      if n <= 1:",
            "          return n",
            "      return fibonacci(n - 1) + fibonacci(n - 2)",
        ]
        # The fix: re-dedent after dedup
        deduped = textwrap.dedent("\n".join(deduped_lines)).strip()
        assert deduped.startswith("def fibonacci")
        assert "    if n <= 1:" in deduped
        assert "        return n" in deduped
        # No residual 2-space margin
        for line in deduped.split("\n"):
            if line.startswith(" "):
                assert line.startswith("    "), f"Unexpected margin: {line!r}"

    def test_no_margin_when_artifact_absent(self):
        """When there is no artifact, dedent still works correctly."""
        import textwrap

        lines = [
            "def fibonacci(n: int) -> int:",
            '    """Return the nth Fibonacci number."""',
            "    if n <= 1:",
            "        return n",
            "    return fibonacci(n - 1) + fibonacci(n - 2)",
        ]
        deduped = textwrap.dedent("\n".join(lines)).strip()
        assert deduped.startswith("def fibonacci")
        assert "    if n <= 1:" in deduped


class TestFindLastPrompt:
    """Unit tests for find_last_prompt helper."""

    def test_finds_prompt_with_text(self):
        display = [
            "some content",
            "❯ Write a function",
            "⏺ Here is the function:",
            "more content",
        ]
        assert find_last_prompt(display) == 1

    def test_returns_last_prompt_when_multiple(self):
        display = [
            "❯ First prompt text",
            "⏺ First response",
            "❯ Second prompt text",
            "⏺ Second response",
        ]
        assert find_last_prompt(display) == 2

    def test_ignores_bare_prompt(self):
        """Bare ❯ (no text) must be ignored."""
        display = ["❯", "content", "more"]
        assert find_last_prompt(display) is None

    def test_finds_short_user_prompt(self):
        """Short user prompts like '❯ hi' (len 4) must be found."""
        display = ["❯", "content", "❯ hi", "⏺ Hello!", "more"]
        assert find_last_prompt(display) == 2

    def test_skips_idle_hint_prompt(self):
        """Idle hint prompt at screen bottom must be skipped.

        Regression for issue 004: ❯ Try "how does <filepath> work?"
        appears below the response and has no ⏺ below it.  Selecting
        it would truncate the actual response content above.
        """
        display = [
            "❯ /nonexistent",
            "⏺ I don't recognize that command.",
            "────────────────────────────────────",
            '❯ Try "how does <filepath> work?"',
            "────────────────────────────────────",
            "  project │ ⎇ main │ Usage: 5%",
        ]
        # Must select the user prompt (index 0), NOT the idle hint (index 3)
        assert find_last_prompt(display) == 0

    def test_finds_emoji_only_prompt(self):
        """Regression: emoji-only prompt '❯ 🤖💬🔥' (len 5) was incorrectly
        skipped by the old > 5 threshold, causing previous response content
        to leak into the new response during fast-IDLE extraction."""
        display = [
            "⏺ Two.",
            "────────────────────────────────────",
            "❯ 🤖💬🔥",
            "────────────────────────────────────",
            "⏺ Hey! What can I help you with?",
            "────────────────────────────────────",
            "❯",
            "────────────────────────────────────",
        ]
        prompt_idx = find_last_prompt(display)
        assert prompt_idx == 2
        # Trimmed display must NOT include old "Two." response
        trimmed = display[prompt_idx:]
        assert any("Hey" in line for line in trimmed)
        assert not any("Two." in line for line in trimmed)

    def test_returns_none_when_no_prompt(self):
        display = ["line one", "line two", "line three"]
        assert find_last_prompt(display) is None

    def test_returns_none_on_empty_display(self):
        assert find_last_prompt([]) is None


class TestThinkingSnapshotChromeOnly:
    """Regression: thinking snapshot captured content lines (Args:, Returns:,
    code) from a previous response still visible on the pyte screen.  When
    the next response used the same patterns, they were incorrectly deduped.

    Fix: snapshot only captures UI chrome lines (classify_text_line result in
    CHROME_CATEGORIES).  Content, response, and tool lines are excluded.
    """

    def test_snapshot_excludes_content_lines(self):
        """Content lines from a previous response must not be in snapshot."""
        display_at_thinking = [
            "⏺ def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      Args:",
            "          n: The index.",
            "      Returns:",
            "          The nth Fibonacci number.",
            "",
            "────────────────────────────────────",
            "❯ Write a palindrome function",
            "✶ Assimilating human knowledge…",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
                snap.add(stripped)
        assert "Args:" not in snap
        assert "Returns:" not in snap
        assert "def fibonacci(n: int) -> int:" not in snap
        assert '"""Return the nth Fibonacci number."""' not in snap

    def test_snapshot_includes_chrome_elements(self):
        """UI chrome (separators, prompts, thinking, status) must be in snapshot."""
        display_at_thinking = [
            "────────────────────────────────────",
            "❯ Write a palindrome function",
            "✶ Assimilating human knowledge…",
            "project │ ⎇ main │ Usage: 34%",
            "PR #5",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
                snap.add(stripped)
        assert any("palindrome" in s for s in snap)  # prompt
        assert any("────" in s for s in snap)  # separator
        assert any("Assimilating" in s for s in snap)  # thinking star

    def test_snapshot_excludes_response_and_tool_lines(self):
        """Response markers (⏺) and tool connectors (⎿) must be excluded."""
        display_at_thinking = [
            "⏺ Here is the code:",
            "  ⎿ file.py content here",
            "────────────────────────────────────",
            "❯ Next prompt",
            "✶ Launching Skynet initiative…",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
                snap.add(stripped)
        assert not any("⏺" in s for s in snap)
        assert not any("⎿" in s for s in snap)

    def test_fibonacci_palindrome_regression(self):
        """Exact regression: fibonacci Args:/Returns: must not dedup from
        is_palindrome response when both are on the pyte screen at THINKING.

        This reproduces the real scenario where find_last_prompt found the
        fibonacci prompt (not the is_palindrome prompt, which Claude Code
        already cleared), causing the entire fibonacci response to land in
        the snapshot.
        """
        # Simulated display at THINKING entry for is_palindrome
        display_at_thinking = [
            "Claude Code v2.1.39",
            "────────────────────────────────────────",
            "claude-instance-manager │ ⎇ main │ Usage: 34%",
            "PR #5",
            "❯ Write a fibonacci function",
            "  fibonacci prompt continuation",
            "⏺ def fibonacci(n: int) -> int:",
            '      """Return the nth Fibonacci number."""',
            "      Args:",
            "          n: The index.",
            "      Returns:",
            "          The nth Fibonacci number.",
            "      Raises:",
            '          ValueError: If n < 0.',
            '      """',
            "      if n < 0:",
            "────────────────────────────────────────",
            "✢ Initiating singularity sequence…",
            "███▌░░░░░░ ↻ 10:59",
        ]
        snap = set()
        for line in display_at_thinking:
            stripped = line.strip()
            if stripped and classify_text_line(line) in CHROME_CATEGORIES:
                snap.add(stripped)
        # These MUST NOT be in the snap
        assert "Args:" not in snap
        assert "Returns:" not in snap
        assert "Raises:" not in snap
        assert '"""' not in snap
        assert "def fibonacci(n: int) -> int:" not in snap
        # These chrome elements MUST be in the snap
        assert any("────" in s for s in snap)
        assert any("Initiating" in s for s in snap)
        assert any("PR #5" in s for s in snap)


class TestStripMarkerFromSpans:
    """Tests for strip_marker_from_spans."""

    def test_strip_response_marker(self):
        """⏺ prefix is removed from first span."""
        spans = [
            CharSpan(text="⏺ ", fg="default"),
            CharSpan(text="def", fg="blue"),
            CharSpan(text=" foo():", fg="default"),
        ]
        result = strip_marker_from_spans(spans, "⏺")
        texts = [s.text for s in result]
        assert "⏺" not in "".join(texts)
        assert any("def" in t for t in texts)

    def test_strip_tool_connector_marker(self):
        """⎿ prefix is removed from first span."""
        spans = [
            CharSpan(text="⎿ ", fg="default"),
            CharSpan(text="file.py", fg="default"),
        ]
        result = strip_marker_from_spans(spans, "⎿")
        texts = [s.text for s in result]
        assert "⎿" not in "".join(texts)
        assert "file.py" in "".join(texts)

    def test_no_marker_unchanged(self):
        """Spans without marker are returned unchanged."""
        spans = [CharSpan(text="hello world", fg="default")]
        result = strip_marker_from_spans(spans, "⏺")
        assert result == spans

    def test_empty_after_strip(self):
        """Span that becomes empty after stripping is dropped."""
        spans = [
            CharSpan(text="⏺ ", fg="default"),
            CharSpan(text="text", fg="blue"),
        ]
        result = strip_marker_from_spans(spans, "⏺")
        # The first span was "⏺ " -> "" after strip -> dropped
        assert len(result) == 1
        assert result[0].text == "text"


class TestFilterResponseAttr:
    """Tests for filter_response_attr: filters terminal chrome from attributed lines."""

    def test_strips_prompt_and_status_bar(self):
        """Prompt, status bar, and progress bar lines are removed."""
        source = [
            "❯ Write a Python function",
            "  that checks primes.",
            "⏺ Here is the function:",
            "  def is_prime(n):",
            "❯",
            "  claude-instance-manager │ ⎇ feat/test │ Usage: 15%",
            "  █▌░░░░░░░░ ↻ 1:59",
        ]
        attr = [
            [CharSpan(text="❯ Write a Python function", fg="default")],
            [CharSpan(text="  that checks primes.", fg="default")],
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Here is the function:", fg="default")],
            [CharSpan(text="  ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" is_prime(n):", fg="default")],
            [CharSpan(text="❯", fg="default")],
            [CharSpan(text="  claude-instance-manager │ ⎇ feat/test │ Usage: 15%", fg="default")],
            [CharSpan(text="  █▌░░░░░░░░ ↻ 1:59", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        # Should only keep response content (line 2: ⏺ stripped, line 3: code)
        assert len(filtered) == 2
        # ⏺ marker should be stripped
        all_text = "".join(s.text for line in filtered for s in line)
        assert "⏺" not in all_text
        assert "❯" not in all_text
        assert "Usage:" not in all_text
        # Code content preserved
        assert "def" in all_text

    def test_prompt_continuation_skipped(self):
        """Wrapped user input after ❯ is skipped until ⏺ response."""
        source = [
            "❯ This is a very long user prompt that wraps across",
            "  multiple terminal lines because it is so long",
            "⏺ Short answer.",
        ]
        attr = [
            [CharSpan(text="❯ This is a very long user prompt that wraps across", fg="default")],
            [CharSpan(text="  multiple terminal lines because it is so long", fg="default")],
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Short answer.", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        assert len(filtered) == 1
        all_text = "".join(s.text for line in filtered for s in line)
        assert "Short answer." in all_text
        assert "long user prompt" not in all_text

    def test_content_lines_kept(self):
        """Lines classified as 'content' (plain text) are kept."""
        source = [
            "⏺ Here is the code:",
            "  def hello():",
            "      print('hi')",
        ]
        attr = [
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Here is the code:", fg="default")],
            [CharSpan(text="  ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="      ", fg="default"), CharSpan(text="print", fg="cyan"), CharSpan(text="('hi')", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        assert len(filtered) == 3
        # First line should have ⏺ stripped
        first_text = "".join(s.text for s in filtered[0])
        assert "⏺" not in first_text

    def test_empty_input(self):
        """Empty input returns empty output."""
        assert filter_response_attr([], []) == []

    def test_separator_lines_skipped(self):
        """Separator lines (box drawing chars) are filtered out."""
        source = [
            "─" * 40,
            "⏺ Hello world",
            "─" * 40,
        ]
        attr = [
            [CharSpan(text="─" * 40, fg="default")],
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Hello world", fg="default")],
            [CharSpan(text="─" * 40, fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        assert len(filtered) == 1
        assert "Hello world" in "".join(s.text for s in filtered[0])

    def test_dedents_terminal_margin(self):
        """2-space terminal margin from ⏺ column is stripped from all lines.

        Real Claude Code renders content with a 2-space left margin:
        ``  ⏺ text`` for marker lines, ``  content`` for continuation.
        After marker stripping both have a residual 2-space indent that
        filter_response_attr must remove via dedent.
        """
        source = [
            "  ⏺ Here is the code:",
            "      def hello():",
            "          print('hi')",
            "  How it works:",
            "  - It prints hi",
        ]
        attr = [
            [CharSpan(text="  ⏺ ", fg="default"), CharSpan(text="Here is the code:", fg="default")],
            [CharSpan(text="      ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="          ", fg="default"), CharSpan(text="print", fg="cyan"), CharSpan(text="('hi')", fg="default")],
            [CharSpan(text="  How it works:", fg="default")],
            [CharSpan(text="  - It prints hi", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        texts = ["".join(s.text for s in line) for line in filtered]
        # 2-space margin should be stripped from all lines
        assert texts[0] == "Here is the code:"
        assert texts[1] == "    def hello():"
        assert texts[2] == "        print('hi')"
        assert texts[3] == "How it works:"
        assert texts[4] == "- It prints hi"


    def test_dedents_when_marker_at_column_zero(self):
        """Content lines are dedented even when ⏺ sits at column 0.

        When Claude Code renders the ⏺ marker at the leftmost column,
        marker stripping leaves the response line at 0 indent while
        continuation lines retain their 2-space margin.  The dedent
        must exclude marker-stripped lines from the minimum-indent
        computation so continuation lines still get their margin removed.
        """
        source = [
            "⏺ Here is the code:",
            "  def hello():",
            "      print('hi')",
            "  How it works:",
            "  - It prints hi",
        ]
        attr = [
            [CharSpan(text="⏺ ", fg="default"), CharSpan(text="Here is the code:", fg="default")],
            [CharSpan(text="  ", fg="default"), CharSpan(text="def", fg="blue"), CharSpan(text=" hello():", fg="default")],
            [CharSpan(text="      ", fg="default"), CharSpan(text="print", fg="cyan"), CharSpan(text="('hi')", fg="default")],
            [CharSpan(text="  How it works:", fg="default")],
            [CharSpan(text="  - It prints hi", fg="default")],
        ]
        filtered = filter_response_attr(source, attr)
        texts = ["".join(s.text for s in line) for line in filtered]
        # Marker-stripped line stays at 0 indent; content lines get
        # their 2-space margin stripped.
        assert texts[0] == "Here is the code:"
        assert texts[1] == "def hello():"
        assert texts[2] == "    print('hi')"
        assert texts[3] == "How it works:"
        assert texts[4] == "- It prints hi"


class TestLstripNChars:
    """Tests for lstrip_n_chars: strip N leading chars from span list."""

    def test_strip_full_span(self):
        """Span shorter than N is entirely consumed."""
        spans = [
            CharSpan(text="  ", fg="default"),
            CharSpan(text="hello", fg="blue"),
        ]
        result = lstrip_n_chars(spans, 2)
        assert len(result) == 1
        assert result[0].text == "hello"

    def test_strip_partial_span(self):
        """Span longer than N loses first N characters."""
        spans = [CharSpan(text="    code", fg="default")]
        result = lstrip_n_chars(spans, 2)
        assert len(result) == 1
        assert result[0].text == "  code"

    def test_strip_zero(self):
        """Stripping 0 characters returns all spans unchanged."""
        spans = [CharSpan(text="text", fg="default")]
        result = lstrip_n_chars(spans, 0)
        assert len(result) == 1
        assert result[0].text == "text"

    def test_strip_across_spans(self):
        """Strip that spans multiple CharSpans."""
        spans = [
            CharSpan(text=" ", fg="default"),
            CharSpan(text="  ", fg="dim"),
            CharSpan(text="content", fg="blue"),
        ]
        # Strip 3 chars across two spans
        result = lstrip_n_chars(spans, 3)
        assert len(result) == 1
        assert result[0].text == "content"

    def test_strip_preserves_attributes(self):
        """Partially stripped span retains its ANSI attributes."""
        spans = [CharSpan(text="  bold", fg="red", bold=True)]
        result = lstrip_n_chars(spans, 2)
        assert result[0].text == "bold"
        assert result[0].fg == "red"
        assert result[0].bold is True


class TestDedentAttrLines:
    """Tests for dedent_attr_lines: remove common leading whitespace from spans."""

    def test_strips_common_indent(self):
        """All lines with 2-space indent lose 2 leading chars."""
        lines = [
            [CharSpan(text="  hello", fg="default")],
            [CharSpan(text="  world", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts == ["hello", "world"]

    def test_preserves_relative_indent(self):
        """Lines with extra indent beyond the common minimum keep the excess."""
        lines = [
            [CharSpan(text="  code:", fg="default")],
            [CharSpan(text="      indented", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts[0] == "code:"
        assert texts[1] == "    indented"

    def test_no_common_indent(self):
        """Lines with no common indent are returned unchanged."""
        lines = [
            [CharSpan(text="no indent", fg="default")],
            [CharSpan(text="  has indent", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts == ["no indent", "  has indent"]

    def test_empty_lines_skipped(self):
        """Empty lines do not affect min indent calculation."""
        lines = [
            [CharSpan(text="  text", fg="default")],
            [],
            [CharSpan(text="  more", fg="default")],
        ]
        result = dedent_attr_lines(lines)
        texts = ["".join(s.text for s in line) for line in result]
        assert texts[0] == "text"
        assert texts[2] == "more"

    def test_skip_indices_excludes_from_min(self):
        """Skipped lines don't affect min indent; others are still dedented."""
        lines = [
            [CharSpan(text="no indent", fg="default")],   # index 0 — skip
            [CharSpan(text="  two spaces", fg="default")],  # index 1
            [CharSpan(text="  also two", fg="default")],    # index 2
        ]
        result = dedent_attr_lines(lines, skip_indices={0})
        texts = ["".join(s.text for s in line) for line in result]
        # Index 0 has 0 indent but is skipped → min computed from 1,2 → 2
        assert texts[0] == "no indent"  # not enough indent → left as-is
        assert texts[1] == "two spaces"
        assert texts[2] == "also two"

    def test_skip_indices_strips_skipped_if_enough_indent(self):
        """Skipped lines ARE stripped when they have enough indent."""
        lines = [
            [CharSpan(text="  marker line", fg="default")],   # index 0 — skip
            [CharSpan(text="  content", fg="default")],        # index 1
        ]
        result = dedent_attr_lines(lines, skip_indices={0})
        texts = ["".join(s.text for s in line) for line in result]
        # Index 0 has indent 2, min from non-skipped = 2 → stripped
        assert texts[0] == "marker line"
        assert texts[1] == "content"

    def test_empty_input(self):
        """Empty list returns empty list."""
        assert dedent_attr_lines([]) == []


class TestStartupMessage:
    """Startup must send an informational message to all authorized users."""

    @pytest.mark.asyncio
    async def test_on_startup_sends_message_to_authorized_users(self):
        """_on_startup must send a message to every authorized user."""
        from src.main import _on_startup

        app = MagicMock()
        db = AsyncMock()
        db.initialize = AsyncMock()
        db.mark_active_sessions_lost = AsyncMock(return_value=[])
        app.bot_data = {
            "db": db,
            "config": MagicMock(
                telegram=MagicMock(authorized_users=[111, 222]),
            ),
            "session_manager": MagicMock(),
        }
        app.bot = AsyncMock()
        app.bot.set_my_commands = AsyncMock()
        app.bot.send_message = AsyncMock()

        await _on_startup(app)

        # Should have sent a message to each authorized user
        send_calls = app.bot.send_message.call_args_list
        chat_ids = {call.kwargs.get("chat_id") or call.args[0] for call in send_calls}
        assert 111 in chat_ids
        assert 222 in chat_ids
        # Message should contain "started" or "online"
        for call in send_calls:
            text = call.kwargs.get("text", "")
            assert "started" in text.lower() or "online" in text.lower()


class TestShutdownMessage:
    """Shutdown must send a message to all authorized users."""

    @pytest.mark.asyncio
    async def test_send_shutdown_message(self):
        """_send_shutdown_message notifies all authorized users."""
        from src.main import _send_shutdown_message

        bot = AsyncMock()
        bot.send_message = AsyncMock()
        config = MagicMock(
            telegram=MagicMock(authorized_users=[111, 222]),
        )
        sm = MagicMock()
        sm._sessions = {111: {1: "sess1"}, 222: {1: "sess2", 2: "sess3"}}

        await _send_shutdown_message(bot, config, sm)

        send_calls = bot.send_message.call_args_list
        chat_ids = {call.kwargs.get("chat_id") or call.args[0] for call in send_calls}
        assert 111 in chat_ids
        assert 222 in chat_ids
        for call in send_calls:
            text = call.kwargs.get("text", "")
            assert "shutting down" in text.lower() or "stopping" in text.lower()


class TestPollOutputPipelineRunner:
    """poll_output uses PipelineRunner when session has pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_runner_path_feeds_emulator(self):
        """When session.pipeline exists, raw bytes go through PipelineRunner."""
        from src.telegram.pipeline_state import PipelinePhase, PipelineState

        bot = AsyncMock()
        sm = AsyncMock()

        # Create a session with a pipeline
        emu = MagicMock()
        emu.get_display.return_value = [""] * 40
        emu.get_attributed_changes.return_value = []
        emu.get_full_display.return_value = [""] * 40
        emu.get_full_attributed_lines.return_value = [[] for _ in range(40)]
        streaming = AsyncMock()
        streaming.accumulated = ""
        pipeline = PipelineState(emulator=emu, streaming=streaming)

        session = MagicMock()
        session.pipeline = pipeline
        session.process.read_available.return_value = b"hello"

        sm._sessions = {1: {1: session}}

        # Run one cycle
        with patch("src.telegram.output.classify_screen_state") as mock_classify:
            from src.parsing.models import ScreenEvent, TerminalView
            mock_classify.return_value = ScreenEvent(state=TerminalView.IDLE)

            poll_task = asyncio.create_task(poll_output(bot, sm))
            await asyncio.sleep(0.5)
            poll_task.cancel()
            try:
                await poll_task
            except asyncio.CancelledError:
                pass

        emu.feed.assert_called_with(b"hello")
        mock_classify.assert_called()
