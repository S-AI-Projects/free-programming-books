# Verification Evidence: R10-T049

## Overview
- **Task ID**: R10-T049
- **Target File**: `courses/free-courses-kn.md`
- **Checker Script**: `tools/course_checks/r10-t049.py`
- **Verification Runner**: `work/R10-T049/check.py`
- **Timestamp**: Thu Nov 19 13:26:30 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `courses/free-courses-kn.md`
- **SHA-256**: `a71e0e7886e8d478c10ea122366f36d9d29cb594184cf9553460529e04766ad7`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_access_fixture_scenarios_are_classified_with_source_citations (__main__.CourseCheckTests.test_access_fixture_scenarios_are_classified_with_source_citations) ... ok
test_automated_failure_without_manual_page_evidence_is_unverified (__main__.CourseCheckTests.test_automated_failure_without_manual_page_evidence_is_unverified) ... ok
test_failed_self_test_result_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_result_returns_nonzero) ... ok
test_no_credentials_are_stored (__main__.CourseCheckTests.test_no_credentials_are_stored) ... ok
test_selected_entries_and_line_numbers_match_source (__main__.CourseCheckTests.test_selected_entries_and_line_numbers_match_source) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.001s

OK
```

## Extracted Entries & Access Classifications
```json
[
  {
    "url": "https://youtube.com/playlist?list=PLUZkVL-W-8GLVwteCNH_HNoIAhbfBHnLb",
    "status": "public_access_confirmed",
    "automated_status": null,
    "source_url": "https://youtube.com/playlist?list=PLUZkVL-W-8GLVwteCNH_HNoIAhbfBHnLb",
    "evidence": "Public YouTube playlist with 28 videos by script kiddie; free access without login or payment.",
    "requirements": [
      "environment: Web browser or YouTube client with video streaming capability"
    ],
    "authentication_required": false,
    "registration_required": false,
    "payment_required": false,
    "environment_requirements": [
      "Web browser or YouTube client with video streaming capability"
    ],
    "manual_verification": true,
    "removal_recommendation": false,
    "title": "C programming in Kannada",
    "category": "C",
    "line_number": 12,
    "metadata": "- script kiddie"
  },
  {
    "url": "https://youtube.com/playlist?list=PLjvPj4x59YBUYkNJr4kCKOXsP3NyM4-ik",
    "status": "public_access_confirmed",
    "automated_status": null,
    "source_url": "https://youtube.com/playlist?list=PLjvPj4x59YBUYkNJr4kCKOXsP3NyM4-ik",
    "evidence": "Public YouTube playlist by The Coding Class: Yuvaraj Madha; freely watchable without registration or payment.",
    "requirements": [
      "environment: Web browser or YouTube client with video streaming capability"
    ],
    "authentication_required": false,
    "registration_required": false,
    "payment_required": false,
    "environment_requirements": [
      "Web browser or YouTube client with video streaming capability"
    ],
    "manual_verification": true,
    "removal_recommendation": false,
    "title": "Complete C Language Course in KANNADA",
    "category": "C",
    "line_number": 13,
    "metadata": "- The Coding Class: Yuvaraj Madha"
  },
  {
    "url": "https://youtube.com/playlist?list=PLBGSzVCM24iHnpfOMnhuyiyEo_NGSxdPD",
    "status": "public_access_confirmed",
    "automated_status": null,
    "source_url": "https://youtube.com/playlist?list=PLBGSzVCM24iHnpfOMnhuyiyEo_NGSxdPD",
    "evidence": "Public YouTube playlist by DEBUG CODING; free access without credentials, accounts, or payment.",
    "requirements": [
      "environment: Web browser or YouTube client with video streaming capability"
    ],
    "authentication_required": false,
    "registration_required": false,
    "payment_required": false,
    "environment_requirements": [
      "Web browser or YouTube client with video streaming capability"
    ],
    "manual_verification": true,
    "removal_recommendation": false,
    "title": "CSS in Kannada (\u0c95\u0ca8\u0ccd\u0ca8\u0ca1\u0ca6\u0cb2\u0ccd\u0cb2\u0cbf) - Beginner to Advanced.",
    "category": "HTML and CSS",
    "line_number": 18,
    "metadata": "- DEBUG CODING"
  }
]
```

## Test Summary
- Offline unit tests passed: 5/5
- Selected records matched: 3/3
- Public access verified without login/payment: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
