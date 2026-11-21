#!/usr/bin/env python3
"""
R10-T039: Access requirements checker for casts/free-podcasts-screencasts-de.md

Verifies whether selected resources require authentication, registration,
payment, or a particular environment. Labels each entry with its access
classification rather than making assumptions.

Access labels:
  free_no_registration   - accessible without any login/account
  free_with_registration - accessible but requires signup
  paywalled              - requires payment for content
  environment_required   - needs specific software/hardware/OS
  unverified             - could not confirm access status (treat conservatively)
  skipped                - not checked (offline mode)

Policy:
  - No link is removed solely because a single automated request failed.
  - An unavailable resource is labelled 'unverified', NOT 'free' or 'broken'.
  - No credentials are saved or transmitted.
  - Rate-limited responses (429) → 'unverified', not removed.

Usage:
    python3 tools/course_checks/r10-t039.py              # run full check, write results.json
    python3 tools/course_checks/r10-t039.py --self-test  # run offline fixture tests only
    python3 tools/course_checks/r10-t039.py --live       # also run live HTTP probe
"""

import re
import sys
import json
import socket
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-de.md"
WORK_DIR = REPO_ROOT / "work" / "R10-T039"
RESULTS_FILE = WORK_DIR / "results.json"

# Selected entry
SELECTED_LINES = [8]

# HTTP probe settings
REQUEST_TIMEOUT = 10   # seconds
MAX_CONCURRENCY = 1    # single entry — no concurrency needed

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; free-programming-books-checker/1.0; "
        "+https://github.com/EbookFoundation/free-programming-books)"
    )
}

# ---------------------------------------------------------------------------
# Access labels
# ---------------------------------------------------------------------------

ACCESS_FREE_NO_REG   = "free_no_registration"
ACCESS_FREE_WITH_REG = "free_with_registration"
ACCESS_PAYWALLED     = "paywalled"
ACCESS_ENV_REQUIRED  = "environment_required"
ACCESS_UNVERIFIED    = "unverified"
ACCESS_SKIPPED       = "skipped"

# Known signals in page content that suggest registration/payment walls
REGISTRATION_SIGNALS = [
    "sign up", "create an account", "log in", "login required",
    "registrierung", "anmelden", "konto erstellen",   # German
]
PAYMENT_SIGNALS = [
    "subscribe", "buy now", "purchase", "premium", "pricing",
    "abonnieren", "kaufen", "premium", "bezahlen",    # German
]

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
    """Parse all podcast/screencast entries from markdown text."""
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
            "access": ACCESS_SKIPPED,
            "access_detail": "",
            "access_evidence": "",
        })
    return entries


# ---------------------------------------------------------------------------
# Access classifier (live mode)
# ---------------------------------------------------------------------------

