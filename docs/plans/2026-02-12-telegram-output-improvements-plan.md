# Telegram Output Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix blank line loss in dedup, add ANSI re-render on streaming completion, and send startup/shutdown Telegram messages.

**Architecture:** Three independent improvements to the output pipeline: (1) preserve blank lines during content dedup in `poll_output`, (2) run the ANSI-aware pipeline on STREAMING→IDLE transitions to re-render the final message with proper code detection, (3) send informational messages to authorized users on bot start and stop.

**Tech Stack:** Python 3.11+, python-telegram-bot, pyte, pytest

---

### Task 1: Preserve blank lines during content dedup

**Files:**
- Modify: `src/telegram/output.py:519-523`
- Test: `tests/telegram/test_output.py`

**Step 1: Write the failing test**

Add to `tests/telegram/test_output.py` in `TestContentDedup`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/telegram/test_output.py::TestContentDedup::test_blank_lines_preserved_between_paragraphs tests/telegram/test_output.py::TestContentDedup::test_blank_lines_preserved_after_partial_dedup -v`
Expected: FAIL — current dedup drops blank lines

**Step 3: Fix the dedup loop in output.py**

In `src/telegram/output.py:519-523`, change from:

```python
new_lines = []
for line in content.split("\n"):
    stripped = line.strip()
    if stripped and stripped not in sent and stripped not in snap:
        new_lines.append(line)
```

To:

```python
new_lines = []
for line in content.split("\n"):
    stripped = line.strip()
    if not stripped:
        new_lines.append(line)
    elif stripped not in sent and stripped not in snap:
        new_lines.append(line)
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/telegram/test_output.py::TestContentDedup -v`
Expected: ALL PASS

**Step 5: Run full suite**

Run: `pytest -x`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/telegram/output.py tests/telegram/test_output.py
git commit -m "fix: preserve blank lines during content dedup

Blank lines between paragraphs were silently dropped because
the dedup loop checked 'if stripped' before appending. Now
blank lines are always preserved, maintaining paragraph structure."
```

---

### Task 2: ANSI re-render on STREAMING→IDLE completion

**Files:**
- Modify: `src/telegram/output.py:555-570`
- Test: `tests/telegram/test_output.py`

**Step 1: Write the failing test**

Add to `tests/telegram/test_output.py` new class `TestAnsiReRenderOnCompletion`:

```python
class TestAnsiReRenderOnCompletion:
    """STREAMING→IDLE must re-render final message with ANSI pipeline."""

    def _cleanup_session(self, key):
        _session_emulators.pop(key, None)
        _session_streaming.pop(key, None)
        _session_prev_state.pop(key, None)
        _session_sent_lines.pop(key, None)
        _session_thinking_snapshot.pop(key, None)

    @pytest.mark.asyncio
    async def test_streaming_idle_uses_ansi_pipeline(self):
        """STREAMING→IDLE must call classify_regions for final render."""
        key = (750, 1)
        self._cleanup_session(key)

        process = MagicMock()
        process.read_available.side_effect = [b"data", None]
        session = MagicMock()
        session.process = process
        sm = MagicMock()
        sm._sessions = {750: {1: session}}
        bot = AsyncMock()

        from src.parsing.terminal_emulator import TerminalEmulator
        _session_emulators[key] = TerminalEmulator()
        streaming = StreamingMessage(bot=bot, chat_id=750, edit_rate_limit=3)
        streaming.message_id = 42
        streaming.accumulated = "Heuristic content"
        streaming.state = StreamingState.STREAMING
        _session_streaming[key] = streaming
        _session_prev_state[key] = ScreenState.STREAMING
        _session_sent_lines[key] = set()

        idle_event = ScreenEvent(state=ScreenState.IDLE, raw_lines=[])

        classify_calls = []
        def _capture_classify(lines):
            classify_calls.append(lines)
            from src.parsing.content_classifier import ContentRegion
            return [ContentRegion(type="prose", text="ANSI-rendered content")]

        with (
            patch("src.telegram.output.asyncio.sleep", side_effect=[None, asyncio.CancelledError]),
            patch("src.telegram.output.classify_screen_state", return_value=idle_event),
            patch("src.telegram.output.classify_regions", side_effect=_capture_classify),
        ):
            try:
                await poll_output(bot, sm)
            except asyncio.CancelledError:
                pass

        # classify_regions must have been called for re-render
        assert len(classify_calls) >= 1
        # The final message should contain the ANSI-rendered content
        bot.edit_message_text.assert_called()
        final_text = bot.edit_message_text.call_args[1]["text"]
        assert "ANSI-rendered content" in final_text

        self._cleanup_session(key)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/telegram/test_output.py::TestAnsiReRenderOnCompletion::test_streaming_idle_uses_ansi_pipeline -v`
