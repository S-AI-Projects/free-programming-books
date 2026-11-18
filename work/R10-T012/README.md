# R10-T012 validation evidence

Running `python3 tools/course_checks/r10-t012.py` or the same command with
`--self-test` regenerates the evidence files in this directory.

- `inputs.json`: selected source file, categories, display names, URLs, and expected source lines.
- `expected_vs_actual.json`: expected and observed parsed fields, validation mismatches, self-test status, and redirect classifications.
- `tool_versions.txt`: Python, platform, Git commit, and branch at execution.
- `report.md`: human-readable redirect verification summary.
- `self-test-output.txt`: offline test runner output.
- `fixtures/`: 200, 301->200, redirect-loop, and timeout offline scenarios.
