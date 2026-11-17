# R10-T025 Marathi course metadata checker

`r10-t025.py` verifies the title, playlist URL, creator/channel name, and
category stored for three entries in
[`courses/free-courses-mr.md`](../../courses/free-courses-mr.md). It retains
the original source line and writes an evidence table with the catalogue value,
the value observed on the official YouTube playlist page, and the proposed
value.

| Line | Category | Display name | Catalogue creator |
| ---: | --- | --- | --- |
| 19 | Android | अँड्रॉइड ऍप डेव्हलपमेंट मराठी \| Android App Development in Marathi | उत्तर |
| 24 | Angular | Angular in Marathi | Finishing School |
| 25 | Angular | Angular Tutorials in Marathi | Developers Marathi |

Observed official playlist titles and channel names matched the catalogue on
2026-11-17. YouTube redirected the short `youtube.com` host to
`www.youtube.com` while preserving each playlist ID; the shorter listed URLs
are therefore retained. No catalogue correction was needed.

Run the offline success and missing-creator fixtures:

```sh
python3 tools/course_checks/r10-t025.py --self-test
```

The self-test records inputs, expected/actual results, the official-source
evidence table, and tool versions in `work/R10-T025/results.json`. No network
requests are made by the self-test.
