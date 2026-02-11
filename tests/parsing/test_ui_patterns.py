from src.parsing.ui_patterns import ScreenEvent, ScreenState, classify_line, extract_content


class TestScreenState:
    def test_all_states_exist(self):
        assert ScreenState.STARTUP.value == "startup"
        assert ScreenState.IDLE.value == "idle"
        assert ScreenState.THINKING.value == "thinking"
        assert ScreenState.STREAMING.value == "streaming"
        assert ScreenState.USER_MESSAGE.value == "user_message"
        assert ScreenState.TOOL_REQUEST.value == "tool_request"
        assert ScreenState.TOOL_RUNNING.value == "tool_running"
        assert ScreenState.TOOL_RESULT.value == "tool_result"
        assert ScreenState.BACKGROUND_TASK.value == "background_task"
        assert ScreenState.PARALLEL_AGENTS.value == "parallel_agents"
        assert ScreenState.TODO_LIST.value == "todo_list"
        assert ScreenState.ERROR.value == "error"
        assert ScreenState.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        assert len(ScreenState) == 13


class TestScreenEvent:
    def test_default_values(self):
        event = ScreenEvent(state=ScreenState.UNKNOWN)
        assert event.state == ScreenState.UNKNOWN
        assert event.payload == {}
        assert event.raw_lines == []
        assert event.timestamp == 0.0

    def test_with_payload(self):
        event = ScreenEvent(
            state=ScreenState.THINKING,
            payload={"text": "Deploying robot army…"},
            raw_lines=["✶ Deploying robot army…"],
            timestamp=1234.5,
        )
        assert event.state == ScreenState.THINKING
        assert event.payload["text"] == "Deploying robot army…"
        assert len(event.raw_lines) == 1


class TestClassifyLine:
    def test_empty(self):
        assert classify_line("") == "empty"
        assert classify_line("   ") == "empty"

    def test_separator(self):
        assert classify_line("────────────────────") == "separator"
        assert classify_line("━━━━━━━━━━━━━━━━━━━━") == "separator"

    def test_diff_delimiter(self):
        assert classify_line("╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌") == "diff_delimiter"

    def test_status_bar(self):
        assert classify_line("my-project │ ⎇ main │ Usage: 50%") == "status_bar"
        assert (
            classify_line(
                "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
            )
            == "status_bar"
        )

    def test_pr_indicator_is_status_bar(self):
        assert classify_line("PR #13") == "status_bar"
        assert classify_line("PR #1") == "status_bar"
        assert classify_line("PR #999") == "status_bar"
        # PR mention inside a sentence is content, not status bar
        assert classify_line("See PR #13 for details") == "content"

    def test_thinking_star(self):
        assert classify_line("✶ Activating sleeper agents…") == "thinking"
        assert classify_line("✳ Deploying robot army…") == "thinking"
        assert classify_line("✻ Deploying robot army… (thought for 1s)") == "thinking"
        assert classify_line("✽ Fixing error handling in close()…") == "thinking"
        assert classify_line("· Assimilating human knowledge…") == "thinking"

    def test_tool_header(self):
        assert classify_line("  Bash(echo 'capture_test_ok')") == "tool_header"
        assert classify_line("⏺ Write(/tmp/test_capture.txt)") == "tool_header"
        assert classify_line("⏺ Update(scripts/capture_claude_ui.py)") == "tool_header"
        assert classify_line("⏺ Read 1 file (ctrl+o to expand)") == "tool_header"
        assert classify_line("  Searched for *.py (ctrl+o to expand)") == "tool_header"
        assert classify_line("  Reading 1 file… (ctrl+o to expand)") == "tool_header"

    def test_response(self):
        assert classify_line("⏺ ping") == "response"
        assert classify_line("⏺ The project name is claude-instance-manager.") == "response"
        assert classify_line("⏺ Done. Created /tmp/test_capture.txt.") == "response"
        assert classify_line("⏺ 4 agents launched (ctrl+o to expand)") == "response"

    def test_tool_connector(self):
        assert classify_line("  ⎿  Running…") == "tool_connector"
        assert classify_line("  ⎿  Waiting…") == "tool_connector"
        assert classify_line("  ⎿  Added 4 lines, removed 1 line") == "tool_connector"
        assert classify_line("  ⎿  Running PreToolUse hooks…") == "tool_connector"

    def test_todo_item(self):
        assert classify_line("◻ Fix stale docstring") == "todo_item"
        assert classify_line("◼ Fix substring-vs-set check") == "todo_item"
        assert classify_line("✔ Separate pexpect.EOF from TIMEOUT") == "todo_item"

    def test_agent_tree(self):
        assert (
            classify_line("├─ pr-review-toolkit:code-reviewer (Code review)")
            == "agent_tree"
        )
        assert (
            classify_line("└─ pr-review-toolkit:comment-analyzer (Comment analysis)")
            == "agent_tree"
        )

    def test_prompt_marker(self):
        assert classify_line('❯ Try "how does <filepath> work?"') == "prompt"

    def test_box_drawing_pure_borders(self):
        """Pure box borders (no alpha text) are classified as box."""
        assert classify_line("╰──────────────────────────────────────╯") == "box"
        assert classify_line("├────────────────────┼──────────────────────────────────────────┤") == "box"
        assert classify_line("┌────────────────────┬──────────────────────────────────────────┐") == "box"
        assert classify_line("└────────────────────┴──────────────────────────────────────────┘") == "box"

    def test_box_drawing_with_text_is_content(self):
        """Box lines with substantial text content are content (table data rows)."""
        assert classify_line("│            Welcome back!           │") == "content"
        assert classify_line("│ bot.py             │ Telegram bot handlers                    │") == "content"

    def test_startup_banner_box(self):
        """Startup banner lines are classified as 'startup', not content."""
        assert (
            classify_line("╭─── Claude Code v2.1.37 ─────────────────────────╮")
            == "startup"
        )

    def test_logo(self):
        assert classify_line("▐▛███▜▌   Opus 4.6") == "logo"
        assert classify_line("▝▜█████▛▘  ~/dev/project") == "logo"

    def test_startup_line(self):
        """Startup banner lines (version string) must be classified as 'startup'."""
        assert classify_line("Claude Code v2.1.39") == "startup"
        assert classify_line("           Claude Code v2.1.37") == "startup"
        assert classify_line("╭─── Claude Code v2.1.37 ─────────╮") == "startup"

    def test_content(self):
        assert classify_line("Hello, this is a response from Claude") == "content"
        assert classify_line("4") == "content"
        assert classify_line("The answer is 42.") == "content"


