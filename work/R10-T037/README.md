# R10-T037: Failure Classification Checker for `courses/free-courses-km.md`

## Task Description

**Task ID:** R10-T037  
**Related Issue:** [#39](https://github.com/S-AI-Projects/free-programming-books/issues/39)  
**Branch:** `student/e26b07f0564/R10-T037`  
**Author:** Isha Patidar  
**Target File:** `courses/free-courses-km.md`

This task implements a failure-classification checker (`tools/course_checks/r10-t037.py`) that distinguishes between:

| Label | Meaning |
|-------|---------|
| `ok` | HTTP 200 (or 2xx) — resource available |
| `not_found` | HTTP 404 — resource missing |
| `rate_limited` | HTTP 429 — temporarily blocked (NOT a dead link) |
| `forbidden` | HTTP 403 — access denied (NOT a dead link) |
| `head_unsupported_get_ok` | HEAD→405, GET→200 — server doesn't support HEAD |
| `dns_failure` | Socket/DNS error — hostname unresolvable |
| `timeout` | Request timed out — NOT a dead link |
| `error` | Unexpected HTTP or network error |
| `skipped` | Not checked (offline mode) |

> **Policy:** A link is **never** removed solely because a single automated request failed. Rate-limiting (429) and timeouts are not indicators of a dead link. Only manually confirmed missing resources should be removed.

---

## Selected Entries

| Line | Title | URL | Author |
|------|-------|-----|--------|
| 13 | ចំនេះដឹងទូទៅ | [youtube.com playlist PLB5U9f77...](https://youtube.com/playlist?list=PLB5U9f77LXqL-IC2MAoaKl1tJOuiQZbZQ) | TFD |
| 18 | Flutter food ordering app | [youtube.com playlist PL9nDNu0...](https://youtube.com/playlist?list=PL9nDNu0HsFZk6qC7nfhdYbnB-B9wyfKV9) | Chunlee Thong |
| 19 | Flutter UI Speed Code | [youtube.com playlist PLVY9Ibk...](https://youtube.com/playlist?list=PLVY9IbkulBUiKDrT5BFcMKXxtk4b0IJIX) | Sopheaman Van |

---

## Checker Script

**File:** `tools/course_checks/r10-t037.py`

### Usage

```bash
# Offline self-test (no network required) — exits non-zero on any failure
python3 tools/course_checks/r10-t037.py --self-test

# Full analysis (offline mode — marks selected entries as 'skipped')
python3 tools/course_checks/r10-t037.py

# Full analysis with live HTTP checks (timeout=10s, low concurrency)
python3 tools/course_checks/r10-t037.py --live
```

### Implementation details

- **HEAD first, GET fallback:** Sends HEAD; if the server returns 405 (Method Not Allowed), retries with GET.
- **Timeout:** 10 seconds per request.
- **Concurrency:** Only the small fixed selected entry list is checked live; concurrency is low.
- **DNS vs timeout:** `socket.gaierror` → `dns_failure`; `socket.timeout` / `URLError(timed_out)` → `timeout`.
- **No link removal:** Entries classified as `rate_limited` or `timeout` are never recommended for removal.

---

## Fixture Files

| File | Purpose |
|------|---------|
| `fixtures/fixture_malformed.md` | Malformed entry (no URL) → 0 entries parsed |
| `fixtures/fixture_200.md` | Valid entry — simulates HTTP 200 |
| `fixtures/fixture_404.md` | Valid entry — simulates HTTP 404 |
| `fixtures/fixture_429.md` | Valid entry — simulates HTTP 429 |
| `fixtures/fixture_head_unsupported.md` | Valid entry — simulates HEAD 405 → GET 200 |
| `fixtures/fixture_dns_fail.md` | Valid entry — simulates DNS failure |
| `fixtures/fixture_timeout.md` | Valid entry — simulates timeout |

---

## Self-Test Results

```
All self-tests passed.
```

24 assertions across 9 fixture groups — all offline using `unittest.mock`.

See `self_test_output.txt` for full output.

---

## Results

See `results.json` for the analysis report (written by running the checker without `--self-test`).
