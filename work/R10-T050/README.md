# Evidence Directory: Task R10-T050

This directory contains automated verification assets, offline test fixtures, and execution evidence for Task R10-T050.

## Target Details
- **Issue**: [#51](https://github.com/S-AI-Projects/free-programming-books/issues/51)
- **Task ID**: `R10-T050`
- **Target File**: `books/free-programming-books-no.md`
- **Checker Tool**: `tools/course_checks/r10-t050.py`

## Artifacts in this Directory
- `fixtures/maintenance_scenarios.json`: Offline scenario definitions for maintenance decision testing (healthy resource, metadata drift, transient network failure, confirmed offline document).
- `inputs.json`: Scoped target file, section, and selected entry definitions.
- `expected_vs_actual.json`: Comparison between catalog entries and parsed values, including maintenance evaluations.
- `self-test-output.txt`: Raw console output from running `python3 tools/course_checks/r10-t050.py --self-test`.
- `tool_versions.txt`: Environment information, commit hash, and Python runtime versions.
- `report.md`: Markdown table summarizing the scoped maintenance pass.
- `check.py`: Automated verification script asserting hash invariance, self-test success, extraction validity, and isolated sandbox execution.
- `evidence.md`: Generated verification summary produced by `check.py`.
