# R10-T004: Category Consistency Check for free-programming-books-ur.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T004  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T004`  
**Target File:** `books/free-programming-books-ur.md`  

---

## 1. Objective
Map selected entries in `books/free-programming-books-ur.md` to their declared category and flag misplaced entries or repeated headings without reclassifying entries solely from naive keywords.

## 2. Selected Entries and Verification

| Line | Title | URL | Category | Subject Matter | Status |
|---|---|---|---|---|---|
| 9 | C++ Sikhiyei (Urdu) | `https://archive.org/details/CSikhiyeiUrduByAjnabiii` | C++ | C++ Programming in Urdu | VALID_CATEGORY |
| 14 | HTML In Urdu Complete Tutorial Learning Book | `https://www.eislamicbook.com/html-in-urdu-complete-tutorial-learning-book/` | HTML | HTML web development in Urdu | VALID_CATEGORY |

## 3. Fixtures and Logic
- `fixture_valid.md`: Represents a clean list with proper heading hierarchy (`C++` and `HTML`) and verified entries.
- `fixture_misplaced.md`: Contains a deliberately misplaced entry (HTML tutorial placed under `C++`, and C++ book placed under `HTML`) and duplicate `### HTML` heading.
- The check parses HTML anchor tags cleanly, verifies heading uniqueness, and cross-checks known verified subject matter rather than naive substring matching.

## 4. Verification and Self-Test

```bash
# Run self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t004.py --self-test

# Run category placement audit
python3 tools/course_checks/r10-t004.py
```

## 5. Catalogue Status
Both selected entries in `books/free-programming-books-ur.md` are correctly placed under their respective language/topic headings (`C++` and `HTML`). No catalogue changes required.
