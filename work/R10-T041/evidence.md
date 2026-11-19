# Verification Evidence: R10-T041

## Overview
- **Task ID**: R10-T041
- **Target File**: `courses/free-courses-en.md`
- **Checker Script**: `tools/course_checks/r10-t041.py`
- **Verification Runner**: `work/R10-T041/check.py`
- **Timestamp**: Thu Nov 19 09:35:47 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `courses/free-courses-en.md`
- **SHA-256**: `6482c20f03eee2ac47723bf8fe205459e37305de1bd038e89ce4a8bd53385cf7`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_live_request_does_not_remove_entry (__main__.CourseCheckTests.test_failed_live_request_does_not_remove_entry) ... ok
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_fenced_code_fixture_is_ignored (__main__.CourseCheckTests.test_fenced_code_fixture_is_ignored) ... ok
test_missing_entry_raises_assertion_and_wrong_line_is_detected (__main__.CourseCheckTests.test_missing_entry_raises_assertion_and_wrong_line_is_detected) ... ok
test_success_fixture_extracts_hierarchy_metadata_and_fragment (__main__.CourseCheckTests.test_success_fixture_extracts_hierarchy_metadata_and_fragment) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.006s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "AI School",
    "url": "https://lillytechsystems.com/ai-school/",
    "category": "0 - MOOC",
    "metadata": "",
    "line_number": 127
  },
  {
    "display_name": "AIMarket Courses",
    "url": "https://alexar76.github.io/aimarket-courses/",
    "category": "0 - MOOC",
    "metadata": "- Aleksandr Artamokhov (HTML) (MIT)",
    "line_number": 128
  },
  {
    "display_name": "CheatGrid",
    "url": "https://www.cheatgrid.com/roadmaps",
    "category": "0 - MOOC",
    "metadata": "",
    "line_number": 129
  }
]
```

## Test Summary
- Offline unit tests passed: 5/5
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
