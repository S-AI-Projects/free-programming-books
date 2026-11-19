# Verification Evidence: R10-T045

## Overview
- **Task ID**: R10-T045
- **Target File**: `books/free-programming-books-ml.md`
- **Checker Script**: `tools/course_checks/r10-t045.py`
- **Verification Runner**: `work/R10-T045/check.py`
- **Timestamp**: Thu Nov 19 09:49:48 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `books/free-programming-books-ml.md`
- **SHA-256**: `16a48e429caa53966b297102a762d3c996e4e0fe6a05585a13a3100ee9aeb3c6`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_fenced_code_ignored (__main__.CourseCheckTests.test_fenced_code_ignored) ... ok
test_missing_required_field_fails (__main__.CourseCheckTests.test_missing_required_field_fails) ... ok
test_selected_source_entries (__main__.CourseCheckTests.test_selected_source_entries) ... ok
test_valid_fixture (__main__.CourseCheckTests.test_valid_fixture) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.001s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "XI_Computer_Science_Part_I",
    "url": "https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XI/CompSciencepart1/XI_Computer_Science_Part_1.pdf",
    "category": "Computer Science",
    "line_number": 8,
    "author": "SCERT",
    "format": "PDF",
    "metadata": "- SCERT (PDF)"
  },
  {
    "display_name": "XI_Computer_Science_Part_II",
    "url": "https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XI/CompSciencepart1/XI_Computer_Science_Part_II.pdf",
    "category": "Computer Science",
    "line_number": 9,
    "author": "SCERT",
    "format": "PDF",
    "metadata": "- SCERT (PDF)"
  },
  {
    "display_name": "XII_Computer_Science_Part_I",
    "url": "https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XII/MAL_MED/Computer%20Science%20Part%201%20.pdf",
    "category": "Computer Science",
    "line_number": 10,
    "author": "SCERT",
    "format": "PDF",
    "metadata": "- SCERT (PDF)"
  }
]
```

## Test Summary
- Offline unit tests passed: 5/5
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
