#!/usr/bin/env python3
"""Find exact and conservative normalized URL groups in the Czech book list."""

import argparse
import html
import json
import platform
import re
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "books" / "free-programming-books-cs.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T023"

SELECTED_ENTRIES = {
    "http://i.iinfo.cz/files/root/k/bash_ocima_bohdana_milara.pdf": {
        "display_name": "Bash očima Bohdana Milara",
        "category": "Bash",
        "line_number": 32,
    },
    "https://phoenix.inf.upol.cz/esf/ucebni/sysprog.pdf": {
        "display_name": "Systémové programování v jazyce C#",
        "category": "C#",
        "line_number": 37,
    },
    "https://akela.mendelu.cz/~xvencal2/CPP/opora.pdf": {
        "display_name": "Moderní programování objektových aplikací v C++",
        "category": "C++",
        "line_number": 42,
    },
}

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)\s*$")
ENTRY_RE = re.compile(r"^\s*[*+-]\s+\[([^\]]+)\]\(([^)]+)\)(.*)$")
ANCHOR_RE = re.compile(r"</?a\b[^>]*>", re.I)
ESCAPED_MARKDOWN_RE = re.compile(r"\\([\\`*_{}\[\]()#+.!-])")


def _heading_title(raw_title):
    title = ANCHOR_RE.sub("", raw_title)
    title = ESCAPED_MARKDOWN_RE.sub(r"\1", title)
    return html.unescape(title).strip()


def parse_entries(markdown_text, source_file="<memory>"):
    entries = []
    fence_character = None
    fence_length = 0
    heading_stack = []
    in_index = False

    for line_number, raw_line in enumerate(markdown_text.splitlines(), start=1):
        fence_match = FENCE_RE.match(raw_line)
        if fence_match:
            marker = fence_match.group(1)
            info = fence_match.group(2)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif (
                marker[0] == fence_character
                and len(marker) >= fence_length
                and not info.strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if fence_character is not None:
            continue

        heading_match = HEADING_RE.match(raw_line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            title = _heading_title(heading_match.group(2))
            if level == 3:
                in_index = title.lower() == "index"
                heading_stack = [] if in_index else [(level, title)]
            elif level < 3:
                in_index = False
                heading_stack = []
            elif not in_index:
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))
            continue

        if in_index or not heading_stack:
            continue
        entry_match = ENTRY_RE.match(raw_line)
        if not entry_match:
            continue

        display_name, url, trailing_metadata = entry_match.groups()
        entries.append(
            {
                "line_number": line_number,
                "source_file": source_file,
                "category": " > ".join(title for _, title in heading_stack),
                "display_name": display_name.strip(),
                "url": url.strip(),
                "metadata": trailing_metadata.strip() or None,
            }
        )
    return entries


def normalize_url_conservatively(url):
    """Normalize only authority casing/default ports and an empty root path."""
    try:
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        if scheme not in ("http", "https") or not parts.hostname:
            return None
        port = parts.port
    except ValueError:
        return None

    hostname = parts.hostname.lower()
    if ":" in hostname:
        hostname = f"[{hostname}]"
    userinfo = parts.netloc.rsplit("@", 1)[0] + "@" if "@" in parts.netloc else ""
    default_port = (scheme == "http" and port == 80) or (
        scheme == "https" and port == 443
    )
    authority = userinfo + hostname
    if port is not None and not default_port:
        authority += f":{port}"

    normalized = f"{scheme}://{authority}{parts.path or '/'}"
    before_fragment = url.split("#", 1)[0]
    has_query_delimiter = "?" in before_fragment
    has_fragment_delimiter = "#" in url
    if has_query_delimiter:
        normalized += f"?{parts.query}"
    if has_fragment_delimiter:
        normalized += f"#{parts.fragment}"
    return normalized


def _review_pairs(entries):
    return [
        {
            "left": {
                "line_number": left["line_number"],
                "display_name": left["display_name"],
                "url": left["url"],
            },
            "right": {
                "line_number": right["line_number"],
                "display_name": right["display_name"],
                "url": right["url"],
            },
            "review_status": "pending",
            "deletion_proposed": False,
        }
        for left, right in combinations(entries, 2)
    ]


def group_duplicate_urls(entries):
    exact_by_url = {}
    normalized_by_url = {}
    for entry in entries:
        exact_by_url.setdefault(entry["url"], []).append(entry)
        normalized_url = normalize_url_conservatively(entry["url"])
        if normalized_url is not None:
            normalized_by_url.setdefault(normalized_url, []).append(entry)

    exact_groups = [
        {
            "url": url,
            "entries": group,
            "review_pairs": _review_pairs(group),
            "deletion_proposed": False,
        }
        for url, group in exact_by_url.items()
        if len(group) > 1
    ]
    normalized_groups = [
        {
            "normalized_url": normalized_url,
            "entries": group,
            "review_pairs": _review_pairs(group),
            "deletion_proposed": False,
        }
        for normalized_url, group in normalized_by_url.items()
        if len({entry["url"] for entry in group}) > 1
    ]
    return exact_groups, normalized_groups


