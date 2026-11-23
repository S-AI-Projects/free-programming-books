#!/usr/bin/env python3
"""
tools/course_checks/r10-t001.py - Structured parser for casts/free-podcasts-screencasts-es.md
Student: Anshuman Holkar (Task R10-T001)

Features:
- Extracts display name, URL, category, author, and format while preserving exact 1-based source line numbers.
- Supports balanced parentheses in URLs (e.g. Wikipedia links).
- Collects and reports malformed bullet lines with line numbers.
- Ignores links inside fenced code blocks (``` and ~~~).
- Preserves full URLs including fragments (#...).
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
"""

import os
import re
import sys
import json

TARGET_FILE = "casts/free-podcasts-screencasts-es.md"
SELECTED_URLS = {
    "https://www.youtube.com/playlist?list=PLzSFZWTjelbJ01UciHPAWTqUFWesoGr9A": "Conceptos fundamentales: Bases de datos relacionales",
    "https://open.spotify.com/show/0aikWOJmQMglEmbmbHqv4q": "BigDateame",
    "https://podcasts.apple.com/es/podcast/data-futurology-espa%C3%B1ol/id1523527265": "DataFuturologyEspanol"
}

# Regex for markdown bullet entries with balanced URL parentheses support:
# * [Title](URL) - Author (Format) *(Note)*
ENTRY_PATTERN = re.compile(
    r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://(?:[^\s()]|\([^\s()]*\))+)\)(?:\s*-\s*(?P<author>[^(]+?))?(?:\s*\((?P<format>[^)]+)\))?(?:\s*\*(?P<note>[^*]+)\*)?\s*$'
)

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T001] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

