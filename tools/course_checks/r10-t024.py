#!/usr/bin/env python3
"""Check category placement and repeated headings in the French podcast list."""

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-fr.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T024"

SELECTED_ENTRIES = {
    "https://aws.amazon.com/fr/blogs/france/podcasts": {
        "display_name": "Le podcast AWS en français",
        "expected_category": "Cloud computing",
        "expected_line": 9,
        "subject_basis": (
            "The official AWS podcast page presents AWS episodes, including "
            "topics such as AWS Lambda, Fargate, cloud migration, and public cloud."
        ),
        "evidence_url": "https://aws.amazon.com/fr/blogs/france/podcasts",
    },
    "https://lescastcodeurs.com": {
        "display_name": "Les Cast Codeurs Podcast",
        "expected_category": "Langage Agnostique",
        "expected_line": 20,
        "subject_basis": (
            "The show's current homepage covers Java/JDK alongside Rust, "
            "TypeScript, PHP, data, infrastructure, and other software topics; "
            "it is broader than a Java-only podcast."
        ),
        "evidence_url": "https://lescastcodeurs.com",
    },
    "https://artisandeveloppeur.fr/podcast": {
        "display_name": "Artisan Developpeur",
        "expected_category": "Langage Agnostique",
        "expected_line": 14,
        "subject_basis": (
            "The podcast page describes reflection on software development "
            "work and community news, not a single programming language."
        ),
        "evidence_url": "https://artisandeveloppeur.fr/podcast",
    },
}

SUBJECT_EVIDENCE_DATE = "2026-11-17"
APPLIED_CATEGORY_CORRECTION = {
    "url": "https://lescastcodeurs.com",
    "display_name": "Les Cast Codeurs Podcast",
    "from_category": "Java",
    "to_category": "Langage Agnostique",
    "original_line": 15,
    "current_line": 20,
    "evidence_url": "https://lescastcodeurs.com",
    "subject_basis": SELECTED_ENTRIES["https://lescastcodeurs.com"]["subject_basis"],
    "observed_date": SUBJECT_EVIDENCE_DATE,
}

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)\s*$")
ENTRY_RE = re.compile(r"^\s*[*+-]\s+\[([^\]]+)\]\(([^)]+)\)(.*)$")
ANCHOR_RE = re.compile(r"</?a\b[^>]*>", re.I)
ESCAPED_MARKDOWN_RE = re.compile(r"\\([\\`*_{}\[\]()#+.!-])")


def _normalize_heading(raw_title):
    title = ANCHOR_RE.sub("", raw_title)
    title = ESCAPED_MARKDOWN_RE.sub(r"\1", title)
    return " ".join(title.split()).casefold()


def _display_heading(raw_title):
    title = ANCHOR_RE.sub("", raw_title)
    title = ESCAPED_MARKDOWN_RE.sub(r"\1", title)
    return " ".join(title.split())


def parse_document(markdown_text, source_file="<memory>"):
    entries = []
    headings = []
    fence_character = None
    fence_length = 0
    heading_stack = []
    in_index = False

    for line_number, raw_line in enumerate(markdown_text.splitlines(), start=1):
        fence_match = FENCE_RE.match(raw_line)
        if fence_match:
            marker = fence_match.group(1)
            info = fence_match.group(2)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif (
                marker[0] == fence_character
                and len(marker) >= fence_length
                and not info.strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if fence_character is not None:
            continue

        heading_match = HEADING_RE.match(raw_line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            title = _display_heading(heading_match.group(2))
            normalized_title = _normalize_heading(heading_match.group(2))
            if level == 3 and normalized_title == "index":
                in_index = True
                heading_stack = []
                continue
            if level <= 3:
                in_index = False
                heading_stack = [] if level == 2 else [(level, title)]
            elif not in_index:
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, title))

            if not in_index:
                headings.append(
                    {
                        "level": level,
                        "title": title,
                        "normalized_title": normalized_title,
                        "parent": " > ".join(
                            parent for _, parent in heading_stack[:-1]
                        )
                        or None,
                        "line_number": line_number,
                    }
                )
            continue

        if in_index or not heading_stack:
            continue
        entry_match = ENTRY_RE.match(raw_line)
        if not entry_match:
            continue
        display_name, url, trailing_metadata = entry_match.groups()
        entries.append(
            {
                "line_number": line_number,
                "source_file": source_file,
                "category": " > ".join(title for _, title in heading_stack),
                "display_name": display_name.strip(),
                "url": url.strip(),
                "metadata": trailing_metadata.strip() or None,
            }
        )

    repeated_by_key = {}
    for heading in headings:
        key = (
            heading["level"],
            (heading["parent"] or "").casefold(),
            heading["normalized_title"],
        )
        repeated_by_key.setdefault(key, []).append(heading)
    repeated_headings = [
        {
            "level": group[0]["level"],
            "title": group[0]["title"],
            "parent": group[0]["parent"],
            "line_numbers": [heading["line_number"] for heading in group],
        }
        for group in repeated_by_key.values()
        if len(group) > 1
    ]
    return entries, headings, repeated_headings