class TestExtractContent:
    def test_filters_ui_chrome(self):
        lines = [
            "────────────────────────────────",
            "claude-instance-manager │ ⎇ main │ Usage: 32%",
            "❯ Try something",
            "Hello, this is actual content",
            "More content here",
            "",
            "────────────────────────────────",
        ]
        result = extract_content(lines)
        assert "Hello, this is actual content" in result
        assert "More content here" in result
        assert "────" not in result
        assert "claude-instance-manager" not in result
        assert "❯" not in result

    def test_filters_startup_banner(self):
        """Startup banner lines must be filtered out by extract_content."""
        lines = [
            "Claude Code v2.1.39",
            "Formatting tip: Keep lines short",
            "This is the actual response content",
        ]
        result = extract_content(lines)
        assert "Claude Code" not in result
        assert "This is the actual response content" in result
        # Tip lines are classified as status_bar, also filtered
        assert "Formatting tip" not in result

    def test_filters_pr_indicator(self):
        """PR indicator from status bar must be filtered by extract_content."""
        lines = [
            "────────────────────────────────",
            "❯",
            "ScreenBuddies │ ⎇ feat/1.2 ⇡2 │ Usage: 48%",
            "PR #13",
        ]
        result = extract_content(lines)
        assert "PR #13" not in result

    def test_preserves_all_content(self):
        lines = ["First line", "Second line", "Third line"]
        result = extract_content(lines)
        assert "First line" in result
        assert "Second line" in result
        assert "Third line" in result

    def test_empty_lines(self):
        lines = ["", "", ""]
        assert extract_content(lines) == ""

    def test_includes_response_marker_text(self):
        """Regression: ⏺ response lines must be included with prefix stripped."""
        lines = [
            "⏺ Hello! How can I help?",
            "  Some follow-up content",
        ]
        result = extract_content(lines)
        assert "Hello! How can I help?" in result
        assert "⏺" not in result
        assert "Some follow-up content" in result

    def test_includes_tool_connector_text(self):
        """Regression: ⎿ tool connector lines must be included with prefix stripped."""
        lines = [
            "  Bash(ls)",
            "  ⎿  src/",
            "  ⎿  tests/",
            "  ⎿  README.md",
        ]
        result = extract_content(lines)
        assert "src/" in result
        assert "tests/" in result
        assert "README.md" in result
        assert "⎿" not in result

    def test_excludes_empty_response_marker(self):
        """⏺ with no text after it should not produce an empty line."""
        lines = ["⏺ ", "actual content"]
        result = extract_content(lines)
        assert result == "actual content"

    def test_mixed_line_types_realistic_screen(self):
        """Regression: realistic screen with all line types must extract only content."""
        lines = [
            " ▐▛███▜▌   Opus 4.6",           # logo -> stripped
            "▝▜█████▛▘  ~/dev/project",       # logo -> stripped
            "  ▘▘ ▝▝",                         # logo -> stripped
            "",                                 # empty -> stripped
            "⏺ Here is the project tree:",     # response -> kept (prefix stripped)
            "  Bash(ls -la)",                   # tool_header -> stripped
            "  ⎿  src/",                       # tool_connector -> kept (prefix stripped)
            "  ⎿  tests/",                     # tool_connector -> kept
            "  ⎿  README.md",                  # tool_connector -> kept
            "The project has 3 directories.",   # content -> kept
            "─" * 40,                           # separator -> stripped
            "  my-project │ ⎇ main │ Usage: 7%",  # status_bar -> stripped
        ]
        result = extract_content(lines)
        assert "Here is the project tree:" in result
        assert "src/" in result
        assert "tests/" in result
        assert "README.md" in result
        assert "The project has 3 directories." in result
        # Verify chrome is stripped
        assert "▐▛" not in result
        assert "Bash(ls" not in result
        assert "─" * 10 not in result
        assert "my-project" not in result
        assert "⏺" not in result
        assert "⎿" not in result
