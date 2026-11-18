# R10-T014 validation evidence

Running `python3 tools/course_checks/r10-t014.py` or the same command with
`--self-test` regenerates the evidence files in this directory.

- `inputs.json`: selected source file, categories, display names, URLs, and expected source lines.
- `expected_vs_actual.json`: expected and observed parsed fields, validation mismatches, self-test status, repeated headings, and subject evidence.
- `tool_versions.txt`: Python, platform, Git commit, and branch at execution.
- `report.md`: human-readable category placement summary.
- `self-test-output.txt`: offline test runner output.
- `fixtures/`: valid, misplaced, repeated-headings, and fenced-code offline fixtures.
