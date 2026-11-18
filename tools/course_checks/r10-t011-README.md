# R10-T011 course-list check

Run `python3 tools/course_checks/r10-t011.py` to print the selected records from
`casts/free-podcasts-screencasts-cs.md` as JSON. Each record includes its
original source line, display name, URL, heading category, and raw trailing
metadata.

The checker is limited to these three podcast URLs:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| Brus kódu | [Link](http://bruskodu.cz) | Podcasty | 3 | - pro frontend vývojáře |
| CZpodcast | [Link](https://soundcloud.com/czpodcast-1) | Podcasty | 4 | |
| DevMinutes | [Link](http://devminutes.cz) | Podcasty | 5 | |

Run `python3 tools/course_checks/r10-t011.py --self-test` for offline success,
fenced-code, missing-entry, and mocked request-failure fixtures. The tests verify
heading hierarchy, fragment preservation, source line mapping, metadata
extraction, and nonzero failure behavior when assertions fail. Live requests are
optional (`--live`), limited to these three URLs, use a 5-second timeout and no
more than two workers, and never remove entries after a request failure.
Generated run evidence is written to `work/R10-T011/`.
