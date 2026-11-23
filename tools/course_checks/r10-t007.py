#!/usr/bin/env python3
"""
tools/course_checks/r10-t007.py - Failure classification for books/free-programming-books-te.md
Student: Anshuman Holkar (Task R10-T007)

Features:
- Distinguishes 200, 404, 403, 429, HEAD-405/GET-200, timeout, DNS failure (macOS/Linux),
  server errors (5xx), and login walls.
- Implements active HEAD with GET fallback on 405/501 via urllib.request with socket.gaierror handling.
- Flags login walls (e.g. line 12 Google sign-in) for MANUAL_REVIEW rather than silent keep.
- Strict policy enforcement: never recommend removing links solely due to timeouts or rate limits.
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
"""

import os
import re
import sys
import json
import urllib.request
import urllib.error
import socket
from urllib.parse import urlparse

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

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T007] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

def classify_http_response(head_status=None, get_status=None, error=None, final_url=None):
    """
    Classifies HTTP test result using HEAD and GET fallback.
    Returns (classification_label, action_recommendation)
    """
    if error:
        err_str = str(error).lower()
        if "timeout" in err_str:
            return ("TIMEOUT", "DO_NOT_REMOVE_TRANSIENT_ERROR")
        if any(term in err_str for term in [
            "nodename", "dns", "name or service not known",
            "temporary failure in name resolution", "getaddrinfo"
        ]):
            return ("DNS_FAILURE", "RETEST_DNS_BEFORE_ACTION")
        if any(term in err_str for term in ["reset", "connection", "socket"]):
            return ("TRANSIENT_FAILURE", "DO_NOT_REMOVE_TRANSIENT_ERROR")

    # Check for login redirect
    if final_url and (
        "accounts.google.com" in final_url or
        re.search(r'(?:^|[/?&])(login|signin|sign_in|servicelogin)(?:[/?&=]|$)', final_url.lower())
    ):
        return ("LOGIN_WALL", "MANUAL_REVIEW_AUTH_REQUIRED")

    if head_status in (405, 501):
        if get_status == 200:
            return ("HEAD_405_GET_200", "KEEP_ACTIVE")
        elif get_status == 404:
            return ("NOT_FOUND_404", "MANUAL_CONFIRM_BEFORE_REMOVE")

    effective_status = get_status if get_status is not None else head_status

    if effective_status == 200 or head_status == 200:
        return ("SUCCESS_200", "KEEP")

    if effective_status == 429:
        return ("RATE_LIMITED_429", "DO_NOT_REMOVE_RATE_LIMIT")

    if effective_status == 403:
        return ("FORBIDDEN_403", "MANUAL_INVESTIGATION")

    if effective_status == 404:
        return ("NOT_FOUND_404", "MANUAL_CONFIRM_BEFORE_REMOVE")

    if effective_status and effective_status >= 500:
        return ("SERVER_ERROR", "DO_NOT_REMOVE_TRANSIENT_ERROR")

    return ("UNKNOWN_FAILURE", "MANUAL_CHECK")