Expected: FAIL — current code does not run ANSI pipeline on STREAMING→IDLE

**Step 3: Implement ANSI re-render on STREAMING→IDLE**

In `src/telegram/output.py:555-570`, change from:

```python
# Finalize on transition to idle (response complete)
if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
    # Re-seed dedup ...
    sent = _session_sent_lines.setdefault(key, set())
    for line in display:
        stripped = line.strip()
        if stripped:
            sent.add(stripped)
    await streaming.finalize()
```

To:

```python
# Finalize on transition to idle (response complete)
if event.state == ScreenState.IDLE and prev != ScreenState.IDLE:
    # Re-seed dedup with all visible content instead of
    # clearing.  When pyte scrolls, get_changes() re-reports
    # shifted lines from a *previous* response.  Keeping
    # those lines in the dedup set prevents them from leaking
    # into the next extraction (e.g. TOOL_REQUEST right after
    # a text response).  The dedup set is properly cleared on
    # USER_MESSAGE for a fresh start when the user sends a
    # new message.
    sent = _session_sent_lines.setdefault(key, set())
    for line in display:
        stripped = line.strip()
        if stripped:
            sent.add(stripped)

    # ANSI re-render: when the response was streamed with
    # the heuristic pipeline, re-render the final message
    # using the ANSI-aware pipeline for accurate code block
    # detection, inline code markers, and heading detection.
    # Only when streaming had content (not fast-IDLE which
    # already uses the ANSI pipeline directly).
    if (
        streaming.state == StreamingState.STREAMING
        and streaming.accumulated
        and not _fast_idle
    ):
        full = emu.get_full_display()
        full_attr = emu.get_full_attributed_lines()
        prompt_idx = _find_last_prompt(full)
        if prompt_idx is not None:
            re_source = full[prompt_idx:]
            re_attr = full_attr[prompt_idx:]
        else:
            re_source = full
            re_attr = full_attr
        filtered = _filter_response_attr(re_source, re_attr)
        if filtered:
            regions = classify_regions(filtered)
            rendered = render_regions(regions)
            re_html = format_html(reflow_text(rendered))
            if re_html.strip():
                streaming.accumulated = re_html

    emu.clear_history()
    await streaming.finalize()
```

**Important:** The `_fast_idle` variable is scoped inside the content-extraction `if` block. We need to lift it to be accessible here. Initialize `_fast_idle = False` before the content block (around line 477), and set it to `True` inside the existing fast-IDLE check. This ensures `_fast_idle` is always defined when we reach the finalize block.

**Step 4: Run test to verify it passes**

Run: `pytest tests/telegram/test_output.py::TestAnsiReRenderOnCompletion -v`
Expected: PASS

**Step 5: Run full suite**

Run: `pytest -x`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/telegram/output.py tests/telegram/test_output.py
git commit -m "feat: ANSI re-render on streaming completion

