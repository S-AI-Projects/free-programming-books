# R10-T026 Myanmar screencast parser and fixtures

`r10-t026.py` parses and validates the React section of
[`casts/free-podcasts-screencasts-my.md`](../../casts/free-podcasts-screencasts-my.md).
It reports the original source line and checks the selected entry's title, URL,
category, creator, and screencast note.

| Line | Category | Display name | URL | Creator | Format |
| ---: | --- | --- | --- | --- | --- |
| 8 | React | Learn React Docker And Containerized In Myanmar Language | <https://www.youtube.com/watch?v=Qqr8oabREA8> | MyanmarFullStackDevelopers | screencast |

No catalogue edit was needed. The checker uses only the Python standard
library and makes no live availability requests.

Run the success, malformed-row, and unusual-URL fixtures:

```sh
python3 tools/course_checks/r10-t026.py --self-test
```

The self-test writes fixture inputs, expected/actual results, the source-list
report, and tool versions to `work/R10-T026/results.json`.