def parse_markdown(file_path):
    """
    Parses a markdown list file, returning a list of parsed entry dicts.
    Fenced code blocks (``` and ~~~) are ignored.
    Category is tracked from headings. Source line numbers are 1-based.
    Malformed bullet lines are collected into entries_errors attribute.
    """
    entries = []
    errors = []
    current_category = "General"
    in_code_block = False

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()

            # Handle fenced code block toggles (``` or ~~~)
            if stripped.startswith("```") or stripped.startswith("~~~"):
                in_code_block = not in_code_block
                continue

            if in_code_block:
                continue

            # Track section headings
            if stripped.startswith("#"):
                heading_match = re.search(r'^#+\s+(?:<a[^>]*>)?\s*(.+?)(?:</a>)?$', stripped)
                if heading_match:
                    heading_text = heading_match.group(1).strip()
                    # Skip top-level Index section
                    if heading_text.lower() != "index":
                        current_category = heading_text
                continue

            # Match entry
            match = ENTRY_PATTERN.match(stripped)
            if match:
                title = match.group("title").strip()
                url = match.group("url").strip()
                author = match.group("author").strip() if match.group("author") else None
                fmt = match.group("format").strip() if match.group("format") else None
                note = match.group("note").strip() if match.group("note") else None

                entries.append({
                    "line": line_num,
                    "title": title,
                    "url": url,
                    "category": current_category,
                    "author": author,
                    "format": fmt,
                    "note": note
                })
            elif re.match(r'^\s*[*+-]\s+', stripped) and "[" in stripped and "]" in stripped:
                # Malformed bullet line
                errors.append({
                    "line": line_num,
                    "raw": stripped,
                    "error": "MALFORMED_ENTRY_SYNTAX"
                })

    parse_markdown.last_errors = errors
    return entries

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    Works under python3 -O.
    """
    print("[R10-T001] Running self-test suite...")

    # Test 1: Test fixture with code block, fragment URL, and Wikipedia URL with parens
    fixture_path = os.path.join(os.path.dirname(__file__), "../../work/R10-T001/fixtures/success_cases.md")
    if not os.path.exists(fixture_path):
        fixture_path = "work/R10-T001/fixtures/success_cases.md"
    
    check(os.path.exists(fixture_path), f"Fixture not found: {fixture_path}")
    parsed_fixture = parse_markdown(fixture_path)

    # Assertion 1: Fenced code block link MUST be ignored
    fake_links = [e for e in parsed_fixture if "fake.example.com" in e["url"]]
    check(len(fake_links) == 0, f"Fake link inside fenced code block was not ignored: {fake_links}")
    print("  ✓ Assertion 1 passed: Fenced-code fake link was correctly ignored.")

    # Assertion 2: URL containing a fragment (#...) MUST be preserved
    fragment_entries = [e for e in parsed_fixture if "#episode12" in e["url"]]
    check(len(fragment_entries) == 1, "URL fragment was not preserved.")
    check(fragment_entries[0]["url"] == "https://example.com/podcast#episode12",
          f"URL mismatch: {fragment_entries[0]['url']}")
    print("  ✓ Assertion 2 passed: URL containing fragment was preserved accurately.")

    # Assertion 3: Real file parsing and selected entries comparison with expected_selected.json
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)
    check(os.path.exists(repo_file), f"Target file not found: {repo_file}")

    real_entries = parse_markdown(repo_file)
    selected_found = [e for e in real_entries if e["url"] in SELECTED_URLS]
    check(len(selected_found) == 3, f"Expected 3 selected entries, found {len(selected_found)}")

    # Load and verify field-by-field against expected_selected.json
    expected_path = os.path.join(os.path.dirname(__file__), "../../work/R10-T001/fixtures/expected_selected.json")
    if not os.path.exists(expected_path):
        expected_path = "work/R10-T001/fixtures/expected_selected.json"
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["url"]: item for item in expected_list}

    for entry in selected_found:
        exp = expected_map.get(entry["url"])
        check(exp is not None, f"Unexpected selected URL: {entry['url']}")
        check(entry["line"] == exp["line"], f"Line mismatch for {entry['title']}: expected {exp['line']}, got {entry['line']}")
        check(entry["title"] == exp["title"], f"Title mismatch: expected {exp['title']}, got {entry['title']}")
        check(entry["category"] == exp["category"], f"Category mismatch: expected {exp['category']}, got {entry['category']}")
        check(entry["author"] == exp["author"], f"Author mismatch: expected {exp['author']}, got {entry['author']}")
        check(entry["format"] == exp["format"], f"Format mismatch: expected {exp['format']}, got {entry['format']}")
    print("  ✓ Assertion 3 passed: All 3 selected real entries match expected_selected.json field-by-field (lines 15, 20, 21).")

    # Assertion 4: Negative test - verify malformed lines are reported and produce 0 valid false positives
    fail_fixture = os.path.join(os.path.dirname(__file__), "../../work/R10-T001/fixtures/failure_cases.md")
    if not os.path.exists(fail_fixture):
        fail_fixture = "work/R10-T001/fixtures/failure_cases.md"
    parsed_fail = parse_markdown(fail_fixture)
    check(len(parsed_fail) == 0, f"Expected 0 entries from failure fixture, got {len(parsed_fail)}")
    check(len(parse_markdown.last_errors) > 0, "Expected malformed lines to be recorded in errors list")
    print(f"  ✓ Assertion 4 passed: Malformed syntax correctly flagged ({len(parse_markdown.last_errors)} errors detected, 0 false positive entries).")

    # Assertion 5: URL with balanced parentheses (e.g. Wikipedia entry) parses cleanly
    test_line = "* [C Language](https://en.wikipedia.org/wiki/C_(programming_language)) - Dennis Ritchie (screencast)"
    m = ENTRY_PATTERN.match(test_line)
    check(m is not None, "Failed to parse URL with balanced parentheses")
    check(m.group("url") == "https://en.wikipedia.org/wiki/C_(programming_language)", "URL with parens truncated")
    print("  ✓ Assertion 5 passed: URL containing balanced parentheses parses without truncation.")

    print("[R10-T001] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T001] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    # Standard run mode: parse real catalogue file
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Parsed {len(entries)} total entries from {TARGET_FILE}")
    print(f"Selected entries ({len(selected)}):\n")

    for e in selected:
        print(f"  Line {e['line']:4d} | Category: {e['category']}")
        print(f"             Title   : {e['title']}")
        print(f"             URL     : {e['url']}")
        print(f"             Author  : {e['author']}")
        print(f"             Format  : {e['format']}")
        if e['note']:
            print(f"             Note    : {e['note']}")
        print()

    # Save results to work/R10-T001/results.json
    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T001")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T001"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"total_parsed": len(entries), "selected": selected}, f, indent=2, ensure_ascii=False)
    
    # Print repo-relative path
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
