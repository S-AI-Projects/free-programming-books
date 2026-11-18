# R10-T027 failure-classification report

- Source: `casts/free-podcasts-screencasts-fa_IR.md`
- Source validation: passed
- Offline self-test: passed
- Live checks: run
- Catalogue corrections: none; automated failures alone do not justify removal.

## Selected entries

- Line 11: پادکست کافه برنامه نویس `https://anchor.fm/codemy` (Programming News)
- Line 12: راکت کست `https://roocket.ir/podcast/` (Programming News)
- Line 17: پارس کلیک `https://anchor.fm/parsclick/` (Technology)

Offline fixtures cover success (200), missing resource (404), forbidden (403), rate-limited (429), HEAD-405/GET-200 fallback, timeout, and DNS failure. Only manually confirmed missing resources can receive a removal recommendation.

## Live classifications

- `https://anchor.fm/codemy`: request_error (HEAD)
- `https://roocket.ir/podcast/`: request_error (HEAD)
- `https://anchor.fm/parsclick/`: request_error (HEAD)
