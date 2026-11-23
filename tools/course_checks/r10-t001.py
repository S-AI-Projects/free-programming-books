#!/usr/bin/env python3
"""
tools/course_checks/r10-t001.py - Structured parser for casts/free-podcasts-screencasts-es.md
Student: Anshuman Holkar (Task R10-T001)

Features:
- Extracts display name, URL, category, author, and format while preserving exact 1-based source line numbers.
- Ignores links inside fenced code blocks (``` ... ```).
- Preserves full URLs including fragments (#...).
- Built-in --self-test mode with assertions that exit non-zero on failure.
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

# Regex for markdown bullet entries: * [Title](URL) - Author (Format) *(Note)*
# Handles variations where author or format might be optional
ENTRY_PATTERN = re.compile(
    r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)(?:\s*-\s*(?P<author>[^(]+?))?(?:\s*\((?P<format>[^)]+)\))?(?:\s*\*(?P<note>[^*]+)\*)?\s*$'
)

def parse_markdown(file_path):
    """
    Parses a markdown list file, returning a list of parsed entry dicts.
    Fenced code blocks are ignored. Category is tracked from headings.
    Source line numbers are 1-based.
    """
    entries = []
    current_category = "General"
    in_code_block = False

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()

            # Handle fenced code block toggles
            if stripped.startswith("```"):
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

    return entries

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    """
    print("[R10-T001] Running self-test suite...")

    # Test 1: Test fixture with code block and fragment URL
    fixture_path = os.path.join(os.path.dirname(__file__), "../../work/R10-T001/fixtures/success_cases.md")
    if not os.path.exists(fixture_path):
        # Fallback if run from repo root
        fixture_path = "work/R10-T001/fixtures/success_cases.md"
    
    assert os.path.exists(fixture_path), f"Fixture not found: {fixture_path}"
    parsed_fixture = parse_markdown(fixture_path)

    # Assertion 1: Fenced code block link MUST be ignored
    fake_links = [e for e in parsed_fixture if "fake.example.com" in e["url"]]
    assert len(fake_links) == 0, f"Assertion failed: Fake link inside fenced code block was not ignored: {fake_links}"
    print("  ✓ Assertion 1 passed: Fenced-code fake link was correctly ignored.")

    # Assertion 2: URL containing a fragment (#...) MUST be preserved
    fragment_entries = [e for e in parsed_fixture if "#episode12" in e["url"]]
    assert len(fragment_entries) == 1, "Assertion failed: URL fragment was not preserved."
    assert fragment_entries[0]["url"] == "https://example.com/podcast#episode12", \
        f"Assertion failed: URL mismatch: {fragment_entries[0]['url']}"
    print("  ✓ Assertion 2 passed: URL containing fragment was preserved accurately.")

    # Assertion 3: Real file parsing and selected entries mapping to source lines
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)
    assert os.path.exists(repo_file), f"Target file not found: {repo_file}"

    real_entries = parse_markdown(repo_file)
    selected_found = [e for e in real_entries if e["url"] in SELECTED_URLS]
    assert len(selected_found) == 3, f"Expected 3 selected entries, found {len(selected_found)}"

    # Check exact line numbers in casts/free-podcasts-screencasts-es.md
    expected_lines = {
        "https://www.youtube.com/playlist?list=PLzSFZWTjelbJ01UciHPAWTqUFWesoGr9A": 15,
        "https://open.spotify.com/show/0aikWOJmQMglEmbmbHqv4q": 20,
        "https://podcasts.apple.com/es/podcast/data-futurology-espa%C3%B1ol/id1523527265": 21
    }

    for entry in selected_found:
        exp_line = expected_lines.get(entry["url"])
        assert entry["line"] == exp_line, f"Line mismatch for {entry['title']}: expected {exp_line}, got {entry['line']}"
        assert entry["category"] in ["Bases de Datos", "Ciencia de Datos"], f"Unexpected category: {entry['category']}"
        assert entry["format"] in ["screencast", "podcast"], f"Unexpected format: {entry['format']}"
    print("  ✓ Assertion 3 passed: All 3 selected real entries map back to their exact source lines (15, 20, 21).")

    # Assertion 4: Negative test - verify malformed lines are rejected or not parsed as valid links
    fail_fixture = os.path.join(os.path.dirname(__file__), "../../work/R10-T001/fixtures/failure_cases.md")
    if not os.path.exists(fail_fixture):
        fail_fixture = "work/R10-T001/fixtures/failure_cases.md"
    parsed_fail = parse_markdown(fail_fixture)
    assert len(parsed_fail) == 0, f"Expected 0 entries from failure fixture, got {len(parsed_fail)}"
    print("  ✓ Assertion 4 passed: Malformed syntax in failure fixture produced 0 false positives.")

    print("[R10-T001] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T001] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
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
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    main()
