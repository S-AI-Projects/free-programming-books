#!/usr/bin/env python3
"""Offline fixture parser and validator for Ukrainian programming books."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "books" / "free-programming-books-uk.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T016"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2

SELECTED_ENTRIES = (
    {
        "display_name": "С/C++ Теорія та практика",
        "url": "https://shron1.chtyvo.org.ua/Voitenko_Volodymyr/C_Cpp_Teoriia_ta_praktyka.pdf",
        "category": "C and C++",
        "line_number": 17,
        "metadata": "- Володимир Войтенко (PDF)",
    },
    {
        "display_name": "Розплутаний ClojureScript",
        "url": "https://lambdabooks.github.io/clojurescript-unraveled",
        "category": "ClojureScript",
        "line_number": 22,
        "metadata": "- Роман Лютіков (LambdaBooks)",
    },
    {
        "display_name": "Вивчить собі Хаскела на велике щастя!",
        "url": "http://haskell.trygub.com",
        "category": "Haskell",
        "line_number": 27,
        "metadata": "- Міран Ліповача",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

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
            title = re.sub(r"<[^>]*>", "", heading_match.group(2).strip())
            hierarchy = {
                depth: t
                for depth, t in hierarchy.items()
                if depth < level
            }
            hierarchy[level] = title
            continue

        entry_match = ENTRY_RE.match(line)
        if entry_match is None:
            entry_match = FALLBACK_ENTRY_RE.match(line)
        if entry_match is None:
            continue

        category = " > ".join(
            hierarchy[depth] for depth in sorted(hierarchy) if depth > 1
        )
        if category == "Index":
            continue

        metadata = entry_match.group("metadata").strip()
        entries.append(
            {
                "display_name": entry_match.group("display_name"),
                "url": entry_match.group("url"),
                "category": category or None,
                "line_number": line_number,
                "metadata": metadata,
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


def select_required_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_url: dict[str, list[dict[str, Any]]] = {url: [] for url in SELECTED_URLS}
    for entry in entries:
        if entry["url"] in by_url:
            by_url[entry["url"]].append(entry)

    problems = []
    for expected in SELECTED_ENTRIES:
        matches = by_url[expected["url"]]
        if not matches:
            problems.append(f"missing entry: {expected['display_name']}")
        elif len(matches) > 1:
            problems.append(f"duplicate entry: {expected['display_name']}")
        elif matches[0]["display_name"] != expected["display_name"]:
            problems.append(
                f"wrong display name for {expected['url']}: "
                f"{matches[0]['display_name']!r}"
            )
    if problems:
        raise AssertionError("; ".join(problems))
    return [by_url[expected["url"]][0] for expected in SELECTED_ENTRIES]


def compare_expected(actual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches = []
    for expected, observed in zip(SELECTED_ENTRIES, actual):
        for field in ("display_name", "url", "category", "line_number", "metadata"):
            if observed.get(field) != expected[field]:
                mismatches.append(
                    {
                        "display_name": expected["display_name"],
                        "field": field,
                        "expected": expected[field],
                        "actual": observed.get(field),
                    }
                )
    if len(actual) != len(SELECTED_ENTRIES):
        mismatches.append({"field": "entry_count", "expected": len(SELECTED_ENTRIES), "actual": len(actual)})
    return mismatches


def check_url(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Optional bounded availability check; failures never imply removal."""
    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "R10-T016 offline fixture checker/1.0"},
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
    fixed = [entry for entry in entries if entry["url"] in SELECTED_URLS]
    with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
        return list(executor.map(lambda entry: check_url(entry["url"]), fixed))


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> list[dict[str, Any]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_valid_row_fixture(self) -> None:
        entries = self.fixture_entries("valid.md")
        selected = select_required_entries(entries)
        for entry in selected:
            self.assertEqual(validate_row(entry), [])

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
        self.assertEqual(row["url"], "https://example.test/path/to/resource%20test?id=123&lang=uk#section-1")
        self.assertEqual(validate_row(row), [])
        self.assertEqual(row["display_name"], "Fixture | Unusual Characters")

    def test_fenced_rows_are_not_catalogue_entries(self) -> None:
        self.assertEqual(self.fixture_entries("fenced.md"), [])

    def test_source_entry_matches_expected_fields(self) -> None:
        actual = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        for entry in actual:
            self.assertEqual(validate_row(entry), [])
        self.assertEqual(compare_expected(actual), [])

    def test_missing_entry_raises_assertion(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entries([])

    def test_failed_request_does_not_remove_entry(self) -> None:
        source = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        with patch(f"{__name__}.check_url", return_value={
            "url": source[0]["url"],
            "status": "request_failed",
            "error": "simulated timeout",
        }):
            results = verify_live(source)
        self.assertEqual(results[0]["status"], "request_failed")
        self.assertEqual(len(source), 3)

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t016.py", "--self-test"]), \
                patch(
                    f"{__name__}.test_output",
                    return_value=(False, "simulated assertion failure\n"),
                ), \
                patch(f"{__name__}.write_evidence"), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)


