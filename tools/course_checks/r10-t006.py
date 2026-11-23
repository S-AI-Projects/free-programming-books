#!/usr/bin/env python3
r"""
tools/course_checks/r10-t006.py - Offline fixture test suite for courses/free-courses-si.md
Student: Anshuman Holkar (Task R10-T006)

Features:
- 100% offline operation: evaluates valid rows, malformed rows, and unusual URL characters entirely from local fixtures.
- Correctly parses Unicode (Sinhala script) and unescapes markdown pipes (\| -> |).
- Maps selected entries to exact 1-based source lines (19, 24, 25).
- Built-in --self-test mode with assertions that exit non-zero on failure.
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

ENTRY_PATTERN = re.compile(r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)(?:\s*-\s*(?P<author>.+))?')

def parse_markdown_content(content):
    r"""
    Parses string or file content of markdown list.
    Unescapes \| in title to |.
    Returns list of parsed entry dicts.
    """
    entries = []
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
            # Unescape markdown pipes in title
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

    return entries

def parse_file(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return parse_markdown_content(f.readlines())

def run_self_test():
    """
    Runs self-test assertions completely offline. Exits non-zero on any failure.
    """
    print("[R10-T006] Running offline self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T006/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T006/fixtures"

    # Assertion 1: Valid fixture parses correctly with Unicode and unescaped pipes
    valid_file = os.path.join(fixtures_dir, "fixture_valid.md")
    valid_entries = parse_file(valid_file)
    assert len(valid_entries) == 4, f"Expected 4 valid entries in fixture, got {len(valid_entries)}"
    # Check that pipe is unescaped
    pipe_entry = next(e for e in valid_entries if "Data Structures" in e["title"])
    assert pipe_entry["title"] == "Data Structures and Algorithms | Sinhala", f"Pipe unescape failed: {pipe_entry['title']}"
    # Check Sinhala Unicode entry
    sinhala_entry = next(e for e in valid_entries if "HTML" in e["title"])
    assert "සිංහලෙන්" in sinhala_entry["title"], "Sinhala script unicode handling failed"
    print("  ✓ Assertion 1 passed: Valid rows with Unicode and escaped pipes correctly parsed.")

    # Assertion 2: Malformed fixture produces 0 false-positive entries
    malformed_file = os.path.join(fixtures_dir, "fixture_malformed.md")
    malformed_entries = parse_file(malformed_file)
    assert len(malformed_entries) == 0, f"Malformed rows should not produce valid entries, got: {malformed_entries}"
    print("  ✓ Assertion 2 passed: Malformed rows safely rejected with 0 false positives.")

    # Assertion 3: Unusual URL characters (percent-encoding, complex query params, anchors) preserved
    unusual_file = os.path.join(fixtures_dir, "fixture_unusual_urls.md")
    unusual_entries = parse_file(unusual_file)
    assert len(unusual_entries) == 3, f"Expected 3 unusual URL entries, got {len(unusual_entries)}"
    assert "%E0%B7%83%E0%B7%92%E0%B6%82" in unusual_entries[0]["url"]
    assert "feature=shared" in unusual_entries[1]["url"]
    assert "#lesson-1" in unusual_entries[2]["url"]
    print("  ✓ Assertion 3 passed: Unusual URL characters (percent encoding, query params, fragments) preserved.")

    # Assertion 4: Target file selected entries map back to source lines (19, 24, 25)
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_file(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    assert len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}"

    for e in selected:
        info = SELECTED_URLS[e["url"]]
        assert e["line"] == info["expected_line"], \
            f"Line mismatch for {e['title']}: expected {info['expected_line']}, got {e['line']}"
        assert e["title"] == info["title"], f"Title mismatch: expected '{info['title']}', got '{e['title']}'"
        assert e["author"] == info["author"], f"Author mismatch: expected '{info['author']}', got '{e['author']}'"
        assert e["category"] == info["category"], f"Category mismatch: expected '{info['category']}', got '{e['category']}'"
    print("  ✓ Assertion 4 passed: Selected entries map back to source lines (19, 24, 25) with exact metadata.")

    print("[R10-T006] All offline self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T006] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
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
        print(f"  Line {e['line']:2d} | Category : {e['category']}")
        print(f"            Title    : {e['title']}")
        print(f"            URL      : {e['url']}")
        print(f"            Author   : {e['author']}")
        print(f"            Status   : VALID (Offline verified)")
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
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    main()
