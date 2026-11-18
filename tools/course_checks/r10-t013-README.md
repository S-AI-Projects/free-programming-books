# R10-T013 duplicate detection check

Run `python3 tools/course_checks/r10-t013.py` to inspect the selected Swedish
casts from `casts/free-podcasts-screencasts-sv.md` as JSON. Each record includes
its original source line, display name, URL, heading category, and metadata.

The checker is limited to these three podcast URLs:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| Agilpodden | [Link](https://www.agilpodden.se) | Language Agnostic | 8 | - Dick Lyhammar, Erik Hultgren (podcast) |
| AI-Podden | [Link](https://ai-podden.se) | Language Agnostic | 9 | - Ather Gattami, Bitynamics, Cloudberry (podcast) |
| Asdf | [Link](https://asdf.pizza) | Language Agnostic | 10 | - Therése Komstadius, Anton Gunnarsson (podcast) |

Run `python3 tools/course_checks/r10-t013.py --self-test` for offline fixture tests:
- `success.md`: exact duplicate detection.
- `normalization.md`: conservative normalization preserving query strings and fragments.
- `fenced-code.md`: ignoring fenced-code links.

Generated run evidence is written to `work/R10-T013/`.
