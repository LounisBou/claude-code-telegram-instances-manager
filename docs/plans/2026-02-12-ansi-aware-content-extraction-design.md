# ANSI-Aware Content Extraction Design

**Date**: 2026-02-12
**Branch**: `feat/rich-output-streaming`
**Goal**: Use pyte buffer character attributes (fg color, bold, italic) to reliably detect code blocks, inline code, headings, and other structured content in Claude Code's TUI output, replacing heuristic text-pattern matching.

## Problem

Claude Code's TUI renders responses with syntax highlighting (ANSI colors) but strips markdown source. Our current pipeline extracts plain text from pyte and tries to re-detect code blocks via keyword heuristics (`wrap_code_blocks()`). This fails for:
- Code without recognizable first-line keywords
- Inline code references within prose
- Mixed prose/code responses
- Bold headings vs regular text

## Key Insight

pyte's screen buffer stores per-character attributes (`fg`, `bold`, `italic`) that encode Claude Code's syntax highlighting:

| Content | Foreground color |
|---------|-----------------|
| Code keywords (`def`, `import`) | `blue` |
| String literals (`"hello"`) | `red` |
| Builtin functions (`print`, `len`) | `cyan` |
| Identifiers (`hello_world`) | `brown` |
| Prose/explanatory text | `default` |
| Response marker (`⏺`) | `ffffff` (white) |
| UI separators (`────`) | `888888` (gray) |

## Architecture

### Layer 1: Attributed Display (`terminal_emulator.py`)

New `get_attributed_lines()` method returns screen lines as lists of `CharSpan` — contiguous runs of characters sharing the same fg, bold, and italic state.

```python
@dataclass(frozen=True, slots=True)
class CharSpan:
    text: str
    fg: str        # normalized: "default", "blue", "red", "cyan", "brown", etc.
    bold: bool
    italic: bool
```

- Adjacent same-attr characters merge into spans (~5-15 per line vs 120 per-char)
- Includes scrollback history for fast-IDLE path
- Color normalization: pyte's various formats → small named set
- Also adds `get_attributed_changes()` for streaming path

### Layer 2: Content Region Classifier (`content_classifier.py` — new file)

Interprets attributes semantically using per-line classification rules:

| Signal | Classification |
|--------|---------------|
| Any span with `fg ∈ {blue, red, cyan, brown, green}` | `CODE` line |
| All spans `fg=default`, no bold | `PROSE` line |
| All spans `fg=default`, bold on first span | `HEADING` line |
| Line starts with `- ` or `* ` or `N. ` | `LIST_ITEM` |
| Line is all `─` chars with `fg=gray` | `SEPARATOR` |
| Empty/whitespace-only | `BLANK` |

Adjacent `CODE` lines merge into code blocks. A `default`-colored line between two `CODE` lines stays in the block (1-line gap tolerance for comments).

**Inline code**: Within `PROSE` lines, short colored spans (<60 chars) are wrapped in backticks. Longer ones promote the line to `CODE`.

Output: list of `ContentRegion` objects:

```python
@dataclass
class ContentRegion:
    type: Literal["code_block", "prose", "heading", "list", "separator", "blank"]
    text: str
    language: str = ""
```

### Layer 3: Region Rendering (`formatter.py`)

New `render_regions()` function produces text with markdown-style markers:
- Code blocks → triple backticks
- Inline code → single backticks (already inserted by classifier)
- Bold headings → `**text**`
- Prose → plain text

### Layer 4: Pipeline Integration (`output.py`)

**New pipeline**:
```
get_attributed_lines() → classify_regions() → render_regions() → format_html()
```

**Replaces**:
```
extract_content() → wrap_code_blocks() → reflow_text() → format_html()
```

Two paths:
1. **Fast-IDLE**: `get_full_attributed_lines()` (history + screen) → classify → render → format
2. **Streaming**: `get_attributed_changes()` → classify → render → append to `StreamingMessage`

Streaming tracks `_in_code_block: bool` state across poll cycles.

### File Changes

| Component | File | Change |
|-----------|------|--------|
| `CharSpan` dataclass | `src/parsing/terminal_emulator.py` | New |
| `get_attributed_lines()` | `src/parsing/terminal_emulator.py` | New method |
| `get_attributed_changes()` | `src/parsing/terminal_emulator.py` | New method |
| `ContentRegion` + `classify_regions()` | `src/parsing/content_classifier.py` | **New file** |
| `render_regions()` | `src/telegram/formatter.py` | New function |
| Pipeline wiring | `src/telegram/output.py` | Modify extraction |
| Remove `wrap_code_blocks()` | `src/telegram/formatter.py` | Delete |

### Backward Compatibility

`get_display()`, `get_changes()`, `get_text()` remain unchanged. Screen classifier and detectors keep working.

## Edge Cases

| Edge case | Handling |
|-----------|----------|
| No syntax highlighting (plain text code) | Fall back to indentation-based heuristic |
| Single-line code snippet | `<code>` if short, `<pre>` if long (>80 chars) |
| Code comments in default fg | 1-line gap tolerance keeps them in the code block |
| Code block split across poll cycles | `_in_code_block` state carries across |
| Scrollback history attributes | pyte `Char` objects in history preserve attributes |

## Testing Strategy

1. **Unit**: `get_attributed_lines()` — feed ANSI, verify spans
2. **Unit**: `classify_regions()` — feed spans, verify regions
3. **Integration**: Full pipeline with real captured data → verify HTML output
4. **Live**: Test via Telegram using live-testing-loop

## YAGNI — Not Doing

- Language detection from syntax colors
- Custom theme/color mapping config
- Reconstructing markdown headers from bold
