#!/usr/bin/env python3
"""
R10-T035 — Metadata Verification for free-podcasts-screencasts-nl.md
=====================================================================
Compares selected entries against the catalogue's required metadata fields
and produces a precise evidence table for each entry showing:
  - source URL
  - observed value (what is in the file)
  - required status (present / missing / malformed)
  - proposed value (if a correction is needed)

Required metadata fields per CONTRIBUTING.md:
  1. title        – display name in [...]
  2. url          – link target in (...)
  3. author       – contributor(s) after ' - '
  4. format       – resource type in (...) e.g. (podcast), (screencast)

Selected entries (as per task R10-T035):
  1. Code Klets
     https://open.spotify.com/show/0Sf8c3aGZmtGiNUEwgDTSu?si=bc273e44deae4584
  2. TDS Team
     https://open.spotify.com/show/63diy2DtpHzQfeNVxAPZgU

Usage:
  python3 tools/course_checks/r10-t035.py               # full metadata report
  python3 tools/course_checks/r10-t035.py --self-test   # offline assertions; exits non-zero on failure
"""

import re
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT   = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-nl.md"

SELECTED_URLS = {
    "https://open.spotify.com/show/0Sf8c3aGZmtGiNUEwgDTSu?si=bc273e44deae4584",
    "https://open.spotify.com/show/63diy2DtpHzQfeNVxAPZgU",
}

# Valid format tokens for casts
VALID_FORMATS = {"podcast", "screencast", "video", "audio"}

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Full entry pattern: * [Title](URL) - Author (format) optional-notes
ENTRY_RE = re.compile(
    r"^\*\s+"
    r"\[(?P<title>[^\]]+)\]"              # [Title]
    r"\((?P<url>[^)]+)\)"                 # (URL)
    r"(?:\s+-\s+(?P<author>[^(\n]+))?"    # optional ' - Author' (greedy up to '(')
    r"(?:\s*\((?P<fmt>[^)]+)\))?"         # optional (format)
    r"(?P<notes>.*)$"
)

FENCE_RE   = re.compile(r"^```")
HEADING_RE = re.compile(r"^#{2,6}\s+(.+)")


