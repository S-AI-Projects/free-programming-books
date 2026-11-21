#!/usr/bin/env python3
"""
R10-T040: Maintenance workflow checker for courses/free-courses-ko.md

Produces a one-command scoped report for the selected entries that includes:
  - Before/after metadata (source line, title, URL, author)
  - Observed facts (parse results, URL structure)
  - Manual decisions (recommendations based on evidence)
  - Reproducible offline fixtures

The report separates observed facts from recommendations and produces
stable output from the same fixtures.

Usage:
    python3 tools/course_checks/r10-t040.py              # run full check, write results.json
    python3 tools/course_checks/r10-t040.py --self-test  # run offline fixture tests only
    python3 tools/course_checks/r10-t040.py --live       # also run live HTTP probe
"""

import re
import sys
import json
import socket
import hashlib
from pathlib import Path
from typing import Optional
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "courses" / "free-courses-ko.md"
WORK_DIR = REPO_ROOT / "work" / "R10-T040"
RESULTS_FILE = WORK_DIR / "results.json"

# Selected entries (line numbers 1-based)
SELECTED_LINES = [45, 46, 47]

# HTTP probe settings
REQUEST_TIMEOUT = 10   # seconds
MAX_CONCURRENCY = 2    # low concurrency

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; free-programming-books-checker/1.0; "
        "+https://github.com/EbookFoundation/free-programming-books)"
    )
}

# ---------------------------------------------------------------------------
# HTTP status labels
# ---------------------------------------------------------------------------

STATUS_OK          = "ok"
STATUS_NOT_FOUND   = "not_found"
STATUS_RATE_LIMITED = "rate_limited"
STATUS_FORBIDDEN   = "forbidden"
STATUS_HEAD_UNSUP  = "head_unsupported_get_ok"
STATUS_DNS_FAIL    = "dns_failure"
STATUS_TIMEOUT     = "timeout"
STATUS_ERROR       = "error"
STATUS_SKIPPED     = "skipped"

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
        })
    return entries


# ---------------------------------------------------------------------------
# Observed facts extractor
# ---------------------------------------------------------------------------

def extract_facts(entry: dict) -> dict:
    """
    Derive observable facts from an entry without making HTTP requests.
    Returns a dict of facts that is stable across runs.
    """
    url = entry["url"]
    facts = {
        "source_line": entry["lineno"],
        "title": entry["title"],
        "url": url,
        "author": entry["author"],
        "format_hint": entry["format"],
        "url_scheme": url.split("://")[0] if "://" in url else "",
        "url_host": "",
        "url_path_prefix": "",
        "is_youtube_playlist": False,
        "playlist_id": None,
        "has_author": bool(entry["author"]),
        "title_is_ascii": entry["title"].isascii(),
        "url_hash": hashlib.sha256(url.encode()).hexdigest()[:12],
    }

    # Parse host and path
    try:
        after_scheme = url.split("://", 1)[1]
        host_part = after_scheme.split("/")[0]
        path_part = "/" + "/".join(after_scheme.split("/")[1:])
        facts["url_host"] = host_part
        facts["url_path_prefix"] = path_part[:50]
    except Exception:
        pass

    # YouTube playlist detection
    if "youtube.com/playlist" in url or "youtu.be" in url:
        facts["is_youtube_playlist"] = True
        # Extract list= param
        m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
        if m:
            facts["playlist_id"] = m.group(1)

    return facts


# ---------------------------------------------------------------------------
# HTTP probe (live mode)
# ---------------------------------------------------------------------------

def probe_url(url: str) -> tuple[str, str]:
    """
    Probe url with HEAD (GET fallback on 405).
    Returns (status_label, detail).
    Policy: no link removed solely because a single automated request failed.
    """
    import urllib.request
    import urllib.error

    try:
        req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                code = resp.status
                if 200 <= code < 300:
                    return STATUS_OK, f"HEAD {code}"
                elif code == 429:
                    return STATUS_RATE_LIMITED, f"HEAD {code}"
                elif code == 403:
                    return STATUS_FORBIDDEN, f"HEAD {code}"
                elif code == 404:
                    return STATUS_NOT_FOUND, f"HEAD {code}"
                else:
                    return STATUS_ERROR, f"HEAD {code}"
        except urllib.error.HTTPError as e:
            if e.code == 405:
                req_get = urllib.request.Request(url, headers=HEADERS, method="GET")
                try:
                    with urllib.request.urlopen(req_get, timeout=REQUEST_TIMEOUT) as resp2:
                        code2 = resp2.status
                        if 200 <= code2 < 300:
                            return STATUS_HEAD_UNSUP, f"HEAD 405 → GET {code2}"
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
            if "timed out" in reason.lower() or isinstance(e.reason, socket.timeout):
                return STATUS_TIMEOUT, f"Timeout: {reason}"
            if isinstance(e.reason, socket.gaierror) or "getaddrinfo" in reason.lower():
                return STATUS_DNS_FAIL, f"DNS failure: {reason}"
            return STATUS_ERROR, f"URLError: {reason}"
        except (TimeoutError, socket.timeout):
            return STATUS_TIMEOUT, "Timeout"
    except Exception as ex:
        return STATUS_ERROR, f"Unexpected: {ex}"


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

