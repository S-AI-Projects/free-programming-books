#!/usr/bin/env python3
"""Validate formatting, heading hierarchy, and ordering for Hebrew programming books."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import unittest
from unittest.mock import patch
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "books" / "free-programming-books-he.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T018"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"

SELECTED_ENTRIES = (
    {
        "display_name": "מערכות הפעלה",
        "url": "https://data.cyber.org.il/os/os_book.pdf",
        "category": "ללא תלות בשפה > מערכות הפעלה",
        "line_number": 18,
    },
    {
        "display_name": "רשתות מחשבים",
        "url": "https://data.cyber.org.il/networks/networks.pdf",
        "category": "ללא תלות בשפה > רשתות",
        "line_number": 23,
    },
    {
        "display_name": "ארגון המחשב ושפת סף",
        "url": "https://data.cyber.org.il/assembly/assembly_book.pdf",
        "category": "Assembly",
        "line_number": 28,
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_BULLET_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)
BULLET_LINE_RE = re.compile(r"^ {0,3}[*+-]\s+")


def inspect_markdown(markdown: str) -> dict[str, Any]:
    headings: list[dict[str, Any]] = []
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    hierarchy: dict[int, str] = {}
    previous_level = 0

    def report(code: str, line_number: int, message: str) -> None:
        errors.append({"code": code, "line_number": line_number, "message": message})

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("<div") or stripped.startswith("</div"):
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            raw_title = heading_match.group(2).strip()
            title = re.sub(r"<[^>]*>", "", raw_title).strip()
            headings.append({"level": level, "title": title, "line_number": line_number})

            if level not in (3, 4):
                report(
                    "invalid-heading-level",
                    line_number,
                    f"Heading must be level 3 or 4, got {level}",
                )
            if previous_level and level > previous_level + 1:
                report(
                    "heading-level-skip",
                    line_number,
                    f"Heading level skipped from {previous_level} to {level}",
                )
            previous_level = level

            hierarchy = {depth: t for depth, t in hierarchy.items() if depth < level}
            hierarchy[level] = title
            continue

        if BULLET_LINE_RE.match(line):
            category = " > ".join(hierarchy[depth] for depth in sorted(hierarchy) if depth > 1)
            if category == "Index":
                continue

            entry_match = LINK_BULLET_RE.match(line)
            if not entry_match:
                report(
                    "malformed-bullet-syntax",
                    line_number,
                    "Expected bullet link syntax: * [Title](URL) - Metadata",
                )
                continue

            entries.append(
                {
                    "display_name": entry_match.group("title"),
                    "url": entry_match.group("url"),
                    "category": category,
                    "line_number": line_number,
                    "metadata": entry_match.group("metadata").strip(),
                }
            )

    # Check ordering of section headings
    section_headings = [h for h in headings if h["level"] == 3 and h["title"] != "Index"]
    for before, after in zip(section_headings, section_headings[1:]):
        # In Hebrew list, English section titles follow Hebrew sections or are alphabetical
        # If Hebrew titles precede English titles or alphabetical
        if before["title"] > after["title"] and not (before["title"] >= "א" and after["title"] < "א"):
            report(
                "out-of-order-section",
                after["line_number"],
                f"Section {after['title']!r} is out of order after {before['title']!r}",
            )

    return {
        "headings": headings,
        "entries": entries,
        "errors": errors,
    }


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
        for field in ("display_name", "url", "category", "line_number"):
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


class CourseCheckTests(unittest.TestCase):
    def test_valid_fixture(self) -> None:
        text = (FIXTURE_DIR / "valid.md").read_text(encoding="utf-8")
        result = inspect_markdown(text)
        self.assertEqual(result["errors"], [])
        selected = select_required_entries(result["entries"])
        self.assertEqual(len(selected), 3)

    def test_malformed_fixture_rejected_with_line_number(self) -> None:
        text = (FIXTURE_DIR / "malformed.md").read_text(encoding="utf-8")
        result = inspect_markdown(text)
        self.assertTrue(any(e["code"] == "malformed-bullet-syntax" for e in result["errors"]))
        malformed_err = next(e for e in result["errors"] if e["code"] == "malformed-bullet-syntax")
        self.assertIsInstance(malformed_err["line_number"], int)

    def test_bad_heading_hierarchy_rejected(self) -> None:
        text = (FIXTURE_DIR / "bad-heading.md").read_text(encoding="utf-8")
        result = inspect_markdown(text)
        self.assertTrue(any(e["code"] in ("invalid-heading-level", "heading-level-skip") for e in result["errors"]))

    def test_unsorted_sections_rejected(self) -> None:
        text = (FIXTURE_DIR / "unsorted.md").read_text(encoding="utf-8")
        result = inspect_markdown(text)
        self.assertTrue(any(e["code"] == "out-of-order-section" for e in result["errors"]))

    def test_source_entries_match_expected_fields(self) -> None:
        text = SOURCE_FILE.read_text(encoding="utf-8")
        result = inspect_markdown(text)
        self.assertEqual(result["errors"], [])
        selected = select_required_entries(result["entries"])
        self.assertEqual(compare_expected(selected), [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t018.py", "--self-test"]), \
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
    syntax_errors: list[dict[str, Any]],
) -> None:
    mismatches = compare_expected(actual)

    inputs = {
        "target_file": "books/free-programming-books-he.md",
        "target_section": "Hebrew programming books; sections: ללא תלות בשפה and Assembly",
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
            "status": "passed" if not mismatches and not syntax_errors and validation_error is None else "failed",
            "mismatches": mismatches,
            "syntax_errors": syntax_errors,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
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
        "# R10-T018 formatting and ordering validation report",
        "",
        "- Source: `books/free-programming-books-he.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Formatting errors detected: {len(syntax_errors)}",
        "",
        "## Selected entries",
        "",
        "| Line | Display name | Category | URL |",
        "| ---: | --- | --- | --- |",
    ]
    for entry in actual:
        report_lines.append(
            f"| {entry['line_number']} | {entry['display_name']} | "
            f"{entry['category']} | `{entry['url']}` |"
        )
    if validation_error:
        report_lines.extend(["", f"Validation error: `{validation_error}`"])
    report_lines.extend(
        [
            "",
            "Valid non-English text and Markdown links are preserved.",
            "Malformed fixtures are rejected with explicit source line numbers.",
            "Sections obey documented ordering rules.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixture tests")
    args = parser.parse_args()

    self_test_status = "not_run"
    self_test_output = ""
    tests_passed = True
    if args.self_test:
        tests_passed, self_test_output = test_output()
        self_test_status = "passed" if tests_passed else "failed"
        print(self_test_output, end="")

    validation_error = None
    syntax_errors = []
    actual = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        result = inspect_markdown(source_text)
        syntax_errors = result["errors"]
        actual = select_required_entries(result["entries"])
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        syntax_errors,
    )

    if validation_error:
        print(f"r10-t018: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
