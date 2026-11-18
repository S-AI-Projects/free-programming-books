#!/usr/bin/env python3
"""Check access evidence for three Romanian UTM course catalogue entries."""

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
SOURCE_FILE = ROOT / "courses" / "free-courses-ro.md"
EVIDENCE_DIR = ROOT / "work" / "R10-T029"
FIXTURE_FILE = EVIDENCE_DIR / "fixtures" / "access_scenarios.json"

EXPECTED_ENTRIES = (
    {
        "title": "Structuri de Date și Algoritmi",
        "url": "https://lectii.utm.md/courses/structuri-de-date-si-algoritmi/",
        "section": "Algoritmi și Structuri de Date",
        "line_number": 11,
    },
    {
        "title": "Programarea calculatoarelor",
        "url": "https://lectii.utm.md/courses/programarea-calculatoarelor/",
        "section": "C++",
        "line_number": 16,
    },
    {
        "title": "Programarea Orientată pe Obiecte",
        "url": "https://lectii.utm.md/courses/programarea-orientata-pe-obiecte/",
        "section": "C++",
        "line_number": 17,
    },
)
ENTRY_BY_URL = {entry["url"]: entry for entry in EXPECTED_ENTRIES}
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)

# Browser checks were limited to these official pages. No login or credentials
# were used; page content could not be inspected, so requirements remain unknown.
MANUAL_OBSERVATIONS = (
    {
        "url": EXPECTED_ENTRIES[0]["url"],
        "source_url": EXPECTED_ENTRIES[0]["url"],
        "manual_verified": False,
        "observation": "Browser load failed (ERR_FAILED); course content was unavailable.",
        "automated_status": "browser navigation failed",
    },
    {
        "url": EXPECTED_ENTRIES[1]["url"],
        "source_url": EXPECTED_ENTRIES[1]["url"],
        "manual_verified": False,
        "observation": "Browser load failed (ERR_FAILED); course content was unavailable.",
        "automated_status": "browser navigation failed",
    },
    {
        "url": EXPECTED_ENTRIES[2]["url"],
        "source_url": EXPECTED_ENTRIES[2]["url"],
        "manual_verified": False,
        "observation": (
            "Browser displayed a Cloudflare HTTP 403 security-verification "
            "challenge before the course content."
        ),
        "automated_status": "403 from Cloudflare challenge; origin page unverified",
    },
)


def clean_heading(title: str) -> str:
    return re.sub(r"</?a\b[^>]*>", "", title).strip()


