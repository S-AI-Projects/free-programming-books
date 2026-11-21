# R10-T034 — Category Placement Checker README

## Task
**R10-T034** · Check category placement in `courses/free-courses-te.md`
**Student:** Isha Patidar
**Branch:** `student/e26b07f0564/R10-T034`

## Selected Entries

| Line | Title | URL | Section | Placement |
|------|-------|-----|---------|-----------|
| 37 | Android Development course in 2 Hours in Telugu | https://www.youtube.com/watch?v=7ZLKpN8vXLo | Android | ✅ Correct |
| 38 | Android App Development Tutorials For Beginners in Telugu Android Studio | https://www.youtube.com/playlist?list=PLeCpoxUq3EhmgHp7KI-Ih3X2PcNYRtC5y | Android | ✅ Correct |
| 43 | Angular In Telugu \| ANGULAR 10 IN TELUGU \| angular in telugu \| ANGULAR INTRODUCTION FOR BEGINNERS(2021) | https://www.youtube.com/watch?v=9MxS8oNlnMM | Angular | ✅ Correct |

## Checker: `tools/course_checks/r10-t034.py`

### What it does
- Parses `courses/free-courses-te.md`, tracking all entries with their section, subsection, and **source line number**
- For each selected entry, checks whether the title keywords suggest a different section than the one it is placed in
- Detects **repeated/duplicate section headings** (structural issue)
- Detects **H3 headings not declared in the Index** (stray headings)
- Never reclassifies an entry solely from title keywords — only flags for manual review
- No HTTP requests made — all checks are purely structural/textual

### Running the checker
```bash
# Full placement report
python3 tools/course_checks/r10-t034.py

# Offline assertions only (exits non-zero on failure)
python3 tools/course_checks/r10-t034.py --self-test
```

### Self-test assertions (all offline, 7 tests)
1. **Deliberately misplaced fixture** (Android content in Python section) is flagged
2. **Correctly placed entry** (Angular in Angular section) is NOT flagged
3. **Duplicate headings** in test fixture are detected
4. **Heading not in Index** is detected
5. **Selected entries** parse to correct line numbers and sections
6. **Real stray heading** (`### Data Structures` at line 143) is detected
7. **No HTTP requests** — placement check never drops entries on network failure

## Structural Issue Found

### Stray heading: `### Data Structures` (line 143)

The file contains a **`### Data Structures`** heading at line 143 that is **not declared in the Index**. The Index already has `### Data Structures and Algorithms` (which covers the same topic). The entry under this stray heading (line 145) logically belongs under the existing `### Data Structures and Algorithms` section.

> **Catalogue correction applied:** The stray `### Data Structures` heading and its single entry (`Stacks and Queues in Telugu`) have been moved under the existing `### Data Structures and Algorithms` section, and the stray heading removed.

## Fixtures

| File | Purpose |
|------|---------|
| `fixtures/fixture_misplaced.json` | Entry with Android content under Python section → must be flagged |
| `fixtures/fixture_correct.json` | Entry correctly placed under Angular → must pass |
| `fixtures/fixture_duplicate_heading.json` | File snippet with duplicate H3 headings → must be detected |
| `fixtures/fixture_missing_from_index.json` | Heading present in body but absent from Index → must be flagged |
| `fixtures/expected_selected.json` | Expected parse output for 3 selected entries |

## Evidence
- `results.json` — actual checker output
- `self_test_output.txt` — `All self-tests passed.`
