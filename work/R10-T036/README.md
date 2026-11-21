# R10-T036: Offline Fixture Test Suite for `free-programming-books-tr.md`

## Task Description

**Task ID:** R10-T036  
**Related Issue:** [#38](https://github.com/S-AI-Projects/free-programming-books/issues/38)  
**Branch:** `student/e26b07f0564/R10-T036`  
**Author:** Isha Patidar  
**Target File:** `books/free-programming-books-tr.md`

This task implements an offline fixture-based test suite that validates the parsing and format rules for Turkish-language book entries in the EbookFoundation free-programming-books repository.

---

## Selected Entries

The following entries from `books/free-programming-books-tr.md` were selected for analysis:

| Line | Title | URL | Author | Format |
|------|-------|-----|--------|--------|
| 32 | Algoritma ve Programlama Soru Bankası | [archive.org PDF](https://ia601404.us.archive.org/34/items/algoritma-ve-programlama-soru-bankasi/algoritma-ve-programlama-soru-bankas%C4%B1.pdf) | *(none)* | PDF |
| 33 | Algoritma ve Programlamaya Giriş Ders Notları | [archive.org PDF](https://ia601404.us.archive.org/12/items/algoritma-ve-programlamaya-giris-ders-notlari/Algoritma%20ve%20Programlamaya%20Giri%C5%9F%20Ders%20Notlar%C4%B1.pdf) | [İbrahim Küçükkoç](http://ikucukkoc.baun.edu.tr) | PDF |

**Notable characteristics:**
- **Line 32:** No author field; URL contains percent-encoded Turkish characters (`%C4%B1`).
- **Line 33:** Author is a hyperlinked name `[İbrahim Küçükkoç](http://ikucukkoc.baun.edu.tr)` — requires special parsing; URL also contains percent-encoded characters (`%20`, `%C5%9F`).

---

## Checker Script

**File:** `tools/course_checks/r10-t036.py`

### Usage

```bash
# Run full analysis — writes work/R10-T036/results.json
python3 tools/course_checks/r10-t036.py

# Run offline fixture tests (no network required)
python3 tools/course_checks/r10-t036.py --self-test
```

### What the checker validates

1. **Parsing correctness** — entries are matched by a carefully constructed regex that handles:
   - Standard entries: `* [Title](URL) (Format)`
   - Entries with plain author: `* [Title](URL) - Author Name (Format)`
   - Entries with linked author: `* [Title](URL) - [Author Name](Author URL) (Format)`
   - Percent-encoded URLs (preserved verbatim, not decoded)
   - Fenced code blocks (skipped)

2. **Format field presence** — warns if an entry has no format specifier (PDF, HTML, etc.)

3. **Non-empty URL** — errors if URL field is empty

---

## Fixture Files

| File | Purpose |
|------|---------|
| `fixtures/fixture_malformed.md` | Malformed entry (missing closing bracket + URL) → 0 entries parsed |
| `fixtures/fixture_valid_percent_url.md` | Valid entry with percent-encoded URL → URL preserved verbatim |
| `fixtures/fixture_linked_author.md` | Valid entry with `[Author](URL)` author field → both name and URL extracted |
| `fixtures/fixture_no_author.md` | Valid entry with no author → author field empty |
| `expected_selected.json` | Expected parse output for the two selected lines |

---

## Self-Test Results

```
All self-tests passed.
```

See `self_test_output.txt` for full output.

---

## Results

See `results.json` for the full analysis report (written by running the checker without `--self-test`).
