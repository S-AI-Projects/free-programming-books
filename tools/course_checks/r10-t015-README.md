# R10-T015 metadata verification check

Run `python3 tools/course_checks/r10-t015.py` to inspect the selected Italian
courses from `courses/free-courses-it.md` as JSON. Each record includes its
original source line, display name, URL, heading category, author, and provider.

The checker is limited to these three course URLs:

| Display name | URL | Category | Source line | Author | Provider |
| --- | --- | --- | ---: | --- | --- |
| Corso Java - Android | [Playlist](https://www.youtube.com/playlist?list=PL0qAPtx8YtJeqmBWbE1Rbac2QWHoPCjR2) | Android | 43 | Fabrizio Camuso | YouTube |
| AlgoMOOC - Algoritmi quotidiani | [Playlist](https://www.youtube.com/playlist?list=PLjTV6y5YWc5HNnLyXkzUe9IlkG2n6guxU) | Algoritmi e Strutture Dati | 48 | Alessandro Bogliolo | YouTube |
| Algoritmi e Programmazione (C) | [Playlist](https://www.youtube.com/playlist?list=PLUFFnpJdi99nqESTPaxlPMOF7yEEb8_sS) | Algoritmi e Strutture Dati | 49 | P. Camurati, G. Cabodi, Politecnico di Torino | YouTube |

Run `python3 tools/course_checks/r10-t015.py --self-test` for offline fixture tests:
- `valid.md`: verifies all required metadata fields are present.
- `missing-field.md`: detects missing required fields and produces assertion failures.
- `fenced-code.md`: ensures links inside fenced code blocks are ignored.

Generated run evidence is written to `work/R10-T015/`.
