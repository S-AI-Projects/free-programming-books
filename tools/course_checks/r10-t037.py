#!/usr/bin/env python3
"""
R10-T037: Failure classification checker for courses/free-courses-km.md

Distinguishes: 200/success, 404/missing, 429/rate-limited, HEAD-405-then-GET-200,
DNS failure, and timeout — using GET fallback where HEAD is unsupported.

Usage:
    python3 tools/course_checks/r10-t037.py              # run full check, write results.json
    python3 tools/course_checks/r10-t037.py --self-test  # run offline fixture tests only
    python3 tools/course_checks/r10-t037.py --live       # also run live HTTP checks
"""

import re
import sys
import json
import os
import socket
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "courses" / "free-courses-km.md"
WORK_DIR = REPO_ROOT / "work" / "R10-T037"
RESULTS_FILE = WORK_DIR / "results.json"

# Selected entries (line numbers 1-based)
SELECTED_LINES = [13, 18, 19]

# HTTP request settings for live mode
REQUEST_TIMEOUT = 10   # seconds
MAX_CONCURRENCY = 2    # low concurrency

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; free-programming-books-checker/1.0; "
        "+https://github.com/EbookFoundation/free-programming-books)"
    )
}

# ---------------------------------------------------------------------------
# Status labels — the core classification vocabulary
# ---------------------------------------------------------------------------

STATUS_OK = "ok"                    # 200 (or 2xx)
STATUS_NOT_FOUND = "not_found"      # 404
STATUS_RATE_LIMITED = "rate_limited"  # 429
STATUS_FORBIDDEN = "forbidden"      # 403
STATUS_HEAD_UNSUPPORTED = "head_unsupported_get_ok"  # HEAD→405, GET→200
STATUS_DNS_FAIL = "dns_failure"     # socket.gaierror / Name resolution failure
STATUS_TIMEOUT = "timeout"          # requests.Timeout
STATUS_ERROR = "error"              # any other unexpected error
STATUS_SKIPPED = "skipped"          # not checked (offline mode)

# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(
    r"^\*\s+\[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\)"
    r"(?:\s+-\s+(?P<author>[^(\n]+))?"
    r"(?:\s*\((?P<fmt>[^)]+)\))?"
    r"(?P<notes>.*)$"
)


