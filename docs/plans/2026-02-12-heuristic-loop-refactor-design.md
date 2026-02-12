# Heuristic Loop Refactor — Design Document

## Problem Statement

The current `heuristic-loop` skill is a 323-line monolithic skill that tries to do everything in one loop: test the bot via Telegram, debug issues, fix code, write tests, commit, and restart. This causes four compounding problems:

1. **Context window bloat** — Testing + debugging + fixing all run in one session, burning through context rapidly.
2. **Shallow testing** — The loop stops to fix the first bug it finds, so it never tests long interaction flows or multiple scenario categories in depth.
3. **Evidence loss** — Investigating bug A erases the context and observations from bug B. Issues get forgotten or poorly documented.
4. **Weak fix verification** — Regression tests are rushed, non-regression testing is skipped, and live re-testing is inconsistent.

## Solution: Three Sub-Skills + Orchestrator

Split the monolithic skill into three specialized sub-skills, each with a clear responsibility and its own context window. The existing `heuristic-loop` becomes a lightweight orchestrator.

### Architecture

| Skill | Role | Context scope |
|-------|------|---------------|
| `heuristic-loop` | Orchestrator — manages loop, transitions, /clear | Survives via files on disk |
| `heuristic-loop:test-and-gather` | Run test scenarios, document ALL issues with evidence | One full context window |
| `heuristic-loop:fix-one` | Pick one issue, systematic-debug, fix it, commit | Fresh context per issue |
| `heuristic-loop:verify-one` | Verify fix (regression test + non-regression + live re-test) | Same context as fix-one |

### The Loop

```
Test & Gather → [/clear] → Fix #1 + Verify #1 → [/clear] → Fix #2 + Verify #2 → [/clear]
→ ... → all fixed → [/clear] → Test & Gather again (harder scenarios) → ...
```

Fix and Verify run in the **same context** (sequential for one issue), then /clear before the next issue. Each issue gets its own clean context window.

The loop never stops. Only the user can break it.

## Durable State: File-Based Memory

All state lives in `.claude/heuristic-loop-state/` (added to `.gitignore`). This directory is the orchestrator's memory — it survives /clear and allows resuming across sessions.

### File Structure

```
.claude/heuristic-loop-state/
├── state.md                    # Orchestrator state
├── issues/
│   ├── index.md                # Issue list with statuses
│   ├── issue-001.md            # Full description + evidence
│   ├── issue-002.md
│   └── ...
└── evidence/
    ├── issue-001-console.txt   # Raw console log extract
    ├── issue-002-console.txt
    └── ...
```

### `state.md` — Orchestrator Brain

```markdown
# Heuristic Loop State
phase: fixing          # testing | fixing | idle
round: 2               # increments each test-and-gather cycle
current_issue: 003     # which issue fix-one is working on (null during testing)
categories_tested: [1, 2, 4, 7]  # scenario categories covered so far
```

### `issues/index.md` — Issue Backlog

```markdown
# Issues - Round 2

| ID | Status | Summary |
|----|--------|---------|
| 001 | verified | Empty message after /exit |
| 002 | fixing | Truncated code blocks in long responses |
| 003 | open | No response after file upload |
```

Statuses: `open` → `fixing` → `fixed` → `verified`

### `issues/issue-NNN.md` — Issue Evidence File

```markdown
# Issue 003: No response after file upload

## Scenario
Category: 6 (File operations)
Sent a .py file to the bot, no response within 30s.

## Telegram Observation
Last bot message was "Processing..." — never updated. No error shown.

## Console Evidence
See evidence/issue-003-console.txt
Key line: `ERROR: file_handler.py:42 - UnicodeDecodeError on binary file`

## Reproduction Steps
1. Start session, select project
2. Upload a .py file
3. Wait 30s — no response
```

Evidence is **text-based** — written observations and console log extracts, not screenshots. Screenshots are context-heavy and the next session can always take a fresh one during live re-test.

## Sub-Skill 1: `heuristic-loop:test-and-gather`

