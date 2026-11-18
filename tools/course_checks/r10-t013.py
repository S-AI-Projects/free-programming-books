#!/usr/bin/env python3
"""Report exact and conservative-normalization duplicate URLs in the Swedish casts list."""

from __future__ import annotations

import argparse
from collections import defaultdict
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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-sv.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T013"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"

SELECTED_ENTRIES = (
    {
        "display_name": "Agilpodden",
        "url": "https://www.agilpodden.se",
        "category": "Language Agnostic",
        "line_number": 8,
        "metadata": "- Dick Lyhammar, Erik Hultgren (podcast)",
    },
    {
        "display_name": "AI-Podden",
        "url": "https://ai-podden.se",
        "category": "Language Agnostic",
        "line_number": 9,
        "metadata": "- Ather Gattami, Bitynamics, Cloudberry (podcast)",
    },
    {
        "display_name": "Asdf",
        "url": "https://asdf.pizza",
        "category": "Language Agnostic",
        "line_number": 10,
        "metadata": "- Therése Komstadius, Anton Gunnarsson (podcast)",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)


def parse_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse resource bullets, fenced blocks excluded, with heading and line context."""
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
            elif fence[0] == fence_char and len(fence) >= fence_length:
                fence_char, fence_length = None, 0
            continue
        if fence_char is not None:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_hierarchy = {
                depth: title
                for depth, title in heading_hierarchy.items()
                if depth < level
            }
            title = re.sub(r"<[^>]*>", "", heading_match.group(2).strip())
            heading_hierarchy[level] = title
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue

        category = " > ".join(
            heading_hierarchy[depth] for depth in sorted(heading_hierarchy)
        )
        # Skip top-level index section
        if category == "Index":
            continue

        entries.append(
            {
                "display_name": entry_match.group("display_name"),
                "url": entry_match.group("url"),
                "category": category or None,
                "line_number": line_number,
                "metadata": entry_match.group("metadata").strip(),
            }
        )
    return entries


def conservative_normalize(url: str) -> str:
    """Normalize only host case, default ports, trailing slashes, and query parameter order."""
    split = urlsplit(url)
    scheme = split.scheme.lower()
    hostname = (split.hostname or "").lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"

    port = split.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None
    netloc = hostname
    if split.username:
        netloc = f"{split.username}@{netloc}"
    if port is not None:
        netloc = f"{netloc}:{port}"

    path = split.path
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(sorted(parse_qsl(split.query, keep_blank_values=True)))
    return urlunsplit((scheme, netloc, path, query, split.fragment))


def group_duplicates(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Return exact raw duplicate groups only."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["url"]].append(entry)
    return {url: matches for url, matches in grouped.items() if len(matches) > 1}


def group_normalized_duplicates(
    entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return normalized groups that are not exact duplicate groups."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[conservative_normalize(entry["url"])].append(entry)

    exact_groups = group_duplicates(entries)
    return {
        normalized: matches
        for normalized, matches in grouped.items()
        if len(matches) > 1
        and not all(match["url"] in exact_groups for match in matches)
    }


def select_required_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Select and validate exactly the three fixed assigned entries."""
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
        mismatches.append(
            {"field": "entry_count", "expected": len(SELECTED_ENTRIES), "actual": len(actual)}
        )
    return mismatches


class CourseCheckTests(unittest.TestCase):
    def fixture_entries(self, name: str) -> list[dict[str, Any]]:
        return parse_entries((FIXTURE_DIR / name).read_text(encoding="utf-8"))

    def test_exact_duplicates(self) -> None:
        fixture = self.fixture_entries("success.md")
        groups = group_duplicates(fixture)
        self.assertIn("https://example.test/cast", groups)
        self.assertEqual(len(groups["https://example.test/cast"]), 2)

    def test_normalization_keeps_meaningful_parts_distinct(self) -> None:
        entries = self.fixture_entries("normalization.md")
        groups = group_normalized_duplicates(entries)
        self.assertTrue(
            conservative_normalize("HTTPS://EXAMPLE.TEST/cast/")
            == conservative_normalize("https://example.test/cast")
        )
        self.assertNotEqual(
            conservative_normalize("https://example.test/cast?a=1&b=2"),
            conservative_normalize("https://example.test/cast?a=1"),
        )
        self.assertNotEqual(
            conservative_normalize("http://example.test/cast"),
            conservative_normalize("https://example.test/cast"),
        )
        self.assertNotEqual(
            conservative_normalize("https://example.test/cast#ep1"),
            conservative_normalize("https://example.test/cast#ep2"),
        )

    def test_parameter_order_is_normalized_but_values_are_not_merged(self) -> None:
        one = "https://example.test/cast?a=1&b=2"
        two = "https://example.test/cast/?b=2&a=1"
        self.assertEqual(conservative_normalize(one), conservative_normalize(two))
        self.assertNotEqual(
            conservative_normalize("https://example.test/cast?a=1"),
            conservative_normalize("https://example.test/cast?a=2"),
        )

    def test_fenced_fake_links_are_ignored(self) -> None:
        self.assertEqual(self.fixture_entries("fenced-code.md"), [])

    def test_missing_and_wrong_entry_assertions(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entries([])
        actual = select_required_entries(self.fixture_entries("success.md"))
        actual[0]["line_number"] += 1
        mismatches = compare_expected(actual)
        self.assertTrue(any(item["field"] == "line_number" for item in mismatches))

    def test_selected_source_entries(self) -> None:
        actual = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        self.assertEqual(compare_expected(actual), [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t013.py", "--self-test"]), \
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
    all_entries: list[dict[str, Any]],
) -> None:
    exact_duplicates = group_duplicates(all_entries)
    normalized_duplicates = group_normalized_duplicates(all_entries)

    inputs = {
        "target_file": "casts/free-podcasts-screencasts-sv.md",
        "target_section": "Swedish casts list; category: Language Agnostic",
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
        "duplicates": {
            "exact_duplicate_count": len(exact_duplicates),
            "exact_duplicates": [
                {"url": url, "matches": matches}
                for url, matches in exact_duplicates.items()
            ],
            "normalized_duplicate_count": len(normalized_duplicates),
            "normalized_duplicates": [
                {"normalized_url": norm, "matches": matches}
                for norm, matches in normalized_duplicates.items()
            ],
        },
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
        "# R10-T013 duplicate detection report",
        "",
        "- Source: `casts/free-podcasts-screencasts-sv.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Exact duplicate groups: {len(exact_duplicates)}",
        f"- Normalized duplicate groups: {len(normalized_duplicates)}",
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
            "Exact duplicates are grouped without merging distinct query parameters or fragments.",
            "Every proposed removal requires manual review of the duplicate pair.",
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
    all_entries: list[dict[str, Any]] = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        all_entries = parse_entries(source_text)
        actual = select_required_entries(all_entries)
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        all_entries,
    )

    if validation_error:
        print(f"r10-t013: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
