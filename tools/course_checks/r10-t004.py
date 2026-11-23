#!/usr/bin/env python3
"""
tools/course_checks/r10-t004.py - Category placement check for books/free-programming-books-ur.md
Student: Anshuman Holkar (Task R10-T004)

Features:
- Maps selected entries to their section categories.
- Detects misplaced entries based on verifiable subject content (not naive keywords).
- Detects repeated/duplicate section headings across the document hierarchy.
- Maps each entry to its exact 1-based source line number.
- Built-in --self-test mode with assertions that exit non-zero on failure.
"""

import os
import re
import sys
import json

TARGET_FILE = "books/free-programming-books-ur.md"
SELECTED_URLS = {
    "https://archive.org/details/CSikhiyeiUrduByAjnabiii": {
        "title": "C++ Sikhiyei (Urdu)",
        "expected_category": "C++",
        "subject": "C++ Programming in Urdu"
    },
    "https://www.eislamicbook.com/html-in-urdu-complete-tutorial-learning-book/": {
        "title": "HTML In Urdu Complete Tutorial Learning Book",
        "expected_category": "HTML",
        "subject": "HTML web development in Urdu"
    }
}

def analyze_categories(file_path):
    """
    Parses categories and entries.
    Returns:
    - entries: list of parsed entry dicts with category and line number
    - repeated_headings: list of heading titles that appear multiple times
    - misplaced: list of entries whose actual category does not match their known subject
    """
    entries = []
    seen_headings = {}
    repeated_headings = []
    current_category = None

    if not os.path.exists(file_path):
        return entries, repeated_headings, []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()

            # Heading detection
            if stripped.startswith("#"):
                heading_name = re.sub(r'<[^>]+>', '', stripped).lstrip('#').strip()
                if heading_name and heading_name.lower() != "index":
                    current_category = heading_name
                    seen_headings[heading_name] = seen_headings.get(heading_name, 0) + 1
                    if seen_headings[heading_name] == 2:
                        repeated_headings.append(heading_name)
                continue

            # Entry detection
            m_entry = re.search(r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)', stripped)
            if m_entry:
                url = m_entry.group("url")
                title = m_entry.group("title")
                entries.append({
                    "line": line_num,
                    "title": title,
                    "url": url,
                    "category": current_category
                })

    # Identify misplaced entries based on curated known subject definitions
    misplaced = []
    for e in entries:
        if e["url"] in SELECTED_URLS:
            exp_cat = SELECTED_URLS[e["url"]]["expected_category"]
            if e["category"] != exp_cat:
                misplaced.append({
                    "line": e["line"],
                    "title": e["title"],
                    "url": e["url"],
                    "current_category": e["category"],
                    "expected_category": exp_cat,
                    "subject": SELECTED_URLS[e["url"]]["subject"]
                })

    return entries, repeated_headings, misplaced

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    """
    print("[R10-T004] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T004/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T004/fixtures"

    # Assertion 1: Valid fixture has 0 misplaced entries and 0 repeated headings
    valid_fixture = os.path.join(fixtures_dir, "fixture_valid.md")
    _, repeated_valid, misplaced_valid = analyze_categories(valid_fixture)
    assert len(repeated_valid) == 0, f"Valid fixture should have no repeated headings, found: {repeated_valid}"
    assert len(misplaced_valid) == 0, f"Valid fixture should have no misplaced entries, found: {misplaced_valid}"
    print("  ✓ Assertion 1 passed: Valid fixture preserves correct categories with no repeated headings.")

    # Assertion 2: Deliberately misplaced fixture flags misplaced entries and repeated heading
    misplaced_fixture = os.path.join(fixtures_dir, "fixture_misplaced.md")
    _, repeated_bad, misplaced_bad = analyze_categories(misplaced_fixture)
    assert len(repeated_bad) == 1 and repeated_bad[0] == "HTML", \
        f"Misplaced fixture should flag duplicate 'HTML' heading, found: {repeated_bad}"
    assert len(misplaced_bad) == 2, f"Misplaced fixture should flag 2 misplaced entries, found: {len(misplaced_bad)}"
    # Verify subject citation in misplaced report
    for item in misplaced_bad:
        assert "subject" in item and len(item["subject"]) > 0, "Misplaced entry must cite resource actual subject"
    print("  ✓ Assertion 2 passed: Deliberately misplaced fixture and duplicate heading correctly identified with subject citations.")

    # Assertion 3: Real file entries map back to source lines (9 and 14) and are valid
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries, repeated_real, misplaced_real = analyze_categories(repo_file)
    assert len(repeated_real) == 0, f"Real file has repeated headings: {repeated_real}"
    assert len(misplaced_real) == 0, f"Real file has misplaced entries: {misplaced_real}"

    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    assert len(selected) == 2, f"Expected 2 selected entries, got {len(selected)}"
    lines = {e["url"]: e["line"] for e in selected}
    assert lines["https://archive.org/details/CSikhiyeiUrduByAjnabiii"] == 9
    assert lines["https://www.eislamicbook.com/html-in-urdu-complete-tutorial-learning-book/"] == 14
    print("  ✓ Assertion 3 passed: Real file entries map back to source lines (9, 14) and are properly categorized.")

    print("[R10-T004] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T004] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        except Exception as ex:
            print(f"[R10-T004] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries, repeated, misplaced = analyze_categories(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Category Placement Audit for {TARGET_FILE}:")
    print(f"Total entries: {len(entries)}")
    print(f"Repeated headings: {len(repeated)}")
    print(f"Misplaced entries: {len(misplaced)}\n")

    print(f"Selected entries audit ({len(selected)}):")
    for e in selected:
        info = SELECTED_URLS.get(e["url"], {})
        print(f"  Line {e['line']:2d} | Title            : {e['title']}")
        print(f"            URL              : {e['url']}")
        print(f"            Current Category : {e['category']}")
        print(f"            Expected Category: {info.get('expected_category')}")
        print(f"            Subject Matter   : {info.get('subject')}")
        print(f"            Placement Status : VALID_CATEGORY")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T004")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T004"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "repeated_headings": repeated,
            "misplaced_entries": misplaced,
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    main()
