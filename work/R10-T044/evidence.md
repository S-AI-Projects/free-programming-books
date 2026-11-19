# Verification Evidence: R10-T044

## Overview
- **Task ID**: R10-T044
- **Target File**: `more/free-programming-playgrounds.md`
- **Checker Script**: `tools/course_checks/r10-t044.py`
- **Verification Runner**: `work/R10-T044/check.py`
- **Timestamp**: Thu Nov 19 09:46:46 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `more/free-programming-playgrounds.md`
- **SHA-256**: `2940cfb369a06a786bc1612bdebbfb500ba82a86dacf2cf90b869b053c56c696`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_fenced_code_ignored (__main__.CourseCheckTests.test_fenced_code_ignored) ... ok
test_misplaced_fixture_is_identified_with_subject_evidence (__main__.CourseCheckTests.test_misplaced_fixture_is_identified_with_subject_evidence) ... ok
test_repeated_headings_are_flagged (__main__.CourseCheckTests.test_repeated_headings_are_flagged) ... ok
test_selected_source_entries (__main__.CourseCheckTests.test_selected_source_entries) ... ok
test_valid_fixture_preserves_valid_categories (__main__.CourseCheckTests.test_valid_fixture_preserves_valid_categories) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.003s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "Data Structures Visualization",
    "url": "https://www.cs.usfca.edu/~galles/visualization/Algorithms.html",
    "category": "Algorithms",
    "line_number": 61,
    "metadata": "- David Galles"
  },
  {
    "display_name": "The Algorithm Visualizer",
    "url": "https://algorithm-visualizer.org",
    "category": "Algorithms",
    "line_number": 62,
    "metadata": ""
  },
  {
    "display_name": "visualising data structures and algorithms through animation",
    "url": "https://visualgo.net/en",
    "category": "Algorithms",
    "line_number": 63,
    "metadata": ""
  }
]
```

## Test Summary
- Offline unit tests passed: 6/6
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
