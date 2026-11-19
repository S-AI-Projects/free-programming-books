# Verification Evidence: R10-T042

## Overview
- **Task ID**: R10-T042
- **Target File**: `courses/free-courses-fi.md`
- **Checker Script**: `tools/course_checks/r10-t042.py`
- **Verification Runner**: `work/R10-T042/check.py`
- **Timestamp**: Thu Nov 19 09:39:10 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `courses/free-courses-fi.md`
- **SHA-256**: `35110e90ab8a480c489f4ca1744707ac39c37a0c6f3cb31ce294510958f2d5d1`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_live_request_does_not_remove_entry (__main__.CourseCheckTests.test_failed_live_request_does_not_remove_entry) ... ok
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_offline_200 (__main__.CourseCheckTests.test_offline_200) ... ok
test_offline_301_then_200 (__main__.CourseCheckTests.test_offline_301_then_200) ... ok
test_offline_redirect_loop (__main__.CourseCheckTests.test_offline_redirect_loop) ... ok
test_offline_timeout (__main__.CourseCheckTests.test_offline_timeout) ... ok
test_selected_entries_and_source_lines (__main__.CourseCheckTests.test_selected_entries_and_source_lines) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.002s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "Jyv\u00e4skyl\u00e4n yliopiston C#-kieli ohjelmointikurssi",
    "url": "https://tim.jyu.fi/view/kurssit/tie/ohj1/moniste/Ohjelmointi-1",
    "category": "C#",
    "line_number": 11
  },
  {
    "display_name": "Elements of AI",
    "url": "https://www.elementsofai.com/fi/",
    "category": "Other",
    "line_number": 16
  },
  {
    "display_name": "Koodiaapinen",
    "url": "https://koodiaapinen.fi",
    "category": "Other",
    "line_number": 17
  }
]
```

## Test Summary
- Offline unit tests passed: 7/7
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
