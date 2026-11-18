# R10-T022 redirect verification check

Run `python3 tools/course_checks/r10-t022.py` to print the three assigned
Vietnamese resource records as JSON. The records retain their original source
line numbers and category.

The checker is limited to these entries:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| The Little Go Book | [Resource](https://github.com/nainglinaung/the-little-go-book) | Go | 10 |
| HTML | [HTML](https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md) | Go | 10 |
| Đắm chìm vào Học sâu | [Resource](https://d2l.aivivn.com) | Học máy | 15 |

Run `python3 tools/course_checks/r10-t022.py --self-test` for offline 200,
301-to-200, redirect-loop, timeout, missing-entry, and failing-self-test
fixtures. A failed assertion exits non-zero.

Live requests are optional (`--live`) and are informational only. They use
GET, a fixed 5-second timeout, at most two workers, and no removal is performed
when a request times out or otherwise fails. `--live` records the observed final
URL and UTC observation date where a redirect reaches a successful response.

Generated run evidence is written to `work/R10-T022/`. The checker uses only
the Python standard library.