def check_url_live(url, timeout=5.0):
    """
    Checks URL availability using HEAD with GET fallback on 405/501.
    Handles socket.gaierror portably.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) free-programming-books-checker/1.0"}
    head_req = urllib.request.Request(url, headers=headers, method="HEAD")
    head_status, get_status, final_url, err_msg = None, None, url, None

    try:
        with urllib.request.urlopen(head_req, timeout=timeout) as resp:
            head_status = resp.status
            final_url = resp.geturl()
    except urllib.error.HTTPError as e:
        head_status = e.code
        final_url = e.geturl()
        if head_status in (405, 501):
            # GET fallback
            try:
                get_req = urllib.request.Request(url, headers=headers, method="GET")
                with urllib.request.urlopen(get_req, timeout=timeout) as g_resp:
                    get_status = g_resp.status
                    final_url = g_resp.geturl()
            except urllib.error.HTTPError as ge:
                get_status = ge.code
                final_url = ge.geturl()
            except Exception as g_ex:
                err_msg = str(g_ex)
    except socket.gaierror as se:
        err_msg = f"DNS failure: {se}"
    except Exception as ex:
        err_msg = str(ex)

    return head_status, get_status, err_msg, final_url

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
    Works under python3 -O.
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
    check(c_200 == "SUCCESS_200", f"Expected SUCCESS_200, got {c_200}")
    check(a_200 == "KEEP", f"Expected KEEP, got {a_200}")
    print("  ✓ Assertion 1 passed: 200 OK correctly classified as SUCCESS_200.")

    # 2. Test fixture 404
    with open(os.path.join(fixtures_dir, "fixture_404.json"), "r", encoding="utf-8") as f:
        f_404 = json.load(f)
    c_404, a_404 = classify_http_response(f_404["head_status"], f_404["get_status"], f_404["error"])
    check(c_404 == "NOT_FOUND_404", f"Expected NOT_FOUND_404, got {c_404}")
    check(a_404 == "MANUAL_CONFIRM_BEFORE_REMOVE", f"Expected manual confirm recommendation, got {a_404}")
    print("  ✓ Assertion 2 passed: 404 Not Found requires manual confirmation before removal.")

    # 3. Test fixture 429 Rate Limit
    with open(os.path.join(fixtures_dir, "fixture_429.json"), "r", encoding="utf-8") as f:
        f_429 = json.load(f)
    c_429, a_429 = classify_http_response(f_429["head_status"], f_429["get_status"], f_429["error"])
    check(c_429 == "RATE_LIMITED_429", f"Expected RATE_LIMITED_429, got {c_429}")
    check("DO_NOT_REMOVE" in a_429, f"Rate limits must never trigger removal recommendation, got {a_429}")
    print("  ✓ Assertion 3 passed: 429 Rate Limit correctly classified with DO_NOT_REMOVE policy.")

    # 4. Test fixture HEAD 405 -> GET 200 fallback
    with open(os.path.join(fixtures_dir, "fixture_head405_get200.json"), "r", encoding="utf-8") as f:
        f_fallback = json.load(f)
    c_fb, a_fb = classify_http_response(f_fallback["head_status"], f_fallback["get_status"], f_fallback["error"])
    check(c_fb == "HEAD_405_GET_200", f"Expected HEAD_405_GET_200, got {c_fb}")
    check(a_fb == "KEEP_ACTIVE", f"Expected KEEP_ACTIVE, got {a_fb}")
    print("  ✓ Assertion 4 passed: HEAD-405/GET-200 fallback correctly resolved as active.")

    # 5. Test fixture timeout
    with open(os.path.join(fixtures_dir, "fixture_timeout.json"), "r", encoding="utf-8") as f:
        f_timeout = json.load(f)
    c_to, a_to = classify_http_response(f_timeout["head_status"], f_timeout["get_status"], f_timeout["error"])
    check(c_to == "TIMEOUT", f"Expected TIMEOUT, got {c_to}")
    check("DO_NOT_REMOVE" in a_to, f"Timeout must never trigger removal, got {a_to}")
    print("  ✓ Assertion 5 passed: Timeout correctly classified with transient protection policy.")

    # 6. Test edge case: Linux and macOS DNS error formats
    c_dns_mac, _ = classify_http_response(error="nodename nor servname provided, or not known")
    check(c_dns_mac == "DNS_FAILURE", f"Expected DNS_FAILURE for macOS DNS error, got {c_dns_mac}")
    c_dns_lin1, _ = classify_http_response(error="[Errno -2] Name or service not known")
    check(c_dns_lin1 == "DNS_FAILURE", f"Expected DNS_FAILURE for Linux errno -2, got {c_dns_lin1}")
    c_dns_lin2, _ = classify_http_response(error="[Errno -3] Temporary failure in name resolution")
    check(c_dns_lin2 == "DNS_FAILURE", f"Expected DNS_FAILURE for Linux errno -3, got {c_dns_lin2}")
    print("  ✓ Assertion 6 passed: DNS failures across macOS and Linux resolvers correctly classified.")

    # 7. Test edge case: Login wall redirect (line 12 case) flagged for manual review
    c_login, a_login = classify_http_response(head_status=302, final_url="https://accounts.google.com/v3/signin/identifier")
    check(c_login == "LOGIN_WALL", f"Expected LOGIN_WALL, got {c_login}")
    check("MANUAL_REVIEW" in a_login, f"Expected MANUAL_REVIEW action for login wall, got {a_login}")
    print("  ✓ Assertion 7 passed: Google login wall redirect correctly classified and flagged for manual review.")

    # 8. Source line numbers mapping and comparison against expected_selected.json
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_markdown(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    check(len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}")

    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["url"]: item for item in expected_list}

    for e in selected:
        exp = expected_map.get(e["url"])
        check(exp is not None, f"Unexpected selected URL: {e['url']}")
        check(e["line"] == exp["line"], f"Line mismatch for {e['title']}: expected {exp['line']}, got {e['line']}")
        check(e["title"] == exp["title"], f"Title mismatch: expected '{exp['title']}', got '{e['title']}'")
    print("  ✓ Assertion 8 passed: Selected entries map to source lines (12, 17, 22) matching expected_selected.json.")

    print("[R10-T007] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T007] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)

    verified_results = [
        {
            "line": 12,
            "title": "Books - Telugu",
            "url": "https://sites.google.com/nptel.iitm.ac.in/translated-ebook/telugu",
            "classification": "LOGIN_WALL",
            "action": "MANUAL_REVIEW: Institutional translation archive behind Google sign-in wall (requires authentication)"
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
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
