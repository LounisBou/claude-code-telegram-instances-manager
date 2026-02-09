# PR Review: Quality Improvements (Phases A-G)

**Date:** 2026-02-09
**Reviewers:** code-reviewer, comment-analyzer, test-analyzer, silent-failure-hunter
**Commits reviewed:** 8 (phases A through G)

---

## Critical

| # | File | Issue | Resolution |
|---|------|-------|------------|
| 1 | `src/bot.py` | Path traversal in `/download` — no validation that requested path is within allowed directories | Added `os.path.realpath()` check against project path and upload base dir |
| 2 | `src/bot.py` | File handle leak — `open()` result not closed if `reply_document` fails | Wrapped in `with` block |

## Important

| # | File | Issue | Resolution |
|---|------|-------|------------|
| 3 | `src/claude_process.py` | Bare `except Exception: pass` in PTY drain silently swallows errors | Added `logger.warning()` with exception details |
| 4 | `src/git_info.py` | Two bare `except Exception` blocks hide failures silently | Added `logger.warning()` to both |
| 5 | `src/git_info.py` | `_run_command` has no timeout — can hang indefinitely | Added 10s timeout via `asyncio.wait_for()` |
| 6 | `src/bot.py` | `_run_update_command` has no timeout, doesn't report exit code | Added 60s timeout, prefix output with OK/FAILED |
| 7 | `src/bot.py` | `update:confirm` and `update:cancel` callbacks not handled | Added handler branches in `handle_callback_query` |
| 8 | `src/main.py` | DebugIt monkey-patch doesn't document limitation | Added comment about module-level access requirement, stored original ref |

## Suggestions (Documentation)

| # | File | Issue | Resolution |
|---|------|-------|------------|
| 9 | `docs/architecture.md` | 4 factual errors: send mechanism, HTML vs MarkdownV2, TOOL_APPROVAL vs TOOL_REQUEST, 3-pass descriptions, snapshot count | All corrected |
| 10 | `docs/installation.md` | Missing `silence_warning_minutes` and `env` config fields | Added to example |
| 11 | `docs/usage.md` | Says uploads go to "project directory" but actually go to temp session dir | Corrected |
| 12 | Multiple source files | Docstring issues: over-documented `is_authorized`, duplicate Args on Database class, inaccurate return descriptions, redundant `Returns: None.` | All trimmed/fixed |

## Suggestions (Tests)

| # | File | Issue | Resolution |
|---|------|-------|------------|
| 13 | `tests/test_bot.py` | `test_debug_mode_applies_debugit` doesn't verify wrapping | Now checks `op.classify_screen_state is not original_fn` |
| 14 | `tests/test_main.py` | `TestSetupLogging` only asserts `is not None` | Now asserts actual log level (DEBUG vs INFO) |
| 15 | `tests/test_main.py` | No tests for `_parse_args` | Added default and custom arg tests |
| 16 | `tests/test_bot.py` | No test for unauthorized file upload | Added `test_unauthorized_ignored` |
| 17 | `tests/test_bot.py` | No test for auto-switch after `/exit` | Added `test_auto_switch_after_kill` |
| 18 | `tests/test_bot.py` | No tests for `update:confirm`/`update:cancel` callbacks | Added both tests |
| 19 | `tests/test_bot.py` | No test for path traversal denial | Added `test_path_traversal_denied` |