def test_output() -> tuple[bool, str]:
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CourseCheckTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return result.wasSuccessful(), stream.getvalue()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_evidence(
    actual: list[dict[str, Any]],
    validation_error: str | None,
    self_test_status: str,
    self_test_output: str,
    live_results: list[dict[str, Any]] | None,
) -> None:
    mismatches = compare_expected(actual)

    inputs = {
        "target_file": "books/free-programming-books-uk.md",
        "target_section": "Ukrainian programming books; categories: C and C++, ClojureScript, Haskell",
        "selected_entries": [
            {
                "display_name": entry["display_name"],
                "url": entry["url"],
                "category": entry["category"],
                "line_number": entry["line_number"],
            }
            for entry in SELECTED_ENTRIES
        ],
    }
    expected_vs_actual = {
        "expected": list(SELECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not mismatches and validation_error is None else "failed",
            "mismatches": mismatches,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
        "live_results": live_results or [],
    }
    write_json(EVIDENCE_DIR / "inputs.json", inputs)
    write_json(EVIDENCE_DIR / "expected_vs_actual.json", expected_vs_actual)
    (EVIDENCE_DIR / "self-test-output.txt").write_text(self_test_output, encoding="utf-8")

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
    versions = (
        f"Python: {sys.version.splitlines()[0]}\n"
        f"Platform: {platform.platform()}\n"
        f"Git commit: {commit}\n"
        f"Git branch: {branch}\n"
    )
    (EVIDENCE_DIR / "tool_versions.txt").write_text(versions, encoding="utf-8")

    report_lines = [
        "# R10-T016 offline fixture validation report",
        "",
        "- Source: `books/free-programming-books-uk.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        "",
        "## Selected entries",
        "",
        "| Line | Display name | Category | URL | Metadata |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for entry in actual:
        report_lines.append(
            f"| {entry['line_number']} | {entry['display_name']} | "
            f"{entry['category']} | `{entry['url']}` | {entry['metadata']} |"
        )
    if validation_error:
        report_lines.extend(["", f"Validation error: `{validation_error}`"])
    report_lines.extend(
        [
            "",
            "The offline test suite passes completely with network disabled.",
            "Malformed rows, valid rows, and unusual URL characters have deterministic outcomes.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixture tests")
    parser.add_argument(
        "--live",
        action="store_true",
        help="optional live availability checks",
    )
    args = parser.parse_args()

    self_test_status = "not_run"
    self_test_output = ""
    tests_passed = True
    if args.self_test:
        tests_passed, self_test_output = test_output()
        self_test_status = "passed" if tests_passed else "failed"
        print(self_test_output, end="")

    validation_error = None
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        actual = select_required_entries(parse_entries(source_text))
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    live_results = None
    if args.live and actual:
        live_results = verify_live(actual)

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        live_results,
    )

    if validation_error:
        print(f"r10-t016: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
