# ANSI-Aware Content Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use pyte buffer character attributes (fg color, bold, italic) to reliably detect code blocks, inline code, headings, and prose in Claude Code's TUI output, replacing heuristic text-pattern matching.

**Architecture:** Three new layers — attributed span extraction from pyte buffer, semantic region classification using syntax-highlight colors, and region rendering to markdown — wired into the fast-IDLE extraction path of `output.py`. The streaming path keeps the old heuristic pipeline as fallback.

**Tech Stack:** pyte (terminal emulator), Python dataclasses, existing Telegram HTML formatter

---

### Task 1: CharSpan dataclass and CODE_FG_COLORS constant

**Files:**
- Modify: `src/parsing/terminal_emulator.py:1-6` (add imports and constants at top)
- Test: `tests/parsing/test_content_classifier.py` (new file)

**Step 1: Write the failing test**

```python
# tests/parsing/test_content_classifier.py
from src.parsing.terminal_emulator import CharSpan, CODE_FG_COLORS

class TestCharSpan:
    def test_frozen(self):
        span = CharSpan(text="hello", fg="blue", bold=True)
        assert span.text == "hello"
        assert span.fg == "blue"
        assert span.bold is True
        try:
            span.text = "world"
            assert False, "Should not be mutable"
        except AttributeError:
            pass

    def test_defaults(self):
        span = CharSpan(text="x")
        assert span.fg == "default"
        assert span.bold is False
        assert span.italic is False

    def test_code_fg_colors_contains_expected(self):
        for color in ("blue", "red", "cyan", "brown", "green"):
            assert color in CODE_FG_COLORS
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_content_classifier.py::TestCharSpan -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Add to top of `src/parsing/terminal_emulator.py`:

```python
from dataclasses import dataclass

CODE_FG_COLORS: frozenset[str] = frozenset({
    "blue", "red", "cyan", "brown", "green",
    "lightblue", "lightred", "lightcyan", "lightgreen",
})

@dataclass(frozen=True, slots=True)
class CharSpan:
    text: str
    fg: str = "default"
    bold: bool = False
    italic: bool = False
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py::TestCharSpan -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/parsing/terminal_emulator.py tests/parsing/test_content_classifier.py
git commit -m "feat: add CharSpan dataclass and CODE_FG_COLORS constant"
```

---

### Task 2: `_row_to_spans()` static method

**Files:**
- Modify: `src/parsing/terminal_emulator.py` (add `_row_to_spans` to `TerminalEmulator`)
- Test: `tests/parsing/test_content_classifier.py`

**Step 1: Write the failing test**

```python
from src.parsing.terminal_emulator import TerminalEmulator, CharSpan

class TestAttributedIntegration:
    def test_get_attributed_lines_basic(self):
        emu = TerminalEmulator(rows=5, cols=40)
        emu.feed("\x1b[34mdef\x1b[0m \x1b[33mhello\x1b[0m():")
        lines = emu.get_attributed_lines()
        assert len(lines) == 5
        first = lines[0]
        assert any(s.fg == "blue" for s in first)
        assert any(s.fg == "brown" for s in first)

    def test_get_attributed_lines_empty_screen(self):
        emu = TerminalEmulator(rows=3, cols=20)
        lines = emu.get_attributed_lines()
        assert len(lines) == 3
        assert all(len(line) == 0 for line in lines)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_content_classifier.py::TestAttributedIntegration -v`
Expected: FAIL with `AttributeError: 'TerminalEmulator' object has no attribute 'get_attributed_lines'`

**Step 3: Write minimal implementation**

Add `_row_to_spans()` static method and `get_attributed_lines()` to `TerminalEmulator`:

```python
@staticmethod
def _row_to_spans(row: dict, cols: int) -> list[CharSpan]:
    spans: list[CharSpan] = []
    cur_text, cur_fg, cur_bold, cur_italic = [], "default", False, False
    for col in range(cols):
        char = row[col]
        fg = char.fg if char.fg else "default"
        bold, italic = bool(char.bold), bool(char.italics)
        if fg == cur_fg and bold == cur_bold and italic == cur_italic:
            cur_text.append(char.data)
        else:
            if cur_text:
                spans.append(CharSpan("".join(cur_text), cur_fg, cur_bold, cur_italic))
            cur_text, cur_fg, cur_bold, cur_italic = [char.data], fg, bold, italic
    if cur_text:
        spans.append(CharSpan("".join(cur_text), cur_fg, cur_bold, cur_italic))
    # Strip trailing whitespace-only spans
    while spans and not spans[-1].text.strip():
        spans.pop()
    if spans:
        last = spans[-1]
        rstripped = last.text.rstrip()
        if rstripped != last.text:
            if rstripped:
                spans[-1] = CharSpan(rstripped, last.fg, last.bold, last.italic)
            else:
                spans.pop()
    return spans

