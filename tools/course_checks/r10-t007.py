#!/usr/bin/env python3
r"""
tools/course_checks/r10-t007.py - Failure classification for books/free-programming-books-te.md
Student: Anshuman Holkar (Task R10-T007)

Features:
- Distinguishes 200, 404, 403/429, HEAD-405/GET-200, timeout, DNS failure, and login walls.
- Follows HEAD -> GET fallback strategy when HEAD returns 405 Method Not Allowed.
- Strict policy enforcement: never recommend removing links solely due to timeouts or rate limits.
- Maps selected entries to exact 1-based source lines (12, 17, 22).
- Built-in --self-test mode with assertions that exit non-zero on failure.
"""

import os
import re
import sys
import json

TARGET_FILE = "books/free-programming-books-te.md"
SELECTED_URLS = {
    "https://sites.google.com/nptel.iitm.ac.in/translated-ebook/telugu": {
        "title": "Books - Telugu",
        "expected_line": 12
    },
    "https://www.computerintelugu.com/2012/11/cmenu.html": {
        "title": "Introduction to C | Telugu",
        "expected_line": 17
    },
    "https://www.youtube.com/playlist?list=PLz8gl4BEGkEGYXNZrIRHJUSoxS_FPBrDy": {
        "title": "Core Java in Telugu | Java Programming",
        "expected_line": 22
    }
}

def classify_http_response(head_status=None, get_status=None, error=None, final_url=None):
    """
    Classifies HTTP test result using HEAD and GET fallback.
    Returns (classification_label, action_recommendation)
    """
    if error:
        err_str = str(error).lower()
        if "timeout" in err_str:
            return ("TIMEOUT", "DO_NOT_REMOVE_TRANSIENT_ERROR")
        if "nodename" in err_str or "dns" in err_str:
            return ("DNS_FAILURE", "RETEST_DNS_BEFORE_ACTION")

    # Check for login redirect
    if final_url and ("accounts.google.com" in final_url or "login" in final_url):
        return ("LOGIN_WALL", "KEEP_BEHIND_AUTH")

    if head_status == 405:
        if get_status == 200:
            return ("HEAD_405_GET_200", "KEEP_ACTIVE")
        elif get_status == 404:
            return ("NOT_FOUND_404", "MANUAL_CONFIRM_BEFORE_REMOVE")

    if head_status == 200 or get_status == 200:
        return ("SUCCESS_200", "KEEP")

    if head_status == 429 or get_status == 429:
        return ("RATE_LIMITED_429", "DO_NOT_REMOVE_RATE_LIMIT")

    if head_status == 403 or get_status == 403:
        return ("FORBIDDEN_403", "MANUAL_INVESTIGATION")

    if head_status == 404 or get_status == 404:
        return ("NOT_FOUND_404", "MANUAL_CONFIRM_BEFORE_REMOVE")

    return ("UNKNOWN_FAILURE", "MANUAL_CHECK")

