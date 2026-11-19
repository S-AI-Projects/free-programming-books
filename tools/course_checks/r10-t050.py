#!/usr/bin/env python3
"""Repeatable maintenance pass checker for Norwegian free programming book entries."""

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
SOURCE_FILE = ROOT / "books" / "free-programming-books-no.md"
EVIDENCE_DIR = ROOT / "work" / "R10-T050"
FIXTURES_FILE = EVIDENCE_DIR / "fixtures" / "maintenance_scenarios.json"

EXPECTED_ENTRIES = (
    {
        "title": "LaTeX for nybegynnere",
        "url": "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-for-nybegynnere.pdf",
        "category": "Latex",
        "line_number": 8,
        "author": "Dag Langmyhr",
        "format": "PDF",
        "metadata": "- Dag Langmyhr (PDF)",
    },
    {
        "title": "LaTeX for viderekomne",
        "url": "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-videre.pdf",
        "category": "Latex",
        "line_number": 9,
        "author": "Dag Langmyhr",
        "format": "PDF",
        "metadata": "- Dag Langmyhr (PDF)",
    },
    {
        "title": "Lokal guide til farger i LaTeX",
        "url": "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/farger.pdf",
        "category": "Latex",
        "line_number": 10,
        "author": "Dag Langmyhr",
        "format": "PDF",
        "metadata": "- Dag Langmyhr (PDF)",
    },
)
ENTRY_BY_URL = {entry["url"]: entry for entry in EXPECTED_ENTRIES}

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)(?:\s+#+)?\s*$")
LINK_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)
META_RE = re.compile(r"^-\s+(?P<author>[^(]+?)(?:\s+\((?P<format>[^)]+)\))?\s*$")

VERIFIED_OBSERVATIONS = {
    "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-for-nybegynnere.pdf": {
        "http_status": 200,
        "content_type": "application/pdf",
        "content_length_bytes": 9432358,
        "observed_title": "LaTeX for nybegynnere",
        "observed_author": "Dag Langmyhr",
        "observed_format": "PDF",
        "manual_verification": True,
        "notes": "Verified official lecture notes by Dag Langmyhr at UiO IFI; publicly accessible PDF.",
    },
    "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/latex-videre.pdf": {
        "http_status": 200,
        "content_type": "application/pdf",
        "content_length_bytes": 487711,
        "observed_title": "LaTeX for viderekomne",
        "observed_author": "Dag Langmyhr",
        "observed_format": "PDF",
        "manual_verification": True,
        "notes": "Verified advanced LaTeX notes by Dag Langmyhr at UiO IFI; publicly accessible PDF.",
    },
    "https://www.mn.uio.no/ifi/tjenester/it/hjelp/latex/farger.pdf": {
        "http_status": 200,
        "content_type": "application/pdf",
        "content_length_bytes": 131814,
        "observed_title": "Lokal guide til farger i LaTeX",
        "observed_author": "Dag Langmyhr",
        "observed_format": "PDF",
        "manual_verification": True,
        "notes": "Verified color guide by Dag Langmyhr at UiO IFI; publicly accessible PDF.",
    },
}


def parse_selected_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse only the assigned Norwegian book entries and retain source line numbers."""
    entries: list[dict[str, Any]] = []
    category: str | None = None

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading:
            category = re.sub(r"</?a\b[^>]*>", "", heading.group(2)).strip()
            continue

        match = LINK_RE.match(line)
        if match is None:
            continue

        url = match.group("url")
        expected = ENTRY_BY_URL.get(url)
        if expected is None:
            continue

        meta_str = match.group("metadata").strip()
        author: str | None = None
        doc_format: str | None = None
        meta_match = META_RE.match(meta_str)
        if meta_match:
            author = meta_match.group("author").strip()
            doc_format = meta_match.group("format")

        entries.append(
            {
                "title": match.group("title").strip(),
                "url": url,
                "category": category,
                "line_number": line_number,
                "author": author,
                "format": doc_format,
                "metadata": meta_str,
                "expected": expected,
            }
        )
    return entries


def validate_source(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate that the source markdown matches expected selected entries."""
    errors: list[dict[str, Any]] = []
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
        for field in ("title", "category", "line_number", "author", "format"):
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


def evaluate_maintenance(
    entry: dict[str, Any], facts: dict[str, Any]
) -> dict[str, Any]:
    """Separate observed facts from maintenance recommendations."""
    manual_verified = facts.get("manual_verification") is True
    http_status = facts.get("http_status")
    observed_author = facts.get("observed_author")
    observed_title = facts.get("observed_title")
    observed_format = facts.get("observed_format")

    # Clear separation of observed facts
    observed_record = {
        "http_status": http_status,
        "content_type": facts.get("content_type"),
        "content_length_bytes": facts.get("content_length_bytes"),
        "observed_title": observed_title,
        "observed_author": observed_author,
        "observed_format": observed_format,
        "manual_verification": manual_verified,
        "notes": facts.get("notes", ""),
    }

    # Derive recommendation based on established maintenance policy
    if not manual_verified and (http_status is None or http_status >= 400):
        # Automated failure without manual inspection: NEVER remove
        recommendation = {
            "action": "investigate",
            "removal_recommended": False,
            "metadata_change_recommended": False,
            "decision_rationale": "Automated network issue without manual verification; link must not be deleted.",
        }
    elif manual_verified and http_status == 404:
        # Confirmed dead resource with manual inspection
        recommendation = {
            "action": "propose_removal",
            "removal_recommended": True,
            "metadata_change_recommended": False,
            "decision_rationale": "Manual inspection confirmed resource is permanently gone without redirect.",
        }
    elif manual_verified and (
        (observed_author and observed_author != entry.get("author"))
        or (observed_title and observed_title != entry.get("title"))
        or (observed_format and observed_format != entry.get("format"))
    ):
        # Metadata drift detected
        recommendation = {
            "action": "update_metadata",
            "removal_recommended": False,
            "metadata_change_recommended": True,
            "decision_rationale": "Resource remains available, but title, author, or format changed; update metadata.",
        }
    else:
        # Resource is healthy and metadata aligns
        recommendation = {
            "action": "retain",
            "removal_recommended": False,
            "metadata_change_recommended": False,
            "decision_rationale": "Resource is available, format is valid PDF, metadata accurately reflects document attributes.",
        }

    return {
        "url": entry["url"],
        "line_number": entry["line_number"],
        "title": entry["title"],
        "category": entry["category"],
        "author": entry.get("author"),
        "format": entry.get("format"),
        "observed_facts": observed_record,
        "recommendation": recommendation,
    }


