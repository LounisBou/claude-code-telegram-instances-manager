from src.parsing.detectors import (
    ContextUsage,
    DetectedPrompt,
    PromptType,
    StatusBar,
    detect_background_task,
    detect_context_usage,
    detect_file_paths,
    detect_parallel_agents,
    detect_prompt,
    detect_thinking,
    detect_todo_list,
    detect_tool_request,
    parse_extra_status,
    parse_status_bar,
)
from src.parsing.terminal_emulator import TerminalEmulator
from tests.parsing.conftest import REAL_STATUS_BAR_ANSI


class TestDetectPrompt:
    def test_detects_yes_no_uppercase_default(self):
        result = detect_prompt("Allow Read tool? [Y/n]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO
        assert result.options == ["Yes", "No"]
        assert result.default == "Yes"

    def test_detects_yes_no_lowercase_default(self):
        result = detect_prompt("Continue? [y/N]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO
        assert result.default == "No"

    def test_detects_multiple_choice(self):
        text = "Choose an option:\n  1. Option A\n  2. Option B\n  3. Option C\n> "
        result = detect_prompt(text)
        assert result is not None
        assert result.prompt_type == PromptType.MULTIPLE_CHOICE
        assert len(result.options) == 3

    def test_detects_tool_approval(self):
        result = detect_prompt("Allow Bash tool? [Y/n]")
        assert result is not None
        assert result.prompt_type == PromptType.YES_NO

    def test_no_prompt_in_regular_text(self):
        result = detect_prompt("Hello, this is normal output from Claude.")
        assert result is None

    def test_empty_string(self):
        result = detect_prompt("")
        assert result is None

    def test_detects_selection_menu(self):
        """Real Claude trust prompt: ❯ 1. Yes, I trust this folder / 2. No, exit"""
        text = "❯ 1. Yes, I trust this folder\n   2. No, exit"
        result = detect_prompt(text)
        assert result is not None
        assert result.prompt_type == PromptType.MULTIPLE_CHOICE
        assert len(result.options) == 2
        assert "Yes, I trust this folder" in result.options[0]


class TestDetectContextUsage:
    def test_detects_percentage(self):
        result = detect_context_usage("Context: 75% used")
        assert result is not None
        assert result.percentage == 75

    def test_detects_compact_suggestion(self):
        result = detect_context_usage(
            "Context window is almost full. Consider using /compact"
        )
        assert result is not None
        assert result.needs_compact is True

    def test_no_context_info(self):
        result = detect_context_usage("Hello world, just some normal output")
        assert result is None

    def test_empty_string(self):
        result = detect_context_usage("")
        assert result is None

    def test_detects_token_count(self):
        result = detect_context_usage("Context: 150k/200k tokens used")
        assert result is not None

    def test_detects_real_claude_usage_format(self):
        result = detect_context_usage("Usage: 32% ███▎░░░░░░")
        assert result is not None
        assert result.percentage == 32

    def test_detects_usage_in_status_line(self):
        text = "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
        result = detect_context_usage(text)
        assert result is not None
        assert result.percentage == 32


class TestParseStatusBar:
    def test_parses_full_status_bar(self):
        text = "claude-instance-manager │ ⎇ main ⇡7 │ Usage: 32% ███▎░░░░░░ ↻ 5:00"
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "claude-instance-manager"
        assert result.branch == "main"
        assert result.usage_pct == 32

    def test_parses_status_bar_no_branch(self):
        text = "my-project │ Usage: 50% █████░░░░░"
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "my-project"
        assert result.usage_pct == 50

    def test_parses_pyte_reconstructed_status_bar(self):
        """Feed real ANSI through pyte, then parse the result."""
        emu = TerminalEmulator(rows=5, cols=120)
        emu.feed(REAL_STATUS_BAR_ANSI)
        text = emu.get_text()
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "claude-instance-manager"
        assert result.branch == "main"
        assert result.usage_pct == 32

    def test_empty_string(self):
        assert parse_status_bar("") is None

    def test_no_match(self):
        assert parse_status_bar("just some random text") is None

    def test_dirty_branch(self):
        text = "claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59"
        result = parse_status_bar(text)
        assert result is not None
        assert result.dirty is True
        assert result.branch == "main"

    def test_commits_ahead(self):
        text = "claude-instance-manager │ ⎇ main ⇡12 │ Usage: 6%"
        result = parse_status_bar(text)
        assert result is not None
        assert result.commits_ahead == 12

    def test_timer(self):
        text = "claude-instance-manager │ ⎇ main │ Usage: 7% ▋░░░░░░░░░ ↻ 9:59"
        result = parse_status_bar(text)
        assert result is not None
        assert result.timer == "9:59"

    def test_no_timer(self):
        text = "claude-instance-manager │ ⎇ main │ Usage: 7%"
        result = parse_status_bar(text)
        assert result is not None
        assert result.timer is None

    def test_all_fields(self):
        text = "claude-instance-manager │ ⎇ main* ⇡12 │ Usage: 6% ▋░░░░░░░░░ ↻ 9:59"
        result = parse_status_bar(text)
        assert result is not None
        assert result.project == "claude-instance-manager"
        assert result.branch == "main"
        assert result.dirty is True
        assert result.commits_ahead == 12
        assert result.usage_pct == 6
        assert result.timer == "9:59"


class TestParseExtraStatus:
    def test_bash_tasks(self):
        result = parse_extra_status("  1 bash · 1 file +194 -192")
        assert result["bash_tasks"] == 1

    def test_local_agents(self):
        result = parse_extra_status("  4 local agents · 1 file +194 -192")
        assert result["local_agents"] == 4

    def test_file_changes(self):
        result = parse_extra_status("  1 file +194 -192")
        assert result["files_changed"] == 1
        assert result["lines_added"] == 194
        assert result["lines_removed"] == 192

    def test_combined(self):
        result = parse_extra_status("  1 bash · 1 file +194 -192")
        assert result["bash_tasks"] == 1
        assert result["files_changed"] == 1
        assert result["lines_added"] == 194

    def test_empty(self):
        result = parse_extra_status("just random text")
        assert result == {}


class TestDetectFilePaths:
    def test_detects_wrote_to(self):
        paths = detect_file_paths("Wrote to /home/user/output.png")
        assert "/home/user/output.png" in paths

    def test_detects_saved(self):
        paths = detect_file_paths("File saved /tmp/result.pdf")
        assert "/tmp/result.pdf" in paths

    def test_detects_created(self):
        paths = detect_file_paths("Created /home/user/project/new_file.py")
        assert "/home/user/project/new_file.py" in paths

    def test_no_paths_in_regular_text(self):
        paths = detect_file_paths("Hello world, just some text")
        assert paths == []

    def test_multiple_paths(self):
        text = "Wrote to /a/file1.txt and saved /b/file2.txt"
        paths = detect_file_paths(text)
        assert len(paths) == 2

    def test_empty_string(self):
        assert detect_file_paths("") == []

    def test_ignores_short_paths(self):
        paths = detect_file_paths("Wrote to /tmp")
        assert paths == []


class TestDetectThinking:
    def test_basic_thinking(self):
        lines = ["✶ Activating sleeper agents…"]
        result = detect_thinking(lines)
        assert result is not None
        assert result["text"] == "Activating sleeper agents…"
        assert result["elapsed"] is None

    def test_thinking_with_elapsed(self):
        lines = ["✻ Deploying robot army… (thought for 1s)"]
        result = detect_thinking(lines)
        assert result is not None
        assert "Deploying robot army…" in result["text"]
        assert result["elapsed"] == "1s"

    def test_thinking_with_hook(self):
        lines = ["✶ Enslaving smart toasters… (running stop hook)"]
        result = detect_thinking(lines)
        assert result is not None
        assert "Enslaving smart toasters…" in result["text"]

    def test_minimal_thinking_dot(self):
        lines = ["· Assimilating human knowledge…"]
        result = detect_thinking(lines)
        assert result is not None
        assert "Assimilating human knowledge…" in result["text"]

    def test_all_star_variants(self):
        for star in "✶✳✻✽✢·":
            lines = [f"{star} Working on something…"]
            result = detect_thinking(lines)
            assert result is not None, f"Failed for star: {star}"

    def test_no_thinking(self):
        lines = ["Hello, this is normal text", "More text here"]
        assert detect_thinking(lines) is None

    def test_empty_lines(self):
        assert detect_thinking([]) is None
        assert detect_thinking([""]) is None

    def test_mixed_content(self):
        lines = [
            "❯ What is 2+2?",
            "",
            "✶ Activating sleeper agents…",
        ]
        result = detect_thinking(lines)
        assert result is not None
        assert result["text"] == "Activating sleeper agents…"


class TestDetectToolRequest:
    def test_approval_menu(self):
        lines = [
            " Do you want to create test_capture.txt?",
            " ❯ 1. Yes",
            "   2. Yes, allow all edits during this session (shift+tab)",
            "   3. No",
            "",
            " Esc to cancel · Tab to amend",
        ]
        result = detect_tool_request(lines)
        assert result is not None
        assert result["options"] == [
            "Yes",
            "Yes, allow all edits during this session (shift+tab)",
            "No",
        ]
        assert result["selected"] == 0
        assert result["has_hint"] is True
        assert result["question"] == "Do you want to create test_capture.txt?"

    def test_trust_prompt(self):
        lines = [
            "❯ 1. Yes, I trust this folder",
            "   2. No, exit",
        ]
        result = detect_tool_request(lines)
        assert result is not None
        assert len(result["options"]) == 2
        assert "Yes, I trust this folder" in result["options"][0]
        assert result["selected"] == 0

    def test_no_menu(self):
        lines = ["Hello", "World", "Just text"]
        assert detect_tool_request(lines) is None

    def test_empty_lines(self):
        assert detect_tool_request([]) is None
        assert detect_tool_request([""]) is None

    def test_single_option_not_menu(self):
        lines = ["❯ 1. Yes"]
        assert detect_tool_request(lines) is None


class TestDetectTodoList:
    def test_full_todo(self):
        lines = [
            "  5 tasks (2 done, 1 in progress, 2 open) · ctrl+t to hide tasks",
            "  ◼ Fix substring-vs-set check in smoke test",
            '  ◻ Fix stale docstring "steps 1-8" to "steps 1-5"',
            "  ✔ Separate pexpect.EOF from TIMEOUT in feed()",
            "  ✔ Replace bare except Exception: pass in close()",
            "  ✔ Remove dead since_last variable",
        ]
        result = detect_todo_list(lines)
        assert result is not None
        assert result["total"] == 5
        assert result["done"] == 2
        assert result["in_progress"] == 1
        assert result["open"] == 2
        assert len(result["items"]) == 5

    def test_item_statuses(self):
        lines = [
            "  ◻ Pending task",
            "  ◼ In-progress task",
            "  ✔ Completed task",
        ]
        result = detect_todo_list(lines)
        assert result is not None
        items = result["items"]
        assert items[0]["status"] == "pending"
        assert items[0]["text"] == "Pending task"
        assert items[1]["status"] == "in_progress"
        assert items[1]["text"] == "In-progress task"
        assert items[2]["status"] == "completed"
        assert items[2]["text"] == "Completed task"

    def test_header_without_in_progress(self):
        lines = [
            "  3 tasks (1 done, 2 open)",
            "  ✔ Done task",
            "  ◻ Open task 1",
            "  ◻ Open task 2",
        ]
        result = detect_todo_list(lines)
        assert result is not None
        assert result["total"] == 3
        assert result["in_progress"] == 0

    def test_no_todo(self):
        lines = ["Hello", "World"]
        assert detect_todo_list(lines) is None

    def test_empty_lines(self):
        assert detect_todo_list([]) is None
        assert detect_todo_list([""]) is None


class TestDetectBackgroundTask:
    def test_background_down_hint(self):
        lines = ["     Running in the background (↓ to manage)"]
        result = detect_background_task(lines)
        assert result is not None
        assert "in the background" in result["raw"]

    def test_background_shift_hint(self):
        lines = ["   ⎿  Running in the background (shift+↑ to manage)"]
        result = detect_background_task(lines)
        assert result is not None

    def test_no_background(self):
        lines = ["Hello", "World"]
        assert detect_background_task(lines) is None

    def test_empty_lines(self):
        assert detect_background_task([]) is None


class TestDetectParallelAgents:
    def test_agents_launched(self):
        lines = [
            "⏺ 4 agents launched (ctrl+o to expand)",
            "   ├─ pr-review-toolkit:code-reviewer (Code review of PR changes)",
            "   ├─ pr-review-toolkit:silent-failure-hunter (Silent failure hunting)",
            "   ├─ pr-review-toolkit:code-simplifier (Code simplification review)",
            "   └─ pr-review-toolkit:comment-analyzer (Comment accuracy analysis)",
        ]
        result = detect_parallel_agents(lines)
        assert result is not None
        assert result["count"] == 4
        assert len(result["agents"]) == 4

    def test_agent_completion(self):
        lines = [
            '⏺ Agent "Code simplification review" completed',
            "⏺ Code review is done. 2 of 4 agents complete.",
        ]
        result = detect_parallel_agents(lines)
        assert result is not None
        assert len(result["completed"]) == 1
        assert result["completed"][0] == "Code simplification review"

    def test_no_agents(self):
        lines = ["Hello", "World"]
        assert detect_parallel_agents(lines) is None

    def test_empty_lines(self):
        assert detect_parallel_agents([]) is None
