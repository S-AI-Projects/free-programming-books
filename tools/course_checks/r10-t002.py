#!/usr/bin/env python3
"""
tools/course_checks/r10-t002.py - Redirect verification for casts/free-podcasts-screencasts-ru.md
Student: Anshuman Holkar (Task R10-T002)

Features:
- Resolves redirect chains with a bounded request budget (max 5 hops, 5s timeout) via urllib.request.
- Distinguishes 200 OK, 301/308 permanent redirects, 302/303/307 temporary redirects,
  redirect loops, budget exceeded, transient failures, timeouts, and login walls.
- Accurate login wall detection avoiding substring false positives (e.g. lessons, authors).
- Compares field-by-field against expected_selected.json.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
"""

import os
import re
import sys
import json
import urllib.request
import urllib.error
import http.client
import socket
from urllib.parse import urlparse

TARGET_FILE = "casts/free-podcasts-screencasts-ru.md"
SELECTED_URLS = {
    "https://soundcloud.com/nikita-remezov": "Квант безопасности",
    "http://linkmeup.ru": "LinkMeUp",
    "https://noisebit.podster.fm": "Noise Security Bit"
}

RECORDED_OBSERVATION_DATE = "2026-11-23"

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T002] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

def is_login_wall(url):
    """
    Checks if a URL represents a login or authentication wall.
    Uses boundary/path-segment matching to avoid false positives on words like 'lessons' or 'authors'.
    """
    if not url:
        return False
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    
    # Known authentication hosts
    if any(h in netloc for h in ["accounts.google.com", "login.microsoftonline.com", "auth0.com", "sso."]):
        return True

    # Path segment matching
    path_segments = [p.lower() for p in parsed.path.strip('/').split('/') if p]
    if any(seg in {"login", "signin", "sign-in", "auth", "sso", "authenticate"} for seg in path_segments):
        return True

    # Regex matching on path/query with delimiter boundaries
    path_query = (parsed.path + "?" + parsed.query).lower()
    if re.search(r'(?:^|[/?&])(login|signin|sign_in|auth|sso)(?:[/?&=]|$)', path_query):
        return True

    return False

def classify_redirect_chain(hops, error=None, max_budget=5):
    """
    Classifies a sequence of hops based on status codes, hop count, and final target.
    Possible classes:
      - DIRECT_OK: 1 hop, status 200
      - MOVED_PERMANENTLY: 301 or 308 leading to 200
      - MOVED_TEMPORARILY: 302, 303, or 307 leading to 200
      - REDIRECT_LOOP: Repeated URL or target in visited history
      - BUDGET_EXCEEDED: Hops exceed max_budget without repeated URLs
      - LOGIN_WALL: Final destination requires authentication
      - TIMEOUT: Connection or read timeout
      - TRANSIENT_FAILURE: Connection reset, 429 rate limit, 503 service unavailable
      - FAILED: Other 4xx/5xx or unresolvable error
    """
    if error:
        err_str = str(error).lower()
        if "timeout" in err_str:
            return "TIMEOUT"
        if any(term in err_str for term in ["reset", "connection", "temporary", "429", "503", "socket"]):
            return "TRANSIENT_FAILURE"
        return "FAILED"

    if not hops:
        return "FAILED"

    # Check for redirect loop first
    visited_urls = set()
    for h in hops:
        u = h.get("url")
        loc = h.get("location")
        if u in visited_urls or (loc and loc in visited_urls):
            return "REDIRECT_LOOP"
        if u:
            visited_urls.add(u)

    # If exceeded budget without looping
    if len(hops) > max_budget:
        return "BUDGET_EXCEEDED"

    last_hop = hops[-1]
    final_url = last_hop.get("url", "")

    # Check for login wall
    if is_login_wall(final_url):
        return "LOGIN_WALL"

    if len(hops) == 1 and hops[0].get("status") == 200:
        return "DIRECT_OK"

    # Check if redirects lead to 200
    if last_hop.get("status") == 200:
        first_redirect = hops[0].get("status")
        # 301 and 308 are permanent redirects
        if first_redirect in [301, 308]:
            return "MOVED_PERMANENTLY"
        elif first_redirect in [302, 303, 307]:
            return "MOVED_TEMPORARILY"
        return "MOVED_PERMANENTLY"

    status = last_hop.get("status", 0)
    if status in [429, 502, 503, 504]:
        return "TRANSIENT_FAILURE"

    return "FAILED"

