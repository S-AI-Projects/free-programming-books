# R10-T038: Ordering and Formatting Checker for `books/free-programming-books-en.md`

## Task Description

**Task ID:** R10-T038  
**Related Issue:** [#40](https://github.com/S-AI-Projects/free-programming-books/issues/40)  
**Branch:** `student/e26b07f0564/R10-T038`  
**Author:** Isha Patidar  
**Target File:** `books/free-programming-books-en.md`

This task implements an ordering and formatting checker (`tools/course_checks/r10-t038.py`) that validates the structure of `books/free-programming-books-en.md` against the EbookFoundation contribution guide rules.

---

## Selected Entries

The first three bullet entries in `books/free-programming-books-en.md`:

| Line | Section | Title | URL |
|------|---------|-------|-----|
| 3 | Index | All | `#all` (fragment anchor) |
| 8 | All | English, By Programming Language | `free-programming-books-langs.md` |
| 9 | All | English, By Subject | `free-programming-books-subjects.md` |

---

## Checks Implemented

The checker validates:

| Check | Description |
|-------|-------------|
| **Bullet syntax** | Each `*` line must follow `* [Title](URL) [optional rest]` |
| **Non-English text preserved** | Unicode/non-ASCII titles pass through unchanged |
| **Markdown links preserved** | `[Title](URL)` structure must remain intact |
| **Heading hierarchy** | Levels must not skip (e.g., H1→H3 is rejected; H1→H2→H3 is valid) |
| **Alphabetical ordering** | Entries within a section must be sorted by title (case-insensitive) |
| **Trailing whitespace** | Lines must not end with trailing spaces or tabs |
| **Non-empty URL** | URL field inside `[Title](URL)` must not be empty |
| **Fragment anchors** | `#anchor` URLs are valid internal references |

---

## Checker Script

**File:** `tools/course_checks/r10-t038.py`

### Usage

```bash
# Offline self-test (no network required) — exits non-zero on any failure
python3 tools/course_checks/r10-t038.py --self-test

# Full analysis — writes work/R10-T038/results.json
python3 tools/course_checks/r10-t038.py
```

---

## Fixture Files

| File | Purpose |
|------|---------|
| `fixtures/fixture_malformed.md` | Malformed bullet (no URL) → error detected |
| `fixtures/fixture_valid.md` | Valid entry with Unicode title → passes all checks |
| `fixtures/fixture_heading_skip.md` | H1→H3 (skips H2) → heading hierarchy error |
| `fixtures/fixture_out_of_order.md` | Entries out of alphabetical order → ordering warning |
| `fixtures/fixture_trailing_ws.md` | Line with trailing whitespace → warning |
| `fixtures/fixture_anchor.md` | Fragment anchor `#anchor` URL → accepted as valid |

---

## Results

The target file `books/free-programming-books-en.md` **passes all checks**:
- 0 errors
- 0 warnings
- 2 headings (`### Index`, `### All`)
- 3 entries (all selected)

See `results.json` for the full report.

---

## Self-Test Results

```
All self-tests passed.
```

28 assertions across 7 fixture groups — all offline.

See `self_test_output.txt` for full output.

