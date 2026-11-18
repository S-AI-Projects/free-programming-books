# R10-T025 Marathi course metadata checker

Run `python3 tools/course_checks/r10-t025.py` to print the three selected course
records. The catalogue fields checked are display title, source URL, category,
source line, author/provider text, and YouTube provider identity.

| Display name | URL | Author | Category | Source line |
| --- | --- | --- | --- | ---: |
| अँड्रॉइड ऍप डेव्हलपमेंट मराठी \| Android App Development in Marathi | [Playlist](https://youtube.com/playlist?list=PLy1NOWTMDFjDLCgmxRNLDJtlutJOYl2d7) | उत्तर | Android | 19 |
| Angular in Marathi | [Playlist](https://youtube.com/playlist?list=PLpDAynbYcV3sruD9MNfmZtimPCKHicA2V) | Finishing School | Angular | 24 |
| Angular Tutorials in Marathi | [Playlist](https://youtube.com/playlist?list=PLMs908ICeVMEBw4CevNdPvvIJDaQV1ISN) | Developers Marathi | Angular | 25 |

Official YouTube/oEmbed observations were checked on 2026-11-18. The Android
playlist title and author were `अँड्रॉइड ऍप डेव्हलपमेंट मराठी | Android App Development in Marathi`
and `उत्तर`; Angular was `Angular in Marathi` / `Finishing School`; Angular
Tutorials was `Angular Tutorials in Marathi` / `Developers Marathi`. All three
provider values were YouTube.

Run `python3 tools/course_checks/r10-t025.py --self-test` for success,
missing-required-field, evidence-table, missing-entry, and failing-self-test
fixtures. A failed assertion exits non-zero.

Optional live verification is `python3 tools/course_checks/r10-t025.py --live`.
It uses YouTube oEmbed, a 5-second timeout, at most two workers, and only the
three fixed entries. Live or single-request failures never remove links.

Generated run evidence is written to `work/R10-T025/`. The checker uses only
the Python standard library.
