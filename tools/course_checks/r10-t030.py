#!/usr/bin/env python3
"""Generate a deterministic maintenance report for one Norwegian course entry."""

from __future__ import annotations

import argparse
import io
import json
import platform
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = ROOT / "courses" / "free-courses-no.md"
EVIDENCE_DIR = ROOT / "work" / "R10-T030"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
FIXTURE_FILE = FIXTURE_DIR / "maintenance_cases.json"
DECISIONS_FILE = FIXTURE_DIR / "manual_decisions.json"

EXPECTED_ENTRY = {
    "title": "Java-programmering",
    "url": (
        "https://www.youtube.com/playlist"
        "?list=PLIrUJXSXz9cmvNZ_Y0QT-r25efmN42rm5"
    ),
    "section": "Java",
    "creator": "UDL.no",
}

HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)


def parse_selected_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse only the assigned playlist row, retaining its one-based line."""
    entries = []
    section: str | None = None
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading:
            section = heading.group(1).strip()
            continue
        match = ENTRY_RE.match(line)
        if match is None or match.group("url") != EXPECTED_ENTRY["url"]:
            continue
        metadata = match.group("metadata").strip()
        creator = metadata[2:].strip() if metadata.startswith("- ") else metadata
        entries.append(
            {
                "title": match.group("title"),
                "url": match.group("url"),
                "section": section,
                "creator": creator,
                "metadata": metadata,
                "line_number": line_number,
            }
        )
    return entries


def validate_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors = []
    if len(entries) != 1:
        errors.append(
            {
                "code": "selected-entry-count",
                "line_number": entries[1]["line_number"]
                if len(entries) > 1
                else None,
                "expected": 1,
                "actual": len(entries),
            }
        )
        if not entries:
            return errors

    for entry in entries:
        for field in ("title", "url", "section", "creator"):
            expected = EXPECTED_ENTRY[field]
            actual = entry[field]
            if actual != expected:
                errors.append(
                    {
                        "code": "metadata-mismatch",
                        "field": field,
                        "line_number": entry["line_number"],
                        "expected": expected,
                        "actual": actual,
                    }
                )
    return errors


def metadata_snapshot(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": entry["title"],
        "url": entry["url"],
        "section": entry["section"],
        "creator": entry["creator"],
        "source_line": entry["line_number"],
    }


def build_report(
    entries: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    manual_decision: dict[str, str],
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
    if errors:
        decision = {
            "decision": "defer",
            "reason": "The selected source metadata did not match; review it manually.",
        }
        recommendation = {
            "action": "manual_review",
            "reason": "Observed mismatches are not sufficient evidence to edit the catalogue.",
        }
    else:
        decision = dict(manual_decision)
        recommendation = {
            "action": "retain_unchanged",
            "reason": manual_decision["reason"],
        }
    return {
        "source_file": "courses/free-courses-no.md",
        "section": EXPECTED_ENTRY["section"],
        "validation": "passed" if not errors else "failed",
        "observed_facts": observed_facts,
        "before_after_metadata": before_after,
        "manual_decisions": [
            {"url": EXPECTED_ENTRY["url"], **decision}
        ],
        "recommendations": [
            {"url": EXPECTED_ENTRY["url"], **recommendation}
        ],
        "validation_errors": errors,
        "catalogue_changes": [],
    }


def stable_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class CourseCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture_cases = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
        self.manual_decision = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))

    def fixture_report(self, filename: str) -> dict[str, Any]:
        text = (FIXTURE_DIR / filename).read_text(encoding="utf-8")
        entries = parse_selected_entries(text)
        errors = validate_entries(entries)
        return build_report(entries, errors, self.manual_decision)

    def test_actual_entry_is_scoped_and_has_exact_source_line(self) -> None:
        text = SOURCE_FILE.read_text(encoding="utf-8")
        entries = parse_selected_entries(text)
        self.assertEqual(validate_entries(entries), [])
        self.assertEqual(entries[0]["line_number"], 8)
        self.assertEqual(entries[0]["creator"], "UDL.no")

    def test_fixture_outcomes_match_the_maintenance_cases(self) -> None:
        for case in self.fixture_cases["cases"]:
            with self.subTest(case=case["name"]):
                report = self.fixture_report(case["fixture"])
                self.assertEqual(report["validation"], case["expected_validation"])
                self.assertEqual(
                    [error["code"] for error in report["validation_errors"]],
                    case["expected_errors"],
                )

    def test_report_separates_facts_recommendations_and_before_after(self) -> None:
        report = self.fixture_report("valid.md")
        self.assertEqual(report["observed_facts"][0]["source_line"], 8)
        before_after = report["before_after_metadata"][0]
        self.assertEqual(before_after["before"], before_after["after"])
        self.assertEqual(report["manual_decisions"][0]["decision"], "retain")
        self.assertEqual(
            report["recommendations"][0]["action"], "retain_unchanged"
        )
        self.assertNotIn("recommendation", report["observed_facts"][0])

    def test_same_fixture_produces_stable_report_bytes(self) -> None:
        for case in self.fixture_cases["cases"]:
            with self.subTest(case=case["name"]):
                report_a = stable_json(self.fixture_report(case["fixture"]))
                report_b = stable_json(self.fixture_report(case["fixture"]))
                self.assertEqual(report_a, report_b)

    def test_changed_metadata_requests_review_without_proposing_an_edit(self) -> None:
        report = self.fixture_report("changed-metadata.md")
        self.assertEqual(report["recommendations"][0]["action"], "manual_review")
        self.assertEqual(
            report["before_after_metadata"][0]["before"],
            report["before_after_metadata"][0]["after"],
        )

    def test_failed_self_test_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t030.py", "--self-test"]), patch(
            f"{__name__}.test_output",
            return_value=(False, "simulated assertion failure\n"),
        ), patch(f"{__name__}.write_evidence"), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)


def test_output() -> tuple[bool, str]:
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CourseCheckTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return result.wasSuccessful(), stream.getvalue()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json(data), encoding="utf-8")


def fixture_results(manual_decision: dict[str, str]) -> list[dict[str, Any]]:
    cases = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))["cases"]
    results = []
    for case in cases:
        entries = parse_selected_entries(
            (FIXTURE_DIR / case["fixture"]).read_text(encoding="utf-8")
        )
        errors = validate_entries(entries)
        report = build_report(entries, errors, manual_decision)
        results.append(
            {
                "name": case["name"],
                "expected_validation": case["expected_validation"],
                "actual_validation": report["validation"],
                "expected_errors": case["expected_errors"],
                "actual_errors": [
                    error["code"] for error in report["validation_errors"]
                ],
                "actual_diagnostics": report["validation_errors"],
            }
        )
    return results


def write_evidence(
    entries: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    report: dict[str, Any],
    manual_decision: dict[str, str],
    self_test_status: str,
    self_test_output: str,
) -> None:
    write_json(
        EVIDENCE_DIR / "inputs.json",
        {
            "target_file": "courses/free-courses-no.md",
            "selected_entry": EXPECTED_ENTRY,
            "actual_source_rows": entries,
            "manual_decision_input": manual_decision,
            "fixture_file": "work/R10-T030/fixtures/maintenance_cases.json",
        },
    )
    write_json(
        EVIDENCE_DIR / "expected_vs_actual.json",
        {
            "validation": {
                "expected": "passed",
                "actual": "passed" if not errors else "failed",
                "errors": errors,
            },
            "maintenance_report": report,
            "fixture_results": fixture_results(manual_decision),
            "self_test": {"status": self_test_status},
        },
    )
    (EVIDENCE_DIR / "self-test-output.txt").write_text(
        self_test_output, encoding="utf-8"
    )
    git_version = subprocess.run(
        ["git", "--version"],
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
    (EVIDENCE_DIR / "tool_versions.txt").write_text(
        f"Python: {sys.version.splitlines()[0]}\n"
        f"Platform: {platform.platform()}\n"
        f"Git: {git_version}\n"
        f"Branch: {branch}\n",
        encoding="utf-8",
    )
    report_text = [
        "# R10-T030 repeatable maintenance report",
        "",
        "- Source: `courses/free-courses-no.md`",
        f"- Section: `{EXPECTED_ENTRY['section']}`",
        f"- Validation: {report['validation']}",
        f"- Offline self-test: {self_test_status}",
        "- Live requests: not run; this pass compares the selected source metadata only.",
        "",
        "## Observed facts",
        "",
    ]
    report_text.extend(
        f"- Line {fact['source_line']}: `{fact['title']}` — `{fact['url']}`; "
        f"section `{fact['section']}`, creator `{fact['creator']}`."
        for fact in report["observed_facts"]
    )
    report_text.extend(["", "## Before and after metadata", ""])
    report_text.extend(
        f"- `{item['url']}`: before "
        f"`{json.dumps(item['before'], ensure_ascii=False, sort_keys=True)}`; "
        f"after `{json.dumps(item['after'], ensure_ascii=False, sort_keys=True)}`."
        for item in report["before_after_metadata"]
    )
    report_text.extend(["", "## Manual decisions", ""])
    report_text.extend(
        f"- `{item['url']}`: **{item['decision']}** — {item['reason']}"
        for item in report["manual_decisions"]
    )
    report_text.extend(["", "## Recommendations", ""])
    report_text.extend(
        f"- `{item['url']}`: **{item['action']}** — {item['reason']}"
        for item in report["recommendations"]
    )
    report_text.append("")
    (EVIDENCE_DIR / "report.md").write_text(
        "\n".join(report_text), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixtures")
    args = parser.parse_args()

    tests_passed = True
    test_status = "not_run"
    test_text = ""
    if args.self_test:
        tests_passed, test_text = test_output()
        test_status = "passed" if tests_passed else "failed"
        print(test_text, end="")

    try:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        manual_decision = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"r10-t030: cannot read report inputs: {error}", file=sys.stderr)
        return 1
    entries = parse_selected_entries(source)
    errors = validate_entries(entries)
    report = build_report(entries, errors, manual_decision)
    write_evidence(
        entries, errors, report, manual_decision, test_status, test_text
    )
    if errors:
        print(
            "r10-t030: source validation failed: "
            + json.dumps(errors, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    if not tests_passed:
        return 1
    print(stable_json(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
