#!/usr/bin/env python3
"""
R10-T033 — Duplicate Detection for free-programming-books-da.md
================================================================
Groups exact duplicate URLs and conservative URL-normalisation matches
across the entries in books/free-programming-books-da.md.

Rules:
  - EXACT duplicate  : byte-identical URLs after stripping trailing slashes
  - NORMALISED match : scheme-normalised (http→https), lower-cased host,
                       sorted query params — but DISTINCT anchors (#...) and
                       query-dependent resources are kept separate
  - Every proposed deletion must be manually reviewed

Selected entries (as per task R10-T033):
  1. Beej's Guide til Netvarksprogrammierung
     https://web.archive.org/web/20190701062226/http://artcreationforever.com/bgnet.html
  2. Programmering i C
     http://people.cs.aau.dk/~normark/c-prog-06/pdf/all.pdf
  3. Object-oriented Programming in C#
     http://people.cs.aau.dk/~normark/oop-csharp/pdf/all.pdf

Usage:
  python3 tools/course_checks/r10-t033.py               # run full report
  python3 tools/course_checks/r10-t033.py --self-test   # offline assertions; exits non-zero on failure
"""

import re
import sys
import json
import urllib.parse
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT   = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "books" / "free-programming-books-da.md"

SELECTED_URLS = {
    "https://web.archive.org/web/20190701062226/http://artcreationforever.com/bgnet.html",
    "http://people.cs.aau.dk/~normark/c-prog-06/pdf/all.pdf",
    "http://people.cs.aau.dk/~normark/oop-csharp/pdf/all.pdf",
}

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

