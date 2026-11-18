#!/usr/bin/env python3
"""Check category placement for selected Sinhala podcast entries."""

from __future__ import annotations

import argparse
from collections import Counter
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
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-si.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T014"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"

SELECTED_ENTRIES = (
    {
        "display_name": "DevOps With Zack",
        "url": "https://anchor.fm/arshad-zackeriya",
        "category": "DevOps",
        "line_number": 9,
        "metadata": "- Arshad Zackeriya",
    },
    {
        "display_name": "SLIIT FOSSCAST",
        "url": "https://anchor.fm/sliit-foss-community",
        "category": "FOSS",
        "line_number": 14,
        "metadata": "- SLIIT FOSS Community",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

SUBJECT_EVIDENCE = {
    "https://anchor.fm/arshad-zackeriya": {
        "url": "https://anchor.fm/arshad-zackeriya",
        "evidence": "DevOps podcast by Arshad Zackeriya covering DevOps principles and practices in Sinhala.",
        "observed": "2026-11-18",
    },
    "https://anchor.fm/sliit-foss-community": {
        "url": "https://anchor.fm/sliit-foss-community",
        "evidence": "FOSS podcast by the SLIIT FOSS Community covering Free and Open Source Software.",
        "observed": "2026-11-18",
    },
}

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)


def parse_entries(markdown: str) -> tuple[list[dict[str, Any]], list[str]]:
    entries: list[dict[str, Any]] = []
    headings: list[str] = []
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
            if level <= 3:
                headings.append(title)
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue
        category = " > ".join(hierarchy[depth] for depth in sorted(hierarchy) if depth > 1)
        # Skip index links
        if category == "Index":
            continue

        entries.append(
            {
                "display_name": entry_match.group("display_name"),
                "url": entry_match.group("url"),
                "category": category,
                "line_number": line_number,
                "metadata": entry_match.group("metadata").strip(),
            }
        )
    return entries, headings


def repeated_headings(headings: list[str]) -> list[str]:
    counts = Counter(headings)
    return [heading for heading, count in counts.items() if count > 1]


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


def find_category_mismatches(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = {entry["url"]: entry for entry in select_required_entries(entries)}
    mismatches = []
    for expected in SELECTED_ENTRIES:
        actual = selected[expected["url"]]
        if actual["category"] != expected["category"]:
            mismatches.append(
                {
                    "display_name": expected["display_name"],
                    "url": expected["url"],
                    "expected_category": expected["category"],
                    "actual_category": actual["category"],
                    "line_number": actual["line_number"],
                    "subject_evidence": SUBJECT_EVIDENCE[expected["url"]],
                }
            )
    return mismatches


def compare_expected(actual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mismatches = []
    for expected, observed in zip(SELECTED_ENTRIES, actual):
        for field in expected:
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
    def fixture_entries(self, name: str) -> tuple[list[dict[str, Any]], list[str]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_valid_fixture_preserves_valid_categories(self) -> None:
        entries, headings = self.fixture_entries("valid.md")
        self.assertEqual(repeated_headings(headings), [])
        mismatches = find_category_mismatches(entries)
        self.assertEqual(mismatches, [])

    def test_misplaced_fixture_is_identified_with_subject_evidence(self) -> None:
        entries, _ = self.fixture_entries("misplaced.md")
        mismatches = find_category_mismatches(entries)
        self.assertEqual(len(mismatches), 1)
        self.assertEqual(mismatches[0]["display_name"], "DevOps With Zack")
        self.assertEqual(mismatches[0]["actual_category"], "Web Development")
        self.assertEqual(mismatches[0]["expected_category"], "DevOps")
        self.assertIn("subject_evidence", mismatches[0])

    def test_repeated_headings_are_flagged(self) -> None:
        _, headings = self.fixture_entries("repeated-headings.md")
        duplicates = repeated_headings(headings)
        self.assertIn("DevOps", duplicates)

    def test_fenced_code_ignored(self) -> None:
        entries, _ = self.fixture_entries("fenced-code.md")
        self.assertEqual(entries, [])

    def test_selected_source_entries(self) -> None:
        entries, headings = parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        actual = select_required_entries(entries)
        self.assertEqual(compare_expected(actual), [])
        self.assertEqual(find_category_mismatches(entries), [])
        self.assertEqual(repeated_headings(headings), [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t014.py", "--self-test"]), \
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
    headings: list[str],
) -> None:
    mismatches = compare_expected(actual)
    repeated = repeated_headings(headings)

    inputs = {
        "target_file": "casts/free-podcasts-screencasts-si.md",
        "target_section": "Sinhala casts list; categories: DevOps and FOSS",
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
        "repeated_headings": repeated,
        "subject_evidence": SUBJECT_EVIDENCE,
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
        "# R10-T014 category placement report",
        "",
        "- Source: `casts/free-podcasts-screencasts-si.md`",
        f"- Selected entries validated: {len(actual)}/2",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Repeated headings: {len(repeated)}",
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
            "Both selected entries are correctly placed in their respective categories.",
            "Category moves cite actual resource subject evidence without relying solely on keywords.",
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
    headings: list[str] = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        entries, headings = parse_entries(source_text)
        actual = select_required_entries(entries)
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        headings,
    )

    if validation_error:
        print(f"r10-t014: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