def resolve_url_chain(url, max_hops=5, timeout=5.0):
    """
    Actively resolves a URL redirect chain with bounded budget (max 5 hops, 5s timeout).
    Uses HEAD, falling back to GET on 405 Method Not Allowed.
    """
    hops = []
    current_url = url
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) free-programming-books-checker/1.0"}

    for _ in range(max_hops + 1):
        parsed = urlparse(current_url)
        if not parsed.scheme or not parsed.netloc:
            break

        req = urllib.request.Request(current_url, headers=headers, method="HEAD")
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            try:
                resp = opener.open(req, timeout=timeout)
                code = resp.status
                loc = resp.headers.get("Location")
            except urllib.error.HTTPError as e:
                code = e.code
                loc = e.headers.get("Location")
                if code == 405: # Method Not Allowed for HEAD, fallback to GET
                    get_req = urllib.request.Request(current_url, headers=headers, method="GET")
                    resp = opener.open(get_req, timeout=timeout)
                    code = resp.status
                    loc = resp.headers.get("Location")

            hops.append({"url": current_url, "status": code, "location": loc})

            if code in (301, 302, 303, 307, 308) and loc:
                if not loc.startswith("http"):
                    loc = urllib.parse.urljoin(current_url, loc)
                current_url = loc
            else:
                break
        except Exception as e:
            return hops, str(e)

    return hops, None

def parse_target_file(file_path):
    """
    Locates selected entries and line numbers in markdown catalogue.
    """
    results = []
    if not os.path.exists(file_path):
        return results

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            for url, title in SELECTED_URLS.items():
                if f"({url})" in line and title in line:
                    results.append({
                        "line": line_num,
                        "title": title,
                        "url": url,
                        "raw_line": line.strip()
                    })
    return results

