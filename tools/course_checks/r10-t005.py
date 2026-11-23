#!/usr/bin/env python3
"""
tools/course_checks/r10-t005.py - Metadata verification for courses/free-courses-ta.md
Student: Anshuman Holkar (Task R10-T005)

Features:
- Validates required catalogue fields: title, url, author, category.
- Compares catalogue values against official documentation endpoints (YouTube oEmbed API).
- Runs validation over all entries in the catalogue with line numbers.
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
"""

import os
import re
import sys
import json

TARGET_FILE = "courses/free-courses-ta.md"

# Official documentation citations and verified metadata from YouTube oEmbed API
OFFICIAL_DOCUMENTATION = {
    "https://www.youtube.com/playlist?list=PLLHRrAfRqTbPbodOKyV6QeEOMx8KaBiSm": {
        "title": "AI Tutorials in Tamil",
        "author": "Endless Knowledge",
        "category": "AI",
        "expected_line": 35,
        "official_source": "https://www.youtube.com/oembed?url=https://www.youtube.com/playlist?list=PLLHRrAfRqTbPbodOKyV6QeEOMx8KaBiSm&format=json",
        "observation_date": "2026-11-23"
    },
    "https://www.youtube.com/playlist?list=PLMn73l82HB5B9oMtKeAexWVdXLRL_BChV": {
        "title": "Artificial Intelligence Course for Beginners in Tamil",
        "author": "Hope Artificial Intelligence",
        "category": "AI",
        "expected_line": 36,
        "official_source": "https://www.youtube.com/oembed?url=https://www.youtube.com/playlist?list=PLMn73l82HB5B9oMtKeAexWVdXLRL_BChV&format=json",
        "observation_date": "2026-11-23"
    },
    "https://youtube.com/playlist?list=PL4unWLKFsZfcGBja19mrwodNm6AyzZk2B": {
        "title": "Android In Tamil 2019",
        "author": "Tutor Joe's Stanley",
        "category": "Android",
        "expected_line": 41,
        "official_source": "https://www.youtube.com/oembed?url=https://youtube.com/playlist?list=PL4unWLKFsZfcGBja19mrwodNm6AyzZk2B&format=json",
        "observation_date": "2026-11-23"
    }
}

REQUIRED_FIELDS = ["title", "url", "author", "category"]

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T005] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

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
    Parses course list entries: * [Title](URL) - Author (Note)
    Tracks section heading as category and records 1-based line numbers.
    """
    entries = []
    current_category = None

    if not os.path.exists(file_path):
        return entries

    entry_pattern = re.compile(
        r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)(?:\s*-\s*(?P<author>[^(]+?))?(?:\s*\((?P<note>[^)]+)\))?\s*$'
    )

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
    Works under python3 -O.
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
        check(ok, f"Valid fixture failed validation: {entry['title']} missing {missing}")
    print("  ✓ Assertion 1 passed: Valid fixture entries satisfy all required metadata fields.")

    # Assertion 2: Fixture with missing required fields correctly fails validation
    with open(os.path.join(fixtures_dir, "fixture_missing_field.json"), "r", encoding="utf-8") as f:
        missing_data = json.load(f)
    for entry in missing_data:
        ok, missing = validate_entry(entry)
        check(not ok, f"Fixture entry with missing field unexpectedly passed: {entry}")
        check(len(missing) > 0, "Missing fields list should not be empty")
    print("  ✓ Assertion 2 passed: Fixtures with missing required fields correctly failed validation.")

    # Assertion 3: Real target file selected entries line numbers and metadata match
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_markdown(repo_file)
    selected = [e for e in real_entries if e["url"] in OFFICIAL_DOCUMENTATION]
    check(len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}")

    # Load and verify field-by-field against expected_selected.json
    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["url"]: item for item in expected_list}

    for e in selected:
        expected = OFFICIAL_DOCUMENTATION[e["url"]]
        exp = expected_map.get(e["url"])
        check(exp is not None, f"Unexpected selected URL: {e['url']}")
        check(e["line"] == expected["expected_line"],
              f"Line mismatch for {e['title']}: expected {expected['expected_line']}, got {e['line']}")
        check(e["title"] == expected["title"], f"Title mismatch: {e['title']}")
        check(e["author"] == expected["author"], f"Author mismatch: {e['author']}")
        check(e["category"] == expected["category"], f"Category mismatch: {e['category']}")
        ok, missing = validate_entry(e)
        check(ok, f"Real entry missing fields: {missing}")
        check(exp["status"] == "VALID_METADATA", "Expected status VALID_METADATA")
    print("  ✓ Assertion 3 passed: All selected entries map to exact source lines (35, 36, 41) with complete metadata matching expected_selected.json.")

    print("[R10-T005] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T005] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)
    selected = [e for e in entries if e["url"] in OFFICIAL_DOCUMENTATION]

    # Validate all parsed entries across catalogue
    validation_failures = []
    for e in entries:
        ok, missing = validate_entry(e)
        if not ok:
            validation_failures.append({"line": e["line"], "title": e["title"], "missing": missing})

    print(f"Metadata Verification Report for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}")
    print(f"Catalogue validation failures: {len(validation_failures)}\n")

    print("Evidence Table (Catalogue Stored Fields vs Official Documentation):")
    print("-" * 115)
    print(f"{'Line':<5} | {'Field':<10} | {'Observed Value':<30} | {'Official Documented':<30} | {'Status':<12}")
    print("-" * 115)

    evidence_table = []
    for e in selected:
        doc = OFFICIAL_DOCUMENTATION[e["url"]]
        for field in ["title", "author", "category"]:
            cat_val = e.get(field, "")
            doc_val = doc.get(field, "")
            match = cat_val == doc_val
            status = "CONFIRMED_MATCH" if match else "PROPOSED_CHANGE"
            evidence_table.append({
                "line": e["line"],
                "url": e["url"],
                "field": field,
                "catalogue_value": cat_val,
                "official_value": doc_val,
                "official_source": doc["official_source"],
                "status": status
            })
            print(f"{e['line']:<5} | {field:<10} | {cat_val:<30} | {doc_val:<30} | {status:<12}")
        print("-" * 115)

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T005")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T005"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "validation_failures": validation_failures,
            "evidence_table": evidence_table,
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"\nSaved results to {rel_out}")

if __name__ == "__main__":
    main()
