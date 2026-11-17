#!/usr/bin/env python3
"""Extract and verify the selected Portuguese screencast entries."""

import argparse
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-pt_BR.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T021"
TARGET_CATEGORIES = ("Algoritmos", "Databases")

SELECTED_ENTRIES = {
    "https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV": {
        "expected_display_name": "Curso em Vídeo - Curso de Lógica de Programação",
        "expected_category": "Algoritmos",
        "expected_line": 21,
        "expected_format": "screencast",
        "expected_author": "Gustavo Guanabara",
    },
    "https://www.youtube.com/playlist?list=PLJ4lbwalqv3Eaiay2pCeU_QU6vb-Hz989": {
        "expected_display_name": "Portugol Studio",
        "expected_category": "Algoritmos",
        "expected_line": 22,
        "expected_format": "screencast",
        "expected_author": None,
    },
    "https://www.youtube.com/playlist?list=PLucm8g_ezqNoNHU8tjVeHmRGBFnjDIlxD": {
        "expected_display_name": "Bóson Treinamentos - Curso de Modelagem de Dados",
        "expected_category": "Databases",
        "expected_line": 27,
        "expected_format": "screencast",
        "expected_author": None,
    },
}

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)\s*#*\s*$")
ENTRY_RE = re.compile(r"^\s*[*+-]\s+\[([^\]]+)\]\(([^)]+)\)(.*)$")


def parse_trailing_metadata(raw_tail):
    text = raw_tail.strip()
    if not text:
        return {"author": None, "format": None, "raw_metadata": None}

    resource_format = None
    author_text = text
    if text.endswith(")") and "(" in text:
        open_idx = text.rfind("(")
        resource_format = text[open_idx + 1 : -1].strip()
        author_text = text[:open_idx].strip()

    author = None
    if author_text:
        for prefix in ("- ", "– ", "— "):
            if author_text.startswith(prefix):
                author = author_text[len(prefix) :].strip() or None
                break
        else:
            author = author_text

    return {
        "author": author,
        "format": resource_format,
        "raw_metadata": text,
    }


def parse_entries(markdown_text, source_path="<memory>"):
    entries = []
    fence_character = None
    fence_length = 0
    category_stack = []
    in_index_section = False

    for line_number, raw_line in enumerate(markdown_text.splitlines(), start=1):
        stripped = raw_line.strip()
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

        heading_match = HEADING_RE.match(stripped)
        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            if level == 3 and title.lower() == "index":
                in_index_section = True
                category_stack = []
                continue
            if level <= 3:
                in_index_section = False
            while category_stack and category_stack[-1][0] >= level:
                category_stack.pop()
            category_stack.append((level, title))
            continue

        if in_index_section:
            continue

        category = " > ".join(title for _, title in category_stack)
        if not any(category == allowed for allowed in TARGET_CATEGORIES):
            continue

        entry_match = ENTRY_RE.match(raw_line)
        if not entry_match:
            continue
        display_name, url, raw_tail = entry_match.groups()
        entries.append(
            {
                "line_number": line_number,
                "source_file": source_path,
                "category": category,
                "display_name": display_name.strip(),
                "url": url.strip(),
                "metadata": parse_trailing_metadata(raw_tail),
            }
        )
    return entries


def verify_entries(entries, source_file):
    by_url = {}
    for entry in entries:
        by_url.setdefault(entry["url"], []).append(entry)

    selected = []
    errors = []
    for url, expected in SELECTED_ENTRIES.items():
        found_entries = by_url.get(url, [])
        if not found_entries:
            errors.append(f"Missing expected entry URL: {url}")
            continue
        if len(found_entries) > 1:
            errors.append(f"Duplicate expected entry URL: {url}")
        found = found_entries[0]
        selected.append(found)
        if found["line_number"] != expected["expected_line"]:
            errors.append(
                f"Line mismatch for {url}: expected {expected['expected_line']}, "
                f"got {found['line_number']}"
            )
        if found["display_name"] != expected["expected_display_name"]:
            errors.append(f"Name mismatch for {url}")
        if found["category"] != expected["expected_category"]:
            errors.append(f"Category mismatch for {url}")
        if found["metadata"]["format"] != expected["expected_format"]:
            errors.append(f"Format mismatch for {url}")
        if found["metadata"]["author"] != expected["expected_author"]:
            errors.append(f"Author mismatch for {url}")

    return {
        "target_file": source_file,
        "total_parsed_entries": len(entries),
        "selected_entries": selected,
        "errors": errors,
        "passed": not errors,
    }


def verify_selected_entries(target_file):
    content = target_file.read_text(encoding="utf-8")
    try:
        source_file = str(target_file.relative_to(REPO_ROOT))
    except ValueError:
        source_file = str(target_file)
    entries = parse_entries(content, source_path=source_file)
    return verify_entries(entries, source_file)


def read_fixture(path):
    return path.read_text(encoding="utf-8")


