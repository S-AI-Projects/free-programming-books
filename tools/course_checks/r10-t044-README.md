# R10-T044 category consistency check

Run `python3 tools/course_checks/r10-t044.py` to extract and inspect the selected algorithm playground entries from `more/free-programming-playgrounds.md`.

The check targets these three entries:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| Data Structures Visualization | [Link](https://www.cs.usfca.edu/~galles/visualization/Algorithms.html) | Algorithms | 61 | - David Galles |
| The Algorithm Visualizer | [Link](https://algorithm-visualizer.org) | Algorithms | 62 | |
| visualising data structures and algorithms through animation | [Link](https://visualgo.net/en) | Algorithms | 63 | |

Run `python3 tools/course_checks/r10-t044.py --self-test` to test offline category placement and hierarchy validation:
- `valid.md`: Verifies valid category placement under `Algorithms`.
- `misplaced.md`: Verifies identification of misplaced entries citing subject evidence without keyword-only guessing.
- `repeated-headings.md`: Flags duplicated headings in the document structure.
- `fenced-code.md`: Verifies that fenced code blocks are ignored.

Run evidence is written to `work/R10-T044/`.
