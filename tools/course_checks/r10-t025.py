#!/usr/bin/env python3
"""Verify stored metadata for selected Marathi YouTube course playlists."""

import argparse
import html
import json
import platform
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "courses" / "free-courses-mr.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T025"

OFFICIAL_OBSERVATIONS = {
    "https://youtube.com/playlist?list=PLy1NOWTMDFjDLCgmxRNLDJtlutJOYl2d7": {
        "official_title": "अँड्रॉइड ऍप डेव्हलपमेंट मराठी | Android App Development in Marathi",
        "owner_channel": "उत्तर",
        "final_url": "https://www.youtube.com/playlist?list=PLy1NOWTMDFjDLCgmxRNLDJtlutJOYl2d7",
        "category": "Android",
        "subject_evidence": "The official playlist title identifies Android app development.",
        "observed_on": "2026-11-17",
    },
    "https://youtube.com/playlist?list=PLpDAynbYcV3sruD9MNfmZtimPCKHicA2V": {
        "official_title": "Angular in Marathi",
        "owner_channel": "Finishing School",
        "final_url": "https://www.youtube.com/playlist?list=PLpDAynbYcV3sruD9MNfmZtimPCKHicA2V",
        "category": "Angular",
        "subject_evidence": "The official playlist title identifies Angular instruction.",
        "observed_on": "2026-11-17",
    },
    "https://youtube.com/playlist?list=PLMs908ICeVMEBw4CevNdPvvIJDaQV1ISN": {
        "official_title": "Angular Tutorials in Marathi",
        "owner_channel": "Developers Marathi",
        "final_url": "https://www.youtube.com/playlist?list=PLMs908ICeVMEBw4CevNdPvvIJDaQV1ISN",
        "category": "Angular",
        "subject_evidence": "The official playlist title identifies Angular tutorials.",
        "observed_on": "2026-11-17",
    },
}

SELECTED_ENTRIES = {
    "https://youtube.com/playlist?list=PLy1NOWTMDFjDLCgmxRNLDJtlutJOYl2d7": {
        "display_name": OFFICIAL_OBSERVATIONS[
            "https://youtube.com/playlist?list=PLy1NOWTMDFjDLCgmxRNLDJtlutJOYl2d7"
        ]["official_title"],
        "creator": "उत्तर",
        "category": "Android",
        "line_number": 19,
    },
    "https://youtube.com/playlist?list=PLpDAynbYcV3sruD9MNfmZtimPCKHicA2V": {
        "display_name": "Angular in Marathi",
        "creator": "Finishing School",
        "category": "Angular",
        "line_number": 24,
    },
    "https://youtube.com/playlist?list=PLMs908ICeVMEBw4CevNdPvvIJDaQV1ISN": {
        "display_name": "Angular Tutorials in Marathi",
        "creator": "Developers Marathi",
        "category": "Angular",
        "line_number": 25,
    },
}

HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)\s*$")
ENTRY_RE = re.compile(r"^\s*[*+-]\s+\[([^\]]+)\]\(([^)]+)\)(.*)$")
ESCAPED_MARKDOWN_RE = re.compile(r"\\([\\`*_{}\[\]()#+.!|~-])")


