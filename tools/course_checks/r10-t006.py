#!/usr/bin/env python3
r"""
tools/course_checks/r10-t006.py - Offline fixture test suite for courses/free-courses-si.md
Student: Anshuman Holkar (Task R10-T006)

Features:
- 100% offline operation: evaluates valid rows, malformed rows, and unusual URL characters entirely from local fixtures.
- Supports balanced parentheses in URLs (e.g. Wikipedia links).
- Collects and reports malformed rows with line numbers.
- Correctly parses Unicode (Sinhala script) and unescapes markdown pipes (\| -> |).
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
"""

import os
import re
import sys
import json

TARGET_FILE = "courses/free-courses-si.md"
SELECTED_URLS = {
    "https://www.youtube.com/playlist?list=PL495mke12zYDIwsabzb61OLdBpg3QDcXg": {
        "title": "Data Structures and Algorithms | Sinhala",
        "author": "CodePRO LK",
        "category": "Algorithms & Data Structures",
        "expected_line": 19
    },
    "https://www.youtube.com/playlist?list=PL495mke12zYBLz2j_RoYbIltaYxvaTd9k": {
        "title": "Deep Learning Tutorial | Sinhala",
        "author": "CodePRO LK",
        "category": "Artificial Intelligence",
        "expected_line": 24
    },
    "https://www.youtube.com/playlist?list=PL495mke12zYDHN9ONfcal1eQfo8VqmOgu": {
        "title": "Machine Learning Tutorial | Sinhala",
        "author": "CodePRO LK",
        "category": "Artificial Intelligence",
        "expected_line": 25
    }
}

ENTRY_PATTERN = re.compile(
    r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://(?:[^\s()]|\([^\s()]*\))+)\)(?:\s*-\s*(?P<author>[^(]+?))?(?:\s*\((?P<note>[^)]+)\))?\s*$'
)

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T006] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

def parse_markdown_content(content):
    r"""
    Parses string or file content of markdown list.
    Unescapes \| in title to |.
    Returns (entries, errors).
    """
    entries = []
    errors = []
    current_category = None

    lines = content.splitlines() if isinstance(content, str) else content

    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith("#"):
            clean_heading = re.sub(r'<[^>]+>', '', stripped).lstrip('#').strip()
            if clean_heading and clean_heading.lower() != "index":
                current_category = clean_heading
            continue

        m = ENTRY_PATTERN.match(stripped)
        if m:
            raw_title = m.group("title").strip()
            title = raw_title.replace(r'\|', '|').strip()
            url = m.group("url").strip()
            author = m.group("author").strip() if m.group("author") else None
            entries.append({
                "line": line_num,
                "title": title,
                "url": url,
                "author": author,
                "category": current_category
            })
        elif re.match(r'^\s*[*+-]\s+', stripped) and "[" in stripped and "]" in stripped:
            errors.append({
                "line": line_num,
                "raw": stripped,
                "error": "MALFORMED_ENTRY_SYNTAX"
            })

    parse_markdown_content.last_errors = errors
    return entries

def parse_file(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return parse_markdown_content(f.readlines())

def run_self_test():
    """
    Runs self-test assertions completely offline. Exits non-zero on any failure.
    Works under python3 -O.
    """
    print("[R10-T006] Running offline self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T006/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T006/fixtures"

    # Assertion 1: Valid fixture parses correctly with Unicode and unescaped pipes
    valid_file = os.path.join(fixtures_dir, "fixture_valid.md")
    valid_entries = parse_file(valid_file)
    check(len(valid_entries) == 4, f"Expected 4 valid entries in fixture, got {len(valid_entries)}")
    pipe_entry = next(e for e in valid_entries if "Data Structures" in e["title"])
    check(pipe_entry["title"] == "Data Structures and Algorithms | Sinhala", f"Pipe unescape failed: {pipe_entry['title']}")
    sinhala_entry = next(e for e in valid_entries if "HTML" in e["title"])
    check("සිංහලෙන්" in sinhala_entry["title"], "Sinhala script unicode handling failed")
    print("  ✓ Assertion 1 passed: Valid rows with Unicode and escaped pipes correctly parsed.")

    # Assertion 2: Malformed fixture reports errors and produces 0 valid false positives
    malformed_file = os.path.join(fixtures_dir, "fixture_malformed.md")
    malformed_entries = parse_file(malformed_file)
    check(len(malformed_entries) == 0, f"Malformed rows should not produce valid entries, got: {malformed_entries}")
    check(len(parse_markdown_content.last_errors) > 0, "Expected malformed lines to be reported in errors list")
    print(f"  ✓ Assertion 2 passed: Malformed rows safely rejected and recorded ({len(parse_markdown_content.last_errors)} errors detected, 0 false positive entries).")

    # Assertion 3: Unusual URL characters (percent-encoding, query params, fragments, balanced parens)
    unusual_file = os.path.join(fixtures_dir, "fixture_unusual_urls.md")
    unusual_entries = parse_file(unusual_file)
    check(len(unusual_entries) >= 3, f"Expected at least 3 unusual URL entries, got {len(unusual_entries)}")
    unusual_urls = [e["url"] for e in unusual_entries]
    check(any("%E0%B7%83%E0%B7%92%E0%B6%82" in u for u in unusual_urls), "Percent-encoded URL missing")
    check(any("feature=shared" in u for u in unusual_urls), "Query params URL missing")
    check(any("#lesson-1" in u for u in unusual_urls), "Fragment URL missing")
    print("  ✓ Assertion 3 passed: Unusual URL characters (percent encoding, query params, fragments) preserved.")

    # Assertion 4: URL containing balanced parentheses parses cleanly
    wiki_line = "* [C Language](https://en.wikipedia.org/wiki/C_(programming_language)) - Dennis Ritchie"
    m = ENTRY_PATTERN.match(wiki_line)
    check(m is not None, "Failed to parse URL containing balanced parentheses")
    check(m.group("url") == "https://en.wikipedia.org/wiki/C_(programming_language)", "URL with parens truncated")
    print("  ✓ Assertion 4 passed: URLs containing balanced parentheses parsed accurately without truncation.")

    # Assertion 5: Target file selected entries map back to source lines and match expected_selected.json
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_file(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    check(len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}")

    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["url"]: item for item in expected_list}

    for e in selected:
        info = SELECTED_URLS[e["url"]]
        exp = expected_map.get(e["url"])
        check(exp is not None, f"Unexpected selected URL: {e['url']}")
        check(e["line"] == exp["line"], f"Line mismatch for {e['title']}: expected {exp['line']}, got {e['line']}")
        check(e["title"] == exp["title"], f"Title mismatch: expected '{exp['title']}', got '{e['title']}'")
        check(e["author"] == exp["author"], f"Author mismatch: expected '{exp['author']}', got '{e['author']}'")
        check(e["category"] == exp["category"], f"Category mismatch: expected '{exp['category']}, got '{e['category']}'")
    print("  ✓ Assertion 5 passed: Selected entries map to source lines (19, 24, 25) with exact metadata matching expected_selected.json.")

    print("[R10-T006] All offline self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T006] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_file(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Offline Validation Report for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}\n")

    print(f"Selected entries audit ({len(selected)}):")
    for e in selected:
        status = "VALID (Offline verified)" if e["title"] and e["url"] else "INVALID"
        print(f"  Line {e['line']:2d} | Category : {e['category']}")
        print(f"            Title    : {e['title']}")
        print(f"            URL      : {e['url']}")
        print(f"            Author   : {e['author']}")
        print(f"            Status   : {status}")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T006")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T006"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