When a response was streamed using the heuristic pipeline,
re-render the final message using the ANSI-aware pipeline
on STREAMING->IDLE transition. This gives accurate code block
detection via syntax highlighting colors, inline code markers,
and bold headings in the final polished message."
```

---

### Task 3: Startup message to authorized users

**Files:**
- Modify: `src/main.py:104-115`
- Test: `tests/telegram/test_output.py` (or `tests/test_main.py`)

**Step 1: Write the failing test**

Add to `tests/telegram/test_output.py` class `TestBuildApp` or create new test:

```python
class TestStartupMessage:
    """Startup must send an informational message to all authorized users."""

    @pytest.mark.asyncio
    async def test_on_startup_sends_message_to_authorized_users(self):
        """_on_startup must send a message to every authorized user."""
        from unittest.mock import AsyncMock, MagicMock, patch
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/telegram/test_output.py::TestStartupMessage -v`
Expected: FAIL — `_on_startup` does not send messages

**Step 3: Implement startup message**

In `src/main.py:104-115`, add after `set_my_commands`:

```python
async def _on_startup(app: Application) -> None:
    """Run one-time initialization tasks after the application starts."""
    logger = logging.getLogger(__name__)
    db = app.bot_data["db"]
    await db.initialize()
    lost = await db.mark_active_sessions_lost()
    if lost:
        logger.info("Marked %d stale sessions as lost on startup", len(lost))

    await app.bot.set_my_commands(
        [BotCommand(cmd, desc) for cmd, desc in BOT_COMMANDS]
    )

    # Send startup notification to all authorized users
    config = app.bot_data["config"]
    import platform
    hostname = platform.node() or "unknown"
    stale_info = f"\nRecovered sessions: {len(lost)}" if lost else ""
    text = (
        "<b>Bot started</b>\n"
        f"Host: <code>{html_mod.escape(hostname)}</code>"
        f"{stale_info}"
    )
    for user_id in config.telegram.authorized_users:
        try:
            await app.bot.send_message(
                chat_id=user_id, text=text, parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Failed to send startup message to %d: %s", user_id, exc)
```

Add `import html as html_mod` at the top of `src/main.py` (or use `platform` which is stdlib).

**Step 4: Run test to verify it passes**

Run: `pytest tests/telegram/test_output.py::TestStartupMessage -v`
Expected: PASS

**Step 5: Run full suite**

Run: `pytest -x`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/main.py tests/telegram/test_output.py
git commit -m "feat: send startup message to authorized users

On bot startup, sends an informational message to all authorized
Telegram users with hostname and recovered session count."
```

---

### Task 4: Shutdown message to authorized users

**Files:**
- Modify: `src/main.py:161-179`
- Test: `tests/telegram/test_output.py`

**Step 1: Write the failing test**

```python
class TestShutdownMessage:
    """Shutdown must send a message to all authorized users."""

    @pytest.mark.asyncio
    async def test_send_shutdown_message(self):
        """_send_shutdown_message notifies all authorized users."""
        from unittest.mock import AsyncMock, MagicMock
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/telegram/test_output.py::TestShutdownMessage -v`
Expected: FAIL — `_send_shutdown_message` does not exist

**Step 3: Implement shutdown message**

Add to `src/main.py`:

```python
async def _send_shutdown_message(bot: Bot, config: AppConfig, session_manager: SessionManager) -> None:
    """Send shutdown notification to all authorized users.

    Args:
        bot: Telegram Bot instance.
        config: Application configuration with authorized user list.
        session_manager: Session manager to count active sessions.
    """
    active_count = sum(
        len(sessions) for sessions in session_manager._sessions.values()
    )
    active_info = f"\nActive sessions: {active_count} (ending)" if active_count else ""
    text = f"<b>Bot shutting down</b>{active_info}"
    for user_id in config.telegram.authorized_users:
        try:
            await bot.send_message(
                chat_id=user_id, text=text, parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Failed to send shutdown message to %d: %s", user_id, exc)
```

Add import for `Bot` from telegram and `AppConfig` from config at the top.

Then in `main()`, call it before shutdown (around line 171):

```python
logger.info("Shutting down...")
# Notify users before stopping
config = app.bot_data["config"]
session_manager = app.bot_data["session_manager"]
await _send_shutdown_message(app.bot, config, session_manager)
await app.updater.stop()
# ... rest of shutdown
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/telegram/test_output.py::TestShutdownMessage -v`
Expected: PASS

**Step 5: Run full suite**

Run: `pytest -x`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add src/main.py tests/telegram/test_output.py
git commit -m "feat: send shutdown message to authorized users

Before stopping, sends a message to all authorized Telegram users
with count of active sessions being terminated."
```

---

### Task 5: Integration verification

**Step 1: Run full test suite with coverage**

```bash
pytest --cov=src --cov-report=term-missing -x
```

Expected: ALL PASS, coverage on `output.py` and `main.py` maintained or improved.

**Step 2: Verify no regressions in existing formatter tests**

```bash
pytest tests/telegram/test_format_html.py -v
pytest tests/parsing/test_content_classifier.py -v
```

Expected: ALL PASS

**Step 3: Final commit if any cleanup needed**

Only if integration revealed issues during steps 1-2.