def analyze_markdown(markdown_text, source_file="<memory>"):
    entries = parse_entries(markdown_text, source_file)
    exact_groups, normalized_groups = group_duplicate_urls(entries)
    by_url = {}
    for entry in entries:
        by_url.setdefault(entry["url"], []).append(entry)

    selected_entries = []
    errors = []
    for url, expected in SELECTED_ENTRIES.items():
        matches = by_url.get(url, [])
        if not matches:
            errors.append(f"Missing selected URL: {url}")
            continue
        if len(matches) > 1:
            errors.append(f"Selected URL appears multiple times: {url}")
        found = matches[0]
        selected_entries.append(found)
        for key in ("display_name", "category", "line_number"):
            if found[key] != expected[key]:
                errors.append(
                    f"{key} mismatch for {url}: expected {expected[key]!r}, "
                    f"got {found[key]!r}"
                )

    return {
        "source_file": source_file,
        "entry_count": len(entries),
        "selected_entries": selected_entries,
        "exact_duplicate_groups": exact_groups,
        "normalized_match_groups": normalized_groups,
        "proposed_deletions": [],
        "errors": errors,
        "passed": not errors,
    }


def analyze_file(target_file):
    markdown_text = target_file.read_text(encoding="utf-8")
    try:
        source_file = str(target_file.relative_to(REPO_ROOT))
    except ValueError:
        source_file = str(target_file)
    return analyze_markdown(markdown_text, source_file)


def _fixture_summary(report):
    return {
        "exact_duplicate_groups": [
            {
                "url": group["url"],
                "display_names": [entry["display_name"] for entry in group["entries"]],
            }
            for group in report["exact_duplicate_groups"]
        ],
        "normalized_match_groups": [
            {
                "normalized_url": group["normalized_url"],
                "source_urls": sorted({entry["url"] for entry in group["entries"]}),
            }
            for group in report["normalized_match_groups"]
        ],
        "proposed_deletions": report["proposed_deletions"],
        "entry_count": report["entry_count"],
    }


def run_self_test(target_file, work_dir):
    fixture_path = work_dir / "fixture_input.md"
    failure_fixture_path = work_dir / "fixture_catalogue_failure.md"
    fixture_text = fixture_path.read_text(encoding="utf-8")
    fixture_report = analyze_markdown(fixture_text, fixture_path.name)
    expected_fixture = {
        "exact_duplicate_groups": [
            {
                "url": "https://example.org/exact.pdf",
                "display_names": ["Exact One", "Exact Duplicate"],
            }
        ],
        "normalized_match_groups": [
            {
                "normalized_url": "https://example.org/book.pdf",
                "source_urls": [
                    "https://EXAMPLE.org:443/book.pdf",
                    "https://example.org/book.pdf",
                ],
            },
            {
                "normalized_url": "https://example.org/",
                "source_urls": ["https://example.org", "https://example.org/"],
            },
        ],
        "proposed_deletions": [],
        "entry_count": 13,
    }
    fixture_actual = _fixture_summary(fixture_report)
    assert fixture_actual == expected_fixture, (
        f"Duplicate fixture mismatch: expected {expected_fixture}, got {fixture_actual}"
    )

    distinct_urls = {
        entry["url"]
        for entry in parse_entries(fixture_text, fixture_path.name)
    }
    for url in (
        "https://example.org/guide#chapter-1",
        "https://example.org/guide#chapter-2",
        "https://example.org/download?edition=1",
        "https://example.org/download?edition=2",
        "https://example.org/search?a=1&b=2",
        "https://example.org/search?b=2&a=1",
        "http://example.org/book.pdf",
    ):
        assert url in distinct_urls, f"Fixture URL missing: {url}"
        normalized_matches = [
            group
            for group in fixture_report["normalized_match_groups"]
            if any(entry["url"] == url for entry in group["entries"])
        ]
        assert not normalized_matches, (
            f"Meaningful query, fragment, or scheme was merged for {url}"
        )

    source_report = analyze_file(target_file)
    assert source_report["passed"], f"Selected entries failed: {source_report['errors']}"
    assert len(source_report["selected_entries"]) == 3
    assert source_report["proposed_deletions"] == []
    assert all(
        pair["deletion_proposed"] is False
        for group in (
            source_report["exact_duplicate_groups"]
            + source_report["normalized_match_groups"]
        )
        for pair in group["review_pairs"]
    )

    failure_cli = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--file",
            str(failure_fixture_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure_cli.returncode != 0, (
        "The checker CLI returned success for a catalogue missing selected entries"
    )

    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "task_id": "R10-T023",
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "fixture": {
            "input": fixture_path.name,
            "expected_summary": expected_fixture,
            "actual_summary": fixture_actual,
            "actual_report": fixture_report,
        },
        "source_analysis": {
            "input": source_report["source_file"],
            "selected_expected": SELECTED_ENTRIES,
            "actual": source_report,
        },
        "failure_cli": {
            "input": failure_fixture_path.name,
            "expected_exit_code": "non-zero",
            "actual_exit_code": failure_cli.returncode,
            "stdout": failure_cli.stdout,
            "stderr": failure_cli.stderr,
        },
        "self_test_passed": True,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "results.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("SELF-TEST PASSED: duplicate grouping and distinct-URL assertions succeeded.")
    print(json.dumps(source_report, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Group exact URL duplicates and conservative normalization candidates "
            "in books/free-programming-books-cs.md."
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
