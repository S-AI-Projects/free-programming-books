# Evidence Directory: Task R10-T049

This directory contains automated verification assets, offline test fixtures, and execution evidence for Task R10-T049.

## Target Details
- **Issue**: [#50](https://github.com/S-AI-Projects/free-programming-books/issues/50)
- **Task ID**: `R10-T049`
- **Target File**: `courses/free-courses-kn.md`
- **Checker Tool**: `tools/course_checks/r10-t049.py`

## Artifacts in this Directory
- `fixtures/access_scenarios.json`: Offline scenario definitions for access classification validation (public playlist, registration required, login wall, automated 404).
- `inputs.json`: Scoped target file, section, and selected entry definitions.
- `expected_vs_actual.json`: Comparison between catalog entries and parsed values, including access classifications.
- `self-test-output.txt`: Raw console output from running `python3 tools/course_checks/r10-t049.py --self-test`.
- `tool_versions.txt`: Environment information, commit hash, and Python runtime versions.
- `report.md`: Markdown table summarizing access findings for each assigned course.
- `check.py`: Automated verification script asserting hash invariance, self-test success, extraction validity, and isolated sandbox execution.
- `evidence.md`: Generated verification summary produced by `check.py`.
