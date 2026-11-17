# R10-T021 validation evidence

Running `python3 tools/course_checks/r10-t021.py` or the same command with
`--self-test` regenerates the evidence files in this directory.

- `inputs.json`: selected source file, categories, display names, URLs, and
  expected source lines.
- `expected_vs_actual.json`: expected and observed parsed fields, validation
  mismatches, self-test status, and optional live-request results.
- `tool_versions.txt`: Python, platform, Git commit, and branch at execution.
- `report.md`: human-readable extraction and validation summary.
- `self-test-output.txt`: offline test runner output.
- `fixtures/`: success, fenced-code fake-link, and missing-entry inputs.

The source entries already matched the supplied names and URLs, so no catalogue
correction was made.
