# R10-T020 validation evidence

Running `python3 tools/course_checks/r10-t020.py` or the same command with
`--self-test` regenerates the evidence files in this directory.

- `inputs.json`: selected source file, sections, titles, URLs, and expected source lines.
- `expected_vs_actual.json`: expected and observed parsed fields, maintenance report, and self-test status.
- `tool_versions.txt`: Python, platform, Git commit, and branch at execution.
- `report.md`: human-readable maintenance pass summary separating observed facts from recommendations.
- `self-test-output.txt`: offline test runner output.
- `fixtures/`: valid, missing-entry, and changed-metadata fixtures along with manual decisions.