def make_recommendation(entry: dict, facts: dict, http_status: str, http_detail: str) -> dict:
    """
    Separate observed facts from recommendations.
    Returns a recommendation dict with rationale.
    """
    rec = {
        "action": "no_change",
        "rationale": "",
        "confidence": "high",
    }

    if http_status == STATUS_NOT_FOUND:
        rec["action"] = "verify_manually"
        rec["rationale"] = (
            f"HTTP 404 observed on automated probe ({http_detail}). "
            "A single automated failure is insufficient to remove a link. "
            "Manually verify in a browser before any removal."
        )
        rec["confidence"] = "low"
    elif http_status == STATUS_RATE_LIMITED:
        rec["action"] = "no_change"
        rec["rationale"] = (
            f"HTTP 429 (rate-limited) — not a dead link. "
            "YouTube playlists commonly return 429 to automated agents."
        )
    elif http_status == STATUS_TIMEOUT:
        rec["action"] = "no_change"
        rec["rationale"] = "Timeout — not a dead link. Retry later or verify manually."
        rec["confidence"] = "medium"
    elif http_status in (STATUS_OK, STATUS_HEAD_UNSUP):
        rec["action"] = "no_change"
        rec["rationale"] = f"Resource accessible ({http_detail}). No change needed."
    elif http_status == STATUS_SKIPPED:
        rec["action"] = "no_change"
        rec["rationale"] = "Not probed (offline mode). No change recommended without evidence."
    else:
        rec["action"] = "no_change"
        rec["rationale"] = f"Status: {http_status} ({http_detail}). Verify manually before any action."
        rec["confidence"] = "medium"

    return rec


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