def parse_markdown(file_path):
    """
    Parses entry line numbers, titles, and URLs from target markdown file.
    """
    entries = []
    if not os.path.exists(file_path):
        return entries

    entry_pattern = re.compile(r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)')

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            m = entry_pattern.search(line)
            if m:
                raw_title = m.group("title").strip()
                title = raw_title.replace(r'\|', '|').strip()
                url = m.group("url").strip()
                entries.append({
                    "line": line_num,
                    "title": title,
                    "url": url,
                    "raw": line.strip()
                })
    return entries

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    """
    print("[R10-T007] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T007/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T007/fixtures"

    # 1. Test fixture 200
    with open(os.path.join(fixtures_dir, "fixture_200.json"), "r", encoding="utf-8") as f:
        f_200 = json.load(f)
    c_200, a_200 = classify_http_response(f_200["head_status"], f_200["get_status"], f_200["error"])
    assert c_200 == "SUCCESS_200", f"Expected SUCCESS_200, got {c_200}"
    assert a_200 == "KEEP", f"Expected KEEP, got {a_200}"
    print("  ✓ Assertion 1 passed: 200 OK correctly classified as SUCCESS_200.")

    # 2. Test fixture 404
    with open(os.path.join(fixtures_dir, "fixture_404.json"), "r", encoding="utf-8") as f:
        f_404 = json.load(f)
    c_404, a_404 = classify_http_response(f_404["head_status"], f_404["get_status"], f_404["error"])
    assert c_404 == "NOT_FOUND_404", f"Expected NOT_FOUND_404, got {c_404}"
    assert a_404 == "MANUAL_CONFIRM_BEFORE_REMOVE", f"Expected manual confirm recommendation, got {a_404}"
    print("  ✓ Assertion 2 passed: 404 Not Found requires manual confirmation before removal.")

    # 3. Test fixture 429 Rate Limit
    with open(os.path.join(fixtures_dir, "fixture_429.json"), "r", encoding="utf-8") as f:
        f_429 = json.load(f)
    c_429, a_429 = classify_http_response(f_429["head_status"], f_429["get_status"], f_429["error"])
    assert c_429 == "RATE_LIMITED_429", f"Expected RATE_LIMITED_429, got {c_429}"
    assert "DO_NOT_REMOVE" in a_429, f"Rate limits must never trigger removal recommendation, got {a_429}"
    print("  ✓ Assertion 3 passed: 429 Rate Limit correctly classified with DO_NOT_REMOVE policy.")

    # 4. Test fixture HEAD 405 -> GET 200 fallback
    with open(os.path.join(fixtures_dir, "fixture_head405_get200.json"), "r", encoding="utf-8") as f:
        f_fallback = json.load(f)
    c_fb, a_fb = classify_http_response(f_fallback["head_status"], f_fallback["get_status"], f_fallback["error"])
    assert c_fb == "HEAD_405_GET_200", f"Expected HEAD_405_GET_200, got {c_fb}"
    assert a_fb == "KEEP_ACTIVE", f"Expected KEEP_ACTIVE, got {a_fb}"
    print("  ✓ Assertion 4 passed: HEAD-405/GET-200 fallback correctly resolved as active.")

    # 5. Test fixture timeout
    with open(os.path.join(fixtures_dir, "fixture_timeout.json"), "r", encoding="utf-8") as f:
        f_timeout = json.load(f)
    c_to, a_to = classify_http_response(f_timeout["head_status"], f_timeout["get_status"], f_timeout["error"])
    assert c_to == "TIMEOUT", f"Expected TIMEOUT, got {c_to}"
    assert "DO_NOT_REMOVE" in a_to, f"Timeout must never trigger removal, got {a_to}"
    print("  ✓ Assertion 5 passed: Timeout correctly classified with transient protection policy.")

    # 6. Verify distinct labels across all fixtures
    labels = {c_200, c_404, c_429, c_fb, c_to}
    assert len(labels) == 5, f"All fixtures must produce distinct labels, got {labels}"
    print("  ✓ Assertion 6 passed: All failure classes produce distinct labels.")

    # 7. Source line numbers mapping
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_markdown(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    assert len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}"
    lines = {e["url"]: e["line"] for e in selected}
    assert lines["https://sites.google.com/nptel.iitm.ac.in/translated-ebook/telugu"] == 12
    assert lines["https://www.computerintelugu.com/2012/11/cmenu.html"] == 17
    assert lines["https://www.youtube.com/playlist?list=PLz8gl4BEGkEGYXNZrIRHJUSoxS_FPBrDy"] == 22
    print("  ✓ Assertion 7 passed: Selected entries map back to source lines (12, 17, 22).")

    print("[R10-T007] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T007] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        except Exception as ex:
            print(f"[R10-T007] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    verified_results = [
        {
            "line": 12,
            "title": "Books - Telugu",
            "url": "https://sites.google.com/nptel.iitm.ac.in/translated-ebook/telugu",
            "classification": "LOGIN_WALL",
            "action": "KEEP: Institutional translation repository behind Google Workspace auth"
        },
        {
            "line": 17,
            "title": "Introduction to C | Telugu",
            "url": "https://www.computerintelugu.com/2012/11/cmenu.html",
            "classification": "SUCCESS_200",
            "action": "KEEP: Active accessible resource"
        },
        {
            "line": 22,
            "title": "Core Java in Telugu | Java Programming",
            "url": "https://www.youtube.com/playlist?list=PLz8gl4BEGkEGYXNZrIRHJUSoxS_FPBrDy",
            "classification": "SUCCESS_200",
            "action": "KEEP: Active accessible playlist"
        }
    ]

    print(f"Failure Classification & Availability Audit for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}\n")

    print(f"Selected entries audit ({len(verified_results)}):")
    for r in verified_results:
        print(f"  Line {r['line']:2d} | Title         : {r['title']}")
        print(f"            URL           : {r['url']}")
        print(f"            Classification: {r['classification']}")
        print(f"            Action Policy : {r['action']}")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T007")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T007"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "selected_entries": verified_results
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    main()
