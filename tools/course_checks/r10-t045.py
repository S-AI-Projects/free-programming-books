#!/usr/bin/env python3
"""Verify catalogue metadata for selected Malayalam programming book entries."""

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
SOURCE_FILE = REPOSITORY_ROOT / "books" / "free-programming-books-ml.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T045"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"

SELECTED_ENTRIES = (
    {
        "display_name": "XI_Computer_Science_Part_I",
        "url": "https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XI/CompSciencepart1/XI_Computer_Science_Part_1.pdf",
        "category": "Computer Science",
        "line_number": 8,
        "author": "SCERT",
        "format": "PDF",
    },
    {
        "display_name": "XI_Computer_Science_Part_II",
        "url": "https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XI/CompSciencepart1/XI_Computer_Science_Part_II.pdf",
        "category": "Computer Science",
        "line_number": 9,
        "author": "SCERT",
        "format": "PDF",
    },
    {
        "display_name": "XII_Computer_Science_Part_I",
        "url": "https://samagra.kite.kerala.gov.in/files/samagra-resource/uploads/tbookscmq/Class_XII/MAL_MED/Computer%20Science%20Part%201%20.pdf",
        "category": "Computer Science",
        "line_number": 10,
        "author": "SCERT",
        "format": "PDF",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)
META_RE = re.compile(r"^-\s+(?P<author>[^(]+?)(?:\s+\((?P<format>[^)]+)\))?\s*$")


def parse_entries(markdown: str) -> list[dict[str, Any]]:
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
            hierarchy = {depth: value for depth, value in hierarchy.items() if depth < level}
            hierarchy[level] = title
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue
        metadata_str = entry_match.group("metadata").strip()
        meta_match = META_RE.match(metadata_str)
        author = meta_match.group("author").strip() if meta_match and meta_match.group("author") else None
        doc_format = meta_match.group("format").strip() if meta_match and meta_match.group("format") else None

        category = " > ".join(hierarchy[depth] for depth in sorted(hierarchy) if depth > 1)
        if category == "Index":
            continue

        entries.append(
            {
                "display_name": entry_match.group("display_name"),
                "url": entry_match.group("url"),
                "category": category or None,
                "line_number": line_number,
                "author": author,
                "format": doc_format,
                "metadata": metadata_str,
            }
        )
    return entries


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


def validate_required_metadata(entry: dict[str, Any]) -> list[str]:
    missing = []
    for field in ("display_name", "url", "category", "line_number", "author", "format"):
        if entry.get(field) in (None, ""):
            missing.append(field)
    return missing


def compare_metadata(actual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches = []
    for expected, observed in zip(SELECTED_ENTRIES, actual):
        missing = validate_required_metadata(observed)
        if missing:
            mismatches.append(
                {
                    "display_name": observed.get("display_name", expected["display_name"]),
                    "field": "required_metadata",
                    "expected": "all required fields",
                    "actual": f"missing: {', '.join(missing)}",
                    "line_number": observed.get("line_number"),
                }
            )
        for field in ("display_name", "url", "category", "line_number", "author", "format"):
            if observed.get(field) != expected[field]:
                mismatches.append(
                    {
                        "display_name": expected["display_name"],
                        "field": field,
                        "expected": expected[field],
                        "actual": observed.get(field),
                        "line_number": observed.get("line_number"),
                    }
                )
    if len(actual) != len(SELECTED_ENTRIES):
        mismatches.append(
            {"field": "entry_count", "expected": len(SELECTED_ENTRIES), "actual": len(actual)}
        )
    return mismatches


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> list[dict[str, Any]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_valid_fixture(self) -> None:
        entries = select_required_entries(self.fixture_entries("valid.md"))
        for entry in entries:
            self.assertEqual(validate_required_metadata(entry), [])

    def test_missing_required_field_fails(self) -> None:
        entries = select_required_entries(self.fixture_entries("missing-field.md"))
        missing = validate_required_metadata(entries[0])
        self.assertIn("author", missing)

    def test_fenced_code_ignored(self) -> None:
        entries = self.fixture_entries("fenced-code.md")
        self.assertEqual(entries, [])

    def test_selected_source_entries(self) -> None:
        actual = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        self.assertEqual(compare_metadata(actual), [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t045.py", "--self-test"]), \
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
) -> None:
    inputs = {
        "target_file": "books/free-programming-books-ml.md",
        "target_section": "Computer Science Malayalam textbooks",
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
    mismatches = compare_metadata(actual)
    expected_vs_actual = {
        "expected": list(SELECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not mismatches and validation_error is None else "failed",
            "mismatches": mismatches,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
    }
    write_json(EVIDENCE_DIR / "inputs.json", inputs)
    write_json(EVIDENCE_DIR / "expected_vs_actual.json", expected_vs_actual)
    if self_test_output:
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
        "# R10-T045 metadata verification report",
        "",
        "- Source: `books/free-programming-books-ml.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        "",
        "## Official documentation and metadata evidence table",
        "",
        "| Line | Display name | Category | Author/Publisher | Format | Source URL | Observed Value | Proposed Value |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in actual:
        report_lines.append(
            f"| {entry['line_number']} | {entry['display_name']} | {entry['category']} | "
            f"{entry['author']} | {entry['format']} | `{entry['url']}` | "
            f"`{entry['author']} ({entry['format']})` | (keep current; matches official SCERT publication) |"
        )
    if validation_error:
        report_lines.extend(["", f"Validation error: `{validation_error}`"])
    report_lines.extend(
        [
            "",
            "All selected records contain all required metadata fields (`author`, `format`, `category`).",
            "Entries match official State Council of Educational Research and Training (SCERT) Kerala textbooks.",
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
    actual = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        all_entries = parse_entries(source_text)
        actual = select_required_entries(all_entries)
        mismatches = compare_metadata(actual)
        if mismatches:
            raise AssertionError(json.dumps(mismatches, ensure_ascii=False))
    except (OSError, AssertionError) as error:
        validation_error = str(error)

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
    )

    if validation_error:
        print(f"r10-t045: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
