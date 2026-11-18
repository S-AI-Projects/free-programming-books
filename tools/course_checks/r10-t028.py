#!/usr/bin/env python3
"""Validate the heading, index, bullet, and ordering rules for one RU list."""

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
SOURCE_FILE = ROOT / "more" / "free-programming-playgrounds-ru.md"
EVIDENCE_DIR = ROOT / "work" / "R10-T028"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
TARGET_SECTION = "Python"
EXPECTED_ENTRY = {
    "title": "Python онлайн: запусти код в браузере",
    "url": "https://koddo.ru/playground/python",
    "section": TARGET_SECTION,
    "line_number": 8,
}

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_BULLET_RE = re.compile(
    r"^ {0,3}(?P<marker>[-*+])\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)(?P<metadata>.*)$"
)
BULLET_LINE_RE = re.compile(r"^ {0,3}[-*+]\s+")
RUSSIAN_ALPHABET = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"


def alphabetical_key(text: str) -> tuple[int, ...]:
    """Case-insensitive Unicode order with Russian letters in alphabet order."""
    key = []
    for character in text.casefold():
        if character in RUSSIAN_ALPHABET:
            key.append(1000 + RUSSIAN_ALPHABET.index(character))
        elif "a" <= character <= "z":
            key.append(ord(character))
        else:
            key.append(ord(character))
    return tuple(key)


def anchor_for(title: str) -> str:
    return re.sub(r"[^a-z0-9а-яё]+", "-", title.casefold()).strip("-")


def inspect_markdown(markdown: str) -> dict[str, Any]:
    """Parse headings and links, retaining exact text and one-based source lines."""
    headings: list[dict[str, Any]] = []
    index_entries: list[dict[str, Any]] = []
    selected_entries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    active_section: str | None = None
    active_heading_line: int | None = None
    previous_heading_level = 0
    target_heading_lines: list[int] = []

    def report(code: str, line_number: int, message: str) -> None:
        errors.append(
            {"code": code, "line_number": line_number, "message": message}
        )

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            headings.append(
                {"level": level, "title": title, "line_number": line_number}
            )
            if level not in (3, 4):
                report(
                    "invalid-heading-level",
                    line_number,
                    "List sections must use level-three headings and subsections level four.",
                )
            if previous_heading_level and level > previous_heading_level + 1:
                report(
                    "heading-level-skip",
                    line_number,
                    "Heading hierarchy skips a level.",
                )
            previous_heading_level = level
            active_section = title if level == 3 else active_section
            active_heading_line = line_number if level == 3 else active_heading_line
            if title == TARGET_SECTION:
                target_heading_lines.append(line_number)
            continue

        if active_section not in ("Index", TARGET_SECTION):
            continue
        if not BULLET_LINE_RE.match(line):
            if active_section == TARGET_SECTION and line.strip().startswith("|"):
                report(
                    "unexpected-table-row",
                    line_number,
                    "The selected section uses bullet links, not a Markdown table.",
                )
            continue

        entry_match = LINK_BULLET_RE.match(line)
        if entry_match is None:
            report(
                "malformed-list-entry",
                line_number,
                "Expected a bullet followed by a Markdown link.",
            )
            continue

        entry = {
            "title": entry_match.group("title"),
            "url": entry_match.group("url"),
            "metadata": entry_match.group("metadata"),
            "marker": entry_match.group("marker"),
            "section": active_section,
            "line_number": line_number,
            "raw_line": line,
        }
        if active_section == "Index":
            index_entries.append(entry)
            if entry["url"] != f"#{anchor_for(entry['title'])}":
                report(
                    "invalid-index-anchor",
                    line_number,
                    "Index links must point to the matching section anchor.",
                )
        else:
            selected_entries.append(entry)
            if not entry["url"].startswith(("https://", "http://")):
                report(
                    "invalid-resource-url",
                    line_number,
                    "Resource links must use an HTTP or HTTPS URL.",
                )

    if not headings or headings[0]["title"] != "Index" or headings[0]["level"] != 3:
        report(
            "missing-index-heading",
            headings[0]["line_number"] if headings else 1,
            "The file must start with a level-three Index heading.",
        )

    section_headings = [
        heading
        for heading in headings
        if heading["level"] == 3 and heading["title"] != "Index"
    ]
    for before, after in zip(section_headings, section_headings[1:]):
        if alphabetical_key(before["title"]) > alphabetical_key(after["title"]):
            report(
                "out-of-order-section",
                after["line_number"],
                f"Section {after['title']!r} should precede {before['title']!r}.",
            )

    section_titles = [heading["title"] for heading in section_headings]
    index_titles = [entry["title"] for entry in index_entries]
    if index_titles != section_titles:
        report(
            "index-section-mismatch",
            headings[0]["line_number"] if headings else 1,
            "Index links must list the level-three sections in the same order.",
        )

    if len(target_heading_lines) != 1:
        report(
            "target-section-count",
            target_heading_lines[1] if len(target_heading_lines) > 1 else len(markdown.splitlines()) + 1,
            f"Expected exactly one level-three {TARGET_SECTION!r} section.",
        )
    for before, after in zip(selected_entries, selected_entries[1:]):
        if alphabetical_key(before["title"]) > alphabetical_key(after["title"]):
            report(
                "out-of-order-entry",
                after["line_number"],
                f"Entry {after['title']!r} should precede {before['title']!r}.",
            )

    return {
        "headings": headings,
        "index_entries": index_entries,
        "entries": selected_entries,
        "target_heading_line": (
            target_heading_lines[0] if len(target_heading_lines) == 1 else None
        ),
        "errors": errors,
        "active_heading_line": active_heading_line,
    }


