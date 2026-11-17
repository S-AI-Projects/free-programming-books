#!/usr/bin/env python3
"""Parse and verify the selected Myanmar screencast list entry."""

import argparse
import html
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-my.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T026"
TARGET_CATEGORY = "React"
EXPECTED_ENTRY = {
    "display_name": "Learn React Docker And Containerized In Myanmar Language",
    "url": "https://www.youtube.com/watch?v=Qqr8oabREA8",
    "category": TARGET_CATEGORY,
    "creator": "MyanmarFullStackDevelopers",
    "format": "screencast",
    "line_number": 8,
}

HEADING_RE = re.compile(r"^(#{3,6})[ \t]+(.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[*+-]\s+")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
TAIL_RE = re.compile(
    r"^(?:\s+-\s+(?P<creator>.*?))?(?:\s+\((?P<format>[^()]*)\))?\s*$"
)
MARKDOWN_ESCAPE_RE = re.compile(r"\\([\\`*_{}\[\]()#+.!|~-])")


def _unescape_markdown(value):
    return html.unescape(MARKDOWN_ESCAPE_RE.sub(r"\1", value))


def _find_label_end(text, start):
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "]":
            return index
    return -1


def _parse_destination(text, start):
    if start >= len(text) or text[start] != "(":
        return None

    url_start = start + 1
    if url_start < len(text) and text[url_start] == "<":
        end = text.find(">", url_start + 1)
        if end == -1 or end + 1 >= len(text) or text[end + 1] != ")":
            return None
        return text[url_start + 1 : end], end + 2

    depth = 1
    escaped = False
    for index in range(url_start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[url_start:index], index + 1
    return None


def parse_entry(line, line_number, category):
    bullet = BULLET_RE.match(line)
    if not bullet:
        return None, None

    content = line[bullet.end() :]
    if not content.startswith("["):
        return None, f"Malformed list row at line {line_number}: expected a link"
    label_end = _find_label_end(content, 1)
    if label_end < 0:
        return None, f"Malformed list row at line {line_number}: unclosed title"

    destination = _parse_destination(content, label_end + 1)
    if destination is None:
        return None, f"Malformed list row at line {line_number}: invalid URL syntax"
    raw_url, tail_start = destination
    if not raw_url:
        return None, f"Malformed list row at line {line_number}: empty URL"

    tail_match = TAIL_RE.fullmatch(content[tail_start:])
    if not tail_match:
        return None, f"Malformed list row at line {line_number}: invalid metadata"
    creator = tail_match.group("creator")
    if creator is not None:
        creator = creator.strip() or None
    format_note = tail_match.group("format")
    return (
        {
            "line_number": line_number,
            "category": category,
            "display_name": _unescape_markdown(content[1:label_end]),
            "url": raw_url,
            "creator": creator,
            "format": format_note,
        },
        None,
    )


def parse_markdown(markdown_text):
    entries = []
    errors = []
    category = None
    fence_marker = None

    for line_number, line in enumerate(markdown_text.splitlines(), start=1):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            if fence_marker is None:
                fence_marker = marker[0] * len(marker)
            elif marker[0] == fence_marker[0] and len(marker) >= len(fence_marker):
                fence_marker = None
            continue
        if fence_marker is not None:
            continue

        heading = HEADING_RE.match(line.strip())
        if heading:
            if len(heading.group(1)) == 3:
                title = _unescape_markdown(heading.group(2)).strip()
                category = None if title.casefold() == "index" else title
            continue

        if category != TARGET_CATEGORY or not BULLET_RE.match(line):
            continue
        entry, error = parse_entry(line, line_number, category)
        if error:
            errors.append(error)
        elif entry:
            entries.append(entry)

    return entries, errors


def _url_error(url):
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
        port = parts.port
    except ValueError as exc:
        return f"Invalid URL {url!r}: {exc}"
    if parts.scheme != "https" or not hostname:
        return f"URL must be an absolute HTTPS URL: {url}"
    if parts.username is not None or parts.password is not None:
        return f"URL must not contain credentials: {url}"
    if port is not None and not 1 <= port <= 65535:
        return f"URL has an invalid port: {url}"
    return None


def analyze_markdown(markdown_text, source_file="<memory>", check_line=False):
    entries, errors = parse_markdown(markdown_text)
    for entry in entries:
        url_error = _url_error(entry["url"])
        if url_error:
            errors.append(f"Line {entry['line_number']}: {url_error}")

    selected = [entry for entry in entries if entry["url"] == EXPECTED_ENTRY["url"]]
    if not selected:
        errors.append(f"Missing selected entry URL: {EXPECTED_ENTRY['url']}")
    elif len(selected) > 1:
        errors.append(f"Selected entry URL appears multiple times: {EXPECTED_ENTRY['url']}")
    else:
        entry = selected[0]
        for field in ("display_name", "category", "creator", "format"):
            if entry[field] != EXPECTED_ENTRY[field]:
                errors.append(
                    f"{field} mismatch at line {entry['line_number']}: "
                    f"expected {EXPECTED_ENTRY[field]!r}, got {entry[field]!r}"
                )
        if check_line and entry["line_number"] != EXPECTED_ENTRY["line_number"]:
            errors.append(
                f"Line mismatch: expected {EXPECTED_ENTRY['line_number']}, "
                f"got {entry['line_number']}"
            )

    return {
        "source_file": source_file,
        "category": TARGET_CATEGORY,
        "entries": entries,
        "selected_entry": selected[0] if len(selected) == 1 else None,
        "errors": errors,
        "passed": not errors,
    }


def analyze_file(target_file):
    markdown_text = target_file.read_text(encoding="utf-8")
    try:
        source_file = str(target_file.relative_to(REPO_ROOT))
    except ValueError:
        source_file = str(target_file)
    check_line = target_file.resolve() == DEFAULT_TARGET_FILE.resolve()
    return analyze_markdown(markdown_text, source_file, check_line=check_line)


def run_self_test(target_file, work_dir):
    success_path = work_dir / "fixture_success.md"
    malformed_path = work_dir / "fixture_malformed.md"
    unusual_path = work_dir / "fixture_unusual_url.md"

    success_report = analyze_markdown(
        success_path.read_text(encoding="utf-8"), success_path.name
    )
    expected_success = {
        "passed": True,
        "selected_entry": {
            **EXPECTED_ENTRY,
            "line_number": 10,
        },
        "errors": [],
    }
    success_actual = {
        "passed": success_report["passed"],
        "selected_entry": success_report["selected_entry"],
        "errors": success_report["errors"],
    }
    assert success_actual == expected_success, (
        f"Successful fixture mismatch: expected {expected_success}, got {success_actual}"
    )
    assert len(success_report["entries"]) == 1, (
        "The fenced example or index link was incorrectly parsed as a list entry"
    )

    malformed_report = analyze_markdown(
        malformed_path.read_text(encoding="utf-8"), malformed_path.name
    )
    expected_malformed = {
        "passed": False,
        "errors": [
            "Malformed list row at line 3: invalid URL syntax",
            f"Missing selected entry URL: {EXPECTED_ENTRY['url']}",
        ],
    }
    malformed_actual = {
        "passed": malformed_report["passed"],
        "errors": malformed_report["errors"],
    }
    assert malformed_actual == expected_malformed, (
        f"Malformed fixture mismatch: expected {expected_malformed}, "
        f"got {malformed_actual}"
    )
    malformed_cli = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--file",
            str(malformed_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert malformed_cli.returncode != 0, (
        "The checker CLI returned success for a malformed-row fixture"
    )

    unusual_text = unusual_path.read_text(encoding="utf-8")
    unusual_entries, unusual_errors = parse_markdown(unusual_text)
    expected_unusual_url = (
        "https://example.test/a_(b)?first=a%2Fb&second=x+y#section-2"
    )
    expected_unusual = {
        "passed": True,
        "entry": {
            "line_number": 2,
            "category": TARGET_CATEGORY,
            "display_name": "Unusual URL fixture",
            "url": expected_unusual_url,
            "creator": "Fixture Author",
            "format": "screencast",
        },
        "url_error": None,
        "errors": [],
    }
    unusual_actual = {
        "passed": len(unusual_entries) == 1 and not unusual_errors,
        "entry": unusual_entries[0] if len(unusual_entries) == 1 else None,
        "url_error": _url_error(unusual_entries[0]["url"]) if len(unusual_entries) == 1 else None,
        "errors": unusual_errors,
    }
    assert unusual_actual == expected_unusual, (
        f"Unusual URL fixture mismatch: expected {expected_unusual}, "
        f"got {unusual_actual}"
    )

    source_report = analyze_file(target_file)
    assert source_report["passed"], f"Source check failed: {source_report['errors']}"
    assert source_report["selected_entry"]["line_number"] == EXPECTED_ENTRY["line_number"]

    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "task_id": "R10-T026",
        "network_used": False,
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "fixtures": {
            "success": {
                "input": success_path.name,
                "expected": expected_success,
                "actual": success_actual,
                "fenced_and_index_links_ignored": True,
            },
            "malformed": {
                "input": malformed_path.name,
                "expected": {**expected_malformed, "nonzero_cli_exit": True},
                "actual": {
                    **malformed_actual,
                    "cli_exit_code": malformed_cli.returncode,
                    "stdout": malformed_cli.stdout,
                    "stderr": malformed_cli.stderr,
                },
            },
            "unusual_url": {
                "input": unusual_path.name,
                "expected": expected_unusual,
                "actual": unusual_actual,
            },
        },
        "source_verification": {
            "input": source_report["source_file"],
            "expected": EXPECTED_ENTRY,
            "actual": source_report,
        },
        "self_test_passed": True,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "results.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("SELF-TEST PASSED: valid, malformed, and unusual-URL fixtures checked.")
    print(json.dumps(source_report, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Check the selected Myanmar React screencast entry and offline fixtures."
        )
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_TARGET_FILE)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return run_self_test(args.file, args.work_dir)
        report = analyze_file(args.file)
    except (
        OSError,
        UnicodeError,
        AssertionError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
