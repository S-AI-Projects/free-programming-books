# R10-T007: Failure Classification for free-programming-books-te.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T007  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T007`  
**Target File:** `books/free-programming-books-te.md`  

---

## 1. Objective
Distinguish HTTP response states including 200 OK, 404 Not Found, 403 Forbidden, 429 Rate Limited, HEAD-405/GET-200 fallback, timeouts, and login walls. Enforce repository policy that links must never be removed solely due to single automated failures or transient rate-limits.

## 2. Selected Entries & Status

| Line | Title | URL | Classification | Recommendation Policy |
|---|---|---|---|---|
| 12 | Books - Telugu | `https://sites.google.com/nptel.iitm.ac.in/translated-ebook/telugu` | `LOGIN_WALL` | KEEP: Institutional NPTEL translation repository |
| 17 | Introduction to C \| Telugu | `https://www.computerintelugu.com/2012/11/cmenu.html` | `SUCCESS_200` | KEEP: Active accessible resource |
| 22 | Core Java in Telugu \| Java Programming | `https://www.youtube.com/playlist?list=PLz8gl4BEGkEGYXNZrIRHJUSoxS_FPBrDy` | `SUCCESS_200` | KEEP: Active accessible playlist |

## 3. Classification Fixtures
- `fixture_200.json`: Direct 200 OK (`SUCCESS_200`)
- `fixture_404.json`: Missing resource (`NOT_FOUND_404`) -> Requires manual confirmation before proposing removal
- `fixture_429.json`: Rate limited (`RATE_LIMITED_429`) -> Protected by `DO_NOT_REMOVE` policy
- `fixture_head405_get200.json`: Server rejects HEAD with 405 Method Not Allowed, fallback GET succeeds with 200 (`HEAD_405_GET_200`)
- `fixture_timeout.json`: Transient request timeout (`TIMEOUT`) -> Protected by `DO_NOT_REMOVE` policy

## 4. Verification and Self-Test

```bash
# Run self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t007.py --self-test

# Run classification audit on target file
python3 tools/course_checks/r10-t007.py
```

## 5. Catalogue Status
No links are removed. All three selected entries are verified and maintained in `books/free-programming-books-te.md`.
