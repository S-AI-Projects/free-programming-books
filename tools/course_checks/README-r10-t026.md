# R10-T026 offline Myanmar cast fixture check

Run `python3 tools/course_checks/r10-t026.py` to print the one selected Myanmar
React cast record with its source line and metadata.

| Display name | URL | Creator | Category | Source line |
| --- | --- | --- | --- | ---: |
| Learn React Docker And Containerized In Myanmar Language | [Screencast](https://www.youtube.com/watch?v=Qqr8oabREA8) | MyanmarFullStackDevelopers | React | 8 |

The default suite is entirely offline. It verifies:

- a valid catalogue row;
- malformed rows with missing names, invalid URL schemes, whitespace, and unsafe URL characters;
- unusual URL characters such as `&`, `?`, and `#`;
- fenced Markdown code that must not be parsed as catalogue rows;
- source-line and metadata equality;
- nonzero exit behavior for failing assertions;
- that a simulated request failure does not remove or alter the source entry.

Run `python3 tools/course_checks/r10-t026.py --self-test`.

Optional live availability is `python3 tools/course_checks/r10-t026.py --live`.
It uses HEAD, a fixed 5-second timeout, at most two workers, and only this one
entry. It never removes the entry after a request failure.

Generated run evidence is written to `work/R10-T026/`. The checker uses only
the Python standard library.
