# Verification Evidence: R10-T047

## Overview
- **Task ID**: R10-T047
- **Target File**: `books/free-programming-books-sv.md`
- **Checker Script**: `tools/course_checks/r10-t047.py`
- **Verification Runner**: `work/R10-T047/check.py`
- **Timestamp**: Thu Nov 19 13:17:45 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `books/free-programming-books-sv.md`
- **SHA-256**: `c5db8970df66d19a69622fc7e47a71a795479ffec2426e235fc68cd9311bd16c`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_fixtures_produce_different_labels (__main__.CourseCheckTests.test_fixtures_produce_different_labels) ... ok
test_only_manually_confirmed_missing_is_recommended_for_removal (__main__.CourseCheckTests.test_only_manually_confirmed_missing_is_recommended_for_removal) ... ok
test_source_entries_match_expected_fields (__main__.CourseCheckTests.test_source_entries_match_expected_fields) ... ok

----------------------------------------------------------------------
Ran 4 tests in 0.002s

OK
```

## Extracted Entries
```json
[
  {
    "display_name": "C-programmering",
    "url": "https://sv.wikibooks.org/wiki/C-programmering",
    "category": "C",
    "line_number": 13,
    "expected": {
      "display_name": "C-programmering",
      "url": "https://sv.wikibooks.org/wiki/C-programmering",
      "category": "C",
      "line_number": 13
    }
  },
  {
    "display_name": "Programmera spel i C++ f\u00f6r nyb\u00f6rjare",
    "url": "https://sv.wikibooks.org/wiki/Programmera_spel_i_C%2B%2B_f%C3%B6r_nyb%C3%B6rjare",
    "category": "C++",
    "line_number": 18,
    "expected": {
      "display_name": "Programmera spel i C++ f\u00f6r nyb\u00f6rjare",
      "url": "https://sv.wikibooks.org/wiki/Programmera_spel_i_C%2B%2B_f%C3%B6r_nyb%C3%B6rjare",
      "category": "C++",
      "line_number": 18
    }
  },
  {
    "display_name": "Pro Git",
    "url": "https://git-scm.com/book/sv/v2",
    "category": "Git",
    "line_number": 23,
    "expected": {
      "display_name": "Pro Git",
      "url": "https://git-scm.com/book/sv/v2",
      "category": "Git",
      "line_number": 23
    }
  }
]
```

## Test Summary
- Offline unit tests passed: 4/4
- Selected records matched: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
