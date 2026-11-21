# R10-T032 — Redirect Verification Checker README

## Task
**R10-T032** · Verify redirects from `courses/free-courses-bn.md`
**Student:** Isha Patidar
**Branch:** `student/e26b07f0815/R10-T032`

## Selected Entries

| Line | Title | URL | Section | Author |
|------|-------|-----|---------|--------|
| 52 | Android Bangla Tutorials | https://www.youtube.com/playlist?list=PLgH5QX0i9K3p9xzYLFGdfYliIRBLVDRV5 | Android | Anisul Islam |
| 53 | Android Firebase Bangla Tutorials | https://www.youtube.com/playlist?list=PLgH5QX0i9K3oDurEmECb5U_BZ1hrLaHx- | Android | Anisul Islam |
| 54 | Android SQLite Database Bangla Tutorials | https://www.youtube.com/playlist?list=PLgH5QX0i9K3oJBRutwsFgUKrKJCjv9K3p | Android | Anisul Islam |

## Checker: `tools/course_checks/r10-t032.py`

### What it does
- Parses `courses/free-courses-bn.md` and extracts entries with **source line numbers**
- For each selected URL, follows the redirect chain (up to 10 hops, 10s timeout, serial requests)
- Classifies the result as: `OK`, `REDIRECTED`, `LOOP`, `LOGIN_WALL`, `TIMEOUT`, `ERROR`, or `SKIPPED`
- Records the **final official URL** and **observation date** for redirected resources
- Never removes a link solely because a single automated request failed (TIMEOUT/LOOP policy)
- Writes `work/R10-T032/results.json` with full evidence

### Running the checker
```bash
# Live redirect check (makes HTTP HEAD requests)
python3 tools/course_checks/r10-t032.py

# Parse only, no HTTP requests
python3 tools/course_checks/r10-t032.py --offline

# Run offline assertions (exits non-zero on failure)
python3 tools/course_checks/r10-t032.py --self-test
```

### Self-test assertions (all offline)
1. **200 fixture** → classified as `OK`
2. **301→200 fixture** → classified as `REDIRECTED`, hops ≥ 1, final URL recorded
3. **Redirect-loop fixture** → classified as `LOOP`
4. **Timeout fixture** → classified as `TIMEOUT`
5. **Login-wall fixture** → classified as `LOGIN_WALL`
6. **Selected entries** → correct line numbers, titles and sections from source file
7. **No silent removal** → TIMEOUT result is reported, not dropped; `final_url` preserved

## Fixtures

| File | Purpose |
|------|---------|
| `fixtures/fixture_200.json` | 200 OK scenario |
| `fixtures/fixture_301_to_200.json` | Redirect chain resolving to 200 |
| `fixtures/fixture_loop.json` | Redirect loop scenario |
| `fixtures/fixture_timeout.json` | Timeout scenario |
| `fixtures/fixture_login_wall.json` | Login-wall scenario |
| `fixtures/expected_selected.json` | Expected parse output for 3 selected entries |

## Classification Legend

| Class | Meaning |
|-------|---------|
| `OK` | 200 at the original URL (0 or transparent redirects) |
| `REDIRECTED` | Chain resolved to a new final URL; final URL recorded |
| `LOOP` | Redirect cycle detected (> 10 hops or cycle) |
| `LOGIN_WALL` | Final URL is a login/sign-in page |
| `TIMEOUT` | Request did not complete in 10 s |
| `ERROR` | 4xx/5xx HTTP error at final destination |
| `SKIPPED` | Not checked (offline mode) |

## Catalogue Corrections
No corrections required. Manual browser verification confirms all three YouTube playlist URLs are accessible and correctly listed. TIMEOUT or LOOP results alone are not grounds for removal per task policy.

## Evidence
- `results.json` — actual checker output for the selected entries
- `self_test_output.txt` — stdout from `python3 tools/course_checks/r10-t032.py --self-test`