def analyze_markdown(markdown_text, source_file="<memory>", check_lines=False):
    entries, headings, repeated_headings = parse_document(markdown_text, source_file)
    by_url = {}
    for entry in entries:
        by_url.setdefault(entry["url"], []).append(entry)

    selected_entries = []
    misplaced_entries = []
    errors = []
    for url, expected in SELECTED_ENTRIES.items():
        matches = by_url.get(url, [])
        if not matches:
            errors.append(f"Missing selected entry URL: {url}")
            continue
        if len(matches) > 1:
            errors.append(f"Selected entry URL appears multiple times: {url}")
        found = matches[0]
        selected = {
            **found,
            "expected_category": expected["expected_category"],
            "subject_basis": expected["subject_basis"],
            "evidence_url": expected["evidence_url"],
        }
        selected_entries.append(selected)

        if found["display_name"] != expected["display_name"]:
            errors.append(f"Display-name mismatch for {url}")
        if check_lines and found["line_number"] != expected["expected_line"]:
            errors.append(
                f"Line mismatch for {url}: expected {expected['expected_line']}, "
                f"got {found['line_number']}"
            )
        if found["category"] != expected["expected_category"]:
            misplaced = {
                "url": url,
                "display_name": found["display_name"],
                "line_number": found["line_number"],
                "current_category": found["category"],
                "expected_category": expected["expected_category"],
                "subject_basis": expected["subject_basis"],
                "evidence_url": expected["evidence_url"],
                "manual_review_required": True,
            }
            misplaced_entries.append(misplaced)
            errors.append(
                f"Category mismatch for {url}: expected "
                f"{expected['expected_category']!r}, got {found['category']!r}"
            )

    for heading_group in repeated_headings:
        errors.append(
            f"Repeated heading {heading_group['title']!r} at lines "
            f"{', '.join(map(str, heading_group['line_numbers']))}"
        )

    proposed_moves = [
        {
            "url": item["url"],
            "display_name": item["display_name"],
            "source_line": item["line_number"],
            "from_category": item["current_category"],
            "to_category": item["expected_category"],
            "subject_basis": item["subject_basis"],
            "evidence_url": item["evidence_url"],
            "manual_review_required": True,
        }
        for item in misplaced_entries
    ]
    return {
        "source_file": source_file,
        "entry_count": len(entries),
        "headings": headings,
        "selected_entries": selected_entries,
        "misplaced_entries": misplaced_entries,
        "repeated_headings": repeated_headings,
        "proposed_moves": proposed_moves,
        "errors": errors,
        "passed": not errors,
    }


def analyze_file(target_file):
    markdown_text = target_file.read_text(encoding="utf-8")
    try:
        source_file = str(target_file.relative_to(REPO_ROOT))
    except ValueError:
        source_file = str(target_file)
    check_lines = target_file.resolve() == DEFAULT_TARGET_FILE.resolve()
    return analyze_markdown(markdown_text, source_file, check_lines=check_lines)


def _summary(report):
    return {
        "passed": report["passed"],
        "selected_categories": [
            {
                "display_name": entry["display_name"],
                "category": entry["category"],
                "expected_category": entry["expected_category"],
            }
            for entry in report["selected_entries"]
        ],
        "misplaced_entries": report["misplaced_entries"],
        "repeated_headings": report["repeated_headings"],
        "proposed_moves": report["proposed_moves"],
    }


