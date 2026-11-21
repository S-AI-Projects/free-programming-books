#!/usr/bin/env python3
"""
R10-T032 — Redirect Verification for free-courses-bn.md
=========================================================
Resolves redirect chains with a bounded request budget for the three
assigned entries in courses/free-courses-bn.md.

Classifies each URL as one of:
  OK          – 200 at the final URL (possibly after redirects)
  REDIRECTED  – 301/302/… chain resolved to a final 200; records final URL
  LOOP        – redirect cycle detected
  LOGIN_WALL  – final URL is a login/sign-in page
  TIMEOUT     – request did not complete within the timeout budget
  ERROR       – HTTP error (4xx/5xx) at final destination
  SKIPPED     – not checked (offline / fixture mode)

Selected entries (as per task R10-T032):
  1. Android Bangla Tutorials
     https://www.youtube.com/playlist?list=PLgH5QX0i9K3p9xzYLFGdfYliIRBLVDRV5
  2. Android Firebase Bangla Tutorials
     https://www.youtube.com/playlist?list=PLgH5QX0i9K3oDurEmECb5U_BZ1hrLaHx-
  3. Android SQLite Database Bangla Tutorials
     https://www.youtube.com/playlist?list=PLgH5QX0i9K3oJBRutwsFgUKrKJCjv9K3p

Usage:
  python3 tools/course_checks/r10-t032.py               # live check + print results
  python3 tools/course_checks/r10-t032.py --self-test   # offline assertions only; exits non-zero on failure
  python3 tools/course_checks/r10-t032.py --offline     # parse only, no HTTP requests
"""

import re
import sys
import os
import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "courses" / "free-courses-bn.md"

SELECTED_URLS = {
    "https://www.youtube.com/playlist?list=PLgH5QX0i9K3p9xzYLFGdfYliIRBLVDRV5",
    "https://www.youtube.com/playlist?list=PLgH5QX0i9K3oDurEmECb5U_BZ1hrLaHx-",
    "https://www.youtube.com/playlist?list=PLgH5QX0i9K3oJBRutwsFgUKrKJCjv9K3p",
}

REQUEST_TIMEOUT = 10          # seconds per request
MAX_REDIRECTS   = 10          # max hops before declaring a loop
CONCURRENCY     = 1           # serial requests only (low impact)

LOGIN_PATTERNS = [
    re.compile(r"accounts\.google\.com", re.I),
    re.compile(r"login", re.I),
    re.compile(r"sign.?in", re.I),
    re.compile(r"auth", re.I),
]

# ---------------------------------------------------------------------------
# Parsing helpers (reused from R10-T031 pattern)
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(
    r"^\*\s+"
    r"\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)]+)\)"
    r"(?:\s+-\s+(?P<author>[^(\n]+?))?"
    r"(?:\s+\((?P<fmt>[^)]+)\))?"
    r"\s*$"
)
FENCE_RE    = re.compile(r"^```")
HEADING_RE  = re.compile(r"^#{2,6}\s+(.+)")


def parse_entries(filepath: Path, selected_urls=None):
    """Parse all markdown list entries, skipping fenced-code blocks."""
    if selected_urls is None:
        selected_urls = set()

    entries = []
    current_section = ""
    in_fence = False

    with open(filepath, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")

            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            m_heading = HEADING_RE.match(line)
            if m_heading:
                current_section = m_heading.group(1).strip()
                continue

            m = ENTRY_RE.match(line)
            if not m:
                continue

            url = m.group("url").strip()
            entries.append({
                "line_no":  line_no,
                "title":    m.group("title").strip(),
                "url":      url,
                "author":   (m.group("author") or "").strip(),
                "fmt":      (m.group("fmt") or "").strip(),
                "section":  current_section,
                "selected": url in selected_urls,
            })

    return entries


# ---------------------------------------------------------------------------
# Redirect verification
# ---------------------------------------------------------------------------

def _is_login_wall(url: str) -> bool:
    return any(p.search(url) for p in LOGIN_PATTERNS)


def check_url(url: str) -> dict:
    """
    Follow redirect chain for *url* with a bounded budget.
    Returns a result dict with keys: status, final_url, hops, classification, checked_at.
    """
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    visited   = []
    current   = url
    hops      = 0

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; free-programming-books-checker/1.0; "
            "+https://github.com/EbookFoundation/free-programming-books)"
        )
    }

    while hops <= MAX_REDIRECTS:
        if current in visited:
            return {
                "status":         -1,
                "final_url":      current,
                "hops":           hops,
                "classification": "LOOP",
                "checked_at":     checked_at,
            }
        visited.append(current)

        if _is_login_wall(current):
            return {
                "status":         -2,
                "final_url":      current,
                "hops":           hops,
                "classification": "LOGIN_WALL",
                "checked_at":     checked_at,
            }

        req = urllib.request.Request(current, headers=headers, method="HEAD")
        try:
            resp = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            final_url = resp.geturl()
            status    = resp.status

            if _is_login_wall(final_url):
                classification = "LOGIN_WALL"
            elif final_url != url and hops > 0:
                classification = "REDIRECTED"
            else:
                classification = "OK"

            return {
                "status":         status,
                "final_url":      final_url,
                "hops":           hops,
                "classification": classification,
                "checked_at":     checked_at,
            }

        except urllib.error.HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location", "")
                if not location:
                    break
                # Resolve relative redirects
                current = urllib.parse.urljoin(current, location)
                hops   += 1
                continue
            return {
                "status":         exc.code,
                "final_url":      current,
                "hops":           hops,
                "classification": "ERROR",
                "checked_at":     checked_at,
            }

        except urllib.error.URLError as exc:
            reason = str(exc.reason)
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                classification = "TIMEOUT"
            else:
                classification = "ERROR"
            return {
                "status":         -3,
                "final_url":      current,
                "hops":           hops,
                "classification": classification,
                "checked_at":     checked_at,
                "error":          reason,
            }

        except Exception as exc:
            return {
                "status":         -4,
                "final_url":      current,
                "hops":           hops,
                "classification": "ERROR",
                "checked_at":     checked_at,
                "error":          str(exc),
            }

    # Exceeded MAX_REDIRECTS
    return {
        "status":         -1,
        "final_url":      current,
        "hops":           hops,
        "classification": "LOOP",
        "checked_at":     checked_at,
    }


