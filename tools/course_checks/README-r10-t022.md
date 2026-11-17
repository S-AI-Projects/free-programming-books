# R10-T022 redirect checker

`r10-t022.py` extracts selected links from the `Go` and `Học máy` sections of
[`books/free-programming-books-vi.md`](../../books/free-programming-books-vi.md).
Records include the display name, exact URL, category, available creator/format
metadata, and original source line. The checker also represents the linked
Vietnamese HTML format for *The Little Go Book* as a separate entry on the
same source line.

Selected source entries:

| Line | Category | Display name | URL |
| ---: | --- | --- | --- |
| 10 | Go | The Little Go Book | `https://github.com/nainglinaung/the-little-go-book` |
| 10 | Go | HTML | `https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md` |
| 15 | Học máy | Đắm chìm vào Học sâu | `https://d2l.aivivn.com` |

Run the offline redirect and source fixtures:

```sh
python3 tools/course_checks/r10-t022.py --self-test
```

The self-test performs no network requests and saves inputs, expected/actual
results, source-line mappings, and tool versions in `work/R10-T022/results.json`.
To make the three bounded live observations, run:

```sh
python3 tools/course_checks/r10-t022.py --live
```

Live checks are sequential, use an 8-second timeout and a maximum of five
redirects per entry, and save their final URLs and observation date in
`work/R10-T022/live_observations.json`. A timeout, TLS verification problem,
rate limit, access/login wall, or other single failed request is recorded for
review; the tool never removes or edits a catalogue link.

The bounded manual `curl` observations and URL recommendations for this run
are recorded in `work/R10-T022/manual_curl_verification.json`. The source list
was unchanged: each checked URL returned HTTP 200, and the shorter root URL
form for the Học sâu resource remains in the catalogue.
