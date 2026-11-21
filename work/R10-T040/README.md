# R10-T040: Maintenance Workflow Checker for `courses/free-courses-ko.md`

## Task Description

**Task ID:** R10-T040 (10 of 10)  
**Related Issue:** [#42](https://github.com/S-AI-Projects/free-programming-books/issues/42)  
**Branch:** `student/e26b07f0564/R10-T040`  
**Author:** Isha Patidar  
**Target File:** `courses/free-courses-ko.md`

This task implements a maintenance workflow checker (`tools/course_checks/r10-t040.py`) that produces a one-command scoped report for the selected entries. The report includes before/after metadata, observed facts, manual decisions, and is reproducible from the same offline fixtures.

---

## Selected Entries

| Line | Title | URL | Author |
|------|-------|-----|--------|
| 45 | 실전 알고리즘 강좌 | [youtube playlist PLRx0vPvlEmdD...](https://www.youtube.com/playlist?list=PLRx0vPvlEmdDHxCvAQS1_6XV4deOwfVrz) | 동빈나 |
| 46 | 알고리즘 강좌 | [youtube playlist PLNvbgg5to7cf...](https://www.youtube.com/playlist?list=PLNvbgg5to7cfAx80VeQFW1Sq1mHGfiECo) | 권오흠 |
| 47 | 이상진의 자료구조 (2017) | [youtube playlist PL7mmuO705dG...](https://www.youtube.com/playlist?list=PL7mmuO705dG12pP82RPUR3wdD5dbYu9gZ) | 프리렉 |

All three entries are in the `### Algorithms & Data Structures` section.

---

## Report Structure

Each selected entry in the report contains four separate components:

| Component | Contents |
|-----------|---------|
| `before` | Source line number, title, URL, author, format, notes — the entry as it exists in the file |
| `observed_facts` | Objective, stable facts: host, playlist ID, ASCII/Unicode detection, URL hash |
| `http_status` / `http_detail` | HTTP probe result (or `skipped` in offline mode) |
| `recommendation` | Action + rationale + confidence — **kept separate from facts** |
| `after` | Entry as it would appear post-pass (unchanged if no corrections needed) |

> **Key design principle:** Observed facts and recommendations are always kept in separate fields. The same fixtures always produce the same `observed_facts` (stability guaranteed via URL hash).

---

## Checker Script

**File:** `tools/course_checks/r10-t040.py`

### Usage

```bash
# Offline self-test (no network required) — exits non-zero on any failure
python3 tools/course_checks/r10-t040.py --self-test

# Full report (offline mode — HTTP status marked as 'skipped')
python3 tools/course_checks/r10-t040.py

# Full report with live HTTP probes (timeout=10s, concurrency=2)
python3 tools/course_checks/r10-t040.py --live
```

### Implementation details

- **Facts extractor:** Derives stable facts from URL/metadata without network access:
  YouTube playlist detection, playlist ID extraction, Korean/Unicode title detection, URL hash
- **HTTP probe:** HEAD first → GET fallback on 405; timeout=10s; low concurrency
- **Recommendation engine:** Separates observed facts from recommendations:
  - `ok` / `head_unsupported_get_ok` → `no_change`
  - `rate_limited` → `no_change` (not a dead link; YouTube playlists commonly return 429 to bots)
  - `timeout` → `no_change` (retry later)
  - `not_found` → `verify_manually` (single automated failure is insufficient for removal)
  - `skipped` → `no_change` (no evidence)
- **Stability:** Same fixtures → same `observed_facts` (guaranteed by URL hash)

---

## Maintenance Pass Results

All three entries: **no changes recommended** (entries are correctly described).

| Line | Title | Action | Confidence |
|------|-------|--------|-----------|
| 45 | 실전 알고리즘 강좌 | no_change | high |
| 46 | 알고리즘 강좌 | no_change | high |
| 47 | 이상진의 자료구조 (2017) | no_change | high |

---

## Fixture Files

| File | Purpose |
|------|---------|
| `fixtures/fixture_malformed.md` | Malformed entry (no URL) → 0 entries parsed |
| `fixtures/fixture_line45.md` | Line 45 entry — 실전 알고리즘 강좌 |
| `fixtures/fixture_line46.md` | Line 46 entry — 알고리즘 강좌 |
| `fixtures/fixture_line47.md` | Line 47 entry — 이상진의 자료구조 (2017) |

---

## Self-Test Results

```
All self-tests passed.
```

**53 assertions** across 9 fixture groups — all offline using `unittest.mock`.

See `self_test_output.txt` for full output.

---

## Results

See `results.json` for the full maintenance report (133 total entries, 3 selected).
