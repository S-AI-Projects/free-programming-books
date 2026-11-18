# R10-T027 failure-classification checker

Run `python3 tools/course_checks/r10-t027.py --self-test` for the offline
fixtures. The checker uses only Python's standard library and reads only the
assigned Persian podcast catalogue entries below. It preserves their source
line numbers in its output and in `work/R10-T027/inputs.json`.

| Entry | URL | Section | Current source line |
| --- | --- | --- | ---: |
| پادکست کافه برنامه نویس | <https://anchor.fm/codemy> | Programming News | 11 |
| راکت کست | <https://roocket.ir/podcast/> | Programming News | 12 |
| پارس کلیک | <https://anchor.fm/parsclick/> | Technology | 17 |

The classifier reports distinct outcomes for successful HEAD and GET fallback,
403 forbidden, 404 missing resource, 429 rate-limited, timeout, DNS failure,
and other HTTP/request errors. HEAD 405/501 triggers one GET fallback.

Live checks are optional: `python3 tools/course_checks/r10-t027.py --live`.
They check only the three listed URLs with a 5-second timeout and at most two
concurrent requests. A 404 is not a removal recommendation by itself. After
manually confirming a resource is missing in a browser, record that confirmation
with `--confirm-missing URL`; a recommendation is still produced only when the
check result is 404.

Inputs, expected-versus-actual results, test output, tool versions, and the
fixture response scenarios are stored under `work/R10-T027/`.
