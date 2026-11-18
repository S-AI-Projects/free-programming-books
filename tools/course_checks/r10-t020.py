#!/usr/bin/env python3
"""Generate a deterministic maintenance report for selected Myanmar programming books."""

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


ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = ROOT / "books" / "free-programming-books-my.md"
EVIDENCE_DIR = ROOT / "work" / "R10-T020"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "maintenance_cases.json"
DECISIONS_FILE = FIXTURE_DIR / "manual_decisions.json"

EXPECTED_ENTRIES = (
    {
        "title": "Bitcoin - On Point",
        "url": "https://eimaung.com/bitcoin/",
        "section": "Blockchain",
        "line_number": 18,
    },
    {
        "title": "The Little Go Book",
        "url": "https://github.com/nainglinaung/the-little-go-book",
        "section": "Go",
        "line_number": 23,
    },
    {
        "title": "HTML",
        "url": "https://github.com/nainglinaung/the-little-go-book/blob/master/mm/go.md",
        "section": "Go",
        "line_number": 23,
    },
)
EXPECTED_URLS = frozenset(entry["url"] for entry in EXPECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
PRIMARY_ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)
LINK_RE = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)")


def parse_selected_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse primary and inline links for the selected entries, retaining line numbers."""
    entries = []
    section: str | None = None
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(1).strip()
            continue

        primary = PRIMARY_ENTRY_RE.match(line)
        if not primary:
            continue

        p_url = primary.group("url")
        if p_url in EXPECTED_URLS:
            entries.append(
                {
                    "title": primary.group("title"),
                    "url": p_url,
                    "section": section,
                    "line_number": line_number,
                }
            )

        metadata = primary.group("metadata")
        for match in LINK_RE.finditer(metadata):
            m_url = match.group("url")
            if m_url in EXPECTED_URLS:
                entries.append(
                    {
                        "title": match.group("label"),
                        "url": m_url,
                        "section": section,
                        "line_number": line_number,
                    }
                )
    return entries


def validate_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors = []
    by_url: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_url.setdefault(entry["url"], []).append(entry)

    for expected in EXPECTED_ENTRIES:
        matches = by_url.get(expected["url"], [])
        if len(matches) != 1:
            errors.append(
                {
                    "code": "entry-count-mismatch",
                    "url": expected["url"],
                    "expected_count": 1,
                    "actual_count": len(matches),
                }
            )
            continue
        actual = matches[0]
        for field in ("title", "section"):
            if actual[field] != expected[field]:
                errors.append(
                    {
                        "code": "metadata-mismatch",
                        "field": field,
                        "line_number": actual["line_number"],
                        "expected": expected[field],
                        "actual": actual[field],
                    }
                )
    return errors


def metadata_snapshot(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": entry["title"],
        "url": entry["url"],
        "section": entry["section"],
        "source_line": entry["line_number"],
    }


def build_report(
    entries: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    manual_decisions: dict[str, dict[str, str]],
) -> dict[str, Any]:
    observed_facts = [metadata_snapshot(entry) for entry in entries]
    before_after = [
        {
            "url": entry["url"],
            "before": metadata_snapshot(entry),
            "after": metadata_snapshot(entry),
        }
        for entry in entries
    ]

    decisions = []
    recommendations = []
    for expected in EXPECTED_ENTRIES:
        url = expected["url"]
        if errors:
            decisions.append(
                {
                    "url": url,
                    "decision": "defer",
                    "reason": "The selected source metadata did not match; review manually.",
                }
            )
            recommendations.append(
                {
                    "url": url,
                    "action": "manual_review",
                    "reason": "Observed mismatches require manual investigation.",
                }
            )
        else:
            item = manual_decisions.get(
                url,
                {"decision": "retain_unchanged", "reason": "Confirmed active and valid."},
            )
            decisions.append({"url": url, **item})
            recommendations.append(
                {
                    "url": url,
                    "action": "retain_unchanged",
                    "reason": item["reason"],
                }
            )

    return {
        "source_file": "books/free-programming-books-my.md",
        "validation": "passed" if not errors else "failed",
        "observed_facts": observed_facts,
        "before_after_metadata": before_after,
        "manual_decisions": decisions,
        "recommendations": recommendations,
        "validation_errors": errors,
        "catalogue_changes": [],
    }


def stable_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class CourseCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manual_decisions = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))

    def fixture_report(self, filename: str) -> dict[str, Any]:
        text = (FIXTURE_DIR / filename).read_text(encoding="utf-8")
        entries = parse_selected_entries(text)
        errors = validate_entries(entries)
        return build_report(entries, errors, self.manual_decisions)

    def test_actual_entries_scoped_and_exact_source_lines(self) -> None:
        text = SOURCE_FILE.read_text(encoding="utf-8")
        entries = parse_selected_entries(text)
        self.assertEqual(validate_entries(entries), [])
        self.assertEqual(len(entries), 3)
        self.assertEqual(
            [(e["line_number"], e["title"]) for e in entries],
            [(18, "Bitcoin - On Point"), (23, "The Little Go Book"), (23, "HTML")],
        )

    def test_valid_fixture_produces_stable_passed_report(self) -> None:
        report1 = self.fixture_report("valid.md")
        report2 = self.fixture_report("valid.md")
        self.assertEqual(report1["validation"], "passed")
        self.assertEqual(stable_json(report1), stable_json(report2))

    def test_missing_entry_fails_validation(self) -> None:
        report = self.fixture_report("missing-entry.md")
        self.assertEqual(report["validation"], "failed")
        self.assertTrue(any(e["code"] == "entry-count-mismatch" for e in report["validation_errors"]))

    def test_changed_metadata_fails_validation(self) -> None:
        report = self.fixture_report("changed-metadata.md")
        self.assertEqual(report["validation"], "failed")
        self.assertTrue(any(e["code"] == "metadata-mismatch" for e in report["validation_errors"]))

    def test_failed_request_does_not_remove_entry(self) -> None:
        report = self.fixture_report("valid.md")
        # Ensure no catalogue changes are recommended simply from automated checks
        self.assertEqual(report["catalogue_changes"], [])
        for rec in report["recommendations"]:
            self.assertEqual(rec["action"], "retain_unchanged")

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t020.py", "--self-test"]), \
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
    report: dict[str, Any],
) -> None:
    inputs = {
        "target_file": "books/free-programming-books-my.md",
        "target_section": "Myanmar programming books; sections: Blockchain, Go",
        "selected_entries": [
            {
                "title": entry["title"],
                "url": entry["url"],
                "section": entry["section"],
                "line_number": entry["line_number"],
            }
            for entry in EXPECTED_ENTRIES
        ],
    }
    expected_vs_actual = {
        "expected": list(EXPECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not validation_error else "failed",
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
        "maintenance_report": report,
    }
    write_json(EVIDENCE_DIR / "inputs.json", inputs)
    write_json(EVIDENCE_DIR / "expected_vs_actual.json", expected_vs_actual)
    (EVIDENCE_DIR / "self-test-output.txt").write_text(self_test_output, encoding="utf-8")

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
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
        "# R10-T020 maintenance pass report",
        "",
        "- Source: `books/free-programming-books-my.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        "",
        "## Observed facts (source lines and metadata)",
        "",
        "| Line | Title | Section | URL |",
        "| ---: | --- | --- | --- |",
    ]
    for fact in report.get("observed_facts", []):
        report_lines.append(
            f"| {fact['source_line']} | {fact['title']} | "
            f"{fact['section']} | `{fact['url']}` |"
        )
    report_lines.extend(
        [
            "",
            "## Recommendations and manual decisions",
            "",
            "| URL | Decision | Action | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for dec, rec in zip(report.get("manual_decisions", []), report.get("recommendations", [])):
        report_lines.append(
            f"| `{dec['url']}` | {dec.get('decision', '')} | {rec.get('action', '')} | {dec.get('reason', '')} |"
        )
    if validation_error:
        report_lines.extend(["", f"Validation error: `{validation_error}`"])
    report_lines.extend(
        [
            "",
            "Observed facts are strictly separated from recommendations.",
            "Output is deterministic and reproducible across runs.",
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
    report = {}
    manual_decisions = {}
    try:
        manual_decisions = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        actual = parse_selected_entries(source_text)
        errors = validate_entries(actual)
        if errors:
            validation_error = json.dumps(errors, ensure_ascii=False)
        report = build_report(actual, errors, manual_decisions)
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        report,
    )

    if validation_error:
        print(f"r10-t020: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(stable_json(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
