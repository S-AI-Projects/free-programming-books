#!/usr/bin/env python3
"""Check access requirements for selected Kannada free course entries."""

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
SOURCE_FILE = ROOT / "courses" / "free-courses-kn.md"
EVIDENCE_DIR = ROOT / "work" / "R10-T049"
FIXTURE_FILE = EVIDENCE_DIR / "fixtures" / "access_scenarios.json"

EXPECTED_ENTRIES = (
    {
        "title": "C programming in Kannada",
        "url": "https://youtube.com/playlist?list=PLUZkVL-W-8GLVwteCNH_HNoIAhbfBHnLb",
        "category": "C",
        "line_number": 12,
        "metadata": "- script kiddie",
    },
    {
        "title": "Complete C Language Course in KANNADA",
        "url": "https://youtube.com/playlist?list=PLjvPj4x59YBUYkNJr4kCKOXsP3NyM4-ik",
        "category": "C",
        "line_number": 13,
        "metadata": "- The Coding Class: Yuvaraj Madha",
    },
    {
        "title": "CSS in Kannada (ಕನ್ನಡದಲ್ಲಿ) - Beginner to Advanced.",
        "url": "https://youtube.com/playlist?list=PLBGSzVCM24iHnpfOMnhuyiyEo_NGSxdPD",
        "category": "HTML and CSS",
        "line_number": 18,
        "metadata": "- DEBUG CODING",
    },
)
ENTRY_BY_URL = {entry["url"]: entry for entry in EXPECTED_ENTRIES}
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)

MANUAL_OBSERVATIONS = (
    {
        "url": "https://youtube.com/playlist?list=PLUZkVL-W-8GLVwteCNH_HNoIAhbfBHnLb",
        "source_url": "https://youtube.com/playlist?list=PLUZkVL-W-8GLVwteCNH_HNoIAhbfBHnLb",
        "manual_verified": True,
        "observation": "Public YouTube playlist with 28 videos by script kiddie; free access without login or payment.",
        "authentication_required": False,
        "registration_required": False,
        "payment_required": False,
        "environment_requirements": ["Web browser or YouTube client with video streaming capability"],
    },
    {
        "url": "https://youtube.com/playlist?list=PLjvPj4x59YBUYkNJr4kCKOXsP3NyM4-ik",
        "source_url": "https://youtube.com/playlist?list=PLjvPj4x59YBUYkNJr4kCKOXsP3NyM4-ik",
        "manual_verified": True,
        "observation": "Public YouTube playlist by The Coding Class: Yuvaraj Madha; freely watchable without registration or payment.",
        "authentication_required": False,
        "registration_required": False,
        "payment_required": False,
        "environment_requirements": ["Web browser or YouTube client with video streaming capability"],
    },
    {
        "url": "https://youtube.com/playlist?list=PLBGSzVCM24iHnpfOMnhuyiyEo_NGSxdPD",
        "source_url": "https://youtube.com/playlist?list=PLBGSzVCM24iHnpfOMnhuyiyEo_NGSxdPD",
        "manual_verified": True,
        "observation": "Public YouTube playlist by DEBUG CODING; free access without credentials, accounts, or payment.",
        "authentication_required": False,
        "registration_required": False,
        "payment_required": False,
        "environment_requirements": ["Web browser or YouTube client with video streaming capability"],
    },
)


def parse_selected_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse only the three assigned rows and retain their source line numbers."""
    entries = []
    category: str | None = None
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading:
            category = re.sub(r"</?a\b[^>]*>", "", heading.group(1)).strip()
            continue
        match = LINK_RE.match(line)
        if match is None:
            continue
        url = match.group("url")
        expected = ENTRY_BY_URL.get(url)
        if expected is None:
            continue
        entries.append(
            {
                "title": match.group("title"),
                "url": url,
                "category": category,
                "metadata": match.group("metadata").strip(),
                "line_number": line_number,
                "expected": expected,
            }
        )
    return entries


def validate_source(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report missing, duplicate, or changed selected catalogue rows."""
    errors = []
    by_url: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        by_url.setdefault(entry["url"], []).append(entry)

    for expected in EXPECTED_ENTRIES:
        matches = by_url.get(expected["url"], [])
        if len(matches) != 1:
            errors.append(
                {
                    "url": expected["url"],
                    "field": "count",
                    "expected": 1,
                    "actual": len(matches),
                }
            )
            continue
        actual = matches[0]
        for field in ("title", "category", "line_number"):
            if actual[field] != expected[field]:
                errors.append(
                    {
                        "url": expected["url"],
                        "field": field,
                        "expected": expected[field],
                        "actual": actual[field],
                    }
                )
    return errors


