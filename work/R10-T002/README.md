# R10-T002: Redirect Verification for free-podcasts-screencasts-ru.md

**Student:** Anshuman Holkar  
**Task ID:** R10-T002  
**Repository:** https://github.com/S-AI-Projects/free-programming-books  
**Branch:** `student/e26b07f0734/R10-T002`  
**Target File:** `casts/free-podcasts-screencasts-ru.md`  

---

## 1. Objective
Resolve redirect chains with a bounded request budget (max 5 hops, 5s timeout) to accurately distinguish moved resources (301/302 redirects) from redirect loops, timeouts, and login walls.

## 2. Selected Entries and Live Observations

| Line | Title | Initial URL | Final URL | Classification | Recommendation |
|---|---|---|---|---|---|
| 24 | Квант безопасности | `https://soundcloud.com/nikita-remezov` | `https://soundcloud.com/nikita-remezov` | `DIRECT_OK` | KEEP (Resource active at original URL) |
| 25 | LinkMeUp | `http://linkmeup.ru` | `https://linkmeup.ru/` | `MOVED_PERMANENTLY` | UPDATE_HTTPS (Prefer HTTPS link) |
| 26 | Noise Security Bit | `https://noisebit.podster.fm` | `https://podster.fm/podcasts/noisebit` | `MOVED_PERMANENTLY` | UPDATE_FINAL (Update target to canonical domain) |

*Observation Date:* 2026-11-23

## 3. Fixtures and Classification Suite
The offline test suite in `work/R10-T002/fixtures/` covers all states without requiring live network access:
1. `fixture_200.json`: Direct 200 OK (`DIRECT_OK`)
2. `fixture_301_to_200.json`: 301 Moved Permanently leading to 200 (`MOVED_PERMANENTLY`)
3. `fixture_loop.json`: Circular redirect cycle (`REDIRECT_LOOP`)
4. `fixture_timeout.json`: Simulated request timeout (`TIMEOUT`)
5. `fixture_login_wall.json`: Redirect to authentication portal (`LOGIN_WALL`)

## 4. Verification and Self-Test

```bash
# Run self-test suite (exits 0 on success, non-zero on failure)
python3 tools/course_checks/r10-t002.py --self-test

# Run standard redirect report
python3 tools/course_checks/r10-t002.py
```

## 5. Catalogue Status
Per task instructions, no link is removed solely due to an automated test. The entries are documented with recommendations.
