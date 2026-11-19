# Verification Evidence: R10-T050

## Overview
- **Task ID**: R10-T050
- **Target File**: `books/free-programming-books-no.md`
- **Checker Script**: `tools/course_checks/r10-t050.py`
- **Verification Runner**: `work/R10-T050/check.py`
- **Timestamp**: Thu Nov 19 13:30:07 UTC 2026
- **Git Commit**: `b4c4cc4040b614d2aca81ad5f2bcd92ed3d422ec`

## Environment & Tool Versions
- **Python**: `3.15.2 (v3.15.2:5e58eaad7c5, Oct 25 2026, 14:19:34) [Clang 21.0.0 (clang-2100.1.1.101)]`
- **Platform**: `macOS-27.2.1-arm64-arm-64bit-Mach-O`
- **Git**: `git version 2.54.0 (Apple Git-157)`

## Target File Invariance
- **File**: `books/free-programming-books-no.md`
- **SHA-256**: `f755dad2aeba1b9363e77b32d9524d70a3d6d68b03b252e7f3c18444d315ae05`
- **Status**: Unchanged and verified identical before and after check execution.

## Self-Test Output
```
test_failed_self_test_returns_nonzero (__main__.CourseCheckTests.test_failed_self_test_returns_nonzero) ... ok
test_maintenance_scenarios_separate_facts_and_recommendations (__main__.CourseCheckTests.test_maintenance_scenarios_separate_facts_and_recommendations) ... ok
test_no_credentials_stored (__main__.CourseCheckTests.test_no_credentials_stored) ... ok
test_no_link_removed_on_single_automated_failure (__main__.CourseCheckTests.test_no_link_removed_on_single_automated_failure) ... ok
test_selected_entries_match_source_lines (__main__.CourseCheckTests.test_selected_entries_match_source_lines) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.002s

OK
```

## Extracted Maintenance Report
```json
[
  {
    "url": "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-for-nybegynnere.pdf",
    "line_number": 8,
    "title": "LaTeX for nybegynnere",
    "category": "Latex",
    "author": "Dag Langmyhr",
    "format": "PDF",
    "observed_facts": {
      "http_status": 200,
      "content_type": "application/pdf",
      "content_length_bytes": 9432358,
      "observed_title": "LaTeX for nybegynnere",
      "observed_author": "Dag Langmyhr",
      "observed_format": "PDF",
      "manual_verification": true,
      "notes": "Verified official lecture notes by Dag Langmyhr at UiO IFI; publicly accessible PDF."
    },
    "recommendation": {
      "action": "retain",
      "removal_recommended": false,
      "metadata_change_recommended": false,
      "decision_rationale": "Resource is available, format is valid PDF, metadata accurately reflects document attributes."
    }
  },
  {
    "url": "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-videre.pdf",
    "line_number": 9,
    "title": "LaTeX for viderekomne",
    "category": "Latex",
    "author": "Dag Langmyhr",
    "format": "PDF",
    "observed_facts": {
      "http_status": 200,
      "content_type": "application/pdf",
      "content_length_bytes": 487711,
      "observed_title": "LaTeX for viderekomne",
      "observed_author": "Dag Langmyhr",
      "observed_format": "PDF",
      "manual_verification": true,
      "notes": "Verified advanced LaTeX notes by Dag Langmyhr at UiO IFI; publicly accessible PDF."
    },
    "recommendation": {
      "action": "retain",
      "removal_recommended": false,
      "metadata_change_recommended": false,
      "decision_rationale": "Resource is available, format is valid PDF, metadata accurately reflects document attributes."
    }
  },
  {
    "url": "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/farger.pdf",
    "line_number": 10,
    "title": "Lokal guide til farger i LaTeX",
    "category": "Latex",
    "author": "Dag Langmyhr",
    "format": "PDF",
    "observed_facts": {
      "http_status": 200,
      "content_type": "application/pdf",
      "content_length_bytes": 131814,
      "observed_title": "Lokal guide til farger i LaTeX",
      "observed_author": "Dag Langmyhr",
      "observed_format": "PDF",
      "manual_verification": true,
      "notes": "Verified color guide by Dag Langmyhr at UiO IFI; publicly accessible PDF."
    },
    "recommendation": {
      "action": "retain",
      "removal_recommended": false,
      "metadata_change_recommended": false,
      "decision_rationale": "Resource is available, format is valid PDF, metadata accurately reflects document attributes."
    }
  }
]
```

## Test Summary
- Offline unit tests passed: 5/5
- Selected records matched: 3/3
- Facts vs recommendations separation verified: PASS
- Verified active PDF documents at University of Oslo: 3/3
- SHA-256 hash invariance: PASS
- Isolated sandbox check: PASS
- Exit Code: 0
