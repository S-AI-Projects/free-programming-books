# R10-T003: Duplicate Detection for free-programming-books-sk.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T003  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T003`  
**Target File:** `books/free-programming-books-sk.md`  

---

## 1. Objective
Implement conservative duplicate URL detection for `books/free-programming-books-sk.md`. Group exact duplicate URLs and conservative URL-normalization matches while preserving distinct query parameters and meaningful anchor fragments.

## 2. Selected Entries

| Line | Title | Original URL | Normalized URL | Duplicate Status |
|---|---|---|---|---|
| 15 | Zodpovednosť na internete | `https://knihy.nic.cz` | `https://knihy.nic.cz` | UNIQUE |
| 20 | Malá kniha programovania | `https://greenie.elist.sk/knihy/html/mala-kniha-programovania.html` | `https://greenie.elist.sk/knihy/html/mala-kniha-programovania.html` | UNIQUE |
| 25 | Linux ako niečo navyše | `https://greenie.elist.sk/knihy/linux-ako-nieco-navyse.pdf` | `https://greenie.elist.sk/knihy/linux-ako-nieco-navyse.pdf` | UNIQUE |

## 3. Normalization Rules & Fixtures
The checker applies conservative normalization:
- Lowercase scheme and domain host.
- Remove default ports (`:80` for HTTP, `:443` for HTTPS).
- Strip trailing slash ONLY on root domains (`https://example.com/` -> `https://example.com`).
- **Never** strip or merge distinct URL anchors (e.g., `#chapter1` vs `#chapter2`).
- **Never** strip or merge query parameters (e.g., `?page=1` vs `?page=2`).

The offline test suite in `work/R10-T003/fixtures/` tests:
- `fixture_exact_dup.json`: Identical URLs correctly grouped.
- `fixture_trailing_slash.json`: Trailing slash on root domain correctly matched.
- `fixture_distinct_anchors.json`: Distinct anchors verified not merged.
- `fixture_query_distinct.json`: Query-dependent URLs verified not merged.

## 4. Verification and Self-Test

```bash
# Run self-test assertions (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t003.py --self-test

# Run duplicate audit on the target catalogue
python3 tools/course_checks/r10-t003.py
```

## 5. Catalogue Status
No catalogue modifications required: the target file contains zero duplicate entries.
