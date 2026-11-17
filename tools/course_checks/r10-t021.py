#!/usr/bin/env python3
"""Extract and validate the selected entries in the Brazilian Portuguese casts list."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-pt_BR.md"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "r10-t021"
SELECTED_URLS = {
    "https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV",
    "https://www.youtube.com/playlist?list=PLJ4lbwalqv3Eaiay2pCeU_QU6vb-Hz989",
    "https://www.youtube.com/playlist?list=PLucm8g_ezqNoNHU8tjVeHmRGBFnjDIlxD",
}

HEADING_RE = re.compile(r"^ {0,3}#{3,4}\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)
TYPE_RE = re.compile(r"\((podcast|screencast)\)", re.IGNORECASE)


def parse_entries(markdown: str) -> list[dict[str, object]]:
    """Parse markdown resource bullets and retain their original 1-based line numbers."""
    entries: list[dict[str, object]] = []
    category: str | None = None
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
            category = heading_match.group(1).strip()
            continue

        entry_match = ENTRY_RE.match(line)
        if not entry_match:
            continue

        metadata = entry_match.group("metadata").strip()
        kind_match = TYPE_RE.search(metadata)
        creator = TYPE_RE.sub("", metadata).strip()
        if creator.startswith("-"):
            creator = creator[1:].strip()

        entries.append(
            {
                "line": line_number,
                "name": entry_match.group("name"),
                "url": entry_match.group("url"),
                "category": category,
                "metadata": metadata,
                "creator": creator or None,
                "kind": kind_match.group(1).lower() if kind_match else None,
            }
        )

    return entries


def select_required_entries(entries: list[dict[str, object]]) -> list[dict[str, object]]:
    selected = [entry for entry in entries if entry["url"] in SELECTED_URLS]
    counts = {url: 0 for url in SELECTED_URLS}
    for entry in selected:
        counts[str(entry["url"])] += 1

    missing = sorted(url for url, count in counts.items() if count == 0)
    duplicates = sorted(url for url, count in counts.items() if count > 1)
    if missing or duplicates:
        problems = []
        if missing:
            problems.append(f"missing selected URL(s): {', '.join(missing)}")
        if duplicates:
            problems.append(f"duplicate selected URL(s): {', '.join(duplicates)}")
        raise ValueError("; ".join(problems))

    return selected


class CourseCheckTests(unittest.TestCase):
    def test_success_fixture_ignores_fenced_fake_and_keeps_source_lines(self) -> None:
        fixture_path = FIXTURE_DIR / "success.md"
        entries = parse_entries(fixture_path.read_text(encoding="utf-8"))
        selected = select_required_entries(entries)
        self.assertEqual(
            [(entry["line"], entry["name"], entry["category"]) for entry in selected],
            [
                (6, "Curso em Vídeo - Curso de Lógica de Programação", "Algoritmos"),
                (7, "Portugol Studio", "Algoritmos"),
                (12, "Bóson Treinamentos - Curso de Modelagem de Dados", "Databases"),
            ],
        )
        self.assertEqual(len(entries), 4)
        self.assertNotIn("Fake fenced entry", [entry["name"] for entry in entries])
        self.assertEqual(selected[0]["creator"], "Gustavo Guanabara")
        self.assertEqual(selected[0]["kind"], "screencast")
        self.assertEqual(selected[1]["metadata"], "(screencast)")
        self.assertEqual(selected[2]["metadata"], "(screencast)")

    def test_fragment_url_is_preserved(self) -> None:
        fixture_path = FIXTURE_DIR / "success.md"
        entries = parse_entries(fixture_path.read_text(encoding="utf-8"))
        fragment_entry = next(entry for entry in entries if entry["name"] == "Fragment fixture")
        self.assertEqual(fragment_entry["url"], "https://example.test/course#lesson-2")

    def test_failure_fixture_reports_missing_selected_entry(self) -> None:
        fixture_path = FIXTURE_DIR / "failure.md"
        entries = parse_entries(fixture_path.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ValueError, "missing selected URL"):
            select_required_entries(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run offline parser fixtures and assertions",
    )
    args = parser.parse_args()

    if args.self_test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(CourseCheckTests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

    try:
        entries = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
    except (OSError, ValueError) as error:
        print(f"r10-t021: {error}", file=sys.stderr)
        return 1

    print(json.dumps(entries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