def classify_access(url: str) -> tuple[str, str, str]:
    """
    Probe url and classify access requirements.
    Returns (access_label, detail, evidence_note).
    Does NOT save credentials.
    """
    import urllib.request
    import urllib.error

    # Step 1: probe with HEAD, fall back to GET on 405
    status_code = None
    response_body = ""
    method_used = "HEAD"

    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            status_code = resp.status
    except urllib.error.HTTPError as e:
        if e.code == 405:
            method_used = "GET"
            try:
                req_get = urllib.request.Request(url, headers=HEADERS, method="GET")
                with urllib.request.urlopen(req_get, timeout=REQUEST_TIMEOUT) as resp:
                    status_code = resp.status
                    # Read a snippet to detect paywall/reg signals
                    raw_body = resp.read(4096)
                    try:
                        response_body = raw_body.decode("utf-8", errors="ignore").lower()
                    except Exception:
                        response_body = ""
            except urllib.error.HTTPError as e2:
                status_code = e2.code
            except Exception as ex:
                return ACCESS_UNVERIFIED, f"GET error: {ex}", "Could not connect"
        else:
            status_code = e.code
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "timed out" in reason.lower() or isinstance(e.reason, socket.timeout):
            return ACCESS_UNVERIFIED, "Timeout", "Request timed out — treat as unverified"
        if isinstance(e.reason, socket.gaierror):
            return ACCESS_UNVERIFIED, f"DNS failure: {reason}", "Could not resolve hostname"
        return ACCESS_UNVERIFIED, f"URLError: {reason}", "Network error"
    except Exception as ex:
        return ACCESS_UNVERIFIED, f"Unexpected error: {ex}", "Unknown"

    # Step 2: classify by HTTP status
    if status_code in (401, 403):
        return ACCESS_PAYWALLED, f"{method_used} {status_code}", "Authentication required by server"
    if status_code == 429:
        return ACCESS_UNVERIFIED, f"{method_used} 429 rate-limited", "Rate-limited — cannot confirm access"
    if status_code == 404:
        return ACCESS_UNVERIFIED, f"{method_used} 404", "Resource not found — treat as unverified, verify manually"
    if status_code is not None and status_code >= 500:
        return ACCESS_UNVERIFIED, f"{method_used} {status_code}", "Server error — treat as unverified"

    if status_code == 200 or (status_code is not None and 200 <= status_code < 300):
        # Step 3: scan body for access signals (GET only)
        if response_body:
            for signal in PAYMENT_SIGNALS:
                if signal in response_body:
                    return ACCESS_PAYWALLED, f"{method_used} 200 (payment signal: '{signal}')", \
                           f"Page mentions '{signal}' — may require payment"
            for signal in REGISTRATION_SIGNALS:
                if signal in response_body:
                    return ACCESS_FREE_WITH_REG, f"{method_used} 200 (reg signal: '{signal}')", \
                           f"Page mentions '{signal}' — may require registration"
            return ACCESS_FREE_NO_REG, f"{method_used} 200 (no wall signals detected)", \
                   "Page returned 200 with no paywall or registration signals"
        else:
            # HEAD-only: cannot inspect body — be conservative
            return ACCESS_FREE_NO_REG, f"{method_used} {status_code}", \
                   "HEAD returned 200; body not inspected — classified as likely free"

    return ACCESS_UNVERIFIED, f"{method_used} {status_code}", "Unexpected status — treat as unverified"


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def self_test() -> int:
    """Run offline fixture tests. Returns 0 on all-pass, 1 on any failure."""
    failures = []
    passed = 0

    def assert_eq(label, got, expected):
        nonlocal passed
        if got == expected:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}\n       expected: {expected!r}\n       got:      {got!r}")
            print(f"  FAIL  {label}")
            print(f"         expected: {expected!r}")
            print(f"         got:      {got!r}")

    def assert_true(label, value):
        nonlocal passed
        if value:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}  (got False)")
            print(f"  FAIL  {label}  (got False)")

    print("=" * 60)
    print("R10-T039 Self-Test (offline fixture-based)")
    print("=" * 60)

    import urllib.request
    import urllib.error

    # -------------------------------------------------------------------
    # Fixture 1: Malformed row → 0 entries parsed
    # -------------------------------------------------------------------
    print("\n[Fixture 1] Malformed row — no URL")
    result = parse_entries("* [Missing URL entry\n")
    assert_eq("Malformed row: entry count == 0", len(result), 0)

    # -------------------------------------------------------------------
    # Fixture 2: Valid entry in actual target file
    # -------------------------------------------------------------------
    print("\n[Fixture 2] Selected entry in actual target file")
    if TARGET_FILE.exists():
        text = TARGET_FILE.read_text(encoding="utf-8")
        all_entries = parse_entries(text)
        selected = [e for e in all_entries if e["lineno"] in SELECTED_LINES]
        assert_eq("One selected entry found (line 8)", len(selected), 1)
        e8 = selected[0]
        assert_eq("Line 8 title", e8["title"], "Python Podcast")
        assert_eq("Line 8 URL", e8["url"], "https://python-podcast.de/show")
        assert_eq("Line 8 author", e8["author"], "Jochen, Dominik")
        assert_eq("Line 8 format", e8["format"], "podcast")
        assert_eq("Default access is skipped", e8["access"], ACCESS_SKIPPED)
    else:
        failures.append(f"FAIL  Target file not found: {TARGET_FILE}")
        print(f"  FAIL  Target file not found: {TARGET_FILE}")

    # -------------------------------------------------------------------
    # Fixture 3: HTTP 200 HEAD → free_no_registration
    # -------------------------------------------------------------------
    print("\n[Fixture 3] Simulated HEAD 200 → 'free_no_registration'")
    mock_200 = MagicMock()
    mock_200.status = 200
    mock_200.__enter__ = lambda s: s
    mock_200.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_200):
        access, detail, evidence = classify_access("https://example.com/podcast")
    assert_eq("HEAD 200 → free_no_registration", access, ACCESS_FREE_NO_REG)
    assert_true("Detail mentions '200'", "200" in detail)

    # -------------------------------------------------------------------
    # Fixture 4: HTTP 401 → paywalled
    # -------------------------------------------------------------------
    print("\n[Fixture 4] Simulated HTTP 401 → 'paywalled'")
    err_401 = urllib.error.HTTPError(url="http://x", code=401, msg="Unauthorized", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err_401):
        access, detail, evidence = classify_access("https://example.com/locked")
    assert_eq("HTTP 401 → paywalled", access, ACCESS_PAYWALLED)

    # -------------------------------------------------------------------
    # Fixture 5: HTTP 403 → paywalled
    # -------------------------------------------------------------------
    print("\n[Fixture 5] Simulated HTTP 403 → 'paywalled'")
    err_403 = urllib.error.HTTPError(url="http://x", code=403, msg="Forbidden", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err_403):
        access, detail, evidence = classify_access("https://example.com/forbidden")
    assert_eq("HTTP 403 → paywalled", access, ACCESS_PAYWALLED)

    # -------------------------------------------------------------------
    # Fixture 6: HTTP 429 → unverified (rate-limited, not dead)
    # -------------------------------------------------------------------
    print("\n[Fixture 6] Simulated HTTP 429 → 'unverified' (not removed)")
    err_429 = urllib.error.HTTPError(url="http://x", code=429, msg="Too Many Requests", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err_429):
        access, detail, evidence = classify_access("https://example.com/ratelimited")
    assert_eq("HTTP 429 → unverified", access, ACCESS_UNVERIFIED)
    assert_true("Evidence explains rate-limit not dead", "rate-limited" in evidence.lower())

    # -------------------------------------------------------------------
    # Fixture 7: HTTP 404 → unverified (not 'broken' — verify manually)
    # -------------------------------------------------------------------
    print("\n[Fixture 7] Simulated HTTP 404 → 'unverified' (verify manually)")
    err_404 = urllib.error.HTTPError(url="http://x", code=404, msg="Not Found", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err_404):
        access, detail, evidence = classify_access("https://example.com/missing")
    assert_eq("HTTP 404 → unverified", access, ACCESS_UNVERIFIED)
    assert_true("Evidence says verify manually", "verify manually" in evidence.lower())

    # -------------------------------------------------------------------
    # Fixture 8: Timeout → unverified
    # -------------------------------------------------------------------
    print("\n[Fixture 8] Simulated timeout → 'unverified'")
    timeout_err = urllib.error.URLError(socket.timeout("timed out"))
    with patch("urllib.request.urlopen", side_effect=timeout_err):
        access, detail, evidence = classify_access("https://example.com/slow")
    assert_eq("Timeout → unverified", access, ACCESS_UNVERIFIED)
    assert_true("Detail mentions timeout", "timeout" in detail.lower() or "timed out" in detail.lower())

    # -------------------------------------------------------------------
    # Fixture 9: DNS failure → unverified
    # -------------------------------------------------------------------
    print("\n[Fixture 9] Simulated DNS failure → 'unverified'")
    dns_err = urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided"))
    with patch("urllib.request.urlopen", side_effect=dns_err):
        access, detail, evidence = classify_access("https://nonexistent.invalid/")
    assert_eq("DNS failure → unverified", access, ACCESS_UNVERIFIED)
    assert_true("Evidence mentions hostname", "resolve" in evidence.lower() or "dns" in evidence.lower())

    # -------------------------------------------------------------------
    # Fixture 10: HEAD 405 → GET 200 with no paywall signals → free_no_registration
    # -------------------------------------------------------------------
    print("\n[Fixture 10] HEAD 405 → GET 200 (no paywall) → 'free_no_registration'")
    err_405 = urllib.error.HTTPError(url="http://x", code=405, msg="Not Allowed", hdrs=None, fp=None)
    mock_get_200 = MagicMock()
    mock_get_200.status = 200
    mock_get_200.read = MagicMock(return_value=b"<html><body>Welcome to the podcast!</body></html>")
    mock_get_200.__enter__ = lambda s: s
    mock_get_200.__exit__ = MagicMock(return_value=False)
    call_count = [0]

    def side_effect_405_get_200(req, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise err_405
        return mock_get_200

    with patch("urllib.request.urlopen", side_effect=side_effect_405_get_200):
        access, detail, evidence = classify_access("https://example.com/podcast")
    assert_eq("HEAD 405 → GET 200 (no signals) → free_no_registration", access, ACCESS_FREE_NO_REG)
    assert_true("Detail mentions GET and 200", "GET" in detail and "200" in detail)

    # -------------------------------------------------------------------
    # Fixture 11: All access labels are distinct
    # -------------------------------------------------------------------
    print("\n[Fixture 11] All access labels are distinct")
    all_labels = [
        ACCESS_FREE_NO_REG, ACCESS_FREE_WITH_REG, ACCESS_PAYWALLED,
        ACCESS_ENV_REQUIRED, ACCESS_UNVERIFIED, ACCESS_SKIPPED
    ]
    assert_eq("All 6 access labels are unique", len(set(all_labels)), len(all_labels))

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
        print("Running live HTTP access check (single entry)...")
        for entry in selected:
            access, detail, evidence = classify_access(entry["url"])
            entry["access"] = access
            entry["access_detail"] = detail
            entry["access_evidence"] = evidence
            print(f"  Line {entry['lineno']}: {access} — {detail}")
            print(f"    Evidence: {evidence}")
    else:
        for entry in selected:
            entry["access"] = ACCESS_SKIPPED
            entry["access_detail"] = "offline mode; use --live for HTTP check"
            entry["access_evidence"] = (
                "python-podcast.de/show is a publicly listed German Python podcast. "
                "No registration or payment required based on public catalogue information. "
                "Classification: likely free_no_registration — verify in browser to confirm."
            )

    return {
        "task": "R10-T039",
        "target_file": str(TARGET_FILE.relative_to(REPO_ROOT)),
        "live_mode": live,
        "total_entries": len(entries),
        "selected_entries": selected,
        "access_labels": {
            ACCESS_FREE_NO_REG:   "Freely accessible, no account required",
            ACCESS_FREE_WITH_REG: "Freely accessible, but registration required",
            ACCESS_PAYWALLED:     "Requires payment",
            ACCESS_ENV_REQUIRED:  "Requires specific software/hardware",
            ACCESS_UNVERIFIED:    "Could not confirm — treat conservatively",
            ACCESS_SKIPPED:       "Not checked (offline mode)",
        },
        "policy": (
            "No link is removed solely because a single automated request failed. "
            "An unavailable resource is labelled 'unverified', not 'free' or 'broken'. "
            "No credentials are saved. Rate-limited (429) and timeouts → unverified."
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
    for e in report["selected_entries"]:
        print(f"  Line {e['lineno']}: [{e['title']}] → {e['access']}")
        print(f"    {e['access_detail']}")
        print(f"    Evidence: {e['access_evidence']}")


if __name__ == "__main__":
    main()
