# R10-T039: Access Requirements Checker for `casts/free-podcasts-screencasts-de.md`

## Task Description

**Task ID:** R10-T039  
**Related Issue:** [#41](https://github.com/S-AI-Projects/free-programming-books/issues/41)  
**Branch:** `student/e26b07f0564/R10-T039`  
**Author:** Isha Patidar  
**Target File:** `casts/free-podcasts-screencasts-de.md`

This task implements an access requirements checker (`tools/course_checks/r10-t039.py`) that verifies whether selected resources require authentication, registration, payment, or a particular environment.

---

## Selected Entry

| Line | Title | URL | Author | Format |
|------|-------|-----|--------|--------|
| 8 | Python Podcast | [python-podcast.de/show](https://python-podcast.de/show) | Jochen, Dominik | podcast |

---

## Access Classification Labels

| Label | Meaning |
|-------|---------|
| `free_no_registration` | Freely accessible, no account required |
| `free_with_registration` | Freely accessible, but requires registration/signup |
| `paywalled` | Requires payment for access |
| `environment_required` | Needs specific software/hardware/OS |
| `unverified` | Could not confirm access status — treat conservatively |
| `skipped` | Not checked (offline mode) |

> **Policy:** An unavailable resource is labelled **`unverified`**, NOT `free` or `broken`. No link is removed solely because a single automated request failed. No credentials are saved or transmitted. Rate-limited responses (429) → `unverified`, not removed.

---

## Access Assessment: Python Podcast

**URL:** `https://python-podcast.de/show`  
**Classification (offline):** `skipped` (use `--live` for HTTP check)  
**Evidence:** `python-podcast.de/show` is a publicly listed German Python podcast by Jochen and Dominik. Based on public catalogue information and the nature of podcast RSS feeds, no registration or payment is required. The catalogue entry already correctly reflects this. Classification: **likely `free_no_registration`** — verify in browser to confirm.

No catalogue correction is required: the entry is already correctly labelled as a podcast, freely accessible.

---

## Checker Script

**File:** `tools/course_checks/r10-t039.py`

### Usage

```bash
# Offline self-test (no network required) — exits non-zero on any failure
python3 tools/course_checks/r10-t039.py --self-test

# Full analysis (offline mode — marks selected entry as 'skipped')
python3 tools/course_checks/r10-t039.py

# Full analysis with live HTTP access probe
python3 tools/course_checks/r10-t039.py --live
```

### Implementation details

- **HEAD first, GET fallback:** Sends HEAD; if the server returns 405, retries with GET and scans a snippet of the response body for paywall/registration signals (in both English and German).
- **Timeout:** 10 seconds per request.
- **No credentials saved:** The checker never stores, logs, or transmits any login credentials.
- **Conservative labelling:** 404, 429, timeout, DNS failure → `unverified` (never `broken`).
- **Payment/registration signals:** Scans for keywords like `subscribe`, `sign up`, `anmelden`, `abonnieren` to detect walls.

---

## Fixture Files

| File | Purpose |
|------|---------|
| `fixtures/fixture_malformed.md` | Malformed entry (no URL) → 0 entries parsed |
| `fixtures/fixture_free.md` | Valid podcast entry — simulates HEAD 200 |
| `fixtures/fixture_paywalled.md` | Valid entry — simulates HTTP 401/403 |
| `fixtures/fixture_ratelimited.md` | Valid entry — simulates HTTP 429 → unverified |
| `fixtures/fixture_missing.md` | Valid entry — simulates HTTP 404 → unverified |
| `fixtures/fixture_timeout.md` | Valid entry — simulates timeout → unverified |

---

## Self-Test Results

```
All self-tests passed.
```

22 assertions across 11 fixture groups — all offline using `unittest.mock`.

See `self_test_output.txt` for full output.

---

## Results

See `results.json` for the full analysis report.
