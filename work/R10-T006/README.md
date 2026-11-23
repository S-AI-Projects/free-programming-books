# R10-T006: Offline Fixture Tests for free-courses-si.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T006  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T006`  
**Target File:** `courses/free-courses-si.md`  

---

## 1. Objective
Build a fixture-based test suite for parsing and validating `courses/free-courses-si.md` that runs 100% offline without live internet access. Explicitly verify expected outcomes for malformed rows, valid rows, and unusual URL characters.

## 2. Selected Entries

| Line | Title | Category | URL | Author |
|---|---|---|---|---|
| 19 | Data Structures and Algorithms \| Sinhala | Algorithms & Data Structures | `https://www.youtube.com/playlist?list=PL495mke12zYDIwsabzb61OLdBpg3QDcXg` | CodePRO LK |
| 24 | Deep Learning Tutorial \| Sinhala | Artificial Intelligence | `https://www.youtube.com/playlist?list=PL495mke12zYBLz2j_RoYbIltaYxvaTd9k` | CodePRO LK |
| 25 | Machine Learning Tutorial \| Sinhala | Artificial Intelligence | `https://www.youtube.com/playlist?list=PL495mke12zYDHN9ONfcal1eQfo8VqmOgu` | CodePRO LK |

## 3. Fixtures and Test Suite
- `fixture_valid.md`: Covers valid course entries, including escaped markdown pipe characters (`\|` -> `|`) and Sinhala Unicode script.
- `fixture_malformed.md`: Covers malformed markdown syntax (missing parens, unclosed links, empty URLs) and confirms 0 false positives.
- `fixture_unusual_urls.md`: Validates preservation of percent-encoded paths, complex query parameters, and URL fragments.

## 4. Verification and Self-Test

```bash
# Run the self-test suite (operates completely offline, exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t006.py --self-test

# Run offline report on target catalogue
python3 tools/course_checks/r10-t006.py
```

## 5. Catalogue Status
All selected entries are correctly formatted in `courses/free-courses-si.md` and pass offline verification. No catalogue edits required.