def parse_entries(text: str) -> list[dict]:
    """Parse all course entries from markdown text. Skip fenced code blocks."""
    entries = []
    in_fence = False
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if re.match(r"^(`{3,}|~{3,})", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = ENTRY_RE.match(line)
        if not m:
            continue
        entries.append({
            "lineno": lineno,
            "title": m.group("title").strip(),
            "url": m.group("url").strip(),
            "author": (m.group("author") or "").strip(),
            "format": (m.group("fmt") or "").strip(),
            "notes": (m.group("notes") or "").strip(),
            "status": STATUS_SKIPPED,
            "status_detail": "",
        })
    return entries


# ---------------------------------------------------------------------------
# HTTP classification (live mode only)
# ---------------------------------------------------------------------------

def classify_url(url: str) -> tuple[str, str]:
    """
    Probe url and return (status_label, detail).
    Uses HEAD first; falls back to GET if HEAD returns 405.
    Never removes a link solely because a single automated request failed.
    """
    try:
        import urllib.request
        import urllib.error

        req_head = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        try:
            with urllib.request.urlopen(req_head, timeout=REQUEST_TIMEOUT) as resp:
                code = resp.status
                if code == 200:
                    return STATUS_OK, f"HEAD {code}"
                elif code == 429:
                    return STATUS_RATE_LIMITED, f"HEAD {code}"
                elif code == 403:
                    return STATUS_FORBIDDEN, f"HEAD {code}"
                elif code == 404:
                    return STATUS_NOT_FOUND, f"HEAD {code}"
                else:
                    return STATUS_OK, f"HEAD {code}"
        except urllib.error.HTTPError as e:
            if e.code == 405:
                # HEAD not supported — try GET
                req_get = urllib.request.Request(url, headers=HEADERS, method="GET")
                try:
                    with urllib.request.urlopen(req_get, timeout=REQUEST_TIMEOUT) as resp2:
                        code2 = resp2.status
                        if code2 == 200:
                            return STATUS_HEAD_UNSUPPORTED, f"HEAD 405 → GET {code2}"
                        elif code2 == 429:
                            return STATUS_RATE_LIMITED, f"HEAD 405 → GET {code2}"
                        elif code2 == 403:
                            return STATUS_FORBIDDEN, f"HEAD 405 → GET {code2}"
                        elif code2 == 404:
                            return STATUS_NOT_FOUND, f"HEAD 405 → GET {code2}"
                        else:
                            return STATUS_ERROR, f"HEAD 405 → GET {code2}"
                except urllib.error.HTTPError as e2:
                    if e2.code == 429:
                        return STATUS_RATE_LIMITED, f"HEAD 405 → GET {e2.code}"
                    elif e2.code == 403:
                        return STATUS_FORBIDDEN, f"HEAD 405 → GET {e2.code}"
                    elif e2.code == 404:
                        return STATUS_NOT_FOUND, f"HEAD 405 → GET {e2.code}"
                    else:
                        return STATUS_ERROR, f"HEAD 405 → GET HTTP {e2.code}"
                except Exception as ex:
                    return STATUS_ERROR, f"HEAD 405 → GET error: {ex}"
            elif e.code == 429:
                return STATUS_RATE_LIMITED, f"HEAD {e.code}"
            elif e.code == 403:
                return STATUS_FORBIDDEN, f"HEAD {e.code}"
            elif e.code == 404:
                return STATUS_NOT_FOUND, f"HEAD {e.code}"
            else:
                return STATUS_ERROR, f"HEAD HTTP {e.code}"
        except urllib.error.URLError as e:
            reason = str(e.reason)
            # Distinguish DNS vs timeout
            if "timed out" in reason.lower() or isinstance(e.reason, socket.timeout):
                return STATUS_TIMEOUT, f"URLError timeout: {reason}"
            if isinstance(e.reason, socket.gaierror) or "name or service not known" in reason.lower() \
                    or "nodename nor servname" in reason.lower() or "getaddrinfo" in reason.lower():
                return STATUS_DNS_FAIL, f"DNS failure: {reason}"
            return STATUS_ERROR, f"URLError: {reason}"
        except TimeoutError:
            return STATUS_TIMEOUT, "TimeoutError"
        except socket.timeout:
            return STATUS_TIMEOUT, "socket.timeout"
    except Exception as ex:
        return STATUS_ERROR, f"Unexpected: {ex}"


# ---------------------------------------------------------------------------
# Classifier using a mock response (for self-test)
# ---------------------------------------------------------------------------

def _make_mock_response(status_code: int):
    """Return a minimal mock HTTP response object."""
    mock = MagicMock()
    mock.status = status_code
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _make_http_error(code: int):
    import urllib.error
    err = urllib.error.HTTPError(url="http://x", code=code, msg=str(code), hdrs=None, fp=None)
    return err


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    """Run offline fixture tests. Returns 0 on all-pass, 1 on any failure."""
    failures = []
    passed = 0

    def assert_eq(label: str, got, expected):
        nonlocal passed
        if got == expected:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}\n       expected: {expected!r}\n       got:      {got!r}")
            print(f"  FAIL  {label}")
            print(f"         expected: {expected!r}")
            print(f"         got:      {got!r}")

    def assert_true(label: str, value: bool):
        nonlocal passed
        if value:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}  (got False)")
            print(f"  FAIL  {label}  (got False)")

    print("=" * 60)
    print("R10-T037 Self-Test (offline fixture-based)")
    print("=" * 60)

    import urllib.error
    import urllib.request

    # -------------------------------------------------------------------
    # Fixture 1: Malformed row → 0 entries parsed
    # -------------------------------------------------------------------
    print("\n[Fixture 1] Malformed row — no URL")
    result = parse_entries("* [Missing URL entry\n")
    assert_eq("Malformed row: entry count == 0", len(result), 0)

    # -------------------------------------------------------------------
    # Fixture 2: Valid rows parsed correctly
    # -------------------------------------------------------------------
    print("\n[Fixture 2] Valid entries in target file")
    if TARGET_FILE.exists():
        text = TARGET_FILE.read_text(encoding="utf-8")
        all_entries = parse_entries(text)
        selected = [e for e in all_entries if e["lineno"] in SELECTED_LINES]
        assert_eq("Three selected entries found (lines 13, 18, 19)", len(selected), 3)

        e13 = next((e for e in selected if e["lineno"] == 13), None)
        e18 = next((e for e in selected if e["lineno"] == 18), None)
        e19 = next((e for e in selected if e["lineno"] == 19), None)

        assert_true("Line 13 found", e13 is not None)
        if e13:
            assert_eq("Line 13 title", e13["title"], "ចំនេះដឹងទូទៅ")
            assert_eq("Line 13 author", e13["author"], "TFD")
            assert_eq("Line 13 URL", e13["url"],
                      "https://youtube.com/playlist?list=PLB5U9f77LXqL-IC2MAoaKl1tJOuiQZbZQ")

        assert_true("Line 18 found", e18 is not None)
        if e18:
            assert_eq("Line 18 title", e18["title"], "Flutter food ordering app")
            assert_eq("Line 18 author", e18["author"], "Chunlee Thong")
            assert_eq("Line 18 URL", e18["url"],
                      "https://youtube.com/playlist?list=PL9nDNu0HsFZk6qC7nfhdYbnB-B9wyfKV9")

        assert_true("Line 19 found", e19 is not None)
        if e19:
            assert_eq("Line 19 title", e19["title"], "Flutter UI Speed Code")
            assert_eq("Line 19 author", e19["author"], "Sopheaman Van")
            assert_eq("Line 19 URL", e19["url"],
                      "https://youtube.com/playlist?list=PLVY9IbkulBUiKDrT5BFcMKXxtk4b0IJIX")
    else:
        failures.append(f"FAIL  Target file not found: {TARGET_FILE}")
        print(f"  FAIL  Target file not found: {TARGET_FILE}")

    # -------------------------------------------------------------------
    # Fixture 3: Simulated 200 → STATUS_OK
    # -------------------------------------------------------------------
    print("\n[Fixture 3] Simulated HTTP 200 → 'ok'")
    mock_resp_200 = _make_mock_response(200)
    with patch("urllib.request.urlopen", return_value=mock_resp_200):
        status, detail = classify_url("https://example.com/ok")
    assert_eq("HTTP 200 → STATUS_OK", status, STATUS_OK)
    assert_true("HTTP 200 detail contains '200'", "200" in detail)

    # -------------------------------------------------------------------
    # Fixture 4: Simulated 404 → STATUS_NOT_FOUND
    # -------------------------------------------------------------------
    print("\n[Fixture 4] Simulated HTTP 404 → 'not_found'")
    with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
        status, detail = classify_url("https://example.com/missing")
    assert_eq("HTTP 404 → STATUS_NOT_FOUND", status, STATUS_NOT_FOUND)

    # -------------------------------------------------------------------
    # Fixture 5: Simulated 429 → STATUS_RATE_LIMITED
    # -------------------------------------------------------------------
    print("\n[Fixture 5] Simulated HTTP 429 → 'rate_limited'")
    with patch("urllib.request.urlopen", side_effect=_make_http_error(429)):
        status, detail = classify_url("https://example.com/ratelimited")
    assert_eq("HTTP 429 → STATUS_RATE_LIMITED", status, STATUS_RATE_LIMITED)

    # -------------------------------------------------------------------
    # Fixture 6: HEAD 405 → GET 200 → STATUS_HEAD_UNSUPPORTED
    # -------------------------------------------------------------------
    print("\n[Fixture 6] HEAD 405 then GET 200 → 'head_unsupported_get_ok'")
    head_error = _make_http_error(405)
    get_resp_200 = _make_mock_response(200)
    call_count = [0]

    def side_effect_405_then_200(req, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise head_error
        return get_resp_200

    with patch("urllib.request.urlopen", side_effect=side_effect_405_then_200):
        status, detail = classify_url("https://example.com/head-unsupported")
    assert_eq("HEAD 405 → GET 200 → STATUS_HEAD_UNSUPPORTED", status, STATUS_HEAD_UNSUPPORTED)
    assert_true("Detail mentions '405'", "405" in detail)
    assert_true("Detail mentions '200'", "200" in detail)

    # -------------------------------------------------------------------
    # Fixture 7: DNS failure → STATUS_DNS_FAIL
    # -------------------------------------------------------------------
    print("\n[Fixture 7] DNS failure → 'dns_failure'")
    dns_error = urllib.error.URLError(
        socket.gaierror(8, "nodename nor servname provided, or not known")
    )
    with patch("urllib.request.urlopen", side_effect=dns_error):
        status, detail = classify_url("https://nonexistent.invalid/page")
    assert_eq("DNS failure → STATUS_DNS_FAIL", status, STATUS_DNS_FAIL)

    # -------------------------------------------------------------------
    # Fixture 8: Timeout → STATUS_TIMEOUT
    # -------------------------------------------------------------------
    print("\n[Fixture 8] Timeout → 'timeout'")
    timeout_error = urllib.error.URLError(socket.timeout("timed out"))
    with patch("urllib.request.urlopen", side_effect=timeout_error):
        status, detail = classify_url("https://example.com/slow")
    assert_eq("Timeout → STATUS_TIMEOUT", status, STATUS_TIMEOUT)

    # -------------------------------------------------------------------
    # Fixture 9: Status labels are all distinct
    # -------------------------------------------------------------------
    print("\n[Fixture 9] All status labels are distinct")
    all_labels = [STATUS_OK, STATUS_NOT_FOUND, STATUS_RATE_LIMITED,
                  STATUS_FORBIDDEN, STATUS_HEAD_UNSUPPORTED,
                  STATUS_DNS_FAIL, STATUS_TIMEOUT, STATUS_ERROR, STATUS_SKIPPED]
    assert_eq("All 9 status labels are unique", len(set(all_labels)), len(all_labels))

    # -------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------
    print("\n" + "=" * 60)
    total = passed + len(failures)
    if failures:
        print(f"RESULT: {len(failures)} FAILED / {total} assertions")
        for f in failures:
            print(f"  {f}")
        return 1
    else:
        print(f"RESULT: All {passed} assertions passed.")
        print("All self-tests passed.")
        return 0


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def run_analysis(text: str, live: bool = False) -> dict:
    entries = parse_entries(text)
    selected = [e for e in entries if e["lineno"] in SELECTED_LINES]

    if live:
        print("Running live HTTP checks (low concurrency)...")
        for entry in selected:
            status, detail = classify_url(entry["url"])
            entry["status"] = status
            entry["status_detail"] = detail
            print(f"  Line {entry['lineno']}: {status} — {detail}")
    else:
        # Offline: mark all as skipped
        for entry in selected:
            entry["status"] = STATUS_SKIPPED
            entry["status_detail"] = "offline mode; use --live for HTTP checks"

    # Policy note: rate-limited / timeout entries are NOT recommended for removal
    recommendations = []
    for e in selected:
        if e["status"] == STATUS_NOT_FOUND:
            recommendations.append({
                "lineno": e["lineno"],
                "title": e["title"],
                "url": e["url"],
                "recommendation": "VERIFY MANUALLY before removal — single automated failure is insufficient",
            })

    return {
        "task": "R10-T037",
        "target_file": str(TARGET_FILE.relative_to(REPO_ROOT)),
        "live_mode": live,
        "total_entries": len(entries),
        "selected_entries": selected,
        "recommendations": recommendations,
        "policy": (
            "A link is never removed solely because a single automated request failed. "
            "Rate-limiting (429) and timeouts are NOT indicators of a dead link. "
            "Only manually confirmed missing resources should be removed."
        ),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if "--self-test" in sys.argv:
        sys.exit(self_test())

    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    live = "--live" in sys.argv
    text = TARGET_FILE.read_text(encoding="utf-8")
    report = run_analysis(text, live=live)

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report written to {RESULTS_FILE}")
    print(f"Total entries in file: {report['total_entries']}")
    print(f"Selected entries checked: {len(report['selected_entries'])}")
    for e in report["selected_entries"]:
        print(f"  Line {e['lineno']}: [{e['title']}] → {e['status']} ({e['status_detail']})")
    if report["recommendations"]:
        print(f"\nRecommendations ({len(report['recommendations'])}):")
        for r in report["recommendations"]:
            print(f"  Line {r['lineno']}: {r['recommendation']}")


if __name__ == "__main__":
    main()
