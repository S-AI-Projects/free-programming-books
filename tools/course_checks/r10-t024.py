#!/usr/bin/env python3
"""Check category placement for selected French podcast entries."""

from __future__ import annotations

import argparse
import io
import json
import platform
import re
import subprocess
import sys
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-fr.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T024"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"

SELECTED_ENTRIES = (
    {
        "display_name": "Le podcast AWS en français",
        "url": "https://aws.amazon.com/fr/blogs/france/podcasts",
        "category": "Cloud computing",
        "line_number": 9,
    },
    {
        "display_name": "Les Cast Codeurs Podcast",
        "url": "https://lescastcodeurs.com",
        "category": "Langage Agnostique",
        "line_number": 20,
    },
    {
        "display_name": "Artisan Developpeur",
        "url": "https://artisandeveloppeur.fr/podcast",
        "category": "Langage Agnostique",
        "line_number": 14,
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

SUBJECT_EVIDENCE = {
    "https://lescastcodeurs.com": {
        "url": "https://lescastcodeurs.com",
        "evidence": (
            "The homepage covers Java/JDK, Rust, TypeScript, PHP, data/AI, "
            "infrastructure, web, security, and tooling rather than Java alone."
        ),
        "observed": "2026-11-18",
    },
    "https://aws.amazon.com/fr/blogs/france/podcasts": {
        "url": "https://aws.amazon.com/fr/blogs/france/podcasts",
        "evidence": "The resource is an AWS France podcast list.",
        "observed": "2026-11-18",
    },
    "https://artisandeveloppeur.fr/podcast": {
        "url": "https://artisandeveloppeur.fr/podcast",
        "evidence": "The resource covers software craftsmanship and general development topics.",
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
        mismatches.append({"field": "entry_count", "expected": 3, "actual": len(actual)})
    return mismatches


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> tuple[list[dict[str, Any]], list[str]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_valid_fixture_preserves_categories(self) -> None:
        entries, headings = self.fixture_entries("valid.md")
        selected = select_required_entries(entries)
        selected_by_url = {entry["url"]: entry for entry in selected}
        for expected in SELECTED_ENTRIES:
            actual = selected_by_url[expected["url"]]
            self.assertEqual(actual["display_name"], expected["display_name"])
            self.assertEqual(actual["category"], expected["category"])
        self.assertEqual(repeated_headings(headings), [])

    def test_misplaced_fixture_is_detected(self) -> None:
        entries, _ = self.fixture_entries("misplaced.md")
        mismatches = find_category_mismatches(entries)
        self.assertEqual(len(mismatches), 1)
        mismatch = mismatches[0]
        self.assertEqual(mismatch["display_name"], "Les Cast Codeurs Podcast")
        self.assertEqual(mismatch["actual_category"], "Java")
        self.assertIn("Rust", mismatch["subject_evidence"]["evidence"])

    def test_repeated_java_heading_is_detected(self) -> None:
        entries, headings = self.fixture_entries("repeated.md")
        self.assertEqual(repeated_headings(headings), ["Java"])

    def test_missing_entry_raises_assertion(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entries([])

    def test_source_selected_entries_and_no_repeated_headings(self) -> None:
        entries, headings = parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        actual = select_required_entries(entries)
        self.assertEqual(compare_expected(actual), [])
        self.assertEqual(repeated_headings(headings), [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t024.py", "--self-test"]), patch(
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_evidence(
    actual: list[dict[str, Any]],
    mismatches: list[dict[str, Any]],
    duplicate_headings: list[str],
    validation_error: str | None,
    self_test_status: str,
    self_test_output: str,
) -> None:
    inputs = {
        "target_file": "casts/free-podcasts-screencasts-fr.md",
        "target_section": "Cloud computing and Langage Agnostique",
        "selected_entries": list(SELECTED_ENTRIES),
        "subject_evidence": SUBJECT_EVIDENCE,
    }
    mismatches_expected = compare_expected(actual)
    expected_vs_actual = {
        "expected": list(SELECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": (
                "passed"
                if not mismatches_expected
                and not mismatches
                and not duplicate_headings
                and validation_error is None
                else "failed"
            ),
            "mismatches": mismatches_expected,
            "category_mismatches": mismatches,
            "duplicate_headings": duplicate_headings,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
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
        "# R10-T024 category checker report",
        "",
        "- Source: `casts/free-podcasts-screencasts-fr.md`",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Category mismatches: {len(mismatches)}",
        f"- Repeated headings: {len(duplicate_headings)}",
        "",
        "## Selected entries",
        "",
        "| Line | Display name | Category | URL |",
        "| ---: | --- | --- | --- |",
    ]
    for entry in actual:
        report.append(
            f"| {entry['line_number']} | {entry['display_name']} | "
            f"{entry['category']} | `{entry['url']}` |"
        )
    report.extend(["", "## Subject evidence", ""])
    for url, evidence in SUBJECT_EVIDENCE.items():
        report.append(f"- [{url}]({url}): {evidence['evidence']} (observed {evidence['observed']})")
    if mismatches:
        report.extend(["", "## Proposed category moves", ""])
        for mismatch in mismatches:
            report.append(
                f"- Line {mismatch['line_number']}: {mismatch['display_name']} "
                f"from `{mismatch['actual_category']}` to "
                f"`{mismatch['expected_category']}`"
            )
    else:
        report.extend(["", "## Proposed category moves", "", "- None"])
    report.extend(
        [
            "",
            "No entry was reclassified solely by keywords. Reclassification requires",
            "subject evidence and manual review.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report), encoding="utf-8")


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

    actual: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    duplicate_headings: list[str] = []
    validation_error = None
    try:
        entries, headings = parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        actual = select_required_entries(entries)
        mismatches = find_category_mismatches(entries)
        duplicate_headings = repeated_headings(headings)
    except (OSError, AssertionError) as error:
        validation_error = str(error)

    write_evidence(
        actual,
        mismatches,
        duplicate_headings,
        validation_error,
        self_test_status,
        self_test_output,
    )

    if validation_error:
        print(f"r10-t024: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed or mismatches or duplicate_headings:
        return 1
    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