def get_attributed_lines(self) -> list[list[CharSpan]]:
    return [self._row_to_spans(self.screen.buffer[y], self.cols) for y in range(self.rows)]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py::TestAttributedIntegration -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/parsing/terminal_emulator.py tests/parsing/test_content_classifier.py
git commit -m "feat: add _row_to_spans and get_attributed_lines to TerminalEmulator"
```

---

### Task 3: `get_full_attributed_lines()` and `get_attributed_changes()`

**Files:**
- Modify: `src/parsing/terminal_emulator.py`
- Test: `tests/parsing/test_content_classifier.py`

**Step 1: Write the failing tests**

```python
def test_get_full_attributed_lines_with_history(self):
    emu = TerminalEmulator(rows=5, cols=40)
    for i in range(10):
        emu.feed(f"\x1b[34mline_{i}\x1b[0m\r\n")
    full = emu.get_full_attributed_lines()
    assert len(full) > 5
    assert any(s.fg == "blue" for s in full[0])

def test_get_attributed_changes_tracks_diffs(self):
    emu = TerminalEmulator(rows=5, cols=40)
    emu.feed("hello")
    ch1 = emu.get_attributed_changes()
    assert len(ch1) == 1
    ch2 = emu.get_attributed_changes()
    assert ch2 == []
    emu.feed("\r\n\x1b[31mred text\x1b[0m")
    ch3 = emu.get_attributed_changes()
    assert len(ch3) == 1
    assert any(s.fg == "red" for s in ch3[0])
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_content_classifier.py -k "full_attributed or attributed_changes" -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def get_full_attributed_lines(self) -> list[list[CharSpan]]:
    result: list[list[CharSpan]] = []
    for row in self.screen.history.top:
        result.append(self._row_to_spans(row, self.cols))
    result.extend(self.get_attributed_lines())
    return result

def get_attributed_changes(self) -> list[list[CharSpan]]:
    current_text = self.get_display()
    changed_indices = [
        i for i, (cur, prev) in enumerate(zip(current_text, self._prev_display))
        if cur != prev and cur.strip()
    ]
    self._prev_display = list(current_text)
    if not changed_indices:
        return []
    return [self._row_to_spans(self.screen.buffer[i], self.cols) for i in changed_indices]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py -k "full_attributed or attributed_changes" -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/parsing/terminal_emulator.py tests/parsing/test_content_classifier.py
git commit -m "feat: add get_full_attributed_lines and get_attributed_changes"
```

---

### Task 4: `classify_line()` per-line classifier

**Files:**
- Create: `src/parsing/content_classifier.py`
- Test: `tests/parsing/test_content_classifier.py`

**Step 1: Write the failing tests**

```python
from src.parsing.content_classifier import classify_line
from src.parsing.terminal_emulator import CharSpan

class TestClassifyLine:
    def test_empty_spans(self):
        assert classify_line([]) == "blank"

    def test_prose_default_fg(self):
        assert classify_line([CharSpan(text="Plain text.")]) == "prose"

    def test_code_blue_keyword(self):
        spans = [CharSpan(text="def", fg="blue"), CharSpan(text=" foo():")]
        assert classify_line(spans) == "code"

    def test_heading_bold_default(self):
        assert classify_line([CharSpan(text="Title", bold=True)]) == "heading"

    def test_list_item_dash(self):
        assert classify_line([CharSpan(text="- Item")]) == "list_item"

    def test_separator(self):
        assert classify_line([CharSpan(text="─" * 40)]) == "separator"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_content_classifier.py::TestClassifyLine -v`
Expected: FAIL with `ImportError`

**Step 3: Write minimal implementation**

Create `src/parsing/content_classifier.py` with:
- `_LIST_ITEM_RE`, `_SEPARATOR_RE` regexes
- `_has_code_colors()`, `_all_default_fg()`, `_first_nonblank_bold()` helpers
- `classify_line()` function with the priority: blank → separator → list_item → code → heading → prose

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py::TestClassifyLine -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/parsing/content_classifier.py tests/parsing/test_content_classifier.py
git commit -m "feat: add classify_line per-line semantic classifier"
```

---

### Task 5: `_insert_inline_code_markers()` for prose lines

**Files:**
- Modify: `src/parsing/content_classifier.py`
- Test: `tests/parsing/test_content_classifier.py`

**Step 1: Write the failing tests**