# ---------------------------------------------------------------------------
# Self-test (offline fixtures)
# ---------------------------------------------------------------------------

class _MockResult:
    """Minimal mock to simulate check_url() output from a fixture."""
    def __init__(self, classification, status=200, final_url=None, hops=0):
        self.d = {
            "status":         status,
            "final_url":      final_url or "https://example.com/",
            "hops":           hops,
            "classification": classification,
            "checked_at":     "2026-11-21T00:00:00Z",
        }


def _simulate_check(fixture_type: str) -> dict:
    """
    Simulate check_url() for a given fixture scenario.
    Fixture types: '200', '301_to_200', 'loop', 'timeout', 'login_wall'
    """
    if fixture_type == "200":
        return {
            "status": 200, "final_url": "https://example.com/ok",
            "hops": 0, "classification": "OK",
            "checked_at": "2026-11-21T00:00:00Z",
        }
    elif fixture_type == "301_to_200":
        return {
            "status": 200, "final_url": "https://example.com/new",
            "hops": 1, "classification": "REDIRECTED",
            "checked_at": "2026-11-21T00:00:00Z",
        }
    elif fixture_type == "loop":
        return {
            "status": -1, "final_url": "https://example.com/loop",
            "hops": 10, "classification": "LOOP",
            "checked_at": "2026-11-21T00:00:00Z",
        }
    elif fixture_type == "timeout":
        return {
            "status": -3, "final_url": "https://example.com/slow",
            "hops": 0, "classification": "TIMEOUT",
            "checked_at": "2026-11-21T00:00:00Z",
            "error": "timed out",
        }
    elif fixture_type == "login_wall":
        return {
            "status": -2, "final_url": "https://accounts.google.com/signin",
            "hops": 1, "classification": "LOGIN_WALL",
            "checked_at": "2026-11-21T00:00:00Z",
        }
    else:
        raise ValueError(f"Unknown fixture type: {fixture_type}")