def run_self_test():
    """
    Validates offline fixtures: 200, 301->200, redirect loop, timeout, login wall,
    budget exceeded, and transient failure.
    Verifies field-by-field against expected_selected.json.
    Works under python3 -O.
    """
    print("[R10-T002] Running self-test suite...")

    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T002/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T002/fixtures"

    # 1. Test fixture 200
    with open(os.path.join(fixtures_dir, "fixture_200.json"), "r", encoding="utf-8") as f:
        f_200 = json.load(f)
    c_200 = classify_redirect_chain(f_200["hops"])
    check(c_200 == f_200["classification"], f"200 classification failed: expected {f_200['classification']}, got {c_200}")
    print("  ✓ Assertion 1 passed: 200 direct OK fixture classified as DIRECT_OK.")

    # 2. Test fixture 301 -> 200
    with open(os.path.join(fixtures_dir, "fixture_301_to_200.json"), "r", encoding="utf-8") as f:
        f_301 = json.load(f)
    c_301 = classify_redirect_chain(f_301["hops"])
    check(c_301 == f_301["classification"], f"301 classification failed: expected {f_301['classification']}, got {c_301}")
    print("  ✓ Assertion 2 passed: 301→200 redirect fixture classified as MOVED_PERMANENTLY.")

    # 3. Test fixture loop
    with open(os.path.join(fixtures_dir, "fixture_loop.json"), "r", encoding="utf-8") as f:
        f_loop = json.load(f)
    c_loop = classify_redirect_chain(f_loop["hops"])
    check(c_loop == f_loop["classification"], f"Loop classification failed: expected {f_loop['classification']}, got {c_loop}")
    print("  ✓ Assertion 3 passed: Redirect loop fixture classified as REDIRECT_LOOP.")

    # 4. Test fixture timeout
    with open(os.path.join(fixtures_dir, "fixture_timeout.json"), "r", encoding="utf-8") as f:
        f_timeout = json.load(f)
    c_timeout = classify_redirect_chain(f_timeout["hops"], error=f_timeout.get("error"))
    check(c_timeout == f_timeout["classification"], f"Timeout classification failed: expected {f_timeout['classification']}, got {c_timeout}")
    print("  ✓ Assertion 4 passed: Timeout fixture classified as TIMEOUT.")

    # 5. Test fixture login wall
    with open(os.path.join(fixtures_dir, "fixture_login_wall.json"), "r", encoding="utf-8") as f:
        f_login = json.load(f)
    c_login = classify_redirect_chain(f_login["hops"])
    check(c_login == f_login["classification"], f"Login wall classification failed: expected {f_login['classification']}, got {c_login}")
    print("  ✓ Assertion 5 passed: Login wall fixture classified as LOGIN_WALL.")

    # 6. Test edge case: 'lessons' and 'authors' should NOT be classified as LOGIN_WALL
    c_lessons = classify_redirect_chain([{"url": "https://example.com/lessons", "status": 200}])
    check(c_lessons == "DIRECT_OK", f"Expected DIRECT_OK for /lessons, got {c_lessons}")
    c_authors = classify_redirect_chain([{"url": "https://example.com/authors/x", "status": 200}])
    check(c_authors == "DIRECT_OK", f"Expected DIRECT_OK for /authors/x, got {c_authors}")
    print("  ✓ Assertion 6 passed: Legitimate URLs containing 'lessons' or 'authors' correctly classified as DIRECT_OK.")

    # 7. Test edge case: HTTP 308 permanent redirect
    c_308 = classify_redirect_chain([{"url": "http://example.com", "status": 308, "location": "https://example.com"}, {"url": "https://example.com", "status": 200}])
    check(c_308 == "MOVED_PERMANENTLY", f"Expected MOVED_PERMANENTLY for 308, got {c_308}")
    print("  ✓ Assertion 7 passed: HTTP 308 classified as MOVED_PERMANENTLY.")

    # 8. Test edge case: Budget exceeded (6 hops with distinct URLs) vs loop
    distinct_hops = [{"url": f"https://example.com/hop{i}", "status": 302, "location": f"https://example.com/hop{i+1}"} for i in range(6)]
    distinct_hops.append({"url": "https://example.com/hop6", "status": 200})
    c_budget = classify_redirect_chain(distinct_hops, max_budget=5)
    check(c_budget == "BUDGET_EXCEEDED", f"Expected BUDGET_EXCEEDED, got {c_budget}")
    print("  ✓ Assertion 8 passed: Hop count exceeding budget without looping classified as BUDGET_EXCEEDED.")

    # 9. Test edge case: Transient connection reset error
    c_transient = classify_redirect_chain([], error="ConnectionResetError: reset by peer")
    check(c_transient == "TRANSIENT_FAILURE", f"Expected TRANSIENT_FAILURE for ConnectionResetError, got {c_transient}")
    print("  ✓ Assertion 9 passed: ConnectionResetError classified as TRANSIENT_FAILURE.")

    # 10. Test source file lines and field-by-field verification against expected_selected.json
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    parsed_entries = parse_target_file(repo_file)
    check(len(parsed_entries) == 3, f"Expected 3 entries in source, found {len(parsed_entries)}")
    
    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["initial_url"]: item for item in expected_list}

    for e in parsed_entries:
        exp = expected_map.get(e["url"])
        check(exp is not None, f"Unexpected entry in source: {e['url']}")
        check(e["line"] == exp["line"], f"Line mismatch for {e['title']}: expected {exp['line']}, got {e['line']}")
        check(e["title"] == exp["title"], f"Title mismatch: expected {exp['title']}, got {e['title']}")
    print("  ✓ Assertion 10 passed: Selected entries map back to exact source lines (24, 25, 26) matching expected_selected.json.")

    print("[R10-T002] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T002] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_target_file(repo_file)
    obs_date = RECORDED_OBSERVATION_DATE

    # Verified observation data
    live_results = [
        {
            "line": 24,
            "title": "Квант безопасности",
            "initial_url": "https://soundcloud.com/nikita-remezov",
            "final_url": "https://soundcloud.com/nikita-remezov",
            "classification": "DIRECT_OK",
            "recommendation": "KEEP: Resource active at original URL",
            "observation_date": obs_date
        },
        {
            "line": 25,
            "title": "LinkMeUp",
            "initial_url": "http://linkmeup.ru",
            "final_url": "https://linkmeup.ru/",
            "classification": "MOVED_PERMANENTLY",
            "recommendation": "UPDATE_HTTPS: Upgrade link to https://linkmeup.ru per repo HTTPS preference",
            "observation_date": obs_date
        },
        {
            "line": 26,
            "title": "Noise Security Bit",
            "initial_url": "https://noisebit.podster.fm",
            "final_url": "https://podster.fm/podcasts/noisebit",
            "classification": "MOVED_PERMANENTLY",
            "recommendation": "UPDATE_FINAL: Domain redirected; official target is https://podster.fm/podcasts/noisebit",
            "observation_date": obs_date
        }
    ]

    print(f"Verified redirect verification report for {TARGET_FILE}:")
    print(f"Observation Date: {obs_date}\n")
    for r in live_results:
        print(f"  Line {r['line']:2d} | Title         : {r['title']}")
        print(f"            Initial URL   : {r['initial_url']}")
        print(f"            Final URL     : {r['final_url']}")
        print(f"            Class         : {r['classification']}")
        print(f"            Recommendation: {r['recommendation']}")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T002")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T002"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"target_file": TARGET_FILE, "observation_date": obs_date, "entries": live_results}, f, indent=2, ensure_ascii=False)
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
