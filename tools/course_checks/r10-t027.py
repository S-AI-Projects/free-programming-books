#!/usr/bin/env python3
"""Classify availability responses for selected Persian podcast entries."""

import argparse
import html
import json
import platform
import re
import socket
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-fa_IR.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T027"
ENTRY_RE = re.compile(r"^\s*[*+-]\s+\[([^\]]+)\]\(([^)]+)\)(.*)$")
HEADING_RE = re.compile(r"^(#{3,6})[ \t]+(.+?)\s*$")
FORMAT_RE = re.compile(r"\(([^()]*)\)\s*$")
HEAD_FALLBACK_STATUSES = {405, 501}

SELECTED_ENTRIES = {
    "https://anchor.fm/codemy": {
        "display_name": "پادکست کافه برنامه نویس",
        "category": "Programming News",
        "creator": "CafeCodemy\u200f",
        "format": "podcast",
        "line_number": 11,
    },
    "https://roocket.ir/podcast/": {
        "display_name": "راکت کست",
        "category": "Programming News",
        "creator": None,
        "format": "podcast",
        "line_number": 12,
    },
    "https://anchor.fm/parsclick/": {
        "display_name": "پارس کلیک",
        "category": "Technology",
        "creator": "Amir Azimi\u200f",
        "format": "podcast",
        "line_number": 17,
    },
}


def _parse_metadata(trailing):
    value = trailing.strip()
    format_note = None
    format_match = FORMAT_RE.search(value)
    if format_match:
        format_note = format_match.group(1).strip()
        value = value[: format_match.start()].strip()
    if value.startswith("-"):
        value = value[1:].strip()
    creator = html.unescape(value).strip() or None
    return creator, format_note


def parse_entries(markdown_text, source_file="<memory>"):
    entries = []
    category = None
    in_index = False
    for line_number, line in enumerate(markdown_text.splitlines(), start=1):
        heading = HEADING_RE.match(line.strip())
        if heading and len(heading.group(1)) == 3:
            category = heading.group(2).strip()
            in_index = category.casefold() == "index"
            if in_index:
                category = None
            continue
        if in_index or category is None:
            continue
        match = ENTRY_RE.match(line)
        if not match:
            continue
        display_name, url, trailing = match.groups()
        creator, format_note = _parse_metadata(trailing)
        entries.append(
            {
                "line_number": line_number,
                "source_file": source_file,
                "display_name": html.unescape(display_name.strip()),
                "url": url.strip(),
                "category": category,
                "creator": creator,
                "format": format_note,
            }
        )
    return entries


def _classify_status(status, used_get_fallback=False):
    if 200 <= status < 300:
        return "success_after_get_fallback" if used_get_fallback else "success"
    if status in (401, 403):
        return "forbidden"
    if status in (404, 410):
        return "missing_resource"
    if status == 429:
        return "rate_limited"
    if 300 <= status < 400:
        return "redirect"
    if 500 <= status < 600:
        return "server_error"
    return "http_error"


def _classify_exception(exc):
    if isinstance(exc, urllib.error.URLError):
        return _classify_exception(exc.reason)
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, socket.gaierror):
        return "dns_failure"
    if isinstance(exc, ssl.SSLError):
        return "tls_error"
    return "network_error"


def request_once(method, url, timeout):
    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": "free-programming-books-course-check/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"status": response.status, "final_url": response.geturl()}
    except urllib.error.HTTPError as error:
        try:
            return {"status": error.code, "final_url": error.geturl() or url}
        finally:
            error.close()


def probe_url(url, requester=request_once, timeout=5.0, manual_confirmation=None):
    methods = []
    status = None
    final_url = url
    error_message = None
    try:
        methods.append("HEAD")
        response = requester("HEAD", url, timeout)
        status = response["status"]
        final_url = response.get("final_url") or url
        if status in HEAD_FALLBACK_STATUSES:
            methods.append("GET")
            response = requester("GET", url, timeout)
            status = response["status"]
            final_url = response.get("final_url") or url
    except (
        urllib.error.URLError,
        TimeoutError,
        socket.timeout,
        socket.gaierror,
        ssl.SSLError,
        OSError,
    ) as exc:
        label = _classify_exception(exc)
        error_message = str(exc)
    else:
        label = _classify_status(status, used_get_fallback="GET" in methods)

    confirmed = bool(manual_confirmation)
    return {
        "url": url,
        "label": label,
        "status_code": status,
        "final_url": final_url,
        "methods": methods,
        "head_fallback_used": "GET" in methods,
        "error": error_message,
        "manual_confirmation": manual_confirmation,
        "removal_recommended": label == "missing_resource" and confirmed,
    }


