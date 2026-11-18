#!/usr/bin/env python3
"""Offline fixture parser and validator for the Myanmar React cast list."""

from __future__ import annotations

import argparse
import io
import json
import platform
import re
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-my.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T026"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2

SELECTED_ENTRY = {
    "display_name": "Learn React Docker And Containerized In Myanmar Language",
    "url": "https://www.youtube.com/watch?v=Qqr8oabREA8",
    "category": "React",
    "line_number": 8,
    "creator": "MyanmarFullStackDevelopers",
    "kind": "screencast",
}

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)
FALLBACK_ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]*)\]"
    r"\((?P<url>[^)]*)\)(?P<metadata>.*)$"
)


def parse_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse catalogue rows and retain line/category metadata."""
    entries: list[dict[str, Any]] = []
    hierarchy: dict[int, str] = {}
    fence_char: str | None = None
    fence_length = 0

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            if fence_char is None:
                fence_char, fence_length = fence[0], len(fence)
            elif fence[0] == fence_char and len(fence) >= fence_length:
                fence_char, fence_length = None, 0
            continue
        if fence_char is not None:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            hierarchy = {
                depth: title
                for depth, title in hierarchy.items()
                if depth < level
            }
            hierarchy[level] = re.sub(
                r"<[^>]*>", "", heading_match.group(2).strip()
            )
            continue

        entry_match = ENTRY_RE.match(line)
        if entry_match is None:
            entry_match = FALLBACK_ENTRY_RE.match(line)
        if entry_match is None:
            continue

        metadata = entry_match.group("metadata").strip()
        creator = None
        kind = None
        creator_match = re.match(r"^-\s*(.+?)(?:\s+\(([^()]*)\))?$", metadata)
        if creator_match:
            creator = creator_match.group(1).strip()
            kind = creator_match.group(2)
        elif metadata.startswith("(") and metadata.endswith(")"):
            kind = metadata[1:-1]

        entries.append(
            {
                "display_name": entry_match.group("display_name"),
                "url": entry_match.group("url"),
                "category": " > ".join(
                    hierarchy[depth] for depth in sorted(hierarchy)
                )
                or None,
                "line_number": line_number,
                "metadata": metadata,
                "creator": creator,
                "kind": kind.lower() if kind else None,
            }
        )
    return entries


def validate_row(row: dict[str, Any]) -> list[str]:
    """Return explicit validation failures for malformed catalogue rows."""
    failures = []
    for field in ("display_name", "url", "category", "line_number"):
        if row.get(field) in (None, ""):
            failures.append(f"missing:{field}")

    url = row.get("url")
    if url:
        if not re.match(r"^https?://", url):
            failures.append("invalid:url-scheme")
        if any(char.isspace() for char in url):
            failures.append("invalid:url-whitespace")
        if "[" in url or "]" in url or "{" in url or "}" in url:
            failures.append("invalid:url-character")
    return failures


def select_required_entry(entries: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [entry for entry in entries if entry["url"] == SELECTED_ENTRY["url"]]
    if not matches:
        raise AssertionError("missing entry: Learn React Docker And Containerized")
    if len(matches) > 1:
        raise AssertionError("duplicate entry: Learn React Docker And Containerized")
    return matches[0]


def compare_expected(actual: dict[str, Any]) -> list[dict[str, Any]]:
    mismatches = []
    for field in ("display_name", "url", "category", "line_number", "creator", "kind"):
        if actual.get(field) != SELECTED_ENTRY[field]:
            mismatches.append(
                {
                    "field": field,
                    "expected": SELECTED_ENTRY[field],
                    "actual": actual.get(field),
                }
            )
    return mismatches


def check_url(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Optional bounded availability check; failures never imply removal."""
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "R10-T026 offline fixture checker/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "url": url,
                "status": "success",
                "http_status": response.status,
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as error:
        return {
            "url": url,
            "status": "http_error",
            "http_status": error.code,
            "error": str(error),
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"url": url, "status": "request_failed", "error": str(error)}


