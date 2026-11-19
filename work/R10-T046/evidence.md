# Verification Evidence: R10-T046

## Overview
- **Task ID**: R10-T046
- **Target File**: `casts/free-podcasts-screencasts-fi.md`
- **Checker Script**: `tools/course_checks/r10-t046.py`
- **Verification Runner**: `work/R10-T046/check.py`
- **Timestamp**: Thu Nov 19 09:53:23 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `casts/free-podcasts-screencasts-fi.md`
- **SHA-256**: `e19783f9f0b3fb8c82b28afe481559c27aaf8ae90b8b77fa51175fd0871cda2e`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_request_does_not_remove_entry (__main__.CourseCheckTests.test_failed_request_does_not_remove_entry) ... ok
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_fenced_rows_are_not_catalogue_entries (__main__.CourseCheckTests.test_fenced_rows_are_not_catalogue_entries) ... ok
test_malformed_rows_produce_explicit_failures (__main__.CourseCheckTests.test_malformed_rows_produce_explicit_failures) ... ok
test_missing_entry_raises_assertion (__main__.CourseCheckTests.test_missing_entry_raises_assertion) ... ok
test_source_entry_matches_expected_fields (__main__.CourseCheckTests.test_source_entry_matches_expected_fields) ... ok
test_unusual_url_characters_are_preserved_and_validated (__main__.CourseCheckTests.test_unusual_url_characters_are_preserved_and_validated) ... ok
test_valid_row_fixture (__main__.CourseCheckTests.test_valid_row_fixture) ... ok

----------------------------------------------------------------------
Ran 8 tests in 0.002s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "Kahvit n\u00e4ppikselle",
    "url": "https://www.aalto.fi/fi/podcastit/kahvit-nappikselle",
    "category": "Podcastit",
    "line_number": 3,
    "metadata": "- Aalto-yliopisto (podcast)"
  },
  {
    "display_name": "Koodarikuiskaajan podcast",
    "url": "https://koodarikuiskaaja.simplecast.com",
    "category": "Podcastit",
    "line_number": 4,
    "metadata": "- Elisa Heikura (podcast)"
  },
  {
    "display_name": "Koodia pinnan alla",
    "url": "https://koodiapinnanalla.fi",
    "category": "Podcastit",
    "line_number": 5,
    "metadata": "- Markus Hjort ja Yrj\u00f6 Kari-Koskinen (podcast)"
  }
]
```

## Test Summary
- Offline unit tests passed: 8/8
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