def analyze_markdown(markdown_text, source_file="<memory>", check_lines=False):
    entries = parse_entries(markdown_text, source_file)
    entries_by_url = {}
    for entry in entries:
        entries_by_url.setdefault(entry["url"], []).append(entry)

    selected_entries = []
    errors = []
    for url, expected in SELECTED_ENTRIES.items():
        matches = entries_by_url.get(url, [])
        if not matches:
            errors.append(f"Missing selected entry: {url}")
            continue
        if len(matches) > 1:
            errors.append(f"Selected entry appears multiple times: {url}")
        entry = matches[0]
        selected_entries.append(entry)
        for field in ("display_name", "category", "creator", "format"):
            if entry[field] != expected[field]:
                errors.append(
                    f"{field} mismatch for {url}: expected {expected[field]!r}, "
                    f"got {entry[field]!r}"
                )
        if check_lines and entry["line_number"] != expected["line_number"]:
            errors.append(
                f"Line mismatch for {url}: expected {expected['line_number']}, "
                f"got {entry['line_number']}"
            )

    return {
        "source_file": source_file,
        "entry_count": len(entries),
        "selected_entries": selected_entries,
        "errors": errors,
        "passed": not errors,
    }


def analyze_file(target_file):
    text = target_file.read_text(encoding="utf-8")
    try:
        source_file = str(target_file.relative_to(REPO_ROOT))
    except ValueError:
        source_file = str(target_file)
    check_lines = target_file.resolve() == DEFAULT_TARGET_FILE.resolve()
    return analyze_markdown(text, source_file, check_lines=check_lines)


def _fixture_requester(steps, calls):
    remaining = list(steps)

    def request(method, url, timeout):
        if not remaining:
            raise AssertionError("Fixture requester received an unexpected request")
        step = remaining.pop(0)
        calls.append({"method": method, "url": url, "timeout": timeout})
        if method != step["method"]:
            raise AssertionError(
                f"Expected {step['method']} request, got {method}"
            )
        if step.get("error") == "timeout":
            raise TimeoutError("fixture timeout")
        if step.get("error") == "dns_failure":
            raise urllib.error.URLError(
                socket.gaierror(socket.EAI_NONAME, "fixture DNS failure")
            )
        return {
            "status": step["status"],
            "final_url": step.get("final_url", url),
        }

    return request


def run_self_test(target_file, work_dir):
    fixture_path = work_dir / "fixtures.json"
    fixtures = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_results = []
    for fixture in fixtures["cases"]:
        assert fixture["url"] in SELECTED_ENTRIES, (
            f"{fixture['name']}: URL is outside the fixed selected-entry set"
        )
        calls = []
        requester = _fixture_requester(fixture["steps"], calls)
        actual = probe_url(
            fixture["url"],
            requester=requester,
            timeout=5.0,
            manual_confirmation=fixture.get("manual_confirmation"),
        )
        selected_actual = {
            key: actual[key] for key in fixture["expected"]
        }
        assert selected_actual == fixture["expected"], (
            f"{fixture['name']}: expected {fixture['expected']}, "
            f"got {selected_actual}"
        )
        fixture_results.append(
            {
                "name": fixture["name"],
                "expected": fixture["expected"],
                "actual": selected_actual,
                "requests": calls,
            }
        )
    for fixture, result in zip(fixtures["cases"], fixture_results):
        assert len(result["requests"]) == len(fixture["steps"]), (
            f"{fixture['name']}: not all expected requests were made"
        )
    assert all(
        request["timeout"] == 5.0
        for result in fixture_results
        for request in result["requests"]
    ), "All offline fixture requests must use the fixed five-second timeout"

    source_report = analyze_file(target_file)
    assert source_report["passed"], f"Source list check failed: {source_report['errors']}"
    assert [
        entry["line_number"] for entry in source_report["selected_entries"]
    ] == [11, 12, 17]

    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "task_id": "R10-T027",
        "network_used": False,
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "fixtures": fixture_results,
        "source_verification": {
            "input": source_report["source_file"],
            "expected_urls_and_lines": [
                {"url": url, "line_number": entry["line_number"]}
                for url, entry in zip(
                    SELECTED_ENTRIES, source_report["selected_entries"]
                )
            ],
            "actual": source_report,
        },
        "removal_policy": (
            "Automated missing_resource labels are not removal recommendations "
            "without explicit manual confirmation."
        ),
        "self_test_passed": True,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "results.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("SELF-TEST PASSED: HTTP, fallback, timeout, DNS, and removal-policy fixtures.")
    print(json.dumps(source_report, ensure_ascii=False, indent=2))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Parse the selected Persian podcast entries and optionally classify "
            "their availability."
        )
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_TARGET_FILE)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Probe only the three selected URLs sequentially.",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--manual-confirmed",
        action="append",
        choices=tuple(SELECTED_ENTRIES),
        default=[],
        help="URL manually confirmed missing; only use after browser/manual review.",
    )
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 30:
        parser.error("--timeout must be greater than 0 and no more than 30 seconds")

    try:
        if args.self_test:
            return run_self_test(args.file, args.work_dir)
        report = analyze_file(args.file)
        if args.live:
            confirmations = set(args.manual_confirmed)
            report["availability_checks"] = [
                probe_url(
                    url,
                    timeout=args.timeout,
                    manual_confirmation=(
                        "Manual confirmation supplied by operator"
                        if url in confirmations
                        else None
                    ),
                )
                for url in SELECTED_ENTRIES
            ]
    except (
        OSError,
        UnicodeError,
        AssertionError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