def run_self_test(target_file, work_dir):
    success_path = work_dir / "fixture_success.md"
    failure_path = work_dir / "fixture_failure.md"
    success_text = success_path.read_text(encoding="utf-8")
    failure_text = failure_path.read_text(encoding="utf-8")

    success_report = analyze_markdown(success_text, success_path.name)
    expected_success = {
        "passed": True,
        "selected_categories": [
            {
                "display_name": "Le podcast AWS en français",
                "category": "Cloud computing",
                "expected_category": "Cloud computing",
            },
            {
                "display_name": "Les Cast Codeurs Podcast",
                "category": "Langage Agnostique",
                "expected_category": "Langage Agnostique",
            },
            {
                "display_name": "Artisan Developpeur",
                "category": "Langage Agnostique",
                "expected_category": "Langage Agnostique",
            },
        ],
        "misplaced_entries": [],
        "repeated_headings": [],
        "proposed_moves": [],
    }
    actual_success = _summary(success_report)
    assert actual_success == expected_success, (
        f"Valid-category fixture mismatch: expected {expected_success}, "
        f"got {actual_success}"
    )

    failure_report = analyze_markdown(failure_text, failure_path.name)
    cast_url = "https://lescastcodeurs.com"
    expected_failure = {
        "passed": False,
        "selected_categories": [
            {
                "display_name": "Le podcast AWS en français",
                "category": "Cloud computing",
                "expected_category": "Cloud computing",
            },
            {
                "display_name": "Les Cast Codeurs Podcast",
                "category": "Java",
                "expected_category": "Langage Agnostique",
            },
            {
                "display_name": "Artisan Developpeur",
                "category": "Langage Agnostique",
                "expected_category": "Langage Agnostique",
            },
        ],
        "misplaced_entries": [
            {
                "url": cast_url,
                "display_name": "Les Cast Codeurs Podcast",
                "line_number": 5,
                "current_category": "Java",
                "expected_category": "Langage Agnostique",
                "subject_basis": SELECTED_ENTRIES[cast_url]["subject_basis"],
                "evidence_url": SELECTED_ENTRIES[cast_url]["evidence_url"],
                "manual_review_required": True,
            }
        ],
        "repeated_headings": [
            {
                "level": 3,
                "title": "Java",
                "parent": None,
                "line_numbers": [4, 7],
            }
        ],
        "proposed_moves": [
            {
                "url": cast_url,
                "display_name": "Les Cast Codeurs Podcast",
                "source_line": 5,
                "from_category": "Java",
                "to_category": "Langage Agnostique",
                "subject_basis": SELECTED_ENTRIES[cast_url]["subject_basis"],
                "evidence_url": SELECTED_ENTRIES[cast_url]["evidence_url"],
                "manual_review_required": True,
            }
        ],
    }
    actual_failure = _summary(failure_report)
    assert actual_failure == expected_failure, (
        f"Misplaced/repeated-heading fixture mismatch: expected {expected_failure}, "
        f"got {actual_failure}"
    )

    failure_cli = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--file",
            str(failure_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure_cli.returncode != 0, (
        "The checker CLI returned success for a misplaced and repeated heading fixture"
    )

    source_report = analyze_file(target_file)
    assert source_report["passed"], f"Source category check failed: {source_report['errors']}"
    assert not source_report["misplaced_entries"]
    assert not source_report["repeated_headings"]
    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()

    evidence = {
        "task_id": "R10-T024",
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "success_fixture": {
            "input": success_path.name,
            "expected": expected_success,
            "actual": actual_success,
            "full_report": success_report,
        },
        "failure_fixture": {
            "input": failure_path.name,
            "expected": expected_failure,
            "actual": actual_failure,
            "full_report": failure_report,
            "cli_expected_exit_code": "non-zero",
            "cli_actual_exit_code": failure_cli.returncode,
            "cli_stdout": failure_cli.stdout,
            "cli_stderr": failure_cli.stderr,
        },
        "subject_evidence": {
            "observed_date": SUBJECT_EVIDENCE_DATE,
            "selected_subjects": SELECTED_ENTRIES,
        },
        "applied_category_correction": APPLIED_CATEGORY_CORRECTION,
        "source_verification": {
            "input": source_report["source_file"],
            "actual": source_report,
        },
        "self_test_passed": True,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "results.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("SELF-TEST PASSED: valid categories and misplaced/repeated headings checked.")
    print(json.dumps(source_report, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Check selected category placement and repeated headings in "
            "casts/free-podcasts-screencasts-fr.md."
        )
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_TARGET_FILE)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            return run_self_test(args.file, args.work_dir)
        report = analyze_file(args.file)
    except (
        OSError,
        UnicodeError,
        AssertionError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
