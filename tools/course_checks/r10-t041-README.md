# R10-T041 course-list check

Run `python3 tools/course_checks/r10-t041.py` to print the selected records from
`courses/free-courses-en.md` as JSON. Each record includes its original source
line, display name, URL, heading category, and raw trailing metadata.

The checker is limited to these three course URLs:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| AI School | [Link](https://lillytechsystems.com/ai-school/) | 0 - MOOC | 127 | |
| AIMarket Courses | [Link](https://alexar76.github.io/aimarket-courses/) | 0 - MOOC | 128 | - Aleksandr Artamokhov (HTML) (MIT) |
| CheatGrid | [Link](https://www.cheatgrid.com/roadmaps) | 0 - MOOC | 129 | |

Run `python3 tools/course_checks/r10-t041.py --self-test` for offline success,
fenced-code, missing-entry, and mocked request-failure fixtures. The tests verify
heading hierarchy, fragment preservation, source line mapping, metadata
extraction, and nonzero failure behavior when assertions fail. Live requests are
optional (`--live`), limited to these three URLs, use a 5-second timeout and no
more than two workers, and never remove entries after a request failure.
Generated run evidence is written to `work/R10-T041/`.