def run_analysis(text: str, live: bool = False) -> dict:
    entries = parse_entries(text)
    selected = [e for e in entries if e["lineno"] in SELECTED_LINES]

    report_entries = []
    for entry in selected:
        facts = extract_facts(entry)

        # HTTP probe
        if live:
            http_status, http_detail = probe_url(entry["url"])
        else:
            http_status, http_detail = STATUS_SKIPPED, "offline mode; use --live"

        recommendation = make_recommendation(entry, facts, http_status, http_detail)

        report_entries.append({
            # Before metadata (source state)
            "before": {
                "source_line": entry["lineno"],
                "title": entry["title"],
                "url": entry["url"],
                "author": entry["author"],
                "format": entry["format"],
                "notes": entry["notes"],
            },
            # Observed facts (objective, stable)
            "observed_facts": facts,
            # HTTP probe result
            "http_status": http_status,
            "http_detail": http_detail,
            # Recommendation (separated from facts)
            "recommendation": recommendation,
            # After metadata (what the entry looks like post-pass)
            # In this case no changes are recommended, so after == before
            "after": {
                "source_line": entry["lineno"],
                "title": entry["title"],
                "url": entry["url"],
                "author": entry["author"],
                "format": entry["format"],
                "notes": entry["notes"],
                "changed": False,
            },
        })

    return {
        "task": "R10-T040",
        "target_file": str(TARGET_FILE.relative_to(REPO_ROOT)),
        "live_mode": live,
        "total_entries_in_file": len(entries),
        "selected_lines": SELECTED_LINES,
        "report": report_entries,
        "policy": (
            "No link is removed solely because a single automated request failed. "
            "Observed facts and recommendations are kept separate. "
            "Stable output: same fixtures always produce same facts."
        ),
        "tool_version": "r10-t040 v1.0",
    }


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

    def assert_ne(label, got, not_expected):
        nonlocal passed
        if got != not_expected:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failures.append(f"FAIL  {label}  (got {got!r}, expected something else)")
            print(f"  FAIL  {label}  (should not be {not_expected!r})")

    print("=" * 60)
    print("R10-T040 Self-Test (offline fixture-based)")
    print("=" * 60)

    import urllib.error

    # -------------------------------------------------------------------
    # Fixture 1: Malformed row → 0 entries parsed
    # -------------------------------------------------------------------
    print("\n[Fixture 1] Malformed row — no URL")
    result = parse_entries("* [Missing URL entry\n")
    assert_eq("Malformed row: entry count == 0", len(result), 0)

    # -------------------------------------------------------------------
    # Fixture 2: Selected entries in actual target file
    # -------------------------------------------------------------------
    print("\n[Fixture 2] Three selected entries parsed from target file")
    if TARGET_FILE.exists():
        text = TARGET_FILE.read_text(encoding="utf-8")
        all_entries = parse_entries(text)
        selected = [e for e in all_entries if e["lineno"] in SELECTED_LINES]
        assert_eq("Three selected entries found", len(selected), 3)

        e45 = next((e for e in selected if e["lineno"] == 45), None)
        e46 = next((e for e in selected if e["lineno"] == 46), None)
        e47 = next((e for e in selected if e["lineno"] == 47), None)

        assert_true("Line 45 found", e45 is not None)
        if e45:
            assert_eq("Line 45 title", e45["title"], "실전 알고리즘 강좌")
            assert_eq("Line 45 author", e45["author"], "동빈나")
            assert_true("Line 45 URL is YouTube playlist",
                        "youtube.com/playlist" in e45["url"])

        assert_true("Line 46 found", e46 is not None)
        if e46:
            assert_eq("Line 46 title", e46["title"], "알고리즘 강좌")
            assert_eq("Line 46 author", e46["author"], "권오흠")
            assert_true("Line 46 URL is YouTube playlist",
                        "youtube.com/playlist" in e46["url"])

        assert_true("Line 47 found", e47 is not None)
        if e47:
            assert_eq("Line 47 title", e47["title"], "이상진의 자료구조 (2017)")
            assert_eq("Line 47 author", e47["author"], "프리렉")
            assert_true("Line 47 URL is YouTube playlist",
                        "youtube.com/playlist" in e47["url"])
    else:
        failures.append(f"FAIL  Target file not found: {TARGET_FILE}")
        print(f"  FAIL  Target file not found: {TARGET_FILE}")

    # -------------------------------------------------------------------
    # Fixture 3: Observed facts are stable and correct
    # -------------------------------------------------------------------
    print("\n[Fixture 3] Observed facts extraction — stable and correct")
    sample_entry = {
        "lineno": 45,
        "title": "실전 알고리즘 강좌",
        "url": "https://www.youtube.com/playlist?list=PLRx0vPvlEmdDHxCvAQS1_6XV4deOwfVrz",
        "author": "동빈나",
        "format": "",
        "notes": "",
    }
    facts = extract_facts(sample_entry)
    assert_eq("Source line preserved in facts", facts["source_line"], 45)
    assert_eq("URL host correct", facts["url_host"], "www.youtube.com")
    assert_eq("Is YouTube playlist", facts["is_youtube_playlist"], True)
    assert_eq("Playlist ID extracted", facts["playlist_id"], "PLRx0vPvlEmdDHxCvAQS1_6XV4deOwfVrz")
    assert_eq("Has author", facts["has_author"], True)
    assert_eq("Title is not ASCII (Korean)", facts["title_is_ascii"], False)

    # Stability: same input → same hash
    facts2 = extract_facts(sample_entry)
    assert_eq("URL hash is stable across runs", facts["url_hash"], facts2["url_hash"])

    # -------------------------------------------------------------------
    # Fixture 4: Recommendations separate from facts
    # -------------------------------------------------------------------
    print("\n[Fixture 4] Recommendations are separate from observed facts")
    rec_ok = make_recommendation(sample_entry, facts, STATUS_OK, "HEAD 200")
    assert_eq("OK status → no_change", rec_ok["action"], "no_change")
    assert_true("OK rationale is non-empty", bool(rec_ok["rationale"]))

    rec_404 = make_recommendation(sample_entry, facts, STATUS_NOT_FOUND, "HEAD 404")
    assert_eq("404 → verify_manually", rec_404["action"], "verify_manually")
    assert_eq("404 confidence is low", rec_404["confidence"], "low")
    assert_true("404 rationale mentions single failure", "single" in rec_404["rationale"])

    rec_429 = make_recommendation(sample_entry, facts, STATUS_RATE_LIMITED, "HEAD 429")
    assert_eq("429 → no_change (not a dead link)", rec_429["action"], "no_change")
    assert_true("429 rationale mentions rate-limited", "rate-limited" in rec_429["rationale"].lower())

    rec_timeout = make_recommendation(sample_entry, facts, STATUS_TIMEOUT, "Timeout")
    assert_eq("Timeout → no_change", rec_timeout["action"], "no_change")

    rec_skipped = make_recommendation(sample_entry, facts, STATUS_SKIPPED, "offline")
    assert_eq("Skipped → no_change", rec_skipped["action"], "no_change")

    # -------------------------------------------------------------------
    # Fixture 5: HTTP 200 (mocked) → STATUS_OK
    # -------------------------------------------------------------------
    print("\n[Fixture 5] Simulated HTTP 200 → 'ok'")
    mock_200 = MagicMock()
    mock_200.status = 200
    mock_200.__enter__ = lambda s: s
    mock_200.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_200):
        status, detail = probe_url("https://www.youtube.com/playlist?list=test")
    assert_eq("HEAD 200 → STATUS_OK", status, STATUS_OK)

    # -------------------------------------------------------------------
    # Fixture 6: HTTP 429 → STATUS_RATE_LIMITED (not dead link)
    # -------------------------------------------------------------------
    print("\n[Fixture 6] Simulated HTTP 429 → 'rate_limited' (not removed)")
    err_429 = urllib.error.HTTPError(url="http://x", code=429, msg="Too Many Requests", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err_429):
        status, detail = probe_url("https://www.youtube.com/playlist?list=test")
    assert_eq("HTTP 429 → rate_limited", status, STATUS_RATE_LIMITED)
    # Recommendation must NOT be removal
    rec = make_recommendation(sample_entry, facts, status, detail)
    assert_ne("429 recommendation is not 'remove'", rec["action"], "remove")

    # -------------------------------------------------------------------
    # Fixture 7: DNS failure → STATUS_DNS_FAIL
    # -------------------------------------------------------------------
    print("\n[Fixture 7] DNS failure → 'dns_failure'")
    dns_err = urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided"))
    with patch("urllib.request.urlopen", side_effect=dns_err):
        status, detail = probe_url("https://nonexistent.invalid/")
    assert_eq("DNS failure → STATUS_DNS_FAIL", status, STATUS_DNS_FAIL)

    # -------------------------------------------------------------------
    # Fixture 8: Timeout → STATUS_TIMEOUT
    # -------------------------------------------------------------------
    print("\n[Fixture 8] Timeout → 'timeout'")
    timeout_err = urllib.error.URLError(socket.timeout("timed out"))
    with patch("urllib.request.urlopen", side_effect=timeout_err):
        status, detail = probe_url("https://www.youtube.com/playlist?list=test")
    assert_eq("Timeout → STATUS_TIMEOUT", status, STATUS_TIMEOUT)

    # -------------------------------------------------------------------
    # Fixture 9: Full report structure — before/after separate from facts/recommendation
    # -------------------------------------------------------------------
    print("\n[Fixture 9] Full report structure integrity")
    if TARGET_FILE.exists():
        text = TARGET_FILE.read_text(encoding="utf-8")
        report = run_analysis(text, live=False)
        assert_eq("Report has 3 entries", len(report["report"]), 3)
        for item in report["report"]:
            assert_true(f"Line {item['before']['source_line']}: 'before' key present",
                        "before" in item)
            assert_true(f"Line {item['before']['source_line']}: 'observed_facts' key present",
                        "observed_facts" in item)
            assert_true(f"Line {item['before']['source_line']}: 'recommendation' key present",
                        "recommendation" in item)
            assert_true(f"Line {item['before']['source_line']}: 'after' key present",
                        "after" in item)
            assert_eq(f"Line {item['before']['source_line']}: before==after (no changes)",
                      item["before"]["url"], item["after"]["url"])
        assert_eq("Report contains policy statement", True, bool(report["policy"]))
        assert_eq("Tool version present", True, bool(report.get("tool_version")))
    else:
        failures.append(f"FAIL  Target file not found: {TARGET_FILE}")
        print(f"  FAIL  Target file not found")

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
    print(f"Total entries in file: {report['total_entries_in_file']}")
    print(f"Selected entries: {len(report['report'])}")
    print()
    for item in report["report"]:
        b = item["before"]
        f = item["observed_facts"]
        r = item["recommendation"]
        print(f"  Line {b['source_line']}: [{b['title']}]")
        print(f"    URL:    {b['url']}")
        print(f"    Author: {b['author'] or '(none)'}")
        print(f"    Facts:  YouTube={f['is_youtube_playlist']}, "
              f"playlist_id={f['playlist_id']}")
        print(f"    HTTP:   {item['http_status']} ({item['http_detail']})")
        print(f"    Action: {r['action']} [{r['confidence']} confidence]")
        print(f"    Why:    {r['rationale']}")
        print()


if __name__ == "__main__":
    main()
