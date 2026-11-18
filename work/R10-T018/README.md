# R10-T018 validation evidence

Running `python3 tools/course_checks/r10-t018.py` or the same command with
`--self-test` regenerates the evidence files in this directory.

- `inputs.json`: selected source file, categories, display names, URLs, and expected source lines.
- `expected_vs_actual.json`: expected and observed parsed fields, validation mismatches, syntax errors, and self-test status.
- `tool_versions.txt`: Python, platform, Git commit, and branch at execution.
- `report.md`: human-readable formatting and ordering validation summary.
- `self-test-output.txt`: offline test runner output.
- `fixtures/`: valid, malformed, bad-heading, and unsorted offline fixtures.