def parse_entries(markdown_text, source_file="<memory>"):
    entries = []
    category_stack = []
    in_index = False

    for line_number, raw_line in enumerate(markdown_text.splitlines(), start=1):
        heading_match = HEADING_RE.match(raw_line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            title = ESCAPED_MARKDOWN_RE.sub(r"\1", heading_match.group(2)).strip()
            if level == 3 and title.casefold() == "index":
                in_index = True
                category_stack = []
                continue
            if level <= 3:
                in_index = False
            while category_stack and category_stack[-1][0] >= level:
                category_stack.pop()
            category_stack.append((level, title))
            continue

        if in_index or not category_stack:
            continue
        entry_match = ENTRY_RE.match(raw_line)
        if not entry_match:
            continue

        raw_name, url, trailing = entry_match.groups()
        display_name = ESCAPED_MARKDOWN_RE.sub(r"\1", raw_name).strip()
        metadata = trailing.strip()
        creator = None
        if metadata.startswith("- "):
            creator = metadata[2:].strip() or None
        entries.append(
            {
                "line_number": line_number,
                "source_file": source_file,
                "category": " > ".join(title for _, title in category_stack),
                "display_name": html.unescape(display_name),
                "url": url.strip(),
                "creator": creator,
                "metadata": metadata or None,
            }
        )
    return entries


def _playlist_id(url):
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return None
    return parse_qs(parts.query, keep_blank_values=True).get("list", [None])[0]


def _evidence_fields(entry, url, expected):
    official = OFFICIAL_OBSERVATIONS[url]
    fields = [
        {
            "field": "display_name",
            "catalogue_value": entry["display_name"],
            "observed_value": official["official_title"],
            "proposed_value": official["official_title"],
            "evidence_url": official["final_url"],
        },
        {
            "field": "creator",
            "catalogue_value": entry["creator"],
            "observed_value": official["owner_channel"],
            "proposed_value": official["owner_channel"],
            "evidence_url": official["final_url"],
        },
        {
            "field": "category",
            "catalogue_value": entry["category"],
            "observed_value": official["subject_evidence"],
            "proposed_value": official["category"],
            "evidence_url": official["final_url"],
        },
        {
            "field": "url",
            "catalogue_value": entry["url"],
            "observed_value": official["final_url"],
            "proposed_value": entry["url"],
            "evidence_url": official["final_url"],
            "note": (
                "The final URL has the same playlist ID; retain the shorter "
                "youtube.com URL already in the catalogue."
            ),
        },
    ]
    for field in fields:
        if field["field"] == "url":
            field["change_needed"] = (
                _playlist_id(field["catalogue_value"])
                != _playlist_id(field["observed_value"])
            )
        else:
            field["change_needed"] = (
                field["catalogue_value"] != field["proposed_value"]
            )
    return fields


def analyze_markdown(markdown_text, source_file="<memory>", check_lines=False):
    entries = parse_entries(markdown_text, source_file)
    by_url = {}
    for entry in entries:
        by_url.setdefault(entry["url"], []).append(entry)

    selected_entries = []
    evidence_table = []
    proposed_changes = []
    errors = []
    for url, expected in SELECTED_ENTRIES.items():
        matches = by_url.get(url, [])
        if not matches:
            errors.append(f"Missing selected playlist URL: {url}")
            continue
        if len(matches) > 1:
            errors.append(f"Selected playlist URL appears multiple times: {url}")
        found = matches[0]
        official = OFFICIAL_OBSERVATIONS[url]
        selected = {
            **found,
            "expected_category": expected["category"],
            "official_title": official["official_title"],
            "official_owner_channel": official["owner_channel"],
            "official_final_url": official["final_url"],
            "subject_evidence": official["subject_evidence"],
            "observed_on": official["observed_on"],
        }
        selected_entries.append(selected)

        if found["display_name"] != expected["display_name"]:
            errors.append(f"Display-name mismatch for {url}")
        if not found["creator"]:
            errors.append(f"Missing required creator for {url}")
        elif found["creator"] != expected["creator"]:
            errors.append(f"Creator mismatch for {url}")
        if found["category"] != expected["category"]:
            errors.append(f"Category mismatch for {url}")
        if check_lines and found["line_number"] != expected["line_number"]:
            errors.append(
                f"Line mismatch for {url}: expected {expected['line_number']}, "
                f"got {found['line_number']}"
            )

        fields = _evidence_fields(found, url, expected)
        evidence_table.append(
            {
                "source_line": found["line_number"],
                "catalogue_url": url,
                "official_source_url": official["final_url"],
                "observed_on": official["observed_on"],
                "fields": fields,
            }
        )
        for field in fields:
            if field["change_needed"]:
                proposed_changes.append(
                    {
                        "source_line": found["line_number"],
                        "url": url,
                        **field,
                    }
                )

    return {
        "source_file": source_file,
        "entry_count": len(entries),
        "selected_entries": selected_entries,
        "evidence_table": evidence_table,
        "proposed_changes": proposed_changes,
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
        "selected_entries": [
            {
                "line_number": entry["line_number"],
                "display_name": entry["display_name"],
                "category": entry["category"],
                "creator": entry["creator"],
            }
            for entry in report["selected_entries"]
        ],
        "proposed_changes": report["proposed_changes"],
        "errors": report["errors"],
    }


def run_self_test(target_file, work_dir):
    success_path = work_dir / "fixture_success.md"
    failure_path = work_dir / "fixture_missing_creator.md"
    success_report = analyze_markdown(
        success_path.read_text(encoding="utf-8"), success_path.name
    )
    success_actual = _summary(success_report)
    expected_success = {
        "passed": True,
        "selected_entries": [
            {
                "line_number": line_number,
                "display_name": SELECTED_ENTRIES[url]["display_name"],
                "category": SELECTED_ENTRIES[url]["category"],
                "creator": SELECTED_ENTRIES[url]["creator"],
            }
            for url, line_number in zip(SELECTED_ENTRIES, (7, 10, 11))
        ],
        "proposed_changes": [],
        "errors": [],
    }
    assert success_actual == expected_success, (
        f"Successful metadata fixture mismatch: expected {expected_success}, "
        f"got {success_actual}"
    )

    failure_report = analyze_markdown(
        failure_path.read_text(encoding="utf-8"), failure_path.name
    )
    missing_creator_url = next(
        url
        for url in SELECTED_ENTRIES
        if not any(
            entry["url"] == url and entry["creator"]
            for entry in parse_entries(
                failure_path.read_text(encoding="utf-8"), failure_path.name
            )
        )
    )
    assert not failure_report["passed"], "Missing required creator was not rejected"
    assert f"Missing required creator for {missing_creator_url}" in failure_report["errors"]

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
        "The checker CLI returned success for a fixture with a missing creator"
    )

    source_report = analyze_file(target_file)
    assert source_report["passed"], f"Source metadata check failed: {source_report['errors']}"
    assert not source_report["proposed_changes"], (
        f"Evidence-backed changes require review: {source_report['proposed_changes']}"
    )
    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "task_id": "R10-T025",
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "success_fixture": {
            "input": success_path.name,
            "expected": expected_success,
            "actual": success_actual,
            "full_report": success_report,
        },
        "missing_required_field_fixture": {
            "input": failure_path.name,
            "expected": {
                "passed": False,
                "missing_field": "creator",
                "nonzero_cli_exit": True,
            },
            "actual": {
                "report": failure_report,
                "cli_exit_code": failure_cli.returncode,
                "stdout": failure_cli.stdout,
                "stderr": failure_cli.stderr,
            },
        },
        "official_observations": OFFICIAL_OBSERVATIONS,
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
    print("SELF-TEST PASSED: success and missing-required-field fixtures checked.")
    print(json.dumps(source_report, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Verify stored title, URL, creator, and category metadata for the "
            "selected Marathi course playlists."
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
