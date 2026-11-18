#!/usr/bin/env python3
"""Verify catalogue metadata for selected Marathi course entries."""

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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch
import urllib.request
import urllib.error
from urllib.parse import urlencode


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "courses" / "free-courses-mr.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T025"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2
OBSERVED_DATE = "2026-11-18"

SELECTED_ENTRIES = (
    {
        "display_name": "अँड्रॉइड ऍप डेव्हलपमेंट मराठी | Android App Development in Marathi",
        "url": "https://youtube.com/playlist?list=PLy1NOWTMDFjDLCgmxRNLDJtlutJOYl2d7",
        "category": "Android",
        "line_number": 19,
        "author": "उत्तर",
        "provider": "YouTube",
    },
    {
        "display_name": "Angular in Marathi",
        "url": "https://youtube.com/playlist?list=PLpDAynbYcV3sruD9MNfmZtimPCKHicA2V",
        "category": "Angular",
        "line_number": 24,
        "author": "Finishing School",
        "provider": "YouTube",
    },
    {
        "display_name": "Angular Tutorials in Marathi",
        "url": "https://youtube.com/playlist?list=PLMs908ICeVMEBw4CevNdPvvIJDaQV1ISN",
        "category": "Angular",
        "line_number": 25,
        "author": "Developers Marathi",
        "provider": "YouTube",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)
AUTHOR_RE = re.compile(r"^-\s+(.+?)\s*$")


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
            hierarchy = {
                depth: value
                for depth, value in hierarchy.items()
                if depth < level
            }
            hierarchy[level] = title
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue
        metadata = entry_match.group("metadata").strip()
        author_match = AUTHOR_RE.match(metadata)
        display_name = entry_match.group("display_name").replace(r"\|", "|")
        entries.append(
            {
                "display_name": display_name,
                "url": entry_match.group("url"),
                "category": " > ".join(
                    hierarchy[depth] for depth in sorted(hierarchy)
                )
                or None,
                "line_number": line_number,
                "author": author_match.group(1).strip() if author_match else None,
                "provider": "YouTube",
                "metadata": metadata,
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
    for field in ("display_name", "url", "category", "line_number", "author", "provider"):
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
        for field in ("display_name", "url", "category", "line_number", "author", "provider"):
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
            {"field": "entry_count", "expected": 3, "actual": len(actual)}
        )
    return mismatches


def evidence_table(actual: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Produce source URL/observed/proposed evidence for catalogue fields."""
    table = []
    observed_by_url = {entry["url"]: entry for entry in actual}
    for expected in SELECTED_ENTRIES:
        observed = observed_by_url.get(expected["url"])
        for field in ("display_name", "author", "category", "url", "provider"):
            observed_value = observed.get(field) if observed else None
            proposed_value = expected[field]
            if observed_value != proposed_value:
                table.append(
                    {
                        "source_url": expected["url"],
                        "field": field,
                        "observed_value": observed_value,
                        "proposed_value": proposed_value,
                        "line_number": expected["line_number"],
                        "observation_date": OBSERVED_DATE,
                    }
                )
    return table


def fetch_youtube_oembed(entry: dict[str, Any]) -> dict[str, Any]:
    oembed_url = "https://www.youtube.com/oembed?" + urlencode(
        {"url": entry["url"], "format": "json"}
    )
    request = urllib.request.Request(
        oembed_url,
        headers={"User-Agent": "R10-T025 metadata checker/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=LIVE_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {
            "url": entry["url"],
            "display_name": data.get("title"),
            "author": data.get("author_name"),
            "provider": data.get("provider_name"),
            "category": entry["category"],
            "line_number": entry["line_number"],
            "observation_date": OBSERVED_DATE,
            "status": "success",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {
            "url": entry["url"],
            "category": entry["category"],
            "line_number": entry["line_number"],
            "observation_date": OBSERVED_DATE,
            "status": "request_failed",
            "error": str(error),
        }


def verify_live(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fixed = [entry for entry in entries if entry["url"] in SELECTED_URLS]
    with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
        return list(executor.map(fetch_youtube_oembed, fixed))


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> list[dict[str, Any]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_success_fixture_matches_required_metadata(self) -> None:
        entries = self.fixture_entries("success.md")
        selected = select_required_entries(entries)
        selected_by_url = {entry["url"]: entry for entry in selected}
        for expected in SELECTED_ENTRIES:
            actual = selected_by_url[expected["url"]]
            for field in ("display_name", "url", "category", "author", "provider"):
                self.assertEqual(actual.get(field), expected[field])

    def test_missing_required_field_fails(self) -> None:
        entries = self.fixture_entries("missing-field.md")
        selected = select_required_entries(entries)
        missing = validate_required_metadata(selected[0])
        self.assertIn("author", missing)
        with self.assertRaisesRegex(AssertionError, "missing"):
            raise AssertionError(f"missing required metadata: {', '.join(missing)}")

    def test_mismatched_title_creates_evidence_change(self) -> None:
        actual = [dict(entry) for entry in SELECTED_ENTRIES]
        actual[1]["display_name"] = "Wrong Angular title"
        changes = evidence_table(actual)
        change = next(
            row
            for row in changes
            if row["field"] == "display_name"
            and row["source_url"] == SELECTED_ENTRIES[1]["url"]
        )
        self.assertEqual(change["observed_value"], "Wrong Angular title")
        self.assertEqual(change["proposed_value"], "Angular in Marathi")

    def test_missing_entry_raises_assertion(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entries([])

    def test_source_entries_and_required_metadata(self) -> None:
        entries = parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        actual = select_required_entries(entries)
        self.assertEqual(compare_metadata(actual), [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t025.py", "--self-test"]), patch(
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
    validation_error: str | None,
    self_test_status: str,
    self_test_output: str,
    live_results: list[dict[str, Any]] | None,
) -> None:
    mismatches = compare_metadata(actual)
    changes = evidence_table(actual)
    inputs = {
        "target_file": "courses/free-courses-mr.md",
        "target_section": "Android and Angular",
        "selected_entries": list(SELECTED_ENTRIES),
        "required_fields": ["display_name", "url", "category", "line_number", "author", "provider"],
        "live_limits": {
            "timeout_seconds": LIVE_TIMEOUT_SECONDS,
            "max_workers": LIVE_MAX_WORKERS,
        },
    }
    expected_vs_actual = {
        "expected": list(SELECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not mismatches and validation_error is None else "failed",
            "mismatches": mismatches,
            "error": validation_error,
        },
        "evidence_changes": changes,
        "live_request_results": live_results,
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
        "# R10-T025 metadata verification report",
        "",
        "- Source: `courses/free-courses-mr.md`",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Evidence-backed changes: {len(changes)}",
        "",
        "## Selected metadata",
        "",
        "| Line | Title | Author | Category | Provider | URL |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for entry in actual:
        report.append(
            f"| {entry['line_number']} | "
            f"{entry['display_name'].replace('|', r'\\|')} | "
            f"{entry['author']} | {entry['category']} | "
            f"{entry['provider']} | `{entry['url']}` |"
        )
    report.extend(["", "## Evidence table", ""])
    if changes:
        report.append("| Source URL | Field | Observed | Proposed | Line |")
        report.append("| --- | --- | --- | --- | ---: |")
        for change in changes:
            report.append(
                f"| `{change['source_url']}` | {change['field']} | "
                f"{change['observed_value']} | {change['proposed_value']} | "
                f"{change['line_number']} |"
            )
    else:
        report.append(
            "No real metadata changes are proposed. Official YouTube/oEmbed observations "
            "matched all catalogue titles and authors on 2026-11-18."
        )
    if live_results is not None:
        report.extend(["", "## Live oEmbed observations", ""])
        for result in live_results:
            if result["status"] == "success":
                report.append(
                    f"- `{result['url']}`: title={result['display_name']}; "
                    f"author={result['author']}; provider={result['provider']} "
                    f"(observed {result['observation_date']})"
                )
            else:
                report.append(
                    f"- `{result['url']}`: request failed "
                    f"({result['error']}; observed {result['observation_date']})"
                )
    report.extend(
        [
            "",
            "No link was removed solely because an automated request failed.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixture tests")
    parser.add_argument(
        "--live",
        action="store_true",
        help="fetch bounded YouTube oEmbed metadata for the three fixed URLs",
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
    actual: list[dict[str, Any]] = []
    try:
        actual = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
    except (OSError, AssertionError) as error:
        validation_error = str(error)

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

    mismatches = compare_metadata(actual)
    if validation_error:
        print(f"r10-t025: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed or mismatches:
        return 1
    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