def parse_entries(filepath: Path, selected_urls=None):
    """Parse all markdown list entries, skipping fenced-code blocks."""
    if selected_urls is None:
        selected_urls = set()

    entries = []
    current_section = ""
    in_fence = False

    with open(filepath, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")

            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            m_h = HEADING_RE.match(line)
            if m_h:
                current_section = re.sub(r"<[^>]+>", "", m_h.group(1)).strip()
                continue

            m = ENTRY_RE.match(line)
            if not m:
                continue

            url = m.group("url").strip()
            entries.append({
                "line_no":  line_no,
                "title":    m.group("title").strip(),
                "url":      url,
                "author":   (m.group("author") or "").strip(),
                "fmt":      (m.group("fmt") or "").strip(),
                "notes":    (m.group("notes") or "").strip(),
                "section":  current_section,
                "selected": url in selected_urls,
            })

    return entries


# ---------------------------------------------------------------------------
# Metadata verification
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = ["title", "url", "author", "fmt"]

FIELD_LABELS = {
    "title":  "Title",
    "url":    "URL",
    "author": "Author",
    "fmt":    "Format",
}


def verify_metadata(entry: dict) -> dict:
    """
    Check all required metadata fields for one entry.
    Returns a dict with:
      overall_ok  – True if all fields pass
      fields       – per-field results list
      evidence     – evidence table rows (source_url, field, observed, status, proposed)
    """
    fields  = []
    all_ok  = True

    for field in REQUIRED_FIELDS:
        value  = entry.get(field, "")
        label  = FIELD_LABELS[field]
        status = "PRESENT"
        note   = ""
        proposed = None

        if not value:
            status = "MISSING"
            all_ok = False
            note   = f"Required field '{label}' is absent."
            proposed = f"<add {label.lower()}>"
        elif field == "fmt":
            # Format must be a known cast type
            fmt_lower = value.lower()
            known = any(vf in fmt_lower for vf in VALID_FORMATS)
            if not known:
                status   = "UNKNOWN_FORMAT"
                all_ok   = False
                note     = f"Format '{value}' is not a recognised cast type {sorted(VALID_FORMATS)}."
                proposed = "podcast or screencast"
        elif field == "url":
            # Basic URL sanity: must start with http
            if not value.startswith("http"):
                status = "MALFORMED"
                all_ok = False
                note   = "URL does not start with 'http'."

        fields.append({
            "field":    label,
            "observed": value,
            "status":   status,
            "note":     note,
            "proposed": proposed,
        })

    evidence = []
    for f in fields:
        if f["status"] != "PRESENT":
            evidence.append({
                "source_url":    entry["url"],
                "field":         f["field"],
                "observed":      f["observed"],
                "status":        f["status"],
                "proposed_value": f["proposed"],
                "note":          f["note"],
            })

    return {
        "line_no":    entry["line_no"],
        "title":      entry["title"],
        "url":        entry["url"],
        "section":    entry["section"],
        "overall_ok": all_ok,
        "fields":     fields,
        "evidence":   evidence,
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test():
    failures = []

    def assert_true(condition, msg):
        if not condition:
            failures.append(f"FAIL: {msg}")

    def assert_eq(got, expected, msg):
        if got != expected:
            failures.append(f"FAIL: {msg} — expected {expected!r}, got {got!r}")

    # ------------------------------------------------------------------
    # Test 1 – fixture with missing 'author' field fails
    # ------------------------------------------------------------------
    missing_author = {
        "line_no": 10, "title": "Test Podcast",
        "url": "https://example.com/podcast",
        "author": "",           # MISSING
        "fmt": "podcast",
        "notes": "", "section": "Podcasts", "selected": True,
    }
    result = verify_metadata(missing_author)
    assert_true(not result["overall_ok"],
                "Entry with missing author must fail metadata check")
    assert_true(
        any(f["status"] == "MISSING" and f["field"] == "Author"
            for f in result["fields"]),
        "Missing author field must appear as MISSING in fields list",
    )
    assert_true(len(result["evidence"]) >= 1,
                "Evidence table must have at least one row for missing author")

    # ------------------------------------------------------------------
    # Test 2 – fixture with missing 'fmt' field fails
    # ------------------------------------------------------------------
    missing_fmt = {
        "line_no": 11, "title": "Test Podcast",
        "url": "https://example.com/podcast",
        "author": "Some Author",
        "fmt": "",              # MISSING
        "notes": "", "section": "Podcasts", "selected": True,
    }
    result2 = verify_metadata(missing_fmt)
    assert_true(not result2["overall_ok"],
                "Entry with missing format must fail metadata check")

    # ------------------------------------------------------------------
    # Test 3 – fixture with unknown format fails
    # ------------------------------------------------------------------
    bad_fmt = {
        "line_no": 12, "title": "Test Show",
        "url": "https://example.com/show",
        "author": "Host", "fmt": "livestream",   # not a valid cast type
        "notes": "", "section": "Podcasts", "selected": True,
    }
    result3 = verify_metadata(bad_fmt)
    assert_true(not result3["overall_ok"],
                "Entry with unknown format 'livestream' must fail")
    assert_true(
        any(f["status"] == "UNKNOWN_FORMAT" for f in result3["fields"]),
        "Unknown format must appear as UNKNOWN_FORMAT in fields",
    )

    # ------------------------------------------------------------------
    # Test 4 – fully valid fixture passes
    # ------------------------------------------------------------------
    valid_entry = {
        "line_no": 13, "title": "Code Klets",
        "url": "https://open.spotify.com/show/0Sf8c3aGZmtGiNUEwgDTSu?si=bc273e44deae4584",
        "author": "Bernard, Jonny, Kishen, Pauline, Wouter & Saber",
        "fmt": "podcast",
        "notes": "", "section": "Podcasts", "selected": True,
    }
    result4 = verify_metadata(valid_entry)
    assert_true(result4["overall_ok"],
                "Fully valid entry must pass all metadata checks")
    assert_eq(result4["evidence"], [],
              "Evidence table must be empty for a fully valid entry")

    # ------------------------------------------------------------------
    # Test 5 – selected entries parsed with correct line numbers from file
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
        selected    = [e for e in all_entries if e["selected"]]

        assert_eq(len(selected), 2,
                  f"Expected 2 selected entries in {TARGET_FILE.name}")

        expected_map = {
            "https://open.spotify.com/show/0Sf8c3aGZmtGiNUEwgDTSu?si=bc273e44deae4584": {
                "title":   "Code Klets",
                "line_no": 3,
                "section": "Podcasts",
            },
            "https://open.spotify.com/show/63diy2DtpHzQfeNVxAPZgU": {
                "title":   "TDS Team",
                "line_no": 4,
                "section": "Podcasts",
            },
        }
        for entry in selected:
            exp = expected_map.get(entry["url"])
            if exp is None:
                failures.append(f"FAIL: Unexpected URL: {entry['url']}")
                continue
            assert_eq(entry["line_no"], exp["line_no"],
                      f"Line number mismatch for {entry['url']}")
            assert_eq(entry["section"], exp["section"],
                      f"Section mismatch for {entry['url']}")

    # ------------------------------------------------------------------
    # Test 6 – real selected entries pass all metadata checks
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        all_entries2 = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
        selected2    = [e for e in all_entries2 if e["selected"]]
        for entry in selected2:
            vr = verify_metadata(entry)
            assert_true(vr["overall_ok"],
                        f"Real entry '{entry['title']}' must pass all metadata checks")

    # ------------------------------------------------------------------
    # Test 7 – evidence table gives source_url, observed, proposed for each issue
    # ------------------------------------------------------------------
    result5 = verify_metadata(missing_author)
    for row in result5["evidence"]:
        assert_true("source_url" in row,
                    "Evidence row must contain 'source_url'")
        assert_true("observed" in row,
                    "Evidence row must contain 'observed'")
        assert_true("proposed_value" in row,
                    "Evidence row must contain 'proposed_value'")

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    if failures:
        print("\n=== SELF-TEST FAILURES ===")
        for f in failures:
            print(f)
        print(f"\n{len(failures)} test(s) failed.")
        sys.exit(1)
    else:
        print("All self-tests passed.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if "--self-test" in sys.argv:
        run_self_test()
        return

    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    checked_at  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
    selected    = [e for e in all_entries if e["selected"]]

    print(f"Parsed {len(all_entries)} entries from {TARGET_FILE.name}")
    print(f"Checking metadata for {len(selected)} selected entries\n")

    all_results  = []
    all_evidence = []

    for entry in selected:
        vr = verify_metadata(entry)
        vr["checked_at"] = checked_at
        all_results.append(vr)
        all_evidence.extend(vr["evidence"])

        status = "PASS" if vr["overall_ok"] else "FAIL"
        print(f"  Line {entry['line_no']:>3} | {status} | {entry['title']}")
        print(f"           URL    : {entry['url']}")
        for f in vr["fields"]:
            icon = "✓" if f["status"] == "PRESENT" else "✗"
            print(f"           {icon} {f['field']:<8}: {f['observed'] or '(empty)'}"
                  + (f"  [{f['status']}]" if f["status"] != "PRESENT" else ""))
        print()

    # Evidence table
    if all_evidence:
        print("=== Evidence Table (fields needing correction) ===")
        print(f"{'Source URL':<60} {'Field':<10} {'Observed':<20} {'Status':<18} {'Proposed'}")
        print("-" * 130)
        for row in all_evidence:
            print(
                f"{row['source_url']:<60} "
                f"{row['field']:<10} "
                f"{str(row['observed']):<20} "
                f"{row['status']:<18} "
                f"{row['proposed_value'] or ''}"
            )
    else:
        print("All metadata fields are present and correctly formatted.")
        print("No corrections needed.")

    # Save evidence
    out_dir = REPO_ROOT / "work" / "R10-T035"
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump({
            "checked_at":     checked_at,
            "results":        all_results,
            "evidence_table": all_evidence,
        }, fh, ensure_ascii=False, indent=2)
    print(f"\nResults written to {results_path}")


if __name__ == "__main__":
    main()
