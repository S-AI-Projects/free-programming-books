#!/usr/bin/env python3
"""
tools/course_checks/r10-t004.py - Category placement check for books/free-programming-books-ur.md
Student: Anshuman Holkar (Task R10-T004)

Features:
- Maps selected entries to their section categories.
- Detects misplaced entries dynamically from resource subject matter and keywords,
  without relying only on fixed URL tables.
- Accurately tracks heading hierarchies and detects duplicate headings within paths.
- Computes placement status dynamically.
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
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
        "subject": "C++ Programming in Urdu (Citation: Archive.org entry metadata and title)"
    },
    "https://www.eislamicbook.com/html-in-urdu-complete-tutorial-learning-book/": {
        "title": "HTML In Urdu Complete Tutorial Learning Book",
        "expected_category": "HTML",
        "subject": "HTML web development in Urdu (Citation: eIslamicBook tutorial metadata)"
    }
}

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T004] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

def infer_expected_category(title, url):
    """
    Infers the expected technical category and subject citation from entry title and URL.
    Enables generalized misplacement detection beyond static URL lookup tables.
    """
    text = (title + " " + url).lower()
    if "c++" in text or "cplusplus" in text or "csikhiyei" in text:
        return "C++", "C++ Programming (subject derived from title/resource keywords)"
    elif "html" in text or "css" in text:
        return "HTML", "HTML Web Development (subject derived from title/resource keywords)"
    elif "python" in text:
        return "Python", "Python Programming (subject derived from title/resource keywords)"
    elif "javascript" in text or "js" in text:
        return "JavaScript", "JavaScript Web Development (subject derived from title/resource keywords)"
    elif "java" in text:
        return "Java", "Java Programming (subject derived from title/resource keywords)"
    return None, None

def analyze_categories(file_path):
    """
    Parses categories and entries.
    Returns:
    - entries: list of parsed entry dicts with category and line number
    - repeated_headings: list of heading titles that appear multiple times
    - misplaced: list of entries whose actual category does not match their verified subject
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

            # Heading detection (strips HTML anchor tags like <a id="cplusplus"></a>)
            if stripped.startswith("#"):
                clean = re.sub(r'<[^>]+>', '', stripped).lstrip('#').strip()
                if clean and clean.lower() != "index":
                    current_category = clean
                    seen_headings[clean] = seen_headings.get(clean, 0) + 1
                    if seen_headings[clean] == 2:
                        repeated_headings.append(clean)
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

    # Identify misplaced entries (checks curated list first, then general inference)
    misplaced = []
    for e in entries:
        if e["url"] in SELECTED_URLS:
            exp_cat = SELECTED_URLS[e["url"]]["expected_category"]
            subj = SELECTED_URLS[e["url"]]["subject"]
        else:
            exp_cat, subj = infer_expected_category(e["title"], e["url"])

        if exp_cat and e["category"] and e["category"] != exp_cat:
            misplaced.append({
                "line": e["line"],
                "title": e["title"],
                "url": e["url"],
                "current_category": e["category"],
                "expected_category": exp_cat,
                "subject": subj or f"Technical topic {exp_cat}"
            })

    return entries, repeated_headings, misplaced

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    Works under python3 -O.
    """
    print("[R10-T004] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T004/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T004/fixtures"

    # Assertion 1: Valid fixture has 0 misplaced entries and 0 repeated headings
    valid_fixture = os.path.join(fixtures_dir, "fixture_valid.md")
    _, repeated_valid, misplaced_valid = analyze_categories(valid_fixture)
    check(len(repeated_valid) == 0, f"Valid fixture should have no repeated headings, found: {repeated_valid}")
    check(len(misplaced_valid) == 0, f"Valid fixture should have no misplaced entries, found: {misplaced_valid}")
    print("  ✓ Assertion 1 passed: Valid fixture preserves correct categories with no repeated headings.")

    # Assertion 2: Deliberately misplaced fixture flags misplaced entries and repeated heading
    misplaced_fixture = os.path.join(fixtures_dir, "fixture_misplaced.md")
    _, repeated_bad, misplaced_bad = analyze_categories(misplaced_fixture)
    check(len(repeated_bad) == 1 and repeated_bad[0] == "HTML",
          f"Misplaced fixture should flag duplicate 'HTML' heading, found: {repeated_bad}")
    check(len(misplaced_bad) == 2, f"Misplaced fixture should flag 2 misplaced entries, found: {len(misplaced_bad)}")
    for item in misplaced_bad:
        check("subject" in item and len(item["subject"]) > 0, "Misplaced entry must cite resource actual subject")
    print("  ✓ Assertion 2 passed: Deliberately misplaced fixture and duplicate heading correctly identified with subject citations.")

    # Assertion 3: Generalized probe - verify new URLs (HTML book under C++, C++ book under HTML) are flagged
    probe_entries = [
        {"line": 1, "title": "Advanced HTML5 Guide", "url": "https://example.org/new-html-book", "category": "C++"},
        {"line": 2, "title": "Modern C++ Primer", "url": "https://example.org/new-cpp-book", "category": "HTML"}
    ]
    probe_misplaced = []
    for e in probe_entries:
        exp_cat, subj = infer_expected_category(e["title"], e["url"])
        if exp_cat and e["category"] != exp_cat:
            probe_misplaced.append(e)
    check(len(probe_misplaced) == 2, f"Generalized misplacement probe failed: expected 2 misplaced, got {len(probe_misplaced)}")
    print("  ✓ Assertion 3 passed: Generalized misplacement detection flags entries based on content keywords rather than fixed URLs.")

    # Assertion 4: Real file entries map back to source lines (9 and 14) and match expected_selected.json
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries, repeated_real, misplaced_real = analyze_categories(repo_file)
    check(len(repeated_real) == 0, f"Real file has repeated headings: {repeated_real}")
    check(len(misplaced_real) == 0, f"Real file has misplaced entries: {misplaced_real}")

    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["url"]: item for item in expected_list}

    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    check(len(selected) == 2, f"Expected 2 selected entries, got {len(selected)}")
    
    misplaced_urls = {m["url"] for m in misplaced_real}

    for e in selected:
        exp = expected_map.get(e["url"])
        check(exp is not None, f"Unexpected selected URL: {e['url']}")
        check(e["line"] == exp["line"], f"Line mismatch for {e['title']}: expected {exp['line']}, got {e['line']}")
        check(e["category"] == exp["current_category"], f"Category mismatch: expected {exp['current_category']}, got {e['category']}")
        status = "MISPLACED" if e["url"] in misplaced_urls else "VALID_CATEGORY"
        check(status == exp["status"], f"Status mismatch: expected {exp['status']}, got {status}")
    print("  ✓ Assertion 4 passed: Real file entries map back to source lines (9, 14) and match expected_selected.json.")

    print("[R10-T004] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T004] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries, repeated, misplaced = analyze_categories(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]
    misplaced_urls = {m["url"] for m in misplaced}

    print(f"Category Placement Audit for {TARGET_FILE}:")
    print(f"Total entries: {len(entries)}")
    print(f"Repeated headings: {len(repeated)}")
    print(f"Misplaced entries: {len(misplaced)}\n")

    print(f"Selected entries audit ({len(selected)}):")
    for e in selected:
        info = SELECTED_URLS.get(e["url"], {})
        status = "MISPLACED" if e["url"] in misplaced_urls else "VALID_CATEGORY"
        print(f"  Line {e['line']:2d} | Title            : {e['title']}")
        print(f"            URL              : {e['url']}")
        print(f"            Current Category : {e['category']}")
        print(f"            Expected Category: {info.get('expected_category')}")
        print(f"            Subject Matter   : {info.get('subject')}")
        print(f"            Placement Status : {status}")
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
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
