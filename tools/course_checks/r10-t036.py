#!/usr/bin/env python3
"""
R10-T036: Offline fixture-based test suite for free-programming-books-tr.md

Parses markdown book entries, validates format rules, and provides
an offline --self-test mode that uses only local fixture files.

Usage:
    python3 tools/course_checks/r10-t036.py              # run full check, write results.json
    python3 tools/course_checks/r10-t036.py --self-test  # run offline fixture tests only
"""

import re
import sys
import json
import os
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "books" / "free-programming-books-tr.md"
WORK_DIR = REPO_ROOT / "work" / "R10-T036"
RESULTS_FILE = WORK_DIR / "results.json"

# Mandatory selected entries (line numbers are 1-based in the file)
SELECTED_LINES = [32, 33]

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------

# Matches a markdown book entry line:
#   * [Title](URL) - Author (Format) extra notes
# Author may be:
#   - plain text: "John Doe"
#   - a hyperlink: "[John Doe](http://...)"  (which itself contains parens)
# We handle both by trying a linked-author pattern first in a combined regex.
ENTRY_RE = re.compile(
    r"^\*\s+"
    r"\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)"
    r"(?:\s+-\s+"
    r"(?:"
    # Linked author: [Name](URL) — captured as author_linked group
    r"\[(?P<author_name>[^\]]+)\]\((?P<author_url>[^)]+)\)"
    r"|"
    # Plain author (stops at opening paren or newline)
    r"(?P<author_plain>[^(\n]+)"
    r"))?"
    r"(?:\s*\((?P<fmt>[^)]+)\))?"
    r"(?P<notes>.*)$"
)



# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_entries(text: str) -> list[dict]:
    """Parse all book entries from markdown text. Skip fenced code blocks."""
    entries = []
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        # Track fenced code blocks (``` or ~~~)
        if re.match(r"^(`{3,}|~{3,})", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = ENTRY_RE.match(line)
        if not m:
            continue

        title = m.group("title").strip()
        url = m.group("url").strip()
        fmt = (m.group("fmt") or "").strip()
        notes = (m.group("notes") or "").strip()

        # Determine author — may be linked [Name](URL) or plain text
        if m.group("author_name") is not None:
            # Linked author captured directly by ENTRY_RE
            author_name = m.group("author_name").strip()
            author_url: Optional[str] = m.group("author_url").strip()
        else:
            author_name = (m.group("author_plain") or "").strip()
            author_url = None

        entries.append({
            "lineno": lineno,
            "title": title,
            "url": url,
            "author": author_name,
            "author_url": author_url,
            "format": fmt,
            "notes": notes,
        })
    return entries


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def has_percent_encoded_chars(url: str) -> bool:
    """Return True if URL contains percent-encoded sequences like %C4%B1."""
    return bool(re.search(r"%[0-9A-Fa-f]{2}", url))


def check_format_field(entry: dict) -> Optional[str]:
    """Return error string if format field is missing, else None."""
    if not entry["format"]:
        return f"Line {entry['lineno']}: Entry '{entry['title']}' missing format specifier (PDF/HTML/etc.)"
    return None


def check_url_not_empty(entry: dict) -> Optional[str]:
    if not entry["url"]:
        return f"Line {entry['lineno']}: Entry '{entry['title']}' has empty URL"
    return None


# ---------------------------------------------------------------------------
# Full-file analysis
# ---------------------------------------------------------------------------

def run_analysis(text: str) -> dict:
    entries = parse_entries(text)
    errors = []
    warnings = []
    stats = {
        "total_entries": len(entries),
        "with_author": sum(1 for e in entries if e["author"]),
        "with_linked_author": sum(1 for e in entries if e["author_url"]),
        "with_percent_encoded_url": sum(1 for e in entries if has_percent_encoded_chars(e["url"])),
        "missing_format": 0,
    }

    for entry in entries:
        err = check_format_field(entry)
        if err:
            warnings.append(err)
            stats["missing_format"] += 1
        err2 = check_url_not_empty(entry)
        if err2:
            errors.append(err2)

    # Pull out selected entries
    selected = [e for e in entries if e["lineno"] in SELECTED_LINES]

    return {
        "task": "R10-T036",
        "target_file": str(TARGET_FILE.relative_to(REPO_ROOT)),
        "stats": stats,
        "selected_entries": selected,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Self-test (offline, fixture-based)
# ---------------------------------------------------------------------------

def self_test() -> int:
    """Run offline fixture tests. Returns 0 on all-pass, 1 on any failure."""
    failures = []
    passed = 0

    def assert_eq(label: str, got, expected):
        nonlocal passed
        if got == expected:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}\n       expected: {expected!r}\n       got:      {got!r}")
            print(f"  FAIL  {label}")
            print(f"         expected: {expected!r}")
            print(f"         got:      {got!r}")

    def assert_true(label: str, value: bool):
        nonlocal passed
        if value:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}  (got False)")
            print(f"  FAIL  {label}  (got False)")

    print("=" * 60)
    print("R10-T036 Self-Test (offline fixture-based)")
    print("=" * 60)

    # -------------------------------------------------------------------
    # Fixture 1: Malformed row (no URL) → parsed entry count = 0
    # -------------------------------------------------------------------
    print("\n[Fixture 1] Malformed row — no URL")
    fixture_malformed = "* [Missing URL entry\n"
    result_malformed = parse_entries(fixture_malformed)
    assert_eq("Malformed row: entry count == 0", len(result_malformed), 0)

    # -------------------------------------------------------------------
    # Fixture 2: Valid row with percent-encoded URL
    # -------------------------------------------------------------------
    print("\n[Fixture 2] Valid row with percent-encoded URL")
    pct_url = (
        "https://ia601404.us.archive.org/34/items/"
        "algoritma-ve-programlama-soru-bankasi/"
        "algoritma-ve-programlama-soru-bankas%C4%B1.pdf"
    )
    fixture_pct = f"* [Algoritma ve Programlama Soru Bankası]({pct_url}) (PDF)\n"
    result_pct = parse_entries(fixture_pct)
    assert_eq("Percent-encoded URL fixture: 1 entry parsed", len(result_pct), 1)
    assert_eq("Percent-encoded URL preserved verbatim", result_pct[0]["url"], pct_url)
    assert_true("URL contains percent-encoded chars", has_percent_encoded_chars(result_pct[0]["url"]))
    assert_eq("No author (empty string)", result_pct[0]["author"], "")
    assert_eq("Format is PDF", result_pct[0]["format"], "PDF")

    # -------------------------------------------------------------------
    # Fixture 3: Valid row with linked author [Name](URL)
    # -------------------------------------------------------------------
    print("\n[Fixture 3] Valid row with linked author")
    author_url = "http://ikucukkoc.baun.edu.tr"
    book_url = (
        "https://ia601404.us.archive.org/12/items/"
        "algoritma-ve-programlamaya-giris-ders-notlari/"
        "Algoritma%20ve%20Programlamaya%20Giri%C5%9F%20Ders%20Notlar%C4%B1.pdf"
    )
    fixture_linked = (
        f"* [Algoritma ve Programlamaya Giriş Ders Notları]({book_url})"
        f" - [İbrahim Küçükkoç]({author_url}) (PDF)\n"
    )
    result_linked = parse_entries(fixture_linked)
    assert_eq("Linked-author fixture: 1 entry parsed", len(result_linked), 1)
    assert_eq("Author name extracted correctly", result_linked[0]["author"], "İbrahim Küçükkoç")
    assert_eq("Author URL extracted correctly", result_linked[0]["author_url"], author_url)
    assert_eq("Book URL preserved", result_linked[0]["url"], book_url)
    assert_eq("Format is PDF", result_linked[0]["format"], "PDF")

    # -------------------------------------------------------------------
    # Fixture 4: Valid row, no author
    # -------------------------------------------------------------------
    print("\n[Fixture 4] Valid row, no author")
    fixture_no_author = "* [SomeBook](https://example.com/book.pdf) (PDF)\n"
    result_no_author = parse_entries(fixture_no_author)
    assert_eq("No-author fixture: 1 entry parsed", len(result_no_author), 1)
    assert_eq("Author field is empty string", result_no_author[0]["author"], "")
    assert_eq("Author URL is None", result_no_author[0]["author_url"], None)
    assert_eq("Format field is PDF", result_no_author[0]["format"], "PDF")

    # -------------------------------------------------------------------
    # Fixture 5: Selected entries in actual target file
    # -------------------------------------------------------------------
    print("\n[Fixture 5] Selected entries in actual target file")
    if not TARGET_FILE.exists():
        failures.append("FAIL  Target file missing: " + str(TARGET_FILE))
        print(f"  FAIL  Target file not found: {TARGET_FILE}")
    else:
        text = TARGET_FILE.read_text(encoding="utf-8")
        all_entries = parse_entries(text)
        selected = [e for e in all_entries if e["lineno"] in SELECTED_LINES]
        assert_eq("Two selected entries found (lines 32, 33)", len(selected), 2)

        e32 = next((e for e in selected if e["lineno"] == 32), None)
        e33 = next((e for e in selected if e["lineno"] == 33), None)

        assert_true("Line 32 entry exists", e32 is not None)
        if e32:
            assert_eq(
                "Line 32 title",
                e32["title"],
                "Algoritma ve Programlama Soru Bankası",
            )
            assert_true(
                "Line 32 URL is percent-encoded",
                has_percent_encoded_chars(e32["url"]),
            )
            assert_eq("Line 32 format is PDF", e32["format"], "PDF")
            assert_eq("Line 32 no author", e32["author"], "")

        assert_true("Line 33 entry exists", e33 is not None)
        if e33:
            assert_eq(
                "Line 33 title",
                e33["title"],
                "Algoritma ve Programlamaya Giriş Ders Notları",
            )
            assert_eq(
                "Line 33 author name",
                e33["author"],
                "İbrahim Küçükkoç",
            )
            assert_eq(
                "Line 33 author URL",
                e33["author_url"],
                "http://ikucukkoc.baun.edu.tr",
            )
            assert_eq("Line 33 format is PDF", e33["format"], "PDF")
            assert_true(
                "Line 33 URL contains percent-encoded chars",
                has_percent_encoded_chars(e33["url"]),
            )

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    print("\n" + "=" * 60)
    total = passed + len(failures)
    if failures:
        print(f"RESULT: {len(failures)} FAILED / {total} assertions")
        for f in failures:
            print(f"  {f}")
        return 1
    else:
        print(f"RESULT: All {passed} assertions passed.")
        print("All self-tests passed.")
        return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test())

    # Full analysis mode
    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    text = TARGET_FILE.read_text(encoding="utf-8")
    report = run_analysis(text)

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {RESULTS_FILE}")
    print(f"Total entries: {report['stats']['total_entries']}")
    print(f"Entries with author: {report['stats']['with_author']}")
    print(f"Entries with linked author: {report['stats']['with_linked_author']}")
    print(f"Entries with percent-encoded URL: {report['stats']['with_percent_encoded_url']}")
    print(f"Entries missing format: {report['stats']['missing_format']}")
    if report["errors"]:
        print(f"\nErrors ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"  {e}")
    print(f"\nSelected entries (lines {SELECTED_LINES}):")
    for e in report["selected_entries"]:
        print(f"  Line {e['lineno']}: {e['title']}")


if __name__ == "__main__":
    main()