```python
from src.parsing.content_classifier import _insert_inline_code_markers

class TestInsertInlineCodeMarkers:
    def test_no_colored_spans(self):
        spans = [CharSpan(text="Plain text.")]
        assert _insert_inline_code_markers(spans) == "Plain text."

    def test_single_inline_code(self):
        spans = [
            CharSpan(text="Use the ", fg="default"),
            CharSpan(text="print", fg="cyan"),
            CharSpan(text=" function.", fg="default"),
        ]
        assert _insert_inline_code_markers(spans) == "Use the `print` function."

    def test_long_colored_span_not_wrapped(self):
        spans = [CharSpan(text="x" * 60, fg="blue")]
        assert "`" not in _insert_inline_code_markers(spans)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_content_classifier.py::TestInsertInlineCodeMarkers -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def _insert_inline_code_markers(spans: list[CharSpan]) -> str:
    parts = []
    for span in spans:
        if not span.text:
            continue
        if span.fg in CODE_FG_COLORS and span.text.strip() and len(span.text.strip()) < 60:
            stripped = span.text.strip()
            leading = span.text[:len(span.text) - len(span.text.lstrip())]
            trailing = span.text[len(span.text.rstrip()):]
            parts.append(f"{leading}`{stripped}`{trailing}")
        else:
            parts.append(span.text)
    return "".join(parts).rstrip()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py::TestInsertInlineCodeMarkers -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/parsing/content_classifier.py tests/parsing/test_content_classifier.py
git commit -m "feat: add inline code marker insertion for prose lines"
```

---

### Task 6: `classify_regions()` region grouping

**Files:**
- Modify: `src/parsing/content_classifier.py`
- Test: `tests/parsing/test_content_classifier.py`

**Step 1: Write the failing tests**

```python
from src.parsing.content_classifier import classify_regions, ContentRegion

