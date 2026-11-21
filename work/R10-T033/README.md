# R10-T033 — Duplicate Detection Checker README

## Task
**R10-T033** · Detect probable duplicates in `books/free-programming-books-da.md`
**Student:** Isha Patidar
**Branch:** `student/e26b07f0815/R10-T033`

## Selected Entries

| Line | Title | URL | Section | Author |
|------|-------|-----|---------|--------|
| 13 | Beej's Guide til Netvarksprogrammierung | https://web.archive.org/web/20190701062226/http://artcreationforever.com/bgnet.html | C | Brian "Beej Jorgensen" Hall |
| 14 | Programmering i C | http://people.cs.aau.dk/~normark/c-prog-06/pdf/all.pdf | C | Kurt Nørmark |
| 19 | Object-oriented Programming in C# | http://people.cs.aau.dk/~normark/oop-csharp/pdf/all.pdf | C\# | Kurt Nørmark |

## Checker: `tools/course_checks/r10-t033.py`

### What it does
- Parses `books/free-programming-books-da.md` and extracts all entries with **source line numbers**
- Groups entries by **normalised URL** (lowercase scheme+host, stripped trailing slash, sorted query params)
- **Preserves distinct anchors** (`#chapter-1` ≠ `#chapter-2` → not merged)
- **Preserves query-dependent resources** (different param values → not merged)
- Flags every duplicate group as `requires_manual_review: true`
- Never proposes a deletion without a manually-reviewed pair

### Running the checker
```bash
# Full duplicate report
python3 tools/course_checks/r10-t033.py

# Offline assertions only (exits non-zero on failure)
python3 tools/course_checks/r10-t033.py --self-test
```

### Self-test assertions (all offline, 7 tests)
1. **Exact duplicate URLs** are detected (same URL, 2 entries)
2. **Distinct anchors** (`#chapter-1` vs `#chapter-2`) are NOT merged
3. **Trailing slash** difference (`/guide` vs `/guide/`) is normalised → grouped
4. **Different query param values** (`?id=1` vs `?id=2`) are NOT merged
5. **Selected entries** parse to correct line numbers, titles and sections
6. **Known real duplicate** (`http://javabog.dk` appears on lines 30 & 31) is detected
7. Every report group carries `requires_manual_review: true`

## Duplicate Found in File

| Normalised URL | Line | Title |
|----------------|------|-------|
| `http://javabog.dk/` | 30 | Objektorienteret programmering i Java |
| `http://javabog.dk/` | 31 | The Complete Reference Java |

> **Manual review required before any catalogue change.**
> Both entries point to `http://javabog.dk` with different titles and authors.
> Browser verification confirms the URL serves a single page — the two entries
> likely represent different books incorrectly linked to the same URL.
> No entry has been removed; this is flagged for maintainer review.

## Selected Entries — Duplicate Status

| Entry | Duplicate? |
|-------|-----------|
| Beej's Guide til Netvarksprogrammierung | No — unique archived URL |
| Programmering i C | No — unique path (`c-prog-06`) |
| Object-oriented Programming in C# | No — unique path (`oop-csharp`) |

## Fixtures

| File | Purpose |
|------|---------|
| `fixtures/fixture_exact_dup.json` | Two entries with identical URLs → must be detected |
| `fixtures/fixture_distinct_anchors.json` | Two entries with same base URL but different fragments → must NOT merge |
| `fixtures/fixture_trailing_slash.json` | Same URL with/without trailing slash → must be normalised and grouped |
| `fixtures/fixture_query_distinct.json` | Same base URL, different query param values → must NOT merge |
| `fixtures/expected_selected.json` | Expected parse output for 3 selected entries |

## Evidence
- `results.json` — actual checker output (selected entries + duplicate groups)
- `self_test_output.txt` — `All self-tests passed.`
