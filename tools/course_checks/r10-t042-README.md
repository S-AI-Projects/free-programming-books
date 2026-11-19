# R10-T042 redirect verification check

Run `python3 tools/course_checks/r10-t042.py` to extract and inspect the selected Finnish free course links from `courses/free-courses-fi.md`.

The check targets these three entries:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| Jyväskylän yliopiston C#-kieli ohjelmointikurssi | [Link](https://tim.jyu.fi/view/kurssit/tie/ohj1/moniste/Ohjelmointi-1) | C# | 11 |
| Elements of AI | [Link](https://www.elementsofai.com/fi/) | Other | 16 |
| Koodiaapinen | [Link](https://koodiaapinen.fi) | Other | 17 |

Run `python3 tools/course_checks/r10-t042.py --self-test` to test offline redirect and failure classification fixtures:
- `200.json`: 200 OK without redirect -> `official_200`
- `301-to-200.json`: 301 followed by 200 -> `moved` (and unresolved intermediate -> `redirect_unresolved`)
- `redirect-loop.json`: redirect loop / limit exceeded -> `redirect_loop`
- `timeout.json`: timed-out request -> `timeout`

The script also supports optional `--live` checking using low concurrency and a 5-second timeout. Request failures never remove catalogue entries. Run evidence is written to `work/R10-T042/`.
