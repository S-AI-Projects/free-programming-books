# Verification Evidence: R10-T043

## Overview
- **Task ID**: R10-T043
- **Target File**: `more/problem-sets-competitive-programming.md`
- **Checker Script**: `tools/course_checks/r10-t043.py`
- **Verification Runner**: `work/R10-T043/check.py`
- **Timestamp**: Thu Nov 19 09:43:52 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `more/problem-sets-competitive-programming.md`
- **SHA-256**: `e1fa8bae5683dc027a6a65c53fcac21b1a3ef908dd23214436db2e43f789b04b`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_exact_duplicates (__main__.CourseCheckTests.test_exact_duplicates) ... ok
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_fenced_fake_links_are_ignored (__main__.CourseCheckTests.test_fenced_fake_links_are_ignored) ... ok
test_missing_and_wrong_entry_assertions (__main__.CourseCheckTests.test_missing_and_wrong_entry_assertions) ... ok
test_normalization_keeps_meaningful_parts_distinct (__main__.CourseCheckTests.test_normalization_keeps_meaningful_parts_distinct) ... ok
test_parameter_order_is_normalized_but_values_are_not_merged (__main__.CourseCheckTests.test_parameter_order_is_normalized_but_values_are_not_merged) ... ok
test_selected_source_entries (__main__.CourseCheckTests.test_selected_source_entries) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.002s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "A Way to Practice Competitive Programming",
    "url": "https://github.com/E869120/Competitive-Programming/blob/master/%5BTutorial%5D%20A%20Way%20to%20Practice%20Competitive%20Programming.pdf",
    "category": "Competitive Programming",
    "line_number": 13,
    "metadata": "- Masataka Yoneda (PDF)"
  },
  {
    "display_name": "A2 Online Judge",
    "url": "https://a2oj.netlify.app",
    "category": "Competitive Programming",
    "line_number": 14,
    "metadata": ""
  },
  {
    "display_name": "Algorithms for Competitive Programming",
    "url": "https://cp-algorithms.com",
    "category": "Competitive Programming",
    "line_number": 15,
    "metadata": ""
  }
]
```

## Test Summary
- Offline unit tests passed: 7/7
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
