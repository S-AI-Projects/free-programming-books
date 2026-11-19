# R10-T043 duplicate detection check

Run `python3 tools/course_checks/r10-t043.py` to extract and inspect the selected competitive programming resources from `more/problem-sets-competitive-programming.md`.

The check targets these three entries:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| A Way to Practice Competitive Programming | [Link](https://github.com/E869120/Competitive-Programming/blob/master/%5BTutorial%5D%20A%20Way%20to%20Practice%20Competitive%20Programming.pdf) | Competitive Programming | 13 | - Masataka Yoneda (PDF) |
| A2 Online Judge | [Link](https://a2oj.netlify.app) | Competitive Programming | 14 | |
| Algorithms for Competitive Programming | [Link](https://cp-algorithms.com) | Competitive Programming | 15 | |

Run `python3 tools/course_checks/r10-t043.py --self-test` to test offline duplicate detection and URL normalization fixtures:
- `success.md`: Tests exact duplicate detection across sections (e.g. `A2 Online Judge` at line 14 in `Competitive Programming` and line 100 in `Ladders`).
- `normalization.md`: Tests conservative URL normalization rules (ignoring host case and default ports, preserving distinct query parameters, values, and fragments).
- `fenced-code.md`: Verifies that links inside fenced code blocks are ignored.

Run evidence is written to `work/R10-T043/`.
