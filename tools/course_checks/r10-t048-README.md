# R10-T048 list formatting and ordering check

Run `python3 tools/course_checks/r10-t048.py` to extract and inspect the selected Kazakh free course entries from `courses/free-courses-kk.md`.

The check targets these three entries:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| Android | [Link](https://bilgen.academy/course/view.php?id=512) | Android | 19 | (BEGINNER) |
| HTML/CSS. базалық веб-дизайн құрудағы кодтау. | [Link](https://bilgen.academy/course/view.php?id=510) | HTML and CSS | 24 | (BEGINNER) |
| Javascript. Java курсының негізі | [Link](https://bilgen.academy/course/view.php?id=506) | JavaScript | 29 | (BEGINNER) |

Run `python3 tools/course_checks/r10-t048.py --self-test` to test formatting and hierarchy fixtures:
- `valid.md`: Verifies proper bullet link syntax and valid heading levels.
- `malformed.md`: Rejects malformed bullet syntax with exact line number identification.
- `bad-heading.md`: Detects invalid heading levels and level skipping.
- `unsorted.md`: Flags sections that violate documented alphabetical ordering.

Run evidence is written to `work/R10-T048/`.
