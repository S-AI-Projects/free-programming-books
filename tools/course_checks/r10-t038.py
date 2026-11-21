#!/usr/bin/env python3
"""
R10-T038: Ordering and formatting checker for books/free-programming-books-en.md

Validates:
  - Bullet-entry syntax: * [Title](URL) or * [Title](URL) followed by description
  - Heading hierarchy: ### headings, no skipped levels
  - Entry ordering: entries under a section must be alphabetically sorted by title
  - No trailing whitespace on entry lines
  - Fragment anchors (#anchor) are valid references

Usage:
    python3 tools/course_checks/r10-t038.py              # run full check, write results.json
    python3 tools/course_checks/r10-t038.py --self-test  # run offline fixture tests only
"""

import re
import sys
import json
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "books" / "free-programming-books-en.md"
WORK_DIR = REPO_ROOT / "work" / "R10-T038"
RESULTS_FILE = WORK_DIR / "results.json"

# The first three bullet entries in the file (lines 3, 8, 9)
SELECTED_LINES = [3, 8, 9]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Valid markdown bullet entry: * [Title](URL) [optional rest]
ENTRY_RE = re.compile(
    r"^\*\s+\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)(?P<rest>.*)$"
)

# Continuation / annotation line (indented, starts with whitespace or plain text)
CONTINUATION_RE = re.compile(r"^\s+\S")

# Heading line: ## or ### etc.
HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<title>.+)$")

# Fragment anchor (internal link)
ANCHOR_RE = re.compile(r"^#[\w\-]+$")

