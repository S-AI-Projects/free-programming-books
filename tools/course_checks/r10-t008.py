#!/usr/bin/env python3
r"""
tools/course_checks/r10-t008.py - Formatting and ordering linter for more/free-programming-interactive-tutorials-ru.md
Student: Anshuman Holkar (Task R10-T008)

Features:
- Enforces strict '* ' bullet syntax (flags '-', '+', and multiple spaces).
- Validates section heading hierarchy (no skipped heading levels like ## -> #####).
- Accepts standard catalogue notes (*(:construction: in process)*, (PDF), licenses).
- Rejects spaces between bracket and parenthesis ([Title] (URL)).
- Validates dash spacing only on author separators (avoids false positives on ')-' in titles).
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
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

# Accepts valid catalogue entries including notes like *(...)*, (PDF), (license)
VALID_ENTRY_REGEX = re.compile(
    r'^\*\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://(?:[^\s()]|\([^\s()]*\))+)\)(?:\s+-\s+(?P<author>[^(]+?))?(?:\s*\((?P<extra>[^)]+)\))*(?:\s*\*(?P<note>[^*]+)\*)?\s*$'
)

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T008] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

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
    last_heading_level = 0

    if not os.path.exists(file_path):
        return valid_entries, errors

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue

            # Section heading
            if stripped.startswith("#"):
                m_hash = re.match(r'^(#+)\s*(.*)', stripped)
                if m_hash:
                    hashes = m_hash.group(1)
                    level = len(hashes)
                    heading_text = m_hash.group(2).strip()
                    clean_heading = re.sub(r'<[^>]+>', '', heading_text).strip()

                    # Check heading hierarchy (skip index from level check)
                    if clean_heading.lower() != "index":
                        if last_heading_level > 0 and level > last_heading_level + 1:
                            errors.append({
                                "line": line_num,
                                "raw": stripped,
                                "error": f"SKIPPED_HEADING_LEVEL: jumped from level {last_heading_level} to {level}"
                            })
                        last_heading_level = level

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

            # Check bullet lines
            if stripped.startswith(("*", "-", "+")) or "[" in stripped:
                # Enforce strict '*' bullet (reject '-' or '+')
                if stripped.startswith(("- ", "+ ", "-[", "+[")):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "IMPROPER_BULLET_SYNTAX: Must use '*' bullet"
                    })
                    continue

                # Check multiple spaces after '*' (e.g. '*  [')
                if re.match(r'^\*\s{2,}\[', stripped):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "IMPROPER_BULLET_SPACING: Multiple spaces after bullet"
                    })
                    continue

                # Check missing space after bullet
                if stripped.startswith("*["):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "MISSING_SPACE_AFTER_BULLET"
                    })
                    continue

                # Check space between bracket and parenthesis: [Title] (URL)
                if re.search(r'\[[^\]]+\]\s+\(https?://', stripped):
                    errors.append({
                        "line": line_num,
                        "raw": stripped,
                        "error": "SPACE_BETWEEN_BRACKET_AND_PARENTHESIS"
                    })
                    continue

                # Check improper dash spacing between link and author: ](url)-author
                # Only check after the closing parenthesis of URL
                if re.search(r'\)(?:-[^\s]|[^\s]-)', stripped) and not re.search(r'\([^\)]*-[^\)]*\)', stripped):
                    # verify it is actually outside the link
                    m_link = re.search(r'\]\([^\)]+\)', stripped)
                    if m_link and (stripped[m_link.end():m_link.end()+2] == '- ' or stripped[m_link.end():m_link.end()+1] == '-'):
                        errors.append({
                            "line": line_num,
                            "raw": stripped,
                            "error": "IMPROPER_DASH_SPACING"
                        })
                        continue

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
                            # Compare if same script
                            if (prev_title[0].isascii() and title[0].isascii()) or (not prev_title[0].isascii() and not title[0].isascii()):
                                # Standard case-insensitive sorting
                                if prev_title.lower().replace("-", " ") > title.lower().replace("-", " "):
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
    Works under python3 -O.
    """
    print("[R10-T008] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T008/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T008/fixtures"

    # Assertion 1: Valid fixture parses cleanly with 0 formatting errors
    valid_file = os.path.join(fixtures_dir, "fixture_valid.md")
    valid_entries, valid_errors = check_formatting(valid_file)
    check(len(valid_errors) == 0, f"Valid fixture produced unexpected errors: {valid_errors}")
    check(len(valid_entries) == 3, f"Expected 3 valid entries, got {len(valid_entries)}")
    print("  ✓ Assertion 1 passed: Valid fixture with Cyrillic text passed formatting checks cleanly.")

    # Assertion 2: Malformed fixture identifies errors with source lines
    malformed_file = os.path.join(fixtures_dir, "fixture_malformed.md")
    _, malformed_errors = check_formatting(malformed_file)
    check(len(malformed_errors) >= 4, f"Expected at least 4 errors in malformed fixture, found: {len(malformed_errors)}")

    error_types = [e["error"] for e in malformed_errors]
    check(any("SPACE_BETWEEN_BRACKET" in err for err in error_types), "Failed to detect space between bracket and parenthesis")
    check(any("IMPROPER_DASH" in err for err in error_types), "Failed to detect improper dash spacing")
    check(any("MISSING_SPACE_AFTER_BULLET" in err for err in error_types), "Failed to detect missing bullet space")
    check(any("OUT_OF_ORDER" in err for err in error_types), "Failed to detect alphabetical ordering violation")
    print("  ✓ Assertion 2 passed: All malformed syntax cases identified with exact source lines.")

    # Assertion 3: Heading hierarchy violation detection
    probe_hierarchy = "## Heading 2\n##### Heading 5\n* [A](https://example.com) - Author\n"
    tmp_path = "/tmp/probe_hierarchy.md"
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(probe_hierarchy)
    _, h_errors = check_formatting(tmp_path)
    check(any("SKIPPED_HEADING_LEVEL" in e["error"] for e in h_errors), "Failed to detect skipped heading level")
    print("  ✓ Assertion 3 passed: Skipped heading levels (## -> #####) correctly detected.")

    # Assertion 4: Standard catalogue note *(:construction: in process)* accepted as valid
    note_line = "* [Gamma](https://example.com/gamma) - G *(:construction: in process)*\n"
    tmp_note = "/tmp/probe_note.md"
    with open(tmp_note, "w", encoding="utf-8") as f:
        f.write("### Section\n" + note_line)
    n_entries, n_errors = check_formatting(tmp_note)
    check(len(n_entries) == 1, "Standard catalogue note was not accepted")
    check(len(n_errors) == 0, f"Standard catalogue note triggered false errors: {n_errors}")
    print("  ✓ Assertion 4 passed: Standard in-construction note correctly parsed as valid.")

    # Assertion 5: Title containing ')-' not flagged as improper dash spacing
    paren_dash = "* [C (lang)-guide](https://example.com/c) - Dennis Ritchie\n"
    tmp_dash = "/tmp/probe_dash.md"
    with open(tmp_dash, "w", encoding="utf-8") as f:
        f.write("### Section\n" + paren_dash)
    d_entries, d_errors = check_formatting(tmp_dash)
    check(len(d_entries) == 1, "Entry with ')-' in title failed parsing")
    check(len(d_errors) == 0, f"Dash inside title wrongly flagged: {d_errors}")
    print("  ✓ Assertion 5 passed: Title with internal dash not falsely flagged.")

    # Assertion 6: Real file entries mapping against expected_selected.json
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries, real_errors = check_formatting(repo_file)
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
        check(e["section"] == exp["section"], f"Section mismatch: expected '{exp['section']}', got '{e['section']}'")
    print("  ✓ Assertion 6 passed: Selected entries map to source lines (14, 15, 20) matching expected_selected.json.")

    print("[R10-T008] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
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
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
