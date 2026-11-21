# R10-T035 — Metadata Verification Checker README

## Task
**R10-T035** · Verify entry metadata in `casts/free-podcasts-screencasts-nl.md`
**Student:** Isha Patidar
**Branch:** `student/e26b07f0564/R10-T035`

## Selected Entries

| Line | Title | URL | Author | Format | Metadata Status |
|------|-------|-----|--------|--------|----------------|
| 3 | Code Klets | https://open.spotify.com/show/0Sf8c3aGZmtGiNUEwgDTSu?si=bc273e44deae4584 | Bernard, Jonny, Kishen, Pauline, Wouter & Saber | podcast | ✅ All fields present |
| 4 | TDS Team | https://open.spotify.com/show/63diy2DtpHzQfeNVxAPZgU | The TDS team | podcast | ✅ All fields present |

## Checker: `tools/course_checks/r10-t035.py`

### What it does
- Parses `casts/free-podcasts-screencasts-nl.md` and extracts entries with **source line numbers**
- Verifies all required metadata fields per CONTRIBUTING.md:
  1. **Title** — display name in `[...]`
  2. **URL** — link target in `(...)`
  3. **Author** — contributor(s) after ` - `
  4. **Format** — resource type in `(...)` e.g. `(podcast)`, `(screencast)`
- Produces a **precise evidence table** per entry: source URL, observed value, status, proposed value
- Has `--self-test` mode with 7 offline assertions; exits non-zero on failure

### Required metadata fields (CONTRIBUTING.md)

```
* [Title](URL) - Author (format)
```

### Running the checker
```bash
# Full metadata report
python3 tools/course_checks/r10-t035.py

# Offline assertions only (exits non-zero on failure)
python3 tools/course_checks/r10-t035.py --self-test
```

### Self-test assertions (all offline, 7 tests)
1. Fixture with **missing author** fails and appears in evidence table
2. Fixture with **missing format** fails
3. Fixture with **unknown format** (`livestream`) fails with `UNKNOWN_FORMAT`
4. **Fully valid fixture** passes all checks with empty evidence table
5. **Selected entries** parse to correct line numbers and sections
6. **Real selected entries** pass all metadata checks
7. **Evidence table rows** each contain `source_url`, `observed`, `proposed_value`

## Evidence Table

| Source URL | Field | Observed | Status | Proposed |
|------------|-------|----------|--------|---------|
| *(empty — all fields present)* | — | — | — | — |

## Catalogue Corrections
No corrections needed. Both selected entries have all required metadata fields correctly formatted:
- Title ✅
- URL ✅ (https)
- Author ✅
- Format ✅ (`podcast`)

## Fixtures

| File | Purpose |
|------|---------|
| `fixtures/fixture_missing_author.json` | Entry without author → must fail |
| `fixtures/fixture_missing_format.json` | Entry without format → must fail |
| `fixtures/fixture_unknown_format.json` | Entry with unknown format → must fail with UNKNOWN_FORMAT |
| `fixtures/fixture_valid.json` | Fully valid entry → must pass with empty evidence |
| `fixtures/expected_selected.json` | Expected parse & metadata output for 2 selected entries |

## Evidence
- `results.json` — actual checker output with evidence table
- `self_test_output.txt` — `All self-tests passed.`
