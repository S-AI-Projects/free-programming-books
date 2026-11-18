# R10-T014 category placement check

Run `python3 tools/course_checks/r10-t014.py` to inspect the selected Sinhala
casts from `casts/free-podcasts-screencasts-si.md` as JSON. Each record includes
its original source line, display name, URL, heading category, and metadata.

The checker is limited to these two podcast URLs:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| DevOps With Zack | [Link](https://anchor.fm/arshad-zackeriya) | DevOps | 9 | - Arshad Zackeriya |
| SLIIT FOSSCAST | [Link](https://anchor.fm/sliit-foss-community) | FOSS | 14 | - SLIIT FOSS Community |

Run `python3 tools/course_checks/r10-t014.py --self-test` for offline fixture tests:
- `valid.md`: preserves valid category placement.
- `misplaced.md`: identifies misplaced entries and attaches subject evidence.
- `repeated-headings.md`: flags repeated headings in the document hierarchy.
- `fenced-code.md`: ignores fenced code blocks.

Generated run evidence is written to `work/R10-T014/`.
