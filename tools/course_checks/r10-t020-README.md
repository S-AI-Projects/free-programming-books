# R10-T020 maintenance pass check

Run `python3 tools/course_checks/r10-t020.py` to generate the scoped maintenance
report for the selected Myanmar programming books from `books/free-programming-books-my.md`
as deterministic JSON. Each record includes its original source line, title, URL,
and section.

The checker is limited to these three book URLs:

| Title | URL | Section | Source line |
| --- | --- | --- | ---: |
| Bitcoin - On Point | [Link](https://eimaung.com/bitcoin/) | Blockchain | 18 |
| The Little Go Book | [Link](https://github.com/nainglinaung/the-little-go-book) | Go | 23 |
| HTML | [Link](https://github.com/nainglinaung/the-little-go-book/blob/master/mm/go.md) | Go | 23 |

Run `python3 tools/course_checks/r10-t020.py --self-test` for offline fixture tests:
- `valid.md`: verifies deterministic report generation with stable JSON formatting.
- `missing-entry.md`: verifies handling of missing entries.
- `changed-metadata.md`: flags mismatches between observed and expected metadata.
- Separates observed facts from recommendations and manual decisions.

Generated run evidence is written to `work/R10-T020/`.