def run_maintenance_pass(
    entries: list[dict[str, Any]],
    observations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = []
    for entry in entries:
        facts = observations.get(
            entry["url"],
            {
                "http_status": None,
                "manual_verification": False,
                "notes": "No observations recorded.",
            },
        )
        report_item = evaluate_maintenance(entry, facts)
        results.append(report_item)
    return results


class CourseCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = json.loads(FIXTURES_FILE.read_text(encoding="utf-8"))

    def test_selected_entries_match_source_lines(self) -> None:
        entries = parse_selected_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        self.assertEqual(validate_source(entries), [])
        self.assertEqual(len(entries), 3)
        self.assertEqual([e["line_number"] for e in entries], [8, 9, 10])
        self.assertEqual([e["category"] for e in entries], ["Latex", "Latex", "Latex"])
        self.assertEqual([e["author"] for e in entries], ["Dag Langmyhr", "Dag Langmyhr", "Dag Langmyhr"])
        self.assertEqual([e["format"] for e in entries], ["PDF", "PDF", "PDF"])

    def test_maintenance_scenarios_separate_facts_and_recommendations(self) -> None:
        for scenario in self.fixtures["scenarios"]:
            with self.subTest(scenario=scenario["name"]):
                result = evaluate_maintenance(scenario["entry"], scenario["observed_facts"])
                self.assertIn("observed_facts", result)
                self.assertIn("recommendation", result)
                expected_rec = scenario["expected_recommendation"]
                actual_rec = result["recommendation"]
                self.assertEqual(actual_rec["action"], expected_rec["action"])
                self.assertEqual(
                    actual_rec["removal_recommended"], expected_rec["removal_recommended"]
                )
                self.assertEqual(
                    actual_rec["metadata_change_recommended"],
                    expected_rec["metadata_change_recommended"],
                )

    def test_no_link_removed_on_single_automated_failure(self) -> None:
        scenario = next(s for s in self.fixtures["scenarios"] if s["name"] == "transient_automated_failure")
        result = evaluate_maintenance(scenario["entry"], scenario["observed_facts"])
        self.assertFalse(result["recommendation"]["removal_recommended"])
        self.assertEqual(result["recommendation"]["action"], "investigate")

    def test_no_credentials_stored(self) -> None:
        for obs in VERIFIED_OBSERVATIONS.values():
            self.assertNotIn("password", obs)
            self.assertNotIn("token", obs)
            self.assertNotIn("credential", obs)

    def test_failed_self_test_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t050.py", "--self-test"]), \
                patch(
                    f"{__name__}.test_output",
                    return_value=(False, "simulated test failure\n"),
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
    maintenance_report: list[dict[str, Any]],
) -> None:
    inputs = {
        "target_file": "books/free-programming-books-no.md",
        "target_section": "Norwegian programming books: Latex",
        "selected_entries": [
            {
                "title": entry["title"],
                "url": entry["url"],
                "category": entry["category"],
                "line_number": entry["line_number"],
                "author": entry.get("author"),
                "format": entry.get("format"),
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
        "maintenance_report": maintenance_report,
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
        "# R10-T050 Repeatable Maintenance Pass Report",
        "",
        "- Target: `books/free-programming-books-no.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        "",
        "## Scoped Maintenance Report",
        "",
        "| Line | Title | Category | Author | Format | HTTP | Manual Check | Recommendation | Rationale |",
        "| ---: | --- | --- | --- | --- | :---: | :---: | --- | --- |",
    ]
    for item in maintenance_report:
        facts = item["observed_facts"]
        rec = item["recommendation"]
        report_lines.append(
            f"| {item['line_number']} | {item['title']} | {item['category']} | {item['author']} | "
            f"{item['format']} | {facts['http_status']} | {facts['manual_verification']} | "
            f"`{rec['action']}` | {rec['decision_rationale']} |"
        )
    if validation_failures:
        report_lines.extend(["", "### Validation Failures:", f"```json\n{json.dumps(validation_failures, indent=2)}\n```"])
    report_lines.extend(
        [
            "",
            "### Policy Invariants:",
            "1. Exact source line numbers are preserved in every report row.",
            "2. Observed facts (HTTP status, content length, verified format) are strictly decoupled from recommendations.",
            "3. No link is proposed for removal based solely on a single automated crawl or failure.",
            "4. Reproducible offline fixtures verify before/after maintenance decisions without network access.",
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
    maintenance_report = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        actual = parse_selected_entries(source_text)
        validation_failures = validate_source(actual)
        maintenance_report = run_maintenance_pass(actual, VERIFIED_OBSERVATIONS)
    except Exception as error:
        validation_failures = [{"error": str(error)}]

    write_evidence(
        actual,
        validation_failures,
        self_test_status,
        self_test_output,
        maintenance_report,
    )

    if validation_failures:
        print(f"r10-t050: validation failures: {validation_failures}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(maintenance_report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
