# R10-T027 Persian podcast failure classifier

`r10-t027.py` checks the selected entries in
[`casts/free-podcasts-screencasts-fa_IR.md`](../../casts/free-podcasts-screencasts-fa_IR.md)
and preserves their source line numbers.

| Line | Category | Display name | URL | Creator | Format |
| ---: | --- | --- | --- | --- | --- |
| 11 | Programming News | پادکست کافه برنامه نویس | <https://anchor.fm/codemy> | CafeCodemy&rlm; | podcast |
| 12 | Programming News | راکت کست | <https://roocket.ir/podcast/> | — | podcast |
| 17 | Technology | پارس کلیک | <https://anchor.fm/parsclick/> | Amir Azimi&rlm; | podcast |

The offline fixtures distinguish success, forbidden (403), missing resource
(404), rate limited (429), HEAD-not-supported followed by GET success, timeout,
and DNS failure. A missing-resource response is only a removal recommendation
when a URL is explicitly marked as manually confirmed after browser review.

Run the offline tests:

```sh
python3 tools/course_checks/r10-t027.py --self-test
```

Optional live checks issue sequential HEAD requests to only these three URLs,
falling back to GET on 405/501. They use a five-second timeout by default and
never recommend removal unless `--manual-confirmed URL` is supplied after
manual review:

```sh
python3 tools/course_checks/r10-t027.py --live --timeout 5
```

The self-test records fixture inputs, expected/actual classifications, the
source-list report, and tool versions in `work/R10-T027/results.json`.
