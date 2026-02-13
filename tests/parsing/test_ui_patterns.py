from src.parsing.ui_patterns import ScreenEvent, TerminalView, classify_text_line


class TestTerminalView:
    def test_all_states_exist(self):
        assert TerminalView.STARTUP.value == "startup"
        assert TerminalView.IDLE.value == "idle"
        assert TerminalView.THINKING.value == "thinking"
        assert TerminalView.STREAMING.value == "streaming"
        assert TerminalView.USER_MESSAGE.value == "user_message"
        assert TerminalView.TOOL_REQUEST.value == "tool_request"
        assert TerminalView.TOOL_RUNNING.value == "tool_running"
        assert TerminalView.TOOL_RESULT.value == "tool_result"
        assert TerminalView.BACKGROUND_TASK.value == "background_task"
        assert TerminalView.PARALLEL_AGENTS.value == "parallel_agents"
        assert TerminalView.TODO_LIST.value == "todo_list"
        assert TerminalView.ERROR.value == "error"
        assert TerminalView.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        assert len(TerminalView) == 14


class TestScreenEvent:
    def test_default_values(self):
        event = ScreenEvent(state=TerminalView.UNKNOWN)
        assert event.state == TerminalView.UNKNOWN
        assert event.payload == {}
        assert event.raw_lines == []

    def test_with_payload(self):
        event = ScreenEvent(
            state=TerminalView.THINKING,
            payload={"text": "Deploying robot army…"},
            raw_lines=["✶ Deploying robot army…"],
        )
        assert event.state == TerminalView.THINKING
        assert event.payload["text"] == "Deploying robot army…"
        assert len(event.raw_lines) == 1