**Purpose:** Pure testing. Never fixes anything. Maximizes test depth within one context window.

### Iron Rules

1. **NEVER fix anything.** Only observe and document.
2. Stop after **~35 evidence-gathering actions** (screenshots, snapshots, console reads).
3. Rotate through scenario categories not yet covered (reads `state.md` for `categories_tested`).
4. Every issue gets its own file with full evidence BEFORE moving to next scenario.

### Flow

```
Start app (or confirm running) → Open Telegram Web → Pick untested category
→ Run scenario → Observe Telegram + Console → Issue found?
  → Yes: Create issue-NNN.md with evidence, update index.md
  → No: Note category as tested, pick next
→ Evidence action count >= 35?
  → No: Next scenario
  → Yes: Finalize all issue files, update state.md (phase: fixing), STOP
```

### Evidence-Gathering Protocol

For each issue discovered:

1. Take snapshot — describe what you see in text (bot response, formatting, timing)
2. Read console logs — extract relevant lines into `evidence/issue-NNN-console.txt`
3. Write `issues/issue-NNN.md` with: scenario category, what was done, what was expected, what happened, console evidence reference, reproduction steps
4. Add row to `issues/index.md` with status `open`

### Proxy Heuristic for Context Limit

Claude cannot directly measure its own context window usage. Instead, count **evidence-gathering tool calls** (take_screenshot, take_snapshot, TaskOutput for console reads). These are the heaviest context consumers. After ~35 such actions, wrap up the current scenario and finalize all issue files.

### What This Sub-Skill Does NOT Do

- No `systematic-debugging` invocation
- No code reading or investigation
- No fixes, no commits
- No test writing

It is a **pure observer** — a tester who only files bug reports.

### Inherited Content from Current Skill

- Iron rules #2, #3, #4 (no git touch, 30s timeout, working dir)
- Chrome MCP interaction guide (steps 2-5 of current skill)
- Test scenario categories table (9 categories)
- Human-friendliness standard
- Chrome MCP failure handling
- Forbidden actions table (testing-relevant entries)

## Sub-Skill 2: `heuristic-loop:fix-one`

**Purpose:** Pick one open issue, understand it deeply, fix it, commit. Nothing else.

### Flow

```
Read index.md → Pick first open issue → Update index status to "fixing"
→ Read issue-NNN.md + evidence file
→ Invoke superpowers:systematic-debugging (with issue description + evidence as input)
→ Find root cause → Implement fix → Run pytest
  → Fail: iterate on fix
  → Pass: Commit fix only (no tests yet — that's verify's job)
→ Update state.md (current_issue: NNN)
→ Hand off to verify-one (same context, no /clear)
```

### Key Constraints

1. **One issue only.** Never touch a second issue even if you spot it while debugging.
2. **Evidence-first.** The issue file is the starting point — don't re-test in Telegram to rediscover the bug. The evidence is already there.
3. **Systematic-debugging is mandatory.** No guessing fixes. The evidence file gives a head start (console errors, reproduction steps), but all four phases must be followed.
4. **Commit contains only the fix.** No test changes, no cleanups, no "while I'm here" improvements.

### What This Sub-Skill Does NOT Do

