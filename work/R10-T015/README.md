# R10-T015 validation evidence

Running `python3 tools/course_checks/r10-t015.py` or the same command with
`--self-test` regenerates the evidence files in this directory.

- `inputs.json`: selected source file, categories, display names, URLs, and expected source lines.
- `expected_vs_actual.json`: expected and observed parsed fields, validation mismatches, and self-test status.
- `tool_versions.txt`: Python, platform, Git commit, and branch at execution.
- `report.md`: human-readable metadata verification summary and evidence table.
- `self-test-output.txt`: offline test runner output.
- `fixtures/`: valid, missing-field, and fenced-code offline fixtures.
