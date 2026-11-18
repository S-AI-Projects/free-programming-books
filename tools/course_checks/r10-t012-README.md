# R10-T012 redirect verification check

Run `python3 tools/course_checks/r10-t012.py` to inspect the selected Bulgarian
programming books from `books/free-programming-books-bg.md` as JSON. Each record
includes its original source line, display name, URL, and category.

The checker is limited to these three book URLs:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| Програмиране = ++Алгоритми; | [Link](https://programirane.org/download-now) | C | 15 |
| ANSI C - Курс за начинаещи | [Link](https://www.progstarter.com/index.php?option=com_content&view=article&id=8&Itemid=121&lang=bg) | C | 16 |
| ANSI C - Пълен справочник | [Link](https://progstarter.com/index.php?option=com_content&view=article&id=9&Itemid=122&lang=bg) | C | 17 |

Run `python3 tools/course_checks/r10-t012.py --self-test` for offline fixture tests:
- `200.json`: direct official resource classification.
- `301-to-200.json`: redirect chain resolved to final official URL.
- `redirect-loop.json`: loop detection via bounded redirect budget.
- `timeout.json`: non-fatal transient timeout classification.

Optional live requests can be run with `--live` (5-second timeout, max 2 workers).
Generated run evidence is written to `work/R10-T012/`.
