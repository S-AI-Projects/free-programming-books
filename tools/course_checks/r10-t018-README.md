# R10-T018 formatting and ordering check

Run `python3 tools/course_checks/r10-t018.py` to inspect the selected Hebrew
programming books from `books/free-programming-books-he.md` as JSON. Each record
includes its original source line, display name, URL, and category hierarchy.

The checker is limited to these three book URLs:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| מערכות הפעלה | [Link](https://data.cyber.org.il/os/os_book.pdf) | ללא תלות בשפה > מערכות הפעלה | 18 |
| רשתות מחשבים | [Link](https://data.cyber.org.il/networks/networks.pdf) | ללא תלות בשפה > רשתות | 23 |
| ארגון המחשב ושפת סף | [Link](https://data.cyber.org.il/assembly/assembly_book.pdf) | Assembly | 28 |

Run `python3 tools/course_checks/r10-t018.py --self-test` for offline fixture tests:
- `valid.md`: verifies correct Hebrew Markdown structure, RTL tags, and link formatting.
- `malformed.md`: ensures malformed bullet syntax is rejected with explicit line numbers.
- `bad-heading.md`: rejects invalid heading hierarchy.
- `unsorted.md`: catches sections placed out of documented order.

Generated run evidence is written to `work/R10-T018/`.