ENTRY_RE  = re.compile(
    r"^\*\s+"
    r"\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)]+)\)"
    r"(?:\s+-\s+(?P<author>[^(\n*]+?))?"
    r"(?:\s+\((?P<fmt>[^)]+)\))?"
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

            m_heading = HEADING_RE.match(line)
            if m_heading:
                current_section = m_heading.group(1).strip()
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
# URL normalisation
# ---------------------------------------------------------------------------

def normalise_url(url: str) -> str:
    """
    Return a normalised form for grouping purposes.
    - Lowercases scheme and host
    - Strips trailing slash from path (unless path is just '/')
    - Sorts query parameters
    - Preserves fragment (distinct anchors are NOT merged)
    - Does NOT upgrade http→https (different schemes may serve different content)
    """
    try:
        p = urllib.parse.urlparse(url)
        scheme = p.scheme.lower()
        netloc = p.netloc.lower()
        path   = p.path.rstrip("/") or "/"
        # Sort query params for normalisation
        query  = urllib.parse.urlencode(
            sorted(urllib.parse.parse_qsl(p.query)), doseq=True
        )
        # Keep fragment — distinct anchors are not merged
        fragment = p.fragment
        return urllib.parse.urlunparse((scheme, netloc, path, "", query, fragment))
    except Exception:
        return url.strip().rstrip("/")


def find_duplicates(entries: list) -> dict:
    """
    Group entries by normalised URL.
    Returns a dict: normalised_url → list of entries that share it.
    Only groups with 2+ entries are returned (actual duplicates).
    """
    groups = defaultdict(list)
    for entry in entries:
        key = normalise_url(entry["url"])
        groups[key].append(entry)

    return {k: v for k, v in groups.items() if len(v) > 1}


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
    # Test 1 – exact duplicate URLs are found
    # ------------------------------------------------------------------
    exact_entries = [
        {"line_no": 10, "title": "Book A", "url": "http://javabog.dk",
         "author": "Author A", "fmt": "", "notes": "", "section": "Java", "selected": False},
        {"line_no": 11, "title": "Book B", "url": "http://javabog.dk",
         "author": "Author B", "fmt": "", "notes": "", "section": "Java", "selected": False},
    ]
    dups = find_duplicates(exact_entries)
    assert_true(len(dups) >= 1, "Exact duplicate URLs must be detected")
    assert_eq(
        len(list(dups.values())[0]), 2,
        "Exact-duplicate group must contain both entries"
    )

    # ------------------------------------------------------------------
    # Test 2 – distinct anchors are NOT merged
    # ------------------------------------------------------------------
    anchor_entries = [
        {"line_no": 20, "title": "Book C", "url": "http://example.com/book#chapter-1",
         "author": "", "fmt": "", "notes": "", "section": "S", "selected": False},
        {"line_no": 21, "title": "Book D", "url": "http://example.com/book#chapter-2",
         "author": "", "fmt": "", "notes": "", "section": "S", "selected": False},
    ]
    dups2 = find_duplicates(anchor_entries)
    assert_true(
        len(dups2) == 0,
        "Distinct anchors (#chapter-1 vs #chapter-2) must NOT be merged as duplicates"
    )

    # ------------------------------------------------------------------
    # Test 3 – trailing slash normalisation catches duplicates
    # ------------------------------------------------------------------
    slash_entries = [
        {"line_no": 30, "title": "Book E", "url": "http://example.com/guide",
         "author": "", "fmt": "", "notes": "", "section": "S", "selected": False},
        {"line_no": 31, "title": "Book F", "url": "http://example.com/guide/",
         "author": "", "fmt": "", "notes": "", "section": "S", "selected": False},
    ]
    dups3 = find_duplicates(slash_entries)
    assert_true(
        len(dups3) >= 1,
        "URLs differing only by trailing slash must be grouped as duplicates"
    )

    # ------------------------------------------------------------------
    # Test 4 – query-dependent resources with DIFFERENT params are NOT merged
    # ------------------------------------------------------------------
    query_entries = [
        {"line_no": 40, "title": "Book G", "url": "http://example.com/dl?id=1",
         "author": "", "fmt": "", "notes": "", "section": "S", "selected": False},
        {"line_no": 41, "title": "Book H", "url": "http://example.com/dl?id=2",
         "author": "", "fmt": "", "notes": "", "section": "S", "selected": False},
    ]
    dups4 = find_duplicates(query_entries)
    assert_true(
        len(dups4) == 0,
        "URLs with different query param values must NOT be merged"
    )

    # ------------------------------------------------------------------
    # Test 5 – selected entries parsed with correct line numbers from actual file
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
        selected    = [e for e in all_entries if e["selected"]]

        assert_eq(len(selected), 3,
                  f"Expected 3 selected entries in {TARGET_FILE.name}")

        expected_map = {
            "https://web.archive.org/web/20190701062226/http://artcreationforever.com/bgnet.html": {
                "title":   "Beej's Guide til Netvarksprogrammierung",
                "line_no": 13,
                "section": "C",
            },
            "http://people.cs.aau.dk/~normark/c-prog-06/pdf/all.pdf": {
                "title":   "Programmering i C",
                "line_no": 14,
                "section": "C",
            },
            "http://people.cs.aau.dk/~normark/oop-csharp/pdf/all.pdf": {
                "title":   "Object-oriented Programming in C#",
                "line_no": 19,
                "section": "C\\#",
            },
        }

        for entry in selected:
            exp = expected_map.get(entry["url"])
            if exp is None:
                failures.append(f"FAIL: Unexpected URL in selected: {entry['url']}")
                continue
            assert_eq(entry["title"],   exp["title"],
                      f"Title mismatch for {entry['url']}")
            assert_eq(entry["line_no"], exp["line_no"],
                      f"Line number mismatch for {entry['url']}")

    else:
        print(f"WARNING: Target file not found at {TARGET_FILE}; skipping live-file tests.")

    # ------------------------------------------------------------------
    # Test 6 – known exact duplicate in file (javabog.dk appears twice)
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        all_entries = parse_entries(TARGET_FILE)
        all_dups    = find_duplicates(all_entries)
        javabog_key = normalise_url("http://javabog.dk")
        assert_true(
            javabog_key in all_dups,
            "http://javabog.dk appears twice in the file and must be detected as a duplicate"
        )
        assert_eq(
            len(all_dups[javabog_key]), 2,
            "javabog.dk duplicate group must contain exactly 2 entries"
        )

    # ------------------------------------------------------------------
    # Test 7 – every proposed deletion has a manual-review note in results
    # ------------------------------------------------------------------
    sample_dups = {
        "http://example.com/dupe": [
            {"line_no": 1, "title": "A", "url": "http://example.com/dupe",
             "section": "X", "author": "", "fmt": "", "notes": "", "selected": False},
            {"line_no": 2, "title": "B", "url": "http://example.com/dupe",
             "section": "X", "author": "", "fmt": "", "notes": "", "selected": False},
        ]
    }
    report = build_report(sample_dups)
    for group in report:
        assert_true(
            "requires_manual_review" in group,
            "Every duplicate group in the report must carry a requires_manual_review flag"
        )
        assert_true(
            group["requires_manual_review"] is True,
            "requires_manual_review must be True for all groups"
        )

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
# Report builder
# ---------------------------------------------------------------------------

def build_report(duplicate_groups: dict) -> list:
    """Convert duplicate_groups dict into a list of report dicts."""
    report = []
    for norm_url, entries in duplicate_groups.items():
        report.append({
            "normalised_url":        norm_url,
            "count":                 len(entries),
            "entries":               entries,
            "requires_manual_review": True,
            "note": (
                "These entries share the same normalised URL. "
                "Verify in a browser before removing any entry. "
                "A rate-limit or transient error is NOT grounds for removal."
            ),
        })
    return report


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

    all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
    selected    = [e for e in all_entries if e["selected"]]
    all_dups    = find_duplicates(all_entries)
    report      = build_report(all_dups)

    print(f"Parsed {len(all_entries)} total entries from {TARGET_FILE.name}")
    print(f"Selected entries: {len(selected)}")
    print(f"Duplicate groups found (file-wide): {len(all_dups)}\n")

    # Print selected entries
    print("=== Selected Entries ===")
    for entry in selected:
        print(f"  Line {entry['line_no']:>4} | Section: {entry['section']}")
        print(f"           Title  : {entry['title']}")
        print(f"           URL    : {entry['url']}")
        if entry["author"]:
            print(f"           Author : {entry['author']}")
        # Check if this selected entry is part of any duplicate group
        norm = normalise_url(entry["url"])
        if norm in all_dups:
            print(f"           *** DUPLICATE DETECTED (normalised: {norm}) ***")
        print()

    # Print duplicate report
    if report:
        print("=== Duplicate Groups ===")
        for grp in report:
            print(f"\nNormalised URL : {grp['normalised_url']}")
            print(f"Count          : {grp['count']}")
            print(f"Manual review  : {grp['requires_manual_review']}")
            print(f"Note           : {grp['note']}")
            print("Entries:")
            for e in grp["entries"]:
                print(f"  Line {e['line_no']:>4} | {e['section']:20s} | {e['title']}")
                print(f"             URL: {e['url']}")
    else:
        print("No duplicate groups found.")

    # Save evidence
    out_dir = REPO_ROOT / "work" / "R10-T033"
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump({
            "selected_entries": selected,
            "duplicate_groups":  report,
        }, fh, ensure_ascii=False, indent=2)
    print(f"\nResults written to {results_path}")

    # Catalogue corrections
    if report:
        print("\nDuplicate groups requiring manual review before any catalogue change:")
        for grp in report:
            for e in grp["entries"]:
                print(f"  Line {e['line_no']}: [{e['title']}]({e['url']})")
    else:
        print("No catalogue corrections needed.")


if __name__ == "__main__":
    main()

