# R10-T045 entry metadata verification check

Run `python3 tools/course_checks/r10-t045.py` to extract and inspect the selected Malayalam programming book entries from `books/free-programming-books-ml.md`.

The check targets these three entries:

| Display name | URL | Category | Source line | Author | Format |
| --- | --- | --- | ---: | --- | --- |
| XI_Computer_Science_Part_I | [Link](https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XI/CompSciencepart1/XI_Computer_Science_Part_1.pdf) | Computer Science | 8 | SCERT | PDF |
| XI_Computer_Science_Part_II | [Link](https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XI/CompSciencepart1/XI_Computer_Science_Part_II.pdf) | Computer Science | 9 | SCERT | PDF |
| XII_Computer_Science_Part_I | [Link](https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XII/MAL_MED/Computer%20Science%20Part%201%20.pdf) | Computer Science | 10 | SCERT | PDF |

Run `python3 tools/course_checks/r10-t045.py --self-test` to test offline metadata verification:
- `valid.md`: Verifies all required fields (`display_name`, `url`, `category`, `line_number`, `author`, `format`) are present.
- `missing-field.md`: Asserts that missing required metadata triggers an explicit failure.
- `fenced-code.md`: Verifies fenced code blocks are excluded.

Run evidence is written to `work/R10-T045/`.
