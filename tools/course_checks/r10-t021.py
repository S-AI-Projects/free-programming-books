#!/usr/bin/env python3
import argparse
import json
import platform
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "casts" / "free-podcasts-screencasts-pt_BR.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T021"

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


def parse_trailing_metadata(raw_tail):
    if not raw_tail or not raw_tail.strip():
        return {"author": None, "format": None, "raw_metadata": None}
    text = raw_tail.strip()
    fmt = None
    text_wo_fmt = text
    if text.endswith(")") and "(" in text:
        open_idx = text.rfind("(")
        fmt = text[open_idx + 1 : -1].strip()
        text_wo_fmt = text[:open_idx].strip()
    author = None
    for prefix in ("- ", "– ", "— "):
        if text_wo_fmt.startswith(prefix):
            author = text_wo_fmt[len(prefix) :].strip() or None
            break
    else:
        if text_wo_fmt:
            author = text_wo_fmt
    return {"author": author, "format": fmt, "raw_metadata": raw_tail.strip()}


def parse_entries(markdown_text, source_path="<memory>"):
    entries = []
    in_fence = False
    fence_marker = ""
    category_stack = []
    in_index_section = False

    for line_no, raw_line in enumerate(markdown_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif marker == fence_marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue

        if stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if 2 <= hashes <= 6 and len(stripped) > hashes and stripped[hashes] == " ":
                title = stripped[hashes + 1 :].strip()
                if hashes == 3 and title.lower() == "index":
                    in_index_section = True
                    category_stack = []
                    continue
                if hashes <= 3:
                    in_index_section = False
                while category_stack and category_stack[-1][0] >= hashes:
                    category_stack.pop()
                category_stack.append((hashes, title))
                continue

        if in_index_section:
            continue

        if stripped.startswith(("* [", "- [", "+ [")) and "](" in stripped:
            mid = stripped.index("](")
            end_paren = stripped.find(")", mid + 2)
            if end_paren != -1:
                display_name = stripped[3:mid].strip()
                url = stripped[mid + 2 : end_paren].strip()
                raw_tail = stripped[end_paren + 1 :]
                metadata = parse_trailing_metadata(raw_tail)
                category = " > ".join(t for _, t in category_stack) if category_stack else "Uncategorized"
                entries.append({
                    "line_number": line_no,
                    "source_file": source_path,
                    "category": category,
                    "display_name": display_name,
                    "url": url,
                    "metadata": metadata,
                })
    return entries


def verify_selected_entries(target_file):
    content = target_file.read_text(encoding="utf-8")
    rel_path = str(target_file.relative_to(REPO_ROOT)) if target_file.is_relative_to(REPO_ROOT) else str(target_file)
    all_entries = parse_entries(content, source_path=rel_path)
    by_url = {item["url"]: item for item in all_entries}
    matched = []
    errors = []

    for url, spec in SELECTED_ENTRIES.items():
        found = by_url.get(url)
        if found is None:
            errors.append(f"Missing expected entry URL: {url}")
            continue
        matched.append(found)
        if found["line_number"] != spec["expected_line"]:
            errors.append(f"Line mismatch for {url}: expected {spec['expected_line']}, got {found['line_number']}")
        if found["display_name"] != spec["expected_display_name"]:
            errors.append(f"Name mismatch for {url}")
        if found["category"] != spec["expected_category"]:
            errors.append(f"Category mismatch for {url}")
        if found["metadata"]["format"] != spec["expected_format"]:
            errors.append(f"Format mismatch for {url}")
        if found["metadata"]["author"] != spec["expected_author"]:
            errors.append(f"Author mismatch for {url}")

    return {
        "target_file": rel_path,
        "total_parsed_entries": len(all_entries),
        "selected_entries": matched,
        "errors": errors,
        "passed": len(errors) == 0,
    }


def run_self_test(target_file, work_dir=None):
    fixture_markdown = (
        "### Index\n\n"
        "* [Algoritmos](#algoritmos)\n\n"
        "### Algoritmos\n\n"
        "```markdown\n"
        "* [Fake Fenced Link](https://example.com/fake-in-fence) (screencast)\n"
        "```\n\n"
        "~~~text\n"
        "* [Another Fake Link](https://example.com/tilde-fence#sec) (podcast)\n"
        "~~~\n\n"
        "* [Real Fragment Guide](https://example.org/docs/intro#section-2) - Jane Doe (screencast)\n"
    )
    fixture_results = parse_entries(fixture_markdown, source_path="fixture.md")
    urls = [item["url"] for item in fixture_results]
    assert "https://example.com/fake-in-fence" not in urls, "Backtick fenced fake link was not ignored"
    assert "https://example.com/tilde-fence#sec" not in urls, "Tilde fenced fake link was not ignored"
    assert len(fixture_results) == 1, f"Expected 1 entry, got {len(fixture_results)}"

    entry = fixture_results[0]
    assert entry["url"] == "https://example.org/docs/intro#section-2", "Fragment lost"
    assert entry["line_number"] == 15, f"Expected line 15, got {entry['line_number']}"

    real_report = verify_selected_entries(target_file)
    assert real_report["passed"], f"Real file verification failed: {real_report['errors']}"

    failing_caught = False
    try:
        assert entry["line_number"] == 999
    except AssertionError:
        failing_caught = True
    assert failing_caught, "Failing assertion did not raise AssertionError"

    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "fixture_input.md").write_text(fixture_markdown, encoding="utf-8")
        evidence = {
            "task_id": "R10-T021",
            "tool_versions": {"python": sys.version, "platform": platform.platform()},
            "fixture_expected": {
                "ignored_fenced_urls": [
                    "https://example.com/fake-in-fence",
                    "https://example.com/tilde-fence#sec",
                ],
                "parsed_entry": entry,
            },
            "fixture_actual": fixture_results,
            "real_file_verification": real_report,
            "self_test_passed": True,
        }
        (work_dir / "results.json").write_text(
            json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    print("SELF-TEST PASSED: All assertions succeeded.")
    print(json.dumps(real_report["selected_entries"], indent=2, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(description="Parse and verify casts/free-podcasts-screencasts-pt_BR.md (R10-T021).")
    parser.add_argument("--file", type=Path, default=DEFAULT_TARGET_FILE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-evidence", action="store_true")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    args = parser.parse_args()
    try:
        if args.self_test:
            return run_self_test(args.file, args.work_dir if args.write_evidence else None)
        report = verify_selected_entries(args.file)
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report["passed"] else 1
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