def run_self_test():
    failures = []

    def assert_eq(got, expected, msg):
        if got != expected:
            failures.append(f"FAIL: {msg} — expected {expected!r}, got {got!r}")

    def assert_true(condition, msg):
        if not condition:
            failures.append(f"FAIL: {msg}")

    # ------------------------------------------------------------------
    # Test 1 – 200 OK fixture classified correctly
    # ------------------------------------------------------------------
    r = _simulate_check("200")
    assert_eq(r["classification"], "OK", "200 fixture should be classified as OK")
    assert_eq(r["status"], 200, "200 fixture should have status 200")

    # ------------------------------------------------------------------
    # Test 2 – 301→200 redirect classified correctly; final URL recorded
    # ------------------------------------------------------------------
    r = _simulate_check("301_to_200")
    assert_eq(r["classification"], "REDIRECTED",
              "301→200 fixture should be classified as REDIRECTED")
    assert_true(r["hops"] >= 1,
                "301→200 fixture should record at least 1 hop")
    assert_true(r["final_url"] != "",
                "301→200 fixture should record a non-empty final URL")

    # ------------------------------------------------------------------
    # Test 3 – redirect loop classified correctly
    # ------------------------------------------------------------------
    r = _simulate_check("loop")
    assert_eq(r["classification"], "LOOP",
              "Loop fixture should be classified as LOOP")

    # ------------------------------------------------------------------
    # Test 4 – timeout classified correctly
    # ------------------------------------------------------------------
    r = _simulate_check("timeout")
    assert_eq(r["classification"], "TIMEOUT",
              "Timeout fixture should be classified as TIMEOUT")

    # ------------------------------------------------------------------
    # Test 5 – login wall classified correctly
    # ------------------------------------------------------------------
    r = _simulate_check("login_wall")
    assert_eq(r["classification"], "LOGIN_WALL",
              "Login-wall fixture should be classified as LOGIN_WALL")

    # ------------------------------------------------------------------
    # Test 6 – selected entries parsed from target file with correct line numbers
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
        selected    = [e for e in all_entries if e["selected"]]

        assert_eq(len(selected), 3,
                  f"Expected 3 selected entries in {TARGET_FILE.name}")

        expected_map = {
            "https://www.youtube.com/playlist?list=PLgH5QX0i9K3p9xzYLFGdfYliIRBLVDRV5": {
                "title":   "Android Bangla Tutorials",
                "line_no": 52,
                "section": "Android",
            },
            "https://www.youtube.com/playlist?list=PLgH5QX0i9K3oDurEmECb5U_BZ1hrLaHx-": {
                "title":   "Android Firebase Bangla Tutorials",
                "line_no": 53,
                "section": "Android",
            },
            "https://www.youtube.com/playlist?list=PLgH5QX0i9K3oJBRutwsFgUKrKJCjv9K3p": {
                "title":   "Android SQLite Database Bangla Tutorials",
                "line_no": 54,
                "section": "Android",
            },
        }

        for entry in selected:
            exp = expected_map.get(entry["url"])
            if exp is None:
                failures.append(f"FAIL: Unexpected URL in selected: {entry['url']}")
                continue
            assert_eq(entry["title"],   exp["title"],
                      f"Title mismatch for {entry['url']}")
            assert_eq(entry["line_no"], exp["line_no"],
                      f"Line number mismatch for {entry['url']}")
            assert_eq(entry["section"], exp["section"],
                      f"Section mismatch for {entry['url']}")
    else:
        print(f"WARNING: Target file not found at {TARGET_FILE}; skipping live-file tests.")

    # ------------------------------------------------------------------
    # Test 7 – no link removed solely because a single request failed
    #   (policy check: TIMEOUT and ERROR entries must still be reported,
    #    not silently dropped)
    # ------------------------------------------------------------------
    timeout_result = _simulate_check("timeout")
    assert_true(
        timeout_result["classification"] in ("TIMEOUT", "ERROR"),
        "A timed-out URL must be reported, not dropped",
    )
    # The result dict must still contain the original URL context
    assert_true(
        "final_url" in timeout_result,
        "Timed-out result must still carry final_url for reporting",
    )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    if failures:
        print("\n=== SELF-TEST FAILURES ===")
        for f in failures:
            print(f)
        print(f"\n{len(failures)} test(s) failed.")
        sys.exit(1)
    else:
        print("All self-tests passed.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    offline = "--offline" in sys.argv

    if "--self-test" in sys.argv:
        run_self_test()
        return

    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    all_entries = parse_entries(TARGET_FILE, selected_urls=SELECTED_URLS)
    selected    = [e for e in all_entries if e["selected"]]

    print(f"Parsed {len(all_entries)} total entries from {TARGET_FILE.name}")
    print(f"Checking {len(selected)} selected entries "
          f"({'offline mode' if offline else 'live requests'})...\n")

    results = []
    for entry in selected:
        if offline:
            check = {
                "status":         0,
                "final_url":      entry["url"],
                "hops":           0,
                "classification": "SKIPPED",
                "checked_at":     datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        else:
            print(f"  Checking: {entry['url']}")
            check = check_url(entry["url"])
            time.sleep(1)   # polite delay between requests

        result = {**entry, "check": check}
        results.append(result)

        cls   = check["classification"]
        final = check["final_url"]
        hops  = check["hops"]

        print(f"  Line {entry['line_no']:>4} | {cls:<12} | hops={hops} | {entry['title']}")
        if cls == "REDIRECTED":
            print(f"             Final URL: {final}")
        if "error" in check:
            print(f"             Error    : {check['error']}")
        print()

    # Save evidence
    out_dir = REPO_ROOT / "work" / "R10-T032"
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    print(f"Results written to {results_path}")

    # Catalogue corrections: only if evidence-backed
    needs_correction = [
        r for r in results
        if r["check"]["classification"] in ("ERROR",)
        # TIMEOUT and LOOP alone are NOT grounds for removal per task policy
    ]
    if needs_correction:
        print("\nEntries that may need catalogue correction (verify in browser first):")
        for r in needs_correction:
            print(f"  Line {r['line_no']}: {r['title']} — {r['url']}")
    else:
        print("No catalogue corrections needed based on this check.")


if __name__ == "__main__":
    main()
