# R10-T028 Russian playground formatting check

Run `python3 tools/course_checks/r10-t028.py --self-test` to run the offline
fixtures. The checker reads only `more/free-programming-playgrounds-ru.md`,
retains source line numbers, validates the file's actual bullet-list syntax,
and does not rewrite catalogue text.

| Entry | URL | Section | Source line |
| --- | --- | --- | ---: |
| Python онлайн: запусти код в браузере | <https://koddo.ru/playground/python> | Python | 8 |

The checker verifies the level-three `Index` and `Python` headings, matching
index anchors, Markdown bullet links, and alphabetical order. Its fixtures
include a valid Cyrillic entry, a malformed bullet with a line diagnostic,
an out-of-order list, and an invalid heading level. This task checks formatting
only, so it makes no live requests and does not change the catalogue.

Inputs, expected-versus-actual results, test output, and tool versions are
recorded under `work/R10-T028/`.