class TestClassifyLine:
    def test_empty(self):
        assert classify_text_line("") == "empty"
        assert classify_text_line("   ") == "empty"

    def test_separator(self):
        assert classify_text_line("────────────────────") == "separator"
        assert classify_text_line("━━━━━━━━━━━━━━━━━━━━") == "separator"

    def test_diff_delimiter(self):
        assert classify_text_line("╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌") == "diff_delimiter"

    def test_status_bar(self):
        assert classify_text_line("my-project │ ⎇ main │ Usage: 50%") == "status_bar"
        assert (
            classify_text_line(
                "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
            )
            == "status_bar"
        )

    def test_pr_indicator_is_status_bar(self):
        assert classify_text_line("PR #13") == "status_bar"
        assert classify_text_line("PR #1") == "status_bar"
        assert classify_text_line("PR #999") == "status_bar"
        # PR mention inside a sentence is content, not status bar
        assert classify_text_line("See PR #13 for details") == "content"

    def test_progress_bar_timer_is_status_bar(self):
        """Progress bar and/or timer from context window area."""
        # Progress bar + timer
        assert classify_text_line("▊░░░░░░░░░ ↻ 11:00") == "status_bar"
        # Timer alone
        assert classify_text_line("↻ 5:00") == "status_bar"
        assert classify_text_line("↻ 12:34") == "status_bar"
        # Progress bar alone (only block elements)
        assert classify_text_line("▊▊▊░░░░░░░") == "status_bar"
        assert classify_text_line("█████░░░░░") == "status_bar"
        # ↻ inside content sentence should still match (timer is distinctive)
        assert classify_text_line("something ↻ 3:00") == "status_bar"

    def test_thinking_star(self):
        assert classify_text_line("✶ Activating sleeper agents…") == "thinking"
        assert classify_text_line("✳ Deploying robot army…") == "thinking"
        assert classify_text_line("✻ Deploying robot army… (thought for 1s)") == "thinking"
        assert classify_text_line("✽ Fixing error handling in close()…") == "thinking"
        assert classify_text_line("· Assimilating human knowledge…") == "thinking"

    def test_tool_header(self):
        assert classify_text_line("  Bash(echo 'capture_test_ok')") == "tool_header"
        assert classify_text_line("⏺ Write(/tmp/test_capture.txt)") == "tool_header"
        assert classify_text_line("⏺ Update(scripts/capture_claude_ui.py)") == "tool_header"
        assert classify_text_line("⏺ Read 1 file (ctrl+o to expand)") == "tool_header"
        assert classify_text_line("  Searched for *.py (ctrl+o to expand)") == "tool_header"
        assert classify_text_line("  Reading 1 file… (ctrl+o to expand)") == "tool_header"

    def test_response(self):
        assert classify_text_line("⏺ ping") == "response"
        assert classify_text_line("⏺ The project name is claude-instance-manager.") == "response"
        assert classify_text_line("⏺ Done. Created /tmp/test_capture.txt.") == "response"
        assert classify_text_line("⏺ 4 agents launched (ctrl+o to expand)") == "response"

    def test_tool_connector(self):
        assert classify_text_line("  ⎿  Running…") == "tool_connector"
        assert classify_text_line("  ⎿  Waiting…") == "tool_connector"
        assert classify_text_line("  ⎿  Added 4 lines, removed 1 line") == "tool_connector"
        assert classify_text_line("  ⎿  Running PreToolUse hooks…") == "tool_connector"

    def test_todo_item(self):
        assert classify_text_line("◻ Fix stale docstring") == "todo_item"
        assert classify_text_line("◼ Fix substring-vs-set check") == "todo_item"
        assert classify_text_line("✔ Separate pexpect.EOF from TIMEOUT") == "todo_item"

    def test_agent_tree(self):
        assert (
            classify_text_line("├─ pr-review-toolkit:code-reviewer (Code review)")
            == "agent_tree"
        )
        assert (
            classify_text_line("└─ pr-review-toolkit:comment-analyzer (Comment analysis)")
            == "agent_tree"
        )

    def test_prompt_marker(self):
        assert classify_text_line('❯ Try "how does <filepath> work?"') == "prompt"

    def test_box_drawing_pure_borders(self):
        """Pure box borders (no alpha text) are classified as box."""
        assert classify_text_line("╰──────────────────────────────────────╯") == "box"
        assert classify_text_line("├────────────────────┼──────────────────────────────────────────┤") == "box"
        assert classify_text_line("┌────────────────────┬──────────────────────────────────────────┐") == "box"
        assert classify_text_line("└────────────────────┴──────────────────────────────────────────┘") == "box"

    def test_box_drawing_with_text_is_content(self):
        """Box lines with substantial text content are content (table data rows)."""
        assert classify_text_line("│            Welcome back!           │") == "content"
        assert classify_text_line("│ bot.py             │ Telegram bot handlers                    │") == "content"

    def test_startup_banner_box(self):
        """Startup banner lines are classified as 'startup', not content."""
        assert (
            classify_text_line("╭─── Claude Code v2.1.37 ─────────────────────────╮")
            == "startup"
        )

    def test_logo(self):
        assert classify_text_line("▐▛███▜▌   Opus 4.6") == "logo"
        assert classify_text_line("▝▜█████▛▘  ~/dev/project") == "logo"

    def test_startup_line(self):
        """Startup banner lines (version string) must be classified as 'startup'."""
        assert classify_text_line("Claude Code v2.1.39") == "startup"
        assert classify_text_line("           Claude Code v2.1.37") == "startup"
        assert classify_text_line("╭─── Claude Code v2.1.37 ─────────╮") == "startup"

    def test_extra_status_files(self):
        """Regression for issue 003: extra status lines with file counts."""
        assert classify_text_line("4 files +0 -0 · PR #5") == "status_bar"
        assert classify_text_line("1 file +194 -192") == "status_bar"
        assert classify_text_line("12 files +50 -30") == "status_bar"

    def test_extra_status_bash_and_agents(self):
        """Regression for issue 003: extra status lines with bash/agent counts."""
        assert classify_text_line("1 bash · 1 file +194 -192") == "status_bar"
        assert classify_text_line("4 local agents · 1 file +194 -192") == "status_bar"

    def test_extra_status_not_prose(self):
        """Extra status patterns must not false-positive on regular prose."""
        assert classify_text_line("I changed 4 files in this PR") == "content"
        assert classify_text_line("The bash command ran successfully") == "content"

    def test_content(self):
        assert classify_text_line("Hello, this is a response from Claude") == "content"
        assert classify_text_line("4") == "content"
        assert classify_text_line("The answer is 42.") == "content"

