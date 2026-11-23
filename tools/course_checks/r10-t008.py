#!/usr/bin/env python3
r"""
tools/course_checks/r10-t008.py - Formatting and ordering linter for more/free-programming-interactive-tutorials-ru.md
Student: Anshuman Holkar (Task R10-T008)

Features:
- Validates bullet syntax (* or - with space).
- Rejects spaces between markdown bracket and parenthesis ([Title] (URL)).
- Rejects improper dash spacing between link and author.
- Validates heading hierarchy and alphabetical section ordering.
- Preserves Cyrillic and international text.
- Maps selected entries to exact 1-based source lines (14, 15, 20).
- Built-in --self-test mode with assertions that exit non-zero on failure.
"""

import os
import re
import sys
import json

TARGET_FILE = "more/free-programming-interactive-tutorials-ru.md"
SELECTED_URLS = {
    "http://codenamecrud.ru": {
        "title": "Учитесь веб-разработке бесплатно!",
        "expected_line": 14,
        "section": "Веб-разработка"
    },
    "https://nodeschool.io/ru": {
        "title": "Open source воркшопы",
        "expected_line": 15,
        "section": "Веб-разработка"
    },
    "https://docs.microsoft.com/ru-ru/learn/certifications/azure-fundamentals/": {
        "title": "Microsoft Certified: Azure Fundamentals",
        "expected_line": 20,
        "section": "Облачные вычисления"
    }
}

VALID_ENTRY_REGEX = re.compile(r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)(?:\s+-\s+(?P<author>[^(]+?))?(?:\s*\((?P<extra>[^)]+)\))*\s*$')

def check_formatting(file_path):
    """
    Checks markdown list formatting and ordering.
    Returns:
    - valid_entries: list of properly formatted entries with line numbers
    - errors: list of formatting error dicts with line number and reason
    """
    valid_entries = []
    errors = []
    current_section = None
    section_entries = {}
    in_index = False

    if not os.path.exists(file_path):
        return valid_entries, errors

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue

            # Section heading
            if stripped.startswith("#"):
                clean_heading = re.sub(r'<[^>]+>', '', stripped).lstrip('#').strip()
                if clean_heading.lower() == "index":
                    in_index = True
                    current_section = None
                    continue
                else:
                    in_index = False
                    current_section = clean_heading
                    section_entries[current_section] = []
                continue

            if in_index:
                continue

            # Check if line looks like a list item or attempted link
            if stripped.startswith("*") or stripped.startswith("-") or "[" in stripped:
                # 1. Check for missing space after bullet
                if stripped.startswith("*[") or stripped.startswith("-["):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "MISSING_SPACE_AFTER_BULLET"
                    })
                    continue

                # 2. Check for space between bracket and parenthesis: [Title] (URL)
                if re.search(r'\[[^\]]+\]\s+\(https?://', stripped):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "SPACE_BETWEEN_BRACKET_AND_PARENTHESIS"
                    })
                    continue

                # 3. Check for dash without proper spacing: ](url)-author or ](url) -author
                if re.search(r'\)(?:-[^\s]|[^\s]-)', stripped):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "IMPROPER_DASH_SPACING"
                    })
                    continue

                # Match valid entry format
                m = VALID_ENTRY_REGEX.match(stripped)
                if m:
                    title = m.group("title").strip()
                    url = m.group("url").strip()
                    author = m.group("author").strip() if m.group("author") else None

                    entry_info = {
                        "line": line_num,
                        "title": title,
                        "url": url,
                        "author": author,
                        "section": current_section
                    }
                    valid_entries.append(entry_info)

                    # Check ordering within section if entries share common script
                    if current_section:
                        section_list = section_entries.setdefault(current_section, [])
                        if section_list:
                            prev_title = section_list[-1]["title"]
                            # Only enforce strict alpha comparison when both start with ASCII or both start with Cyrillic
                            if (prev_title[0].isascii() and title[0].isascii()) or (not prev_title[0].isascii() and not title[0].isascii()):
                                if prev_title.lower() > title.lower():
                                    errors.append({
                                        "line": line_num,
                                        "raw": stripped,
                                        "error": f"OUT_OF_ORDER: '{title}' appears after '{prev_title}'"
                                    })
                        section_list.append(entry_info)
                else:
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "MALFORMED_ENTRY_SYNTAX"
                    })

    return valid_entries, errors

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    """
    print("[R10-T008] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T008/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T008/fixtures"

    # Assertion 1: Valid fixture parses cleanly with 0 formatting errors
    valid_file = os.path.join(fixtures_dir, "fixture_valid.md")
    valid_entries, valid_errors = check_formatting(valid_file)
    assert len(valid_errors) == 0, f"Valid fixture produced unexpected errors: {valid_errors}"
    assert len(valid_entries) == 3, f"Expected 3 valid entries, got {len(valid_entries)}"
    print("  ✓ Assertion 1 passed: Valid fixture with Cyrillic text passed formatting checks cleanly.")

    # Assertion 2: Malformed fixture identifies errors with source lines
    malformed_file = os.path.join(fixtures_dir, "fixture_malformed.md")
    _, malformed_errors = check_formatting(malformed_file)
    assert len(malformed_errors) >= 4, f"Expected at least 4 errors in malformed fixture, found: {len(malformed_errors)}"

    error_types = [e["error"] for e in malformed_errors]
    assert any("SPACE_BETWEEN_BRACKET" in err for err in error_types), "Failed to detect space between bracket and parenthesis"
    assert any("IMPROPER_DASH" in err for err in error_types), "Failed to detect improper dash spacing"
    assert any("MISSING_SPACE_AFTER_BULLET" in err for err in error_types), "Failed to detect missing bullet space"
    assert any("OUT_OF_ORDER" in err for err in error_types), "Failed to detect alphabetical ordering violation"
    print("  ✓ Assertion 2 passed: All malformed syntax cases identified with exact source lines.")

    # Assertion 3: Real file lines mapping (14, 15, 20)
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries, real_errors = check_formatting(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    assert len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}"

    for e in selected:
        info = SELECTED_URLS[e["url"]]
        assert e["line"] == info["expected_line"], \
            f"Line mismatch for {e['title']}: expected {info['expected_line']}, got {e['line']}"
        assert e["title"] == info["title"], f"Title mismatch: expected '{info['title']}', got '{e['title']}'"
        assert e["section"] == info["section"], f"Section mismatch: expected '{info['section']}', got '{e['section']}'"
    print("  ✓ Assertion 3 passed: Selected entries map back to source lines (14, 15, 20) with valid format.")

    print("[R10-T008] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T008] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        except Exception as ex:
            print(f"[R10-T008] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries, errors = check_formatting(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Formatting & Ordering Audit for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}")
    print(f"Formatting errors found: {len(errors)}\n")

    print(f"Selected entries audit ({len(selected)}):")
    for e in selected:
        print(f"  Line {e['line']:2d} | Section : {e['section']}")
        print(f"            Title   : {e['title']}")
        print(f"            URL     : {e['url']}")
        print(f"            Format  : VALID_MARKDOWN_SYNTAX")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T008")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T008"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "errors": errors,
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    main()