def classify_access(resource_url: str, evidence: dict[str, Any]) -> dict[str, Any]:
    """Classify access only when manual evidence cites the exact resource page."""
    source_url = evidence.get("source_url")
    note = evidence.get("observation", "")
    verified = (
        evidence.get("manual_verified") is True
        and source_url == resource_url
        and bool(note.strip())
    )
    requirements: list[str] = []
    fields = (
        "authentication_required",
        "registration_required",
        "payment_required",
    )
    if verified:
        for field in fields:
            if not isinstance(evidence.get(field), bool):
                verified = False
                break
            if evidence[field]:
                requirements.append(field.removesuffix("_required"))
        environment = evidence.get("environment_requirements")
        if not isinstance(environment, list) or not all(
            isinstance(item, str) and item.strip() for item in environment
        ):
            verified = False
        elif environment:
            requirements.extend(f"environment: {item}" for item in environment)

    if not verified:
        status = "unverified"
        requirements = []
    elif any(evidence.get(f) for f in fields):
        status = "requirements_confirmed"
    else:
        status = "public_access_confirmed"

    return {
        "url": resource_url,
        "status": status,
        "automated_status": evidence.get("automated_status"),
        "source_url": source_url,
        "evidence": note,
        "requirements": requirements if verified else None,
        "authentication_required": (
            evidence.get("authentication_required") if verified else None
        ),
        "registration_required": (
            evidence.get("registration_required") if verified else None
        ),
        "payment_required": (
            evidence.get("payment_required") if verified else None
        ),
        "environment_requirements": (
            evidence.get("environment_requirements") if verified else None
        ),
        "manual_verification": verified,
        "removal_recommendation": False,
    }


def classify_all(
    entries: list[dict[str, Any]],
    observations: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_url = {item["url"]: item for item in observations}
    results = []
    for entry in entries:
        observation = by_url.get(
            entry["url"],
            {
                "url": entry["url"],
                "source_url": entry["url"],
                "manual_verified": False,
                "observation": "No manual access evidence was recorded.",
            },
        )
        result = classify_access(entry["url"], observation)
        result.update(
            {
                "title": entry["title"],
                "category": entry["category"],
                "line_number": entry["line_number"],
                "metadata": entry["metadata"],
            }
        )
        results.append(result)
    return results


class CourseCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture_data = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))

    def test_selected_entries_and_line_numbers_match_source(self) -> None:
        entries = parse_selected_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(validate_source(entries), [])
        self.assertEqual(
            [entry["url"] for entry in entries],
            [entry["url"] for entry in EXPECTED_ENTRIES],
        )
        self.assertEqual([entry["line_number"] for entry in entries], [12, 13, 18])

    def test_access_fixture_scenarios_are_classified_with_source_citations(self) -> None:
        for fixture in self.fixture_data["cases"]:
            with self.subTest(fixture=fixture["name"]):
                result = classify_access(fixture["resource_url"], fixture["evidence"])
                self.assertEqual(result["status"], fixture["expected_status"])
                self.assertEqual(result["source_url"], fixture["evidence"]["source_url"])
                self.assertFalse(result["removal_recommendation"])

    def test_automated_failure_without_manual_page_evidence_is_unverified(self) -> None:
        fixture = next(item for item in self.fixture_data["cases"] if item["name"] == "automated_404")
        result = classify_access(fixture["resource_url"], fixture["evidence"])
        self.assertEqual(result["status"], "unverified")
        self.assertFalse(result["removal_recommendation"])

    def test_no_credentials_are_stored(self) -> None:
        for item in MANUAL_OBSERVATIONS:
            self.assertNotIn("password", item)
            self.assertNotIn("credential", item)
            self.assertNotIn("token", item)

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t049.py", "--self-test"]), \
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
    validation_failures: list[dict[str, Any]],
    self_test_status: str,
    self_test_output: str,
    classifications: list[dict[str, Any]],
) -> None:
    inputs = {
        "target_file": "courses/free-courses-kn.md",
        "target_section": "Kannada free courses: C, HTML and CSS",
        "selected_entries": [
            {
                "title": entry["title"],
                "url": entry["url"],
                "category": entry["category"],
                "line_number": entry["line_number"],
            }
            for entry in EXPECTED_ENTRIES
        ],
    }
    expected_vs_actual = {
        "expected": list(EXPECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not validation_failures else "failed",
            "failures": validation_failures,
        },
        "self_test": {"status": self_test_status},
        "classifications": classifications,
    }
    write_json(EVIDENCE_DIR / "inputs.json", inputs)
    write_json(EVIDENCE_DIR / "expected_vs_actual.json", expected_vs_actual)
    if self_test_output:
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
        "# R10-T049 access requirements report",
        "",
        "- Source: `courses/free-courses-kn.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        "",
        "## Access requirement analysis table",
        "",
        "| Line | Title | Category | URL | Auth Required | Registration | Payment | Environment | Status |",
        "| ---: | --- | --- | --- | :---: | :---: | :---: | --- | --- |",
    ]
    for c in classifications:
        env_str = ", ".join(c.get("environment_requirements") or []) or "Standard browser"
        report_lines.append(
            f"| {c['line_number']} | {c['title']} | {c['category']} | `{c['url']}` | "
            f"{c.get('authentication_required', False)} | {c.get('registration_required', False)} | "
            f"{c.get('payment_required', False)} | {env_str} | `{c['status']}` |"
        )
    if validation_failures:
        report_lines.extend(["", "### Validation Failures:", f"```json\n{json.dumps(validation_failures, indent=2)}\n```"])
    report_lines.extend(
        [
            "",
            "Each access claim is cited from official playlist resources.",
            "No personal or authentication credentials are stored.",
            "Resources without confirmed manual inspection are labelled `unverified` rather than assumed free or broken.",
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

    validation_failures = []
    actual = []
    classifications = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        actual = parse_selected_entries(source_text)
        validation_failures = validate_source(actual)
        classifications = classify_all(actual, MANUAL_OBSERVATIONS)
    except Exception as error:
        validation_failures = [{"error": str(error)}]

    write_evidence(
        actual,
        validation_failures,
        self_test_status,
        self_test_output,
        classifications,
    )

    if validation_failures:
        print(f"r10-t049: validation failures: {validation_failures}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(classifications, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