def validate_selected(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate that the exact assigned resource occurs once in Python."""
    errors = list(document["errors"])
    matches = [
        entry
        for entry in document["entries"]
        if entry["url"] == EXPECTED_ENTRY["url"]
    ]
    diagnostic_line = document["target_heading_line"] or len(
        document["headings"]
    ) + 1
    if len(matches) != 1:
        errors.append(
            {
                "code": "selected-entry-count",
                "line_number": matches[1]["line_number"]
                if len(matches) > 1
                else diagnostic_line,
                "message": (
                    "Expected the assigned playground URL exactly once in "
                    f"the {TARGET_SECTION} section."
                ),
            }
        )
        return errors

    selected = matches[0]
    for field in ("title", "section"):
        expected = EXPECTED_ENTRY[field]
        actual = selected[field]
        if actual != expected:
            errors.append(
                {
                    "code": f"selected-entry-{field}",
                    "line_number": selected["line_number"],
                    "message": f"Expected {field} {expected!r}; found {actual!r}.",
                }
            )
    return errors


def validate_source(markdown: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = inspect_markdown(markdown)
    return document, validate_selected(document)


class CourseCheckTests(unittest.TestCase):
    def fixture(self, name: str) -> str:
        return (FIXTURE_DIR / name).read_text(encoding="utf-8")

    def test_source_has_valid_headings_index_and_selected_bullet(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        document, errors = validate_source(source)
        self.assertEqual(errors, [])
        self.assertEqual(document["target_heading_line"], 6)
        self.assertEqual(document["entries"][0]["line_number"], 8)

    def test_valid_fixture_preserves_cyrillic_text_and_markdown_link(self) -> None:
        document, errors = validate_source(self.fixture("valid.md"))
        self.assertEqual(errors, [])
        selected = document["entries"][0]
        self.assertEqual(selected["title"], EXPECTED_ENTRY["title"])
        self.assertEqual(selected["url"], EXPECTED_ENTRY["url"])
        self.assertEqual(
            selected["raw_line"],
            "* [Python онлайн: запусти код в браузере]"
            "(https://koddo.ru/playground/python) - Koddo (без регистрации)",
        )

    def test_malformed_bullet_is_rejected_with_its_source_line(self) -> None:
        document = inspect_markdown(self.fixture("malformed.md"))
        error = next(
            item
            for item in document["errors"]
            if item["code"] == "malformed-list-entry"
        )
        self.assertEqual(error["line_number"], 9)
        self.assertIn("Markdown link", error["message"])

    def test_out_of_order_entries_are_reported_on_the_later_line(self) -> None:
        document = inspect_markdown(self.fixture("unsorted.md"))
        error = next(
            item
            for item in document["errors"]
            if item["code"] == "out-of-order-entry"
        )
        self.assertEqual(error["line_number"], 9)

    def test_russian_yo_sorts_after_e_and_before_zh(self) -> None:
        self.assertLess(alphabetical_key("Еж"), alphabetical_key("Ёж"))
        self.assertLess(alphabetical_key("Ёж"), alphabetical_key("Жук"))

    def test_invalid_heading_hierarchy_has_a_line_diagnostic(self) -> None:
        document = inspect_markdown(self.fixture("bad-heading.md"))
        error = next(
            item
            for item in document["errors"]
            if item["code"] == "invalid-heading-level"
        )
        self.assertEqual(error["line_number"], 6)

    def test_failed_self_test_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t028.py", "--self-test"]), patch(
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


def fixture_results() -> list[dict[str, Any]]:
    expected_by_file = {
        "valid.md": "valid",
        "malformed.md": "malformed-list-entry",
        "unsorted.md": "out-of-order-entry",
        "bad-heading.md": "invalid-heading-level",
    }
    results = []
    for filename, expected_code in expected_by_file.items():
        document = inspect_markdown(
            (FIXTURE_DIR / filename).read_text(encoding="utf-8")
        )
        actual_codes = [error["code"] for error in document["errors"]]
        if filename == "valid.md":
            actual = "valid" if not actual_codes else actual_codes
        else:
            actual = expected_code if expected_code in actual_codes else actual_codes
        expected_line = next(
            (
                error["line_number"]
                for error in document["errors"]
                if error["code"] == expected_code
            ),
            None,
        )
        results.append(
            {
                "fixture": filename,
                "expected": expected_code,
                "actual": actual,
                "diagnostic_line": expected_line,
            }
        )
    return results


def write_evidence(
    document: dict[str, Any],
    errors: list[dict[str, Any]],
    self_test_status: str,
    self_test_output: str,
) -> None:
    write_json(
        EVIDENCE_DIR / "inputs.json",
        {
            "target_file": "more/free-programming-playgrounds-ru.md",
            "target_section": TARGET_SECTION,
            "expected_entry": EXPECTED_ENTRY,
            "actual_entries": document["entries"],
            "source_line_numbers_preserved": True,
            "external_requests": "not applicable; formatting-only check",
        },
    )
    write_json(
        EVIDENCE_DIR / "expected_vs_actual.json",
        {
            "source_validation": {
                "status": "passed" if not errors else "failed",
                "expected": {
                    "heading": "### Python",
                    "index_link": "* [Python](#python)",
                    "entry": EXPECTED_ENTRY,
                },
                "actual": {
                    "target_heading_line": document["target_heading_line"],
                    "entries": document["entries"],
                },
                "errors": errors,
            },
            "fixtures": fixture_results(),
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
        "# R10-T028 formatting and ordering report",
        "",
        "- Source: `more/free-programming-playgrounds-ru.md`",
        f"- Target section: `{TARGET_SECTION}`",
        "- Source validation: " + ("passed" if not errors else "failed"),
        f"- Offline self-test: {self_test_status}",
        "- External requests: not run (formatting-only check).",
        "- Catalogue corrections: none.",
        "",
        "## Selected entry",
        "",
    ]
    report_lines.extend(
        f"- Line {entry['line_number']}: `{entry['title']}` "
        f"({entry['url']})"
        for entry in document["entries"]
    )
    report_lines.extend(
        [
            "",
            "Fixtures verify malformed bullet diagnostics, preserved Cyrillic "
            "titles and Markdown links, heading levels, and alphabetical order.",
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
        source = SOURCE_FILE.read_text(encoding="utf-8")
    except OSError as error:
        print(f"r10-t028: cannot read source: {error}", file=sys.stderr)
        return 1
    document, errors = validate_source(source)
    write_evidence(document, errors, test_status, test_text)

    if errors:
        print(
            "r10-t028: source validation failed: "
            + json.dumps(errors, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    if not tests_passed:
        return 1
    if not args.self_test:
        print(
            json.dumps(
                {
                    "target_file": SOURCE_FILE.relative_to(ROOT).as_posix(),
                    "section": TARGET_SECTION,
                    "entries": document["entries"],
                    "status": "passed",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