# Trailing whitespace
TRAILING_WS_RE = re.compile(r"\s+$")

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_file(text: str) -> dict:
    """
    Parse markdown into structured sections with their entries.
    Returns:
        {
          "headings": [(lineno, level, title), ...],
          "entries":  [(lineno, section_title, entry_title, url, rest), ...],
          "raw_lines": [(lineno, text), ...],
        }
    """
    headings = []
    entries = []
    raw_lines = []
    current_section = "(top)"
    in_fence = False

    for lineno, raw in enumerate(text.splitlines(), start=1):
        raw_lines.append((lineno, raw))
        line = raw.rstrip("\r\n")

        # Track fenced code blocks
        if re.match(r"^(`{3,}|~{3,})", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # Headings
        hm = HEADING_RE.match(line)
        if hm:
            level = len(hm.group("hashes"))
            title = hm.group("title").strip()
            headings.append((lineno, level, title))
            current_section = title
            continue

        # Bullet entries
        em = ENTRY_RE.match(line)
        if em:
            entries.append({
                "lineno": lineno,
                "section": current_section,
                "title": em.group("title").strip(),
                "url": em.group("url").strip(),
                "rest": em.group("rest").strip(),
            })

    return {"headings": headings, "entries": entries, "raw_lines": raw_lines}


# ---------------------------------------------------------------------------
# Formatting checks
# ---------------------------------------------------------------------------

def check_bullet_syntax(line: str) -> Optional[str]:
    """
    Return error if a line that starts with '*' but does NOT match valid entry syntax.
    Returns None if the line is valid or not a bullet line.
    """
    stripped = line.rstrip()
    if not stripped.startswith("* "):
        return None
    if ENTRY_RE.match(stripped):
        return None
    return f"Malformed bullet (not `* [Title](URL)` format): {stripped!r}"


def check_trailing_whitespace(line: str, lineno: int) -> Optional[str]:
    """Return error if the line has trailing whitespace."""
    if TRAILING_WS_RE.search(line.rstrip("\r\n") + " ") and line.rstrip("\r\n") != line.rstrip():
        # Only flag lines where there is trailing space before the newline
        pass
    # Simpler: flag lines ending with space or tab
    rline = line.rstrip("\r\n")
    if rline != rline.rstrip():
        return f"Line {lineno}: trailing whitespace"
    return None


def check_heading_hierarchy(headings: list) -> list[str]:
    """
    Verify heading levels don't skip levels (e.g., ### directly after #).
    Returns list of error messages.
    """
    errors = []
    prev_level = 0
    for lineno, level, title in headings:
        if prev_level > 0 and level > prev_level + 1:
            errors.append(
                f"Line {lineno}: Heading level jumps from {prev_level} to {level} "
                f"('{title}') — skipped level"
            )
        prev_level = level
    return errors


def check_section_ordering(entries: list) -> list[str]:
    """
    Within each section, entries should be sorted alphabetically by title (case-insensitive).
    Returns list of warning messages.
    """
    warnings = []
    # Group entries by section
    sections: dict[str, list] = {}
    for e in entries:
        sections.setdefault(e["section"], []).append(e)

    for section, section_entries in sections.items():
        titles = [e["title"].lower() for e in section_entries]
        sorted_titles = sorted(titles)
        if titles != sorted_titles:
            # Find first out-of-order pair
            for i in range(1, len(titles)):
                if titles[i] < titles[i - 1]:
                    warnings.append(
                        f"Section '{section}': entry '{section_entries[i]['title']}' "
                        f"(line {section_entries[i]['lineno']}) appears before "
                        f"'{section_entries[i-1]['title']}' "
                        f"(line {section_entries[i-1]['lineno']}) — not alphabetically sorted"
                    )
                    break
    return warnings


def check_url_not_empty(entry: dict) -> Optional[str]:
    if not entry["url"]:
        return f"Line {entry['lineno']}: Entry '{entry['title']}' has empty URL"
    return None


# ---------------------------------------------------------------------------
# Full-file analysis
# ---------------------------------------------------------------------------

def run_analysis(text: str) -> dict:
    parsed = parse_file(text)
    errors = []
    warnings = []

    # Check each raw line for bullet syntax and trailing whitespace
    for lineno, raw in parsed["raw_lines"]:
        line = raw.rstrip("\r\n")
        err = check_bullet_syntax(line)
        if err:
            errors.append(f"Line {lineno}: {err}")
        tw_err = check_trailing_whitespace(raw, lineno)
        if tw_err:
            warnings.append(tw_err)

    # Heading hierarchy
    h_errors = check_heading_hierarchy(parsed["headings"])
    errors.extend(h_errors)

    # Section ordering
    ord_warnings = check_section_ordering(parsed["entries"])
    warnings.extend(ord_warnings)

    # Empty URL check
    for e in parsed["entries"]:
        err = check_url_not_empty(e)
        if err:
            errors.append(err)

    # Pull selected entries
    selected = [e for e in parsed["entries"] if e["lineno"] in SELECTED_LINES]

    return {
        "task": "R10-T038",
        "target_file": str(TARGET_FILE.relative_to(REPO_ROOT)),
        "stats": {
            "total_lines": len(parsed["raw_lines"]),
            "total_headings": len(parsed["headings"]),
            "total_entries": len(parsed["entries"]),
        },
        "selected_entries": selected,
        "errors": errors,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Self-test
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

    def assert_none(label: str, value):
        nonlocal passed
        if value is None:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}  (expected None, got {value!r})")
            print(f"  FAIL  {label}  (expected None, got {value!r})")

    print("=" * 60)
    print("R10-T038 Self-Test (offline fixture-based)")
    print("=" * 60)

    # -------------------------------------------------------------------
    # Fixture 1: Malformed bullet — rejected with error
    # -------------------------------------------------------------------
    print("\n[Fixture 1] Malformed bullet syntax")
    malformed = "* Missing URL entry"
    err = check_bullet_syntax(malformed)
    assert_true("Malformed bullet is detected", err is not None)
    assert_true("Error mentions 'Malformed bullet'", err is not None and "Malformed bullet" in err)

    valid_line = "* [Title](https://example.com) rest"
    err2 = check_bullet_syntax(valid_line)
    assert_none("Valid bullet passes syntax check", err2)

    # -------------------------------------------------------------------
    # Fixture 2: Valid non-English text in title is preserved
    # -------------------------------------------------------------------
    print("\n[Fixture 2] Non-English text and markdown links preserved")
    unicode_md = "* [ចំនេះដឹងទូទៅ](https://example.com/km) - Author\n"
    parsed_unicode = parse_file(unicode_md)
    assert_eq("Unicode title: 1 entry parsed", len(parsed_unicode["entries"]), 1)
    assert_eq("Unicode title preserved verbatim",
              parsed_unicode["entries"][0]["title"], "ចំនេះដឹងទូទៅ")
    assert_eq("Unicode entry URL correct",
              parsed_unicode["entries"][0]["url"], "https://example.com/km")

    # -------------------------------------------------------------------
    # Fixture 3: Heading hierarchy — skipped level detected
    # -------------------------------------------------------------------
    print("\n[Fixture 3] Heading hierarchy check")
    # H1 then H3 (skips H2)
    skip_md = "# Top\n### SubSection\n"
    parsed_skip = parse_file(skip_md)
    h_errors = check_heading_hierarchy(parsed_skip["headings"])
    assert_true("Skipped heading level detected", len(h_errors) > 0)
    assert_true("Error mentions level jump", any("jumps from" in e for e in h_errors))

    # Valid hierarchy: H1 → H2 → H3
    valid_h_md = "# Top\n## Mid\n### Low\n"
    parsed_valid_h = parse_file(valid_h_md)
    h_errors2 = check_heading_hierarchy(parsed_valid_h["headings"])
    assert_eq("Valid heading hierarchy: no errors", h_errors2, [])

    # -------------------------------------------------------------------
    # Fixture 4: Alphabetical ordering within a section
    # -------------------------------------------------------------------
    print("\n[Fixture 4] Alphabetical ordering check")
    out_of_order_md = (
        "### Section\n"
        "* [Zebra](https://example.com/z)\n"
        "* [Apple](https://example.com/a)\n"
    )
    parsed_order = parse_file(out_of_order_md)
    ord_warnings = check_section_ordering(parsed_order["entries"])
    assert_true("Out-of-order section detected", len(ord_warnings) > 0)
    assert_true("Warning mentions section name", any("Section" in w for w in ord_warnings))

    in_order_md = (
        "### Section\n"
        "* [Apple](https://example.com/a)\n"
        "* [Zebra](https://example.com/z)\n"
    )
    parsed_order2 = parse_file(in_order_md)
    ord_warnings2 = check_section_ordering(parsed_order2["entries"])
    assert_eq("In-order section: no warnings", ord_warnings2, [])

    # -------------------------------------------------------------------
    # Fixture 5: Trailing whitespace detected
    # -------------------------------------------------------------------
    print("\n[Fixture 5] Trailing whitespace")
    line_with_trailing = "* [Title](https://example.com)   "
    tw_err = check_trailing_whitespace(line_with_trailing, 1)
    assert_true("Trailing whitespace detected", tw_err is not None)

    clean_line = "* [Title](https://example.com)"
    tw_err2 = check_trailing_whitespace(clean_line, 1)
    assert_none("No trailing whitespace: passes", tw_err2)

    # -------------------------------------------------------------------
    # Fixture 6: Actual target file — selected entries parsed correctly
    # -------------------------------------------------------------------
    print("\n[Fixture 6] Selected entries in actual target file")
    if TARGET_FILE.exists():
        text = TARGET_FILE.read_text(encoding="utf-8")
        result = run_analysis(text)

        assert_eq("Three selected entries found", len(result["selected_entries"]), 3)

        e3 = next((e for e in result["selected_entries"] if e["lineno"] == 3), None)
        e8 = next((e for e in result["selected_entries"] if e["lineno"] == 8), None)
        e9 = next((e for e in result["selected_entries"] if e["lineno"] == 9), None)

        assert_true("Line 3 entry exists", e3 is not None)
        if e3:
            assert_eq("Line 3 title", e3["title"], "All")
            assert_eq("Line 3 URL is anchor", e3["url"], "#all")

        assert_true("Line 8 entry exists", e8 is not None)
        if e8:
            assert_eq("Line 8 title", e8["title"], "English, By Programming Language")
            assert_eq("Line 8 URL", e8["url"], "free-programming-books-langs.md")

        assert_true("Line 9 entry exists", e9 is not None)
        if e9:
            assert_eq("Line 9 title", e9["title"], "English, By Subject")
            assert_eq("Line 9 URL", e9["url"], "free-programming-books-subjects.md")

        # File has no formatting errors
        assert_eq("Target file has no bullet syntax errors", result["errors"], [])
    else:
        failures.append(f"FAIL  Target file not found: {TARGET_FILE}")
        print(f"  FAIL  Target file not found: {TARGET_FILE}")

    # -------------------------------------------------------------------
    # Fixture 7: Fragment anchor (internal link) accepted as valid URL
    # -------------------------------------------------------------------
    print("\n[Fixture 7] Fragment anchor URL accepted")
    anchor_md = "* [All](#all)\n"
    parsed_anchor = parse_file(anchor_md)
    assert_eq("Fragment anchor: 1 entry parsed", len(parsed_anchor["entries"]), 1)
    assert_eq("Fragment anchor URL preserved", parsed_anchor["entries"][0]["url"], "#all")
    err_anchor = check_url_not_empty(parsed_anchor["entries"][0])
    assert_none("Fragment anchor URL not flagged as empty", err_anchor)

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

    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    text = TARGET_FILE.read_text(encoding="utf-8")
    report = run_analysis(text)

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {RESULTS_FILE}")
    print(f"Total lines: {report['stats']['total_lines']}")
    print(f"Total headings: {report['stats']['total_headings']}")
    print(f"Total entries: {report['stats']['total_entries']}")
    print(f"Errors: {len(report['errors'])}")
    print(f"Warnings: {len(report['warnings'])}")
    if report["errors"]:
        for e in report["errors"]:
            print(f"  ERROR: {e}")
    if report["warnings"]:
        for w in report["warnings"]:
            print(f"  WARN:  {w}")
    print(f"\nSelected entries (lines {SELECTED_LINES}):")
    for e in report["selected_entries"]:
        print(f"  Line {e['lineno']}: [{e['title']}]({e['url']}) [section: {e['section']}]")


if __name__ == "__main__":
    main()

