# R10-T017 failure classification check

Run `python3 tools/course_checks/r10-t017.py` to inspect the selected Angular
cheatsheet entries from `more/free-programming-cheatsheets.md` as JSON. Each
record includes its original source line, display name, URL, and category.

The checker is limited to these three cheatsheet URLs:

| Display name | URL | Category | Source line |
| --- | --- | --- | ---: |
| Angular Cheat Sheet | [Link](https://angular.io/guide/cheatsheet) | Angular | 79 |
| Angular Cheat Sheet | [Link](https://zerotomastery.io/cheatsheets/angular-cheat-sheet/) | Angular | 80 |
| Angular Cheat Sheet – A Basic Guide to Angular | [Link](https://www.geeksforgeeks.org/angular-cheat-sheet-a-basic-guide-to-angular/) | Angular | 81 |

Run `python3 tools/course_checks/r10-t017.py --self-test` for offline fixture tests:
- `http_responses.json`: tests distinct classification for 200 (success_head), 404 (missing_resource), 429 (rate_limited), HEAD-405/GET-200 (success_get_fallback), timeout, and dns_failure.
- Verifies that only a manually confirmed missing resource is recommended for removal.

Generated run evidence is written to `work/R10-T017/`.