def parse_selected_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse only the three assigned rows and retain their source line numbers."""
    entries = []
    section: str | None = None
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading:
            section = clean_heading(heading.group(1))
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
                "section": section,
                "metadata": match.group("metadata"),
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
        for field in ("title", "section"):
            actual = matches[0][field]
            if actual != expected[field]:
                errors.append(
                    {
                        "url": expected["url"],
                        "field": field,
                        "expected": expected[field],
                        "actual": actual,
                        "line_number": matches[0]["line_number"],
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
    elif requirements:
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
                "section": entry["section"],
                "line_number": entry["line_number"],
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
        self.assertEqual([entry["line_number"] for entry in entries], [11, 16, 17])

    def test_access_fixture_scenarios_are_classified_with_source_citations(self) -> None:
        for fixture in self.fixture_data["cases"]:
            with self.subTest(fixture=fixture["name"]):
                result = classify_access(fixture["resource_url"], fixture["evidence"])
                self.assertEqual(result["status"], fixture["expected_status"])
                self.assertEqual(
                    result["source_url"], fixture["evidence"]["source_url"]
                )
                self.assertFalse(result["removal_recommendation"])

    def test_automated_404_without_manual_page_evidence_is_unverified(self) -> None:
        fixture = next(
            item
            for item in self.fixture_data["cases"]
            if item["name"] == "automated_404"
        )
        result = classify_access(fixture["resource_url"], fixture["evidence"])
        self.assertEqual(result["status"], "unverified")
        self.assertIsNone(result["payment_required"])
        self.assertFalse(result["removal_recommendation"])

    def test_security_challenge_is_not_mislabeled_as_authentication(self) -> None:
        fixture = next(
            item
            for item in self.fixture_data["cases"]
            if item["name"] == "automated_403_challenge"
        )
        result = classify_access(fixture["resource_url"], fixture["evidence"])
        self.assertEqual(result["status"], "unverified")
        self.assertIsNone(result["authentication_required"])
        self.assertIsNone(result["registration_required"])

    def test_claim_without_official_source_citation_is_unverified(self) -> None:
        fixture = next(
            item
            for item in self.fixture_data["cases"]
            if item["name"] == "public_access"
        )
        evidence = dict(fixture["evidence"], source_url="https://other.example/page")
        result = classify_access(fixture["resource_url"], evidence)
        self.assertEqual(result["status"], "unverified")
        self.assertIsNone(result["authentication_required"])

    def test_no_fixture_contains_credential_fields(self) -> None:
        forbidden_names = {"password", "token", "cookie", "credential"}
        serialized = json.dumps(self.fixture_data).lower()
        for name in forbidden_names:
            self.assertNotIn(f'"{name}"', serialized)

    def test_failed_self_test_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t029.py", "--self-test"]), patch(
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
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_evidence(
    entries: list[dict[str, Any]],
    source_errors: list[dict[str, Any]],
    results: list[dict[str, Any]],
    self_test_status: str,
    self_test_output: str,
) -> None:
    write_json(
        EVIDENCE_DIR / "inputs.json",
        {
            "target_file": "courses/free-courses-ro.md",
            "selected_entries": entries,
            "manual_page_observations": MANUAL_OBSERVATIONS,
            "credentials_used_or_saved": False,
        },
    )
    fixture_results = []
    for fixture in json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))["cases"]:
        actual = classify_access(fixture["resource_url"], fixture["evidence"])
        fixture_results.append(
            {
                "name": fixture["name"],
                "expected": fixture["expected_status"],
                "actual": actual["status"],
                "source_url": actual["source_url"],
                "requirements": actual["requirements"],
                "automated_status": actual["automated_status"],
            }
        )
    write_json(
        EVIDENCE_DIR / "expected_vs_actual.json",
        {
            "source_validation": {
                "status": "passed" if not source_errors else "failed",
                "errors": source_errors,
                "actual_entries": entries,
            },
            "manual_access_results": results,
            "fixtures": fixture_results,
            "self_test": {"status": self_test_status},
            "catalogue_corrections": [],
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
    report_lines = [
        "# R10-T029 course access report",
        "",
        "- Source: `courses/free-courses-ro.md`",
        f"- Source validation: {'passed' if not source_errors else 'failed'}",
        f"- Offline self-test: {self_test_status}",
        "- Manual page access: all three results are unverified.",
        "- Credentials: none used or saved.",
        "- Catalogue corrections: none; automated failures do not establish broken links.",
        "",
        "## Selected entries and official-page observations",
        "",
    ]
    report_lines.extend(
        f"- Line {result['line_number']}: `{result['title']}` "
        f"({result['url']}) — **{result['status']}**. "
        f"Evidence: {result['evidence']}"
        for result in results
    )
    report_lines.extend(
        [
            "",
            "Authentication, registration, payment, and environment requirements "
            "remain unknown because the course content was not reachable for "
            "manual inspection. No access claim is inferred from browser/network errors.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
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
        entries = parse_selected_entries(SOURCE_FILE.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"r10-t029: cannot read source: {error}", file=sys.stderr)
        return 1
    source_errors = validate_source(entries)
    results = classify_all(entries, MANUAL_OBSERVATIONS)
    write_evidence(entries, source_errors, results, test_status, test_text)

    if source_errors:
        print(
            "r10-t029: source validation failed: "
            + json.dumps(source_errors, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    if not tests_passed:
        return 1
    if not args.self_test:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
