# Verification Evidence: R10-T048

## Overview
- **Task ID**: R10-T048
- **Target File**: `courses/free-courses-kk.md`
- **Checker Script**: `tools/course_checks/r10-t048.py`
- **Verification Runner**: `work/R10-T048/check.py`
- **Timestamp**: Thu Nov 19 13:21:37 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `courses/free-courses-kk.md`
- **SHA-256**: `7859747a1b696eb4137de7b05da4275f65716f5f33cdc83dcdf898efbf935723`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_bad_heading_hierarchy_rejected (__main__.CourseCheckTests.test_bad_heading_hierarchy_rejected) ... ok
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_malformed_fixture_rejected_with_line_number (__main__.CourseCheckTests.test_malformed_fixture_rejected_with_line_number) ... ok
test_source_entries_match_expected_fields (__main__.CourseCheckTests.test_source_entries_match_expected_fields) ... ok
test_unsorted_sections_rejected (__main__.CourseCheckTests.test_unsorted_sections_rejected) ... ok
test_valid_fixture (__main__.CourseCheckTests.test_valid_fixture) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.001s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "Android",
    "url": "https://bilgen.academy/course/view.php?id=512",
    "category": "Android",
    "line_number": 19,
    "metadata": "(BEGINNER)"
  },
  {
    "display_name": "HTML/CSS. \u0431\u0430\u0437\u0430\u043b\u044b\u049b \u0432\u0435\u0431-\u0434\u0438\u0437\u0430\u0439\u043d \u049b\u04b1\u0440\u0443\u0434\u0430\u0493\u044b \u043a\u043e\u0434\u0442\u0430\u0443.",
    "url": "https://bilgen.academy/course/view.php?id=510",
    "category": "HTML and CSS",
    "line_number": 24,
    "metadata": "(BEGINNER)"
  },
  {
    "display_name": "Javascript. Java \u043a\u0443\u0440\u0441\u044b\u043d\u044b\u04a3 \u043d\u0435\u0433\u0456\u0437\u0456",
    "url": "https://bilgen.academy/course/view.php?id=506",
    "category": "JavaScript",
    "line_number": 29,
    "metadata": "(BEGINNER)"
  }
]
```

## Test Summary
- Offline unit tests passed: 6/6
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
