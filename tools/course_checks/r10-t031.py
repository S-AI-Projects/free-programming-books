#!/usr/bin/env python3
"""
R10-T031 — Structured Parser for free-courses-th.md
======================================================
Parses selected entries from courses/free-courses-th.md, extracts:
  - display name
  - URL
  - category / section heading
  - author (if present)
  - source line number

Selected entries (as per task R10-T031):
  1. การออกแบบและวิเคราะห์อัลกอริทึม
     https://youtube.com/playlist?list=PL0ROnaCzUGB65_YkASLAEmcW_mtxFtq4m
  2. Natural Language Processing 2023
     https://www.youtube.com/playlist?list=PLyyEwPZh6aHpCAaG6dot5xXrlEK73oF4J
  3. NLP 2021
     https://youtube.com/playlist?list=PLcBOyD1N1T-PIYnPZ9_iHtug9e-BcHIob

Usage:
  python3 tools/course_checks/r10-t031.py               # parse & print results
  python3 tools/course_checks/r10-t031.py --self-test   # run assertions; exits non-zero on failure
"""

import re
import sys
import os
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "courses" / "free-courses-th.md"

# URLs of the selected entries to focus on
SELECTED_URLS = {
    "https://youtube.com/playlist?list=PL0ROnaCzUGB65_YkASLAEmcW_mtxFtq4m",
    "https://www.youtube.com/playlist?list=PLyyEwPZh6aHpCAaG6dot5xXrlEK73oF4J",
    "https://youtube.com/playlist?list=PLcBOyD1N1T-PIYnPZ9_iHtug9e-BcHIob",
}

# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# Matches lines like: * [Title](URL) - Author (format)
# or:                 * [Title](URL) - Author
# or:                 * [Title](URL)
ENTRY_RE = re.compile(
    r"^\*\s+"                             # bullet
    r"\[(?P<title>[^\]]+)\]"             # [Title]
    r"\((?P<url>[^)]+)\)"               # (URL)
    r"(?:\s+-\s+(?P<author>[^(\n]+?))?"  # optional " - Author"
    r"(?:\s+\((?P<fmt>[^)]+)\))?"        # optional "(format)"
    r"\s*$"
)

# Fenced code block marker
FENCE_RE = re.compile(r"^```")

# Section headings: ### Section  or  #### Sub-section
HEADING_RE = re.compile(r"^#{2,6}\s+(.+)")


