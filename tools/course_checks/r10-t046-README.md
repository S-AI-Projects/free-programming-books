# R10-T046 offline checks and fixture test suite

Run `python3 tools/course_checks/r10-t046.py` to extract and inspect the selected Finnish podcast entries from `casts/free-podcasts-screencasts-fi.md`.

The check targets these three entries:

| Display name | URL | Category | Source line | Metadata |
| --- | --- | --- | ---: | --- |
| Kahvit näppikselle | [Link](https://www.aalto.fi/fi/podcastit/kahvit-nappikselle) | Podcastit | 3 | - Aalto-yliopisto (podcast) |
| Koodarikuiskaajan podcast | [Link](https://koodarikuiskaaja.simplecast.com) | Podcastit | 4 | - Elisa Heikura (podcast) |
| Koodia pinnan alla | [Link](https://koodiapinnanalla.fi) | Podcastit | 5 | - Markus Hjort ja Yrjö Kari-Koskinen (podcast) |

Run `python3 tools/course_checks/r10-t046.py --self-test` to execute the offline test suite:
- `valid.md`: Verifies parsing of complete, valid rows.
- `malformed.md`: Verifies explicit failure classification for missing display names, missing URLs, invalid URL schemes, whitespace, and invalid characters.
- `unusual-url.md`: Verifies correct preservation and parsing of URLs with URL encoding and fragment anchors.
- `fenced.md`: Verifies that code blocks are ignored.

The test suite runs 100% offline. An optional `--live` flag allows non-destructive reachability probing. Run evidence is written to `work/R10-T046/`.
