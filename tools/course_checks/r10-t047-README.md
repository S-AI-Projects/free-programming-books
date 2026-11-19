# R10-T047 link failure classification check

Run `python3 tools/course_checks/r10-t047.py` to extract and inspect the selected Swedish programming book entries from `books/free-programming-books-sv.md`.

The check targets these three entries:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| C-programmering | [Link](https://sv.wikibooks.org/wiki/C-programmering) | C | 13 |
| Programmera spel i C++ för nybörjare | [Link](https://sv.wikibooks.org/wiki/Programmera_spel_i_C%2B%2B_f%C3%B6r_nyb%C3%B6rjare) | C++ | 18 |
| Pro Git | [Link](https://git-scm.com/book/sv/v2) | Git | 23 |

Run `python3 tools/course_checks/r10-t047.py --self-test` to test failure classification fixtures:
- `200_ok`: HEAD 200 -> `success_head`
- `404_not_found`: HEAD 404 -> `missing_resource`
- `429_rate_limited`: HEAD 429 -> `rate_limited`
- `head_405_get_200`: HEAD 405 with GET fallback 200 -> `success_get_fallback`
- `timeout`: Request timeout -> `timeout`
- `dns_failure`: Name resolution failure -> `dns_failure`

Automated request failures never remove links without manual confirmation. Run evidence is written to `work/R10-T047/`.
