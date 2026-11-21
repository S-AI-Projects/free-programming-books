# R10-T031 — Checker README

## Task
**R10-T031** · Parse entries from `courses/free-courses-th.md`
**Student:** Isha Patidar
**Branch:** `student/e26b07f0564/R10-T031`

## Selected Entries

| Line | Title | URL | Section | Author |
|------|-------|-----|---------|--------|
| 23 | การออกแบบและวิเคราะห์อัลกอริทึม | https://youtube.com/playlist?list=PL0ROnaCzUGB65_YkASLAEmcW_mtxFtq4m | Algorithms & Data Structures | สมชาย ประสิทธิ์จูตระกูล |
| 28 | Natural Language Processing 2023 | https://www.youtube.com/playlist?list=PLyyEwPZh6aHpCAaG6dot5xXrlEK73oF4J | Artificial Intelligence | อรรถพล ธำรงรัตนฤทธิ์ |
| 29 | NLP 2021 | https://youtube.com/playlist?list=PLcBOyD1N1T-PIYnPZ9_iHtug9e-BcHIob | Artificial Intelligence | EkapolC |

## Checker: `tools/course_checks/r10-t031.py`

### What it does
- Parses `courses/free-courses-th.md` and extracts: display name, URL, author, format, section heading, and **source line number**
- Skips entries inside fenced code blocks (` ``` `)
- Preserves URL fragments (`#...`)
- Filters the three selected entries
- Writes `work/R10-T031/results.json` with the parsed data

### Running the checker
```bash
# Parse and print selected entries
python3 tools/course_checks/r10-t031.py

# Run assertions (exits non-zero on failure)
python3 tools/course_checks/r10-t031.py --self-test
```

### Self-test assertions
1. **Fenced-code fake link is ignored** — a URL inside a ` ``` ` block is not parsed as a real entry.
2. **URL with fragment is preserved** — `#chapter-1` in a URL is kept verbatim.
3. **Selected entries map to correct line numbers** — each entry resolves to the expected line in the source file.
4. **Malformed lines yield no entries** — partial / broken list syntax is silently skipped.

## Fixtures

| File | Purpose |
|------|---------|
| `fixtures/success_cases.md` | Valid markdown entries (should parse correctly) |
| `fixtures/failure_cases.md` | Fenced-code and malformed lines (should be ignored) |
| `fixtures/expected_selected.json` | Expected output for the three selected entries |

## Catalogue Corrections
No corrections were required. All three selected entries are correctly formatted and accessible:
- URLs are valid YouTube playlist links
- Entries are in proper `* [Title](URL) - Author` format
- Entries are in alphabetical order within their sections
- All links are `https`-compatible (YouTube supports https)

## Evidence
- `results.json` — actual parser output for the selected entries
- `self_test_output.txt` — stdout from `python3 tools/course_checks/r10-t031.py --self-test`
