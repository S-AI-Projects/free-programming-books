# R10-T016 offline fixture validation check

Run `python3 tools/course_checks/r10-t016.py` to inspect the selected Ukrainian
programming books from `books/free-programming-books-uk.md` as JSON. Each record
includes its original source line, display name, URL, heading category, and metadata.

The checker is limited to these three book URLs:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| С/C++ Теорія та практика | [Link](https://shron1.chtyvo.org.ua/Voitenko_Volodymyr/C_Cpp_Teoriia_ta_praktyka.pdf) | C and C++ | 17 | - Володимир Войтенко (PDF) |
| Розплутаний ClojureScript | [Link](https://lambdabooks.github.io/clojurescript-unraveled) | ClojureScript | 22 | - Роман Лютіков (LambdaBooks) |
| Вивчить собі Хаскела на велике щастя! | [Link](http://haskell.trygub.com) | Haskell | 27 | - Міран Ліповача |

Run `python3 tools/course_checks/r10-t016.py --self-test` for offline fixture tests:
- `valid.md`: verifies valid row extraction and row validation.
- `malformed.md`: verifies deterministic outcomes for missing fields, invalid schemes, and invalid characters.
- `unusual-url.md`: verifies unusual URL characters, percent encodings, and fragments.
- `fenced.md`: verifies fenced code blocks are excluded.

Generated run evidence is written to `work/R10-T016/`.