def parse_entries(filepath: Path, selected_urls=None):
    """
    Parse all markdown list entries from *filepath*.

    Returns a list of dicts with keys:
        line_no   – 1-based line number in the source file
        title     – display name from [...]
        url       – URL from (...)
        author    – author string (may be empty)
        fmt       – format note (may be empty)
        section   – nearest preceding section heading
        selected  – True if URL is in selected_urls set

    Fenced-code blocks are skipped (a URL inside ``` is not a real link).
    URL fragments (#...) are preserved.
    """
    if selected_urls is None:
        selected_urls = set()

    entries = []
    current_section = ""
    in_fence = False

    with open(filepath, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")

            # Track fenced code blocks
            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue

            if in_fence:
                continue

            # Update current section heading
            m_heading = HEADING_RE.match(line)
            if m_heading:
                current_section = m_heading.group(1).strip()
                continue

            # Try to parse a list entry
            m = ENTRY_RE.match(line)
            if not m:
                continue

            url = m.group("url").strip()
            entry = {
                "line_no": line_no,
                "title": m.group("title").strip(),
                "url": url,
                "author": (m.group("author") or "").strip(),
                "fmt": (m.group("fmt") or "").strip(),
                "section": current_section,
                "selected": url in selected_urls,
            }
            entries.append(entry)

    return entries


def get_selected_entries(filepath: Path):
    """Return only the selected entries from the target file."""
    all_entries = parse_entries(filepath, selected_urls=SELECTED_URLS)
    return [e for e in all_entries if e["selected"]]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test():
    """
    Run assertions against:
      1. Offline fixture strings (no network required)
      2. The actual target file (if present)

    Exits with code 1 on the first assertion failure.
    """
    failures = []

    def assert_true(condition, msg):
        if not condition:
            failures.append(f"FAIL: {msg}")

    # ------------------------------------------------------------------
    # Test 1 – fenced-code fake link is ignored
    # ------------------------------------------------------------------
    fake_md = """\
### Section

```
* [FakeBook](https://example.com/fake)
```

* [RealBook](https://example.com/real)
"""
    _tmp_path = Path("/tmp/_r10_t031_fake_test.md")
    _tmp_path.write_text(fake_md, encoding="utf-8")
    parsed = parse_entries(_tmp_path)
    urls_found = {e["url"] for e in parsed}

    assert_true(
        "https://example.com/fake" not in urls_found,
        "Fenced-code link should be ignored; found it in parsed results",
    )
    assert_true(
        "https://example.com/real" in urls_found,
        "Real link outside fence should be parsed; not found",
    )
    _tmp_path.unlink()

    # ------------------------------------------------------------------
    # Test 2 – URL with fragment is preserved
    # ------------------------------------------------------------------
    fragment_md = """\
### Section

* [FragmentBook](https://example.com/book#chapter-1) - Some Author
"""
    _tmp_path2 = Path("/tmp/_r10_t031_fragment_test.md")
    _tmp_path2.write_text(fragment_md, encoding="utf-8")
    parsed2 = parse_entries(_tmp_path2)
    assert_true(
        len(parsed2) == 1,
        f"Expected 1 entry with fragment URL, got {len(parsed2)}",
    )
    assert_true(
        parsed2[0]["url"] == "https://example.com/book#chapter-1",
        f"Fragment not preserved; got: {parsed2[0]['url'] if parsed2 else 'none'}",
    )
    _tmp_path2.unlink()

    # ------------------------------------------------------------------
    # Test 3 – selected entries map back to their source line numbers
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        selected = get_selected_entries(TARGET_FILE)
        assert_true(
            len(selected) == 3,
            f"Expected 3 selected entries, got {len(selected)}",
        )

        expected = {
            "https://youtube.com/playlist?list=PL0ROnaCzUGB65_YkASLAEmcW_mtxFtq4m": {
                "title": "การออกแบบและวิเคราะห์อัลกอริทึม",
                "line_no": 23,
                "section": "Algorithms & Data Structures",
            },
            "https://www.youtube.com/playlist?list=PLyyEwPZh6aHpCAaG6dot5xXrlEK73oF4J": {
                "title": "Natural Language Processing 2023",
                "line_no": 28,
                "section": "Artificial Intelligence",
            },
            "https://youtube.com/playlist?list=PLcBOyD1N1T-PIYnPZ9_iHtug9e-BcHIob": {
                "title": "NLP 2021",
                "line_no": 29,
                "section": "Artificial Intelligence",
            },
        }

        for entry in selected:
            exp = expected.get(entry["url"])
            if exp is None:
                failures.append(f"FAIL: Unexpected URL in selected: {entry['url']}")
                continue
            assert_true(
                entry["title"] == exp["title"],
                f"Title mismatch for {entry['url']}: "
                f"expected '{exp['title']}', got '{entry['title']}'",
            )
            assert_true(
                entry["line_no"] == exp["line_no"],
                f"Line number mismatch for {entry['url']}: "
                f"expected {exp['line_no']}, got {entry['line_no']}",
            )
            assert_true(
                entry["section"] == exp["section"],
                f"Section mismatch for {entry['url']}: "
                f"expected '{exp['section']}', got '{entry['section']}'",
            )
    else:
        print(f"WARNING: Target file not found at {TARGET_FILE}; skipping live-file tests.")

    # ------------------------------------------------------------------
    # Test 4 – --self-test mode exits non-zero on assertion failure (meta-test)
    # ------------------------------------------------------------------
    # We simulate a failure scenario using a deliberately wrong fixture
    bad_md = "* [Bad entry without url"
    _bad_path = Path("/tmp/_r10_t031_bad_test.md")
    _bad_path.write_text(bad_md, encoding="utf-8")
    bad_entries = parse_entries(_bad_path)
    assert_true(
        len(bad_entries) == 0,
        "Malformed line should yield no entries",
    )
    _bad_path.unlink()

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
        return  # run_self_test calls sys.exit

    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
    selected = [e for e in all_entries if e["selected"]]

    print(f"Parsed {len(all_entries)} total entries from {TARGET_FILE.name}")
    print(f"Selected entries ({len(selected)}):\n")

    for entry in selected:
        print(f"  Line {entry['line_no']:>4} | Section: {entry['section']}")
        print(f"           Title  : {entry['title']}")
        print(f"           URL    : {entry['url']}")
        if entry["author"]:
            print(f"           Author : {entry['author']}")
        if entry["fmt"]:
            print(f"           Format : {entry['fmt']}")
        print()

    # Also dump JSON to work/R10-T031/results.json for evidence
    out_dir = REPO_ROOT / "work" / "R10-T031"
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(selected, fh, ensure_ascii=False, indent=2)
    print(f"Results written to {results_path}")


if __name__ == "__main__":
    main()
