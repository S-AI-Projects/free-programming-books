# R10-T030 Norwegian course maintenance report

Run `python3 tools/course_checks/r10-t030.py` for a deterministic, scoped
maintenance report, or add `--self-test` to run the offline fixtures. The report
separates parsed source facts from the manual decision and recommendation, and
shows before/after metadata for the selected row.

| Course | URL | Section | Creator | Source line |
| --- | --- | --- | --- | ---: |
| Java-programmering | <https://www.youtube.com/playlist?list=PLIrUJXSXz9cmvNZ_Y0QT-r25efmN42rm5> | Java | UDL.no | 8 |

No evidence-backed correction was identified, so the current metadata is
retained unchanged. This check is offline and does not infer that a link is
broken from an automated failure. Inputs, fixture comparisons, report, and tool
versions are recorded under `work/R10-T030/`.
