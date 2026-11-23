#!/usr/bin/env python3
"""
tools/course_checks/r10-t005.py - Metadata verification for courses/free-courses-ta.md
Student: Anshuman Holkar (Task R10-T005)

Features:
- Validates the required fields stored by this catalogue: title, url, author, category.
- Detects missing required fields (e.g. missing author, title, url).
- Generates an evidence table comparing source URL, observed metadata, and proposed values.
- Retains exact 1-based source line numbers.
- Built-in --self-test mode with assertions that exit non-zero on failure.
"""

import os
import re
import sys
import json

TARGET_FILE = "courses/free-courses-ta.md"
SELECTED_URLS = {
    "https://www.youtube.com/playlist?list=PLLHRrAfRqTbPbodOKyV6QeEOMx8KaBiSm": {
        "title": "AI Tutorials in Tamil",
        "author": "Endless Knowledge",
        "category": "AI",
        "expected_line": 35
    },
    "https://www.youtube.com/playlist?list=PLMn73l82HB5B9oMtKeAexWVdXLRL_BChV": {
        "title": "Artificial Intelligence Course for Beginners in Tamil",
        "author": "Hope Artificial Intelligence",
        "category": "AI",
        "expected_line": 36
    },
    "https://youtube.com/playlist?list=PL4unWLKFsZfcGBja19mrwodNm6AyzZk2B": {
        "title": "Android In Tamil 2019",
        "author": "Tutor Joe's Stanley",
        "category": "Android",
        "expected_line": 41
    }
}

REQUIRED_FIELDS = ["title", "url", "author", "category"]

def validate_entry(entry):
    """
    Validates that all required fields are present and non-empty.
    Returns (is_valid, missing_fields)
    """
    missing = []
    for field in REQUIRED_FIELDS:
        val = entry.get(field)
        if not val or not str(val).strip():
            missing.append(field)
    return (len(missing) == 0, missing)

def parse_markdown(file_path):
    """
    Parses course list entries: * [Title](URL) - Author
    Tracks section heading as category and records 1-based line numbers.
    """
    entries = []
    current_category = None

    if not os.path.exists(file_path):
        return entries

    entry_pattern = re.compile(r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)(?:\s*-\s*(?P<author>.+))?')

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()

            if stripped.startswith("#"):
                clean_heading = re.sub(r'<[^>]+>', '', stripped).lstrip('#').strip()
                if clean_heading and clean_heading.lower() != "index":
                    current_category = clean_heading
                continue

            m = entry_pattern.match(stripped)
            if m:
                title = m.group("title").strip()
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

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    """
    print("[R10-T005] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T005/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T005/fixtures"

    # Assertion 1: Valid fixture passes validation with 0 missing fields
    with open(os.path.join(fixtures_dir, "fixture_valid.json"), "r", encoding="utf-8") as f:
        valid_data = json.load(f)
    for entry in valid_data:
        ok, missing = validate_entry(entry)
        assert ok, f"Valid fixture failed validation: {entry['title']} missing {missing}"
    print("  ✓ Assertion 1 passed: Valid fixture entries satisfy all required metadata fields.")

    # Assertion 2: Fixture with missing required fields fails validation
    with open(os.path.join(fixtures_dir, "fixture_missing_field.json"), "r", encoding="utf-8") as f:
        missing_data = json.load(f)
    for entry in missing_data:
        ok, missing = validate_entry(entry)
        assert not ok, f"Fixture entry with missing field unexpectedly passed: {entry}"
        assert len(missing) > 0, "Missing fields list should not be empty"
    print("  ✓ Assertion 2 passed: Fixtures with missing required fields correctly failed validation.")

    # Assertion 3: Real target file selected entries line numbers and metadata match
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_markdown(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    assert len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}"

    for e in selected:
        expected = SELECTED_URLS[e["url"]]
        assert e["line"] == expected["expected_line"], \
            f"Line mismatch for {e['title']}: expected {expected['expected_line']}, got {e['line']}"
        assert e["title"] == expected["title"], f"Title mismatch: {e['title']}"
        assert e["author"] == expected["author"], f"Author mismatch: {e['author']}"
        assert e["category"] == expected["category"], f"Category mismatch: {e['category']}"
        ok, missing = validate_entry(e)
        assert ok, f"Real entry missing fields: {missing}"
    print("  ✓ Assertion 3 passed: All selected entries map to exact source lines (35, 36, 41) with complete metadata.")

    print("[R10-T005] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T005] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        except Exception as ex:
            print(f"[R10-T005] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Metadata Verification Report for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}\n")

    print("Evidence Table (Stored fields vs Verified documentation):")
    print("-" * 105)
    print(f"{'Line':<5} | {'Field':<10} | {'Observed Value':<32} | {'Proposed Value':<32} | {'Status':<10}")
    print("-" * 105)

    evidence_table = []
    for e in selected:
        exp = SELECTED_URLS[e["url"]]
        for field in ["title", "author", "category", "url"]:
            obs_val = e.get(field, "")
            prop_val = exp.get(field, obs_val) if field != "url" else e["url"]
            match = obs_val == prop_val
            status = "CONFIRMED" if match else "PROPOSED_CHANGE"
            evidence_table.append({
                "line": e["line"],
                "url": e["url"],
                "field": field,
                "observed": obs_val,
                "proposed": prop_val,
                "status": status
            })
            print(f"{e['line']:<5} | {field:<10} | {obs_val:<32} | {prop_val:<32} | {status:<10}")
        print("-" * 105)

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T005")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T005"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "evidence_table": evidence_table,
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSaved results to {out_file}")

if __name__ == "__main__":
    main()