def run_self_test(target_file, work_dir):
    success_input = work_dir / "fixture_success.md"
    failure_input = work_dir / "fixture_failure.md"
    success_text = read_fixture(success_input)
    failure_text = read_fixture(failure_input)

    success_actual = parse_entries(success_text, source_path=success_input.name)
    success_expected = [
        {
            "line_number": 15,
            "source_file": success_input.name,
            "category": "Algoritmos",
            "display_name": "Real Fragment Guide",
            "url": "https://example.org/docs/intro#section-2",
            "metadata": {
                "author": "Jane Doe",
                "format": "screencast",
                "raw_metadata": "- Jane Doe (screencast)",
            },
        }
    ]
    assert success_actual == success_expected, (
        f"Successful fixture mismatch: expected {success_expected}, got {success_actual}"
    )

    ignored_urls = [
        "https://example.com/fake-in-fence",
        "https://example.com/tilde-fence#sec",
        "https://example.com/outside-target-section",
    ]
    assert all(
        all(entry["url"] != url for entry in success_actual) for url in ignored_urls
    ), f"A fake or out-of-scope URL was parsed: {ignored_urls}"

    failure_actual = verify_entries(
        parse_entries(failure_text, source_path=failure_input.name),
        failure_input.name,
    )
    failure_expected = {
        "passed": False,
        "selected_count": 1,
        "error_count": 6,
        "error_fragments": [
            "Line mismatch for https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV",
            "Name mismatch for https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV",
            "Category mismatch for https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV",
            "Author mismatch for https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV",
            "Missing expected entry URL: https://www.youtube.com/playlist?list=PLJ4lbwalqv3Eaiay2pCeU_QU6vb-Hz989",
            "Missing expected entry URL: https://www.youtube.com/playlist?list=PLucm8g_ezqNoNHU8tjVeHmRGBFnjDIlxD",
        ],
    }
    failure_actual_summary = {
        "passed": failure_actual["passed"],
        "selected_count": len(failure_actual["selected_entries"]),
        "error_count": len(failure_actual["errors"]),
        "error_fragments": [
            fragment
            for fragment in failure_expected["error_fragments"]
            if any(
                error.startswith(fragment)
                for error in failure_actual["errors"]
            )
        ],
    }
    assert failure_actual_summary == failure_expected, (
        f"Failing fixture mismatch: expected {failure_expected}, "
        f"got {failure_actual_summary}"
    )

    failure_cli = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--file",
            str(failure_input),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure_cli.returncode != 0, (
        "The checker CLI returned success for a fixture with invalid entries"
    )

    real_report = verify_selected_entries(target_file)
    expected_real_entries = [
        {
            "line_number": 21,
            "source_file": "casts/free-podcasts-screencasts-pt_BR.md",
            "category": "Algoritmos",
            "display_name": "Curso em Vídeo - Curso de Lógica de Programação",
            "url": "https://www.youtube.com/playlist?list=PLHz_AreHm4dmSj0MHol_aoNYCSGFqvfXV",
            "metadata": {
                "author": "Gustavo Guanabara",
                "format": "screencast",
                "raw_metadata": "- Gustavo Guanabara (screencast)",
            },
        },
        {
            "line_number": 22,
            "source_file": "casts/free-podcasts-screencasts-pt_BR.md",
            "category": "Algoritmos",
            "display_name": "Portugol Studio",
            "url": "https://www.youtube.com/playlist?list=PLJ4lbwalqv3Eaiay2pCeU_QU6vb-Hz989",
            "metadata": {
                "author": None,
                "format": "screencast",
                "raw_metadata": "(screencast)",
            },
        },
        {
            "line_number": 27,
            "source_file": "casts/free-podcasts-screencasts-pt_BR.md",
            "category": "Databases",
            "display_name": "Bóson Treinamentos - Curso de Modelagem de Dados",
            "url": "https://www.youtube.com/playlist?list=PLucm8g_ezqNoNHU8tjVeHmRGBFnjDIlxD",
            "metadata": {
                "author": None,
                "format": "screencast",
                "raw_metadata": "(screencast)",
            },
        },
    ]
    assert real_report["passed"], (
        f"Real file verification failed: {real_report['errors']}"
    )
    assert real_report["selected_entries"] == expected_real_entries, (
        "Real file entries did not match the expected names, URLs, categories, "
        "metadata, and source lines"
    )

    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "task_id": "R10-T021",
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "fixtures": {
            "success": {
                "input": success_input.name,
                "expected": success_expected,
                "actual": success_actual,
                "ignored_urls": ignored_urls,
            },
            "failure": {
                "input": failure_input.name,
                "expected": failure_expected,
                "actual": failure_actual,
                "cli_expected_exit_code": "non-zero",
                "cli_actual_exit_code": failure_cli.returncode,
                "cli_stdout": failure_cli.stdout,
                "cli_stderr": failure_cli.stderr,
            },
        },
        "source_verification": {
            "input": real_report["target_file"],
            "expected_selected_entries": expected_real_entries,
            "actual": real_report,
        },
        "self_test_passed": True,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "results.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("SELF-TEST PASSED: all success and failure assertions succeeded.")
    print(json.dumps(real_report, indent=2, ensure_ascii=False))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Extract and verify the selected entries in the Algoritmos and "
            "Databases sections of casts/free-podcasts-screencasts-pt_BR.md."
        )
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_TARGET_FILE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            return run_self_test(args.file, args.work_dir)
        report = verify_selected_entries(args.file)
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