class TestClassifyRegions:
    def test_empty_input(self):
        assert classify_regions([]) == []

    def test_single_code_block(self):
        lines = [
            [CharSpan(text="def", fg="blue"), CharSpan(text=" foo():")],
            [CharSpan(text="    "), CharSpan(text="print", fg="cyan"), CharSpan(text="(42)")],
        ]
        regions = classify_regions(lines)
        assert len([r for r in regions if r.type == "code_block"]) == 1

    def test_gap_tolerance_comment_in_code(self):
        lines = [
            [CharSpan(text="x", fg="brown"), CharSpan(text=" = 1")],
            [CharSpan(text="# comment")],  # default fg between code
            [CharSpan(text="y", fg="brown"), CharSpan(text=" = 2")],
        ]
        regions = classify_regions(lines)
        assert len([r for r in regions if r.type == "code_block"]) == 1

    def test_prose_with_inline_code(self):
        # Tested via full integration with TerminalEmulator
        ...

    def test_adjacent_code_lines_merge(self):
        lines = [
            [CharSpan(text="import", fg="blue"), CharSpan(text=" os")],
            [CharSpan(text="import", fg="blue"), CharSpan(text=" sys")],
        ]
        regions = classify_regions(lines)
        assert len([r for r in regions if r.type == "code_block"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_content_classifier.py::TestClassifyRegions -v`
Expected: FAIL

**Step 3: Write minimal implementation**

`classify_regions()` with three steps:
1. Classify each line → `line_types` + `line_texts` (with inline code markers for prose/list)
2. Apply 1-line gap tolerance for code blocks
3. Group adjacent same-type lines into `ContentRegion` objects

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py::TestClassifyRegions -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/parsing/content_classifier.py tests/parsing/test_content_classifier.py
git commit -m "feat: add classify_regions region grouping with gap tolerance"
```

---

### Task 7: `render_regions()` in formatter.py

**Files:**
- Modify: `src/telegram/formatter.py`
- Test: `tests/parsing/test_formatter.py`

**Step 1: Write the failing tests**

```python
from src.parsing.content_classifier import ContentRegion
from src.telegram.formatter import render_regions, format_html, reflow_text

class TestRenderRegions:
    def test_code_block_region(self):
        regions = [ContentRegion(type="code_block", text="def foo():\n    pass")]
        result = render_regions(regions)
        assert result.startswith("```")
        assert "def foo():" in result

    def test_heading_region(self):
        regions = [ContentRegion(type="heading", text="Summary")]
        assert render_regions(regions) == "**Summary**"

    def test_separator_suppressed(self):
        regions = [ContentRegion(type="separator", text="────")]
        assert render_regions(regions) == ""

    def test_full_pipeline_code_becomes_pre(self):
        regions = [
            ContentRegion(type="prose", text="Example:"),
            ContentRegion(type="code_block", text="def hello():\n    print('hi')"),
            ContentRegion(type="prose", text="Uses `print`."),
        ]
        html = format_html(reflow_text(render_regions(regions)))
        assert "<pre><code>" in html
        assert "<code>print</code>" in html
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/parsing/test_formatter.py::TestRenderRegions -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def render_regions(regions: list[ContentRegion]) -> str:
    parts = []
    for region in regions:
        if region.type == "code_block":
            parts.extend([f"```{region.language or ''}", region.text, "```"])
        elif region.type == "heading":
            parts.append(f"**{region.text}**")
        elif region.type == "separator":
            continue
        elif region.type == "blank":
            parts.append("")
        else:
            parts.append(region.text)
    return "\n".join(parts)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/parsing/test_formatter.py::TestRenderRegions -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/telegram/formatter.py tests/parsing/test_formatter.py
git commit -m "feat: add render_regions converting ContentRegion to markdown"
```

---

### Task 8: Wire ANSI-aware pipeline into output.py fast-IDLE path

**Files:**
- Modify: `src/telegram/output.py:1-20` (imports) and `src/telegram/output.py:296-374` (extraction section)
- Test: `tests/telegram/test_output.py` (update existing mocked tests)

**Step 1: Write the failing test**

No new test needed — existing `test_thinking_to_idle_extracts_fast_response_from_display` validates the fast-IDLE path. Verify it still passes after wiring.

**Step 2: Modify output.py imports**

```python
from src.parsing.content_classifier import classify_regions
from src.telegram.formatter import format_html, reflow_text, render_regions, wrap_code_blocks
```

**Step 3: Modify fast-IDLE extraction**

Key changes:
1. Capture `full_attr = emu.get_full_attributed_lines()` **BEFORE** `emu.clear_history()`
2. When `fast_idle_attr is not None`: `classify_regions(attr) → render_regions → format_html`
3. Else (streaming/ultra-fast): keep old `wrap_code_blocks` pipeline

**Step 4: Update existing tests**

Tests that mock `extract_content` for fast-IDLE now also need to mock `render_regions` since the attributed pipeline produces output from the pyte buffer, not from `extract_content`'s return value:

```python
# In test_thinking_to_idle_extracts_fast_response_from_display:
patch("src.telegram.output.render_regions", return_value="Four"),

# In test_thinking_unknown_idle_still_extracts_response:
patch("src.telegram.output.render_regions", return_value="Four."),
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/telegram/test_output.py -v`
Expected: ALL PASS

**Step 6: Run full suite**

Run: `pytest -x -q`
Expected: ALL PASS

**Step 7: Commit**

```bash
git add src/telegram/output.py tests/telegram/test_output.py
git commit -m "feat: wire ANSI-aware pipeline into fast-IDLE extraction path"
```

---

### Task 9: Integration test — full TerminalEmulator → Telegram HTML

**Files:**
- Test: `tests/parsing/test_content_classifier.py`

**Step 1: Write the integration test**

```python
def test_full_claude_response_simulation(self):
    emu = TerminalEmulator(rows=20, cols=80)
    emu.feed("Here is a Python function:\r\n\r\n")
    emu.feed("\x1b[34mdef\x1b[0m \x1b[33mgreet\x1b[0m(name):\r\n")
    emu.feed("    \x1b[36mprint\x1b[0m(\x1b[31mf\"Hello, {name}!\"\x1b[0m)\r\n")
    emu.feed("\r\nThis function:\r\n")
    emu.feed("- Takes a \x1b[33mname\x1b[0m parameter\r\n")
    emu.feed("- Uses \x1b[36mprint\x1b[0m to output\r\n")

    lines = emu.get_attributed_lines()
    regions = classify_regions(lines)
    types = [r.type for r in regions if r.type != "blank"]
    assert "prose" in types
    assert "code_block" in types
    assert "list" in types

    code = next(r for r in regions if r.type == "code_block")
    assert "def greet" in code.text
    list_r = next(r for r in regions if r.type == "list")
    assert "`name`" in list_r.text
    assert "`print`" in list_r.text
```

**Step 2: Run test to verify it passes**

Run: `pytest tests/parsing/test_content_classifier.py::TestClassifyRegions::test_full_claude_response_simulation -v`
Expected: PASS (already implemented)

**Step 3: Commit**

```bash
git add tests/parsing/test_content_classifier.py
git commit -m "test: add full integration test for ANSI-aware pipeline"
```

---

### Task 10: Update documentation

**Files:**
- Modify: `CLAUDE.md` (add content_classifier to architecture diagram and file table)
- Modify: `src/parsing/__init__.py` (update docstring)

**Step 1: Update CLAUDE.md**

Add `content_classifier` node to the mermaid diagram and add a row to the "Where to Find X" table.

**Step 2: Update __init__.py**

```python
"""Terminal output parsing pipeline: emulator → patterns → detectors → classifier → content_classifier."""
```

**Step 3: Run full test suite**

Run: `pytest -x -q`
Expected: ALL PASS, 619+ tests

**Step 4: Commit**

```bash
git add CLAUDE.md src/parsing/__init__.py
git commit -m "docs: add content_classifier to architecture diagram and file map"
```

---

## Compliance Audit: Design vs Implementation

See next section below.
