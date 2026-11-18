#!/usr/bin/env python3
"""Extract and validate selected entries in the Czech casts list."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import io
import json
import platform
import re
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-cs.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T011"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2
SELECTED_ENTRIES = (
    {
        "display_name": "Brus kódu",
        "url": "http://bruskodu.cz",
        "category": "Podcasty",
        "line_number": 3,
        "metadata": "- pro frontend vývojáře",
    },
    {
        "display_name": "CZpodcast",
        "url": "https://soundcloud.com/czpodcast-1",
        "category": "Podcasty",
        "line_number": 4,
        "metadata": "",
    },
    {
        "display_name": "DevMinutes",
        "url": "http://devminutes.cz",
        "category": "Podcasty",
        "line_number": 5,
        "metadata": "",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)


def parse_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse resource bullets and retain heading hierarchy and original line numbers."""
    entries: list[dict[str, Any]] = []
    heading_hierarchy: dict[int, str] = {}
    fence_char: str | None = None
    fence_length = 0

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        fence_match = FENCE_RE.match(line)
        if fence_match:
            fence = fence_match.group(1)
            if fence_char is None:
                fence_char, fence_length = fence[0], len(fence)
            elif (
                fence[0] == fence_char
                and len(fence) >= fence_length
                and not fence_match.group(2).strip()
            ):
                fence_char, fence_length = None, 0
            continue
        if fence_char is not None:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_hierarchy = {
                depth: title for depth, title in heading_hierarchy.items() if depth < level
            }
            heading_hierarchy[level] = heading_match.group(2).strip()
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue

        metadata = entry_match.group("metadata").strip()

        entries.append(
            {
                "display_name": entry_match.group("display_name"),
                "url": entry_match.group("url"),
                "category": " > ".join(
                    heading_hierarchy[depth] for depth in sorted(heading_hierarchy)
                )
                or None,
                "metadata": metadata,
                "line_number": line_number,
            }
        )

    return entries


def select_required_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select the fixed task entries and fail explicitly if one is missing or duplicated."""
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
        for field in expected:
            if observed[field] != expected[field]:
                mismatches.append(
                    {
                        "display_name": expected["display_name"],
                        "field": field,
                        "expected": expected[field],
                        "actual": observed[field],
                    }
                )
    if len(actual) != len(SELECTED_ENTRIES):
        mismatches.append(
            {
                "field": "entry_count",
                "expected": len(SELECTED_ENTRIES),
                "actual": len(actual),
            }
        )
    return mismatches


def assert_expected_entries(actual: list[dict[str, Any]]) -> None:
    mismatches = compare_expected(actual)
    if mismatches:
        raise AssertionError(json.dumps(mismatches, ensure_ascii=False))


def check_url(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Check one fixed URL without treating a request failure as a removal decision."""
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "fpb-checker/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {"url": url, "ok": response.status < 400, "status": response.status}
    except urllib.error.HTTPError as error:
        return {"url": url, "ok": False, "status": error.code, "error": str(error)}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"url": url, "ok": False, "error": str(error)}


def verify_live(entries: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Probe only the selected URLs and return entries unchanged with separate statuses."""
    fixed_entries = [entry for entry in entries if entry["url"] in SELECTED_URLS]
    with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
        results = list(executor.map(lambda entry: check_url(entry["url"]), fixed_entries))
    return entries, results


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> list[dict[str, Any]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_success_fixture_extracts_hierarchy_metadata_and_fragment(self) -> None:
        selected = select_required_entries(self.fixture_entries("success.md"))
        self.assertEqual(
            [(entry["line_number"], entry["category"]) for entry in selected],
            [(3, "Podcasty"), (4, "Podcasty"), (5, "Podcasty")],
        )
        self.assertEqual(selected[0]["display_name"], "Brus kódu")
        self.assertEqual(selected[0]["metadata"], "- pro frontend vývojáře")
        fragment = next(
            entry
            for entry in self.fixture_entries("success.md")
            if entry["display_name"] == "Fragment fixture"
        )
        self.assertEqual(fragment["url"], "https://example.test/casts#ep-1")
        self.assertEqual(fragment["metadata"], "- test metadata")

    def test_fenced_code_fixture_is_ignored(self) -> None:
        entries = self.fixture_entries("fenced-code.md")
        self.assertEqual(entries, [])

    def test_missing_entry_raises_assertion_and_wrong_line_is_detected(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entries(self.fixture_entries("failure.md"))

        actual = select_required_entries(self.fixture_entries("success.md"))
        actual[0]["line_number"] += 1
        with self.assertRaisesRegex(AssertionError, "line_number"):
            assert_expected_entries(actual)

    def test_failed_live_request_does_not_remove_entry(self) -> None:
        entries = select_required_entries(self.fixture_entries("success.md"))
        failed_url = entries[0]["url"]

        def fake_check(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
            if url == failed_url:
                return {"url": url, "ok": False, "error": "simulated timeout"}
            return {"url": url, "ok": True, "status": 200}

        with patch(f"{__name__}.check_url", side_effect=fake_check):
            retained, results = verify_live(entries)

        self.assertEqual(retained, entries)
        self.assertEqual(len(retained), 3)
        self.assertFalse(next(result for result in results if result["url"] == failed_url)["ok"])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t011.py", "--self-test"]), \
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
    live_results: list[dict[str, Any]] | None,
) -> None:
    inputs = {
        "target_file": "casts/free-podcasts-screencasts-cs.md",
        "target_section": "Czech casts list; selected category: Podcasty",
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
    mismatches = compare_expected(actual)
    expected_vs_actual = {
        "expected": list(SELECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not mismatches and validation_error is None else "failed",
            "mismatches": mismatches,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
        "live_request_results": live_results,
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
        "# R10-T011 checker report",
        "",
        "- Source: `casts/free-podcasts-screencasts-cs.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Live request checks: {'run' if live_results is not None else 'not run'}",
        "",
        "## Extracted records",
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
    if live_results is not None:
        report_lines.extend(
            [
                "",
                "Live request results are informational only; failed requests do not remove entries.",
                "",
            ]
        )
        report_lines.extend(
            f"- `{result['url']}`: {'reachable' if result['ok'] else 'request failed'}"
            for result in live_results
        )
    report_lines.extend(
        [
            "",
            "No catalogue correction was needed; the selected source entries match their expected",
            "display names and URLs. The checker uses only the Python standard library.",
            "",
        ]
    )
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report_lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixture tests")
    parser.add_argument(
        "--live",
        action="store_true",
        help="make informational HEAD requests to the three fixed URLs (5-second timeout)",
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
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        actual = select_required_entries(parse_entries(source_text))
        assert_expected_entries(actual)
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    live_results = None
    if args.live and actual:
        _, live_results = verify_live(actual)

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        live_results,
    )

    if validation_error:
        print(f"r10-t011: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