- No Telegram interaction (no chrome-devtools)
- No regression test writing (that's verify-one)
- No coverage checks (that's verify-one)
- No app restart (that's verify-one)

It is a **pure fixer** — a developer who reads the bug report and patches the code.

## Sub-Skill 3: `heuristic-loop:verify-one`

**Purpose:** Prove the fix works. Regression test, coverage, live re-test. Runs in the same context as fix-one (no /clear between them).

### Flow

```
Read issue-NNN.md (reproduction steps)
→ Write regression test that reproduces the exact bug scenario
→ Run pytest → must pass
→ Run pytest --cov on changed files → new code paths covered?
  → No: Add coverage tests → re-run
  → Yes: continue
→ Restart the app
→ Open Telegram Web → Re-test the EXACT scenario from issue-NNN.md
→ Bot behaves correctly?
  → No: Back to fix-one (same context, don't /clear)
  → Yes: Update index.md status to "verified", commit tests
```

### Key Constraints

1. **Regression test is mandatory.** It must fail without the fix, pass with it. Named descriptively (e.g., `test_response_after_file_upload`, not `test_fix_003`).
2. **Live re-test is mandatory.** Passing unit tests isn't enough — the actual Telegram interaction must work. Reproduction steps come from the issue file.
3. **Coverage gate.** Changed code paths must have test coverage before committing.
4. **Commit contains only tests.** Fix was already committed by fix-one. Atomic commits.
5. **If live re-test fails**, don't /clear — loop back to fix-one within the same context (all debugging state is still available).

### What This Sub-Skill Does NOT Do

- No new issue discovery (if something is spotted during re-test, don't file it — that's test-and-gather's job)
- No fixing other issues
- No exploring other scenarios

It is a **pure verifier** — a QA engineer who confirms the bug is actually dead.

## The Orchestrator: `heuristic-loop`

**Purpose:** Manage transitions between sub-skills, handle /clear, maintain the loop. This is the only skill the user invokes directly.

### Startup (After Every /clear or Fresh Start)

```
Read .claude/heuristic-loop-state/state.md
→ Does state dir exist?
  → No: First run. Create dir structure, set phase: testing, invoke test-and-gather
  → Yes: Read phase and resume
```

### Phase Routing

```
phase == "testing"  → invoke heuristic-loop:test-and-gather
phase == "fixing"   → read index.md, find first open/fixing issue
  → open issue exists   → invoke heuristic-loop:fix-one
  → fixing issue exists → invoke heuristic-loop:verify-one (fix done, verify pending)
  → all verified        → set phase: testing, bump round, /clear, restart loop
```

### The /clear Cycle

```
After test-and-gather completes: /clear → orchestrator resumes → phase=fixing → fix-one
After fix+verify completes:      /clear → orchestrator resumes → phase=fixing → next open issue
After all issues verified:       /clear → orchestrator resumes → phase=testing → test-and-gather
```

### Round Escalation

Each new round of test-and-gather tests **harder**:
- Combine multiple scenario categories in single interactions
- Try edge cases within already-tested categories
- Longer interaction flows (multi-message conversations)
- The `categories_tested` list in `state.md` guides category rotation

### Inherited Content from Current Skill

- Iron rules #1 and #6 (loop doesn't break, /clear is memory reset)
- Recommended settings (Opus, /fast, Medium effort)
- Red flags table (orchestrator-relevant entries)
- Overview and philosophy

### Cleanup

When the user says "stop", the orchestrator does NOT delete `.claude/heuristic-loop-state/`. The state persists so the user can resume later or review what was found.

## Skill File Organization

### File Layout

```
.claude/skills/
├── heuristic-loop/SKILL.md                  # Orchestrator (~80 lines)
├── heuristic-loop-test-and-gather/SKILL.md  # Sub-skill 1 (~120 lines)
├── heuristic-loop-fix-one/SKILL.md          # Sub-skill 2 (~60 lines)
└── heuristic-loop-verify-one/SKILL.md       # Sub-skill 3 (~80 lines)
```

### Content Distribution

| Current content | Goes to |
|----------------|---------|
| Iron rules #1, #5, #6 (loop, log bugs, /clear) | orchestrator |
| Iron rules #2, #3, #4 (git, 30s, workdir) | test-and-gather |
| Chrome MCP guide (steps 2-5) | test-and-gather |
| Test scenario categories (9 categories) | test-and-gather |
| Human-friendliness standard | test-and-gather |
| Chrome MCP failure handling | test-and-gather + verify-one |
| Investigate-fix-test-commit flow (step 6) | fix-one + verify-one (split) |
| Recommended settings | orchestrator |
| Red flags table | split across all (relevant entries each) |
| Forbidden actions table | split across all (relevant entries each) |

### .gitignore Addition

```
# Heuristic loop session state (not project code)
.claude/heuristic-loop-state/
```