def verify_live(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixed = [entry for entry in entries if entry["url"] == SELECTED_ENTRY["url"]]
    with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
        return list(executor.map(lambda entry: check_url(entry["url"]), fixed))


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> list[dict[str, Any]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_valid_row_fixture(self) -> None:
        entries = self.fixture_entries("valid.md")
        selected = select_required_entry(entries)
        self.assertEqual(validate_row(selected), [])
        self.assertEqual(selected["display_name"], SELECTED_ENTRY["display_name"])
        self.assertEqual(selected["category"], "React")
        self.assertEqual(selected["creator"], "MyanmarFullStackDevelopers")
        self.assertEqual(selected["kind"], "screencast")

    def test_malformed_rows_have_explicit_outcomes(self) -> None:
        entries = self.fixture_entries("malformed.md")
        outcomes = {
            validate_row(row)[0]: validate_row(row)
            for row in entries
        }
        self.assertIn("missing:display_name", outcomes)
        self.assertIn("invalid:url-scheme", outcomes)
        self.assertIn("invalid:url-whitespace", outcomes)
        self.assertIn("invalid:url-character", outcomes)

    def test_unusual_url_characters_are_preserved_and_validated(self) -> None:
        entries = self.fixture_entries("unusual-url.md")
        row = entries[0]
        self.assertEqual(row["url"], "https://example.test/video?id=1&lang=myanmar#anchor")
        self.assertEqual(validate_row(row), [])
        self.assertEqual(row["display_name"], "Fixture | React & Docker")

    def test_fenced_rows_are_not_catalogue_entries(self) -> None:
        self.assertEqual(self.fixture_entries("fenced.md"), [])

    def test_source_entry_matches_expected_fields(self) -> None:
        actual = select_required_entry(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        self.assertEqual(validate_row(actual), [])
        self.assertEqual(compare_expected(actual), [])

    def test_missing_entry_raises_assertion(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entry([])

    def test_failed_request_does_not_remove_entry(self) -> None:
        source = select_required_entry(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        with patch(f"{__name__}.check_url", return_value={
            "url": source["url"],
            "status": "request_failed",
            "error": "simulated timeout",
        }):
            results = verify_live([source])
        self.assertEqual(results[0]["status"], "request_failed")
        self.assertEqual(select_required_entry([source]), source)

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t026.py", "--self-test"]), patch(
            f"{__name__}.test_output",
            return_value=(False, "simulated assertion failure\n"),
        ), patch(f"{__name__}.write_evidence"), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)


def test_output() -> tuple[bool, str]:
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CourseCheckTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return result.wasSuccessful(), stream.getvalue()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_evidence(
    actual: dict[str, Any] | None,
    validation_error: str | None,
    self_test_status: str,
    self_test_output: str,
    live_results: list[dict[str, Any]] | None,
) -> None:
    mismatches = compare_expected(actual) if actual else []
    inputs = {
        "target_file": "casts/free-podcasts-screencasts-my.md",
        "target_section": "React",
        "selected_entry": SELECTED_ENTRY,
        "live_limits": {
            "timeout_seconds": LIVE_TIMEOUT_SECONDS,
            "max_workers": LIVE_MAX_WORKERS,
        },
    }
    expected_vs_actual = {
        "expected": SELECTED_ENTRY,
        "actual": actual,
        "validation": {
            "status": "passed" if not mismatches and validation_error is None else "failed",
            "mismatches": mismatches,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
        "live_request_results": live_results,
    }
    write_json(EVIDENCE_DIR / "inputs.json", inputs)
    write_json(EVIDENCE_DIR / "expected_vs_actual.json", expected_vs_actual)
    (EVIDENCE_DIR / "self-test-output.txt").write_text(
        self_test_output, encoding="utf-8"
    )

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (EVIDENCE_DIR / "tool_versions.txt").write_text(
        f"Python: {sys.version.splitlines()[0]}\n"
        f"Platform: {platform.platform()}\n"
        f"Git commit: {commit}\n"
        f"Git branch: {branch}\n",
        encoding="utf-8",
    )

    report = [
        "# R10-T026 offline fixture report",
        "",
        "- Source: `casts/free-podcasts-screencasts-my.md`",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Live request checks: {'run' if live_results is not None else 'not run'}",
        "",
        "## Selected entry",
        "",
    ]
    if actual:
        report.append(
            f"- Line {actual['line_number']}: {actual['display_name']} "
            f"`{actual['url']}` - {actual['creator']} ({actual['kind']})"
        )
    if validation_error:
        report.extend(["", f"Validation error: `{validation_error}`"])
    report.extend(
        [
            "",
            "The suite is offline by default. Live HEAD checks are optional and never",
            "remove a resource after a failed automated request.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixture tests")
    parser.add_argument(
        "--live",
        action="store_true",
        help="make an optional bounded HEAD request to the fixed entry",
    )
    args = parser.parse_args()

    self_test_status = "not_run"
    self_test_output = ""
    tests_passed = True
    if args.self_test:
        tests_passed, self_test_output = test_output()
        self_test_status = "passed" if tests_passed else "failed"
        print(self_test_output, end="")

    actual = None
    validation_error = None
    try:
        actual = select_required_entry(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        mismatches = compare_expected(actual)
        if mismatches:
            validation_error = json.dumps(mismatches, ensure_ascii=False)
    except (OSError, AssertionError) as error:
        validation_error = str(error)

    live_results = None
    if args.live and actual:
        live_results = verify_live([actual])

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        live_results,
    )

    if validation_error:
        print(f"r10-t026: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1
    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
