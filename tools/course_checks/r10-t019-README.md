# R10-T019 access requirements check

Run `python3 tools/course_checks/r10-t019.py` to inspect the selected Persian
programming books from `books/free-programming-books-fa_IR.md` as JSON. Each
record includes its original source line, title, URL, section, and access classification.

The checker is limited to these three book URLs:

| Title | URL | Section | Source line |
| --- | --- | --- | ---: |
| رایانش ابری | [Link](http://docs.occc.ir/books/Main%20Book-20110110_2.pdf) | رایانش ابری | 25 |
| علم شبکه | [Link](http://networksciencebook.com) | شبکه | 30 |
| الگوهای طراحی | [Link](https://holosen.net/what-is-design-pattern/) | مهندسی نرم‌افزار | 35 |

Run `python3 tools/course_checks/r10-t019.py --self-test` for offline fixture tests:
- `access_scenarios.json`: tests public access confirmation, registration requirement verification, unverified labeling for automated failures, and security challenge handling.
- Verifies that no credentials are stored and that access claims cite official resource URLs.

Generated run evidence is written to `work/R10-T019/`.
