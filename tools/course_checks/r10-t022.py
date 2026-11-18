#!/usr/bin/env python3
"""Verify redirects for the selected Vietnamese learning resources."""

from __future__ import annotations

import argparse
import io
import json
import platform
import re
import socket
import subprocess
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
import urllib.error
import urllib.request


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "books" / "free-programming-books-vi.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T022"
FIXTURE_DIR = EVIDENCE_DIR / "fixtures"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2
MAX_REDIRECTS = 10

SELECTED_ENTRIES = (
    {
        "display_name": "The Little Go Book",
        "url": "https://github.com/nainglinaung/the-little-go-book",
        "category": "Go",
        "line_number": 10,
        "kind": "primary",
    },
    {
        "display_name": "HTML",
        "url": "https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md",
        "category": "Go",
        "line_number": 10,
        "kind": "HTML",
    },
    {
        "display_name": "Đắm chìm vào Học sâu",
        "url": "https://d2l.aivivn.com",
        "category": "Học máy",
        "line_number": 15,
        "kind": "primary",
    },
)
SELECTED_URLS = frozenset(entry["url"] for entry in SELECTED_ENTRIES)

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
PRIMARY_ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>https?://[^)\s]+)\)(?P<metadata>.*)$"
)
LINK_RE = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<url>https?://[^)\s]+)\)")


class BoundedRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.redirect_count = 0

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        self.redirect_count += 1
        if self.redirect_count > MAX_REDIRECTS:
            raise urllib.error.URLError("too many redirects")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def parse_entries(markdown: str) -> list[dict[str, Any]]:
    """Parse primary and labelled in-line links while preserving source line numbers."""
    entries: list[dict[str, Any]] = []
    heading_hierarchy: dict[int, str] = {}

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading_match = HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_hierarchy = {
                depth: title
                for depth, title in heading_hierarchy.items()
                if depth < level
            }
            heading_hierarchy[level] = re.sub(
                r"<[^>]*>", "", heading_match.group(2)
            ).strip()
            continue

        primary_match = PRIMARY_ENTRY_RE.match(line)
        if not primary_match:
            continue

        category = " > ".join(
            heading_hierarchy[depth] for depth in sorted(heading_hierarchy)
        )
        primary_url = primary_match.group("url")
        entries.append(
            {
                "display_name": primary_match.group("display_name"),
                "url": primary_url,
                "category": category,
                "line_number": line_number,
                "kind": "primary",
            }
        )

        metadata = primary_match.group("metadata")
        for labelled_match in LINK_RE.finditer(metadata):
            entries.append(
                {
                    "display_name": labelled_match.group("label"),
                    "url": labelled_match.group("url"),
                    "category": category,
                    "line_number": line_number,
                    "kind": labelled_match.group("label"),
                }
            )

    return entries


def select_required_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Scope results to exactly the three assigned URLs."""
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
            {
                "field": "entry_count",
                "expected": len(SELECTED_ENTRIES),
                "actual": len(actual),
            }
        )
    return mismatches


def classify_result(
    url: str,
    *,
    status: int | None = None,
    final_url: str | None = None,
    error: BaseException | str | None = None,
    redirect_count: int = 0,
) -> dict[str, Any]:
    """Classify HTTP redirects and failures without implying an entry should be removed."""
    error_text = str(error or "")
    lower_error = error_text.lower()
    result: dict[str, Any] = {
        "url": url,
        "final_url": final_url or url,
        "redirect_count": redirect_count,
    }

    if isinstance(error, (TimeoutError, socket.timeout)) or "timed out" in lower_error:
        result.update(classification="timeout", status=status)
    elif "loop" in lower_error or "too many redirects" in lower_error:
        result.update(classification="redirect_loop", status=status)
    elif isinstance(error, urllib.error.HTTPError) or status in (401, 403):
        code = status or getattr(error, "code", None)
        if code in (401, 403):
            result.update(classification="login_wall", status=code)
        elif code == 429 or (code is not None and 500 <= code <= 599):
            result.update(classification="transient_failure", status=code)
        elif code is not None:
            result.update(classification="http_error", status=code)
    elif isinstance(error, (urllib.error.URLError, OSError)):
        result.update(classification="transient_failure", status=status)
    elif status is not None and 200 <= status < 300:
        official = final_url and final_url != url
        result.update(
            classification="moved" if official else "official_200",
            status=status,
        )
    elif status is not None and 300 <= status < 400:
        result.update(classification="redirect_unresolved", status=status)
    elif status == 429 or (status is not None and 500 <= status <= 599):
        result.update(classification="transient_failure", status=status)
    else:
        result.update(
            classification="transient_failure" if error else "unknown",
            status=status,
            error=error_text or None,
        )
    if error_text and "classification" in result:
        result["error"] = error_text
    return result


def check_url(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Make one bounded informational request to a fixed URL."""
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "R10-T022 redirect checker/1.0"},
    )
    redirect_handler = BoundedRedirectHandler()
    opener = urllib.request.build_opener(redirect_handler)
    try:
        with opener.open(request, timeout=timeout) as response:
            return classify_result(
                url,
                status=response.status,
                final_url=response.geturl(),
                redirect_count=redirect_handler.redirect_count,
            )
    except urllib.error.HTTPError as error:
        return classify_result(
            url,
            status=error.code,
            final_url=error.url or url,
            error=error,
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout, OSError) as error:
        return classify_result(url, error=error)


def verify_live(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Probe only the selected URLs with low concurrency and a fixed timeout."""
    fixed_entries = [entry for entry in entries if entry["url"] in SELECTED_URLS]
    with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
        results = list(executor.map(lambda entry: check_url(entry["url"]), fixed_entries))
    for entry, result in zip(fixed_entries, results):
        result["display_name"] = entry["display_name"]
        result["line_number"] = entry["line_number"]
        result["observation_date"] = datetime.now(timezone.utc).date().isoformat()
    return results


class CourseCheckTests(unittest.TestCase):
    def test_offline_200(self) -> None:
        fixture = json.loads((FIXTURE_DIR / "200.json").read_text())
        result = classify_result(
            fixture["url"],
            status=fixture["status"],
            final_url=fixture["final_url"],
        )
        self.assertEqual(result["classification"], "official_200")

    def test_offline_301_then_200(self) -> None:
        fixture = json.loads((FIXTURE_DIR / "301-to-200.json").read_text())
        first = classify_result(
            fixture["url"],
            status=fixture["chain"][0]["status"],
            final_url=fixture["chain"][0]["location"],
            redirect_count=1,
        )
        final = classify_result(
            fixture["url"],
            status=fixture["chain"][1]["status"],
            final_url=fixture["final_url"],
            redirect_count=2,
        )
        self.assertEqual(first["classification"], "redirect_unresolved")
        self.assertEqual(final["classification"], "moved")
        self.assertEqual(final["final_url"], fixture["final_url"])

    def test_offline_redirect_loop(self) -> None:
        fixture = json.loads((FIXTURE_DIR / "redirect-loop.json").read_text())
        result = classify_result(
            fixture["url"],
            status=fixture["status"],
            final_url=fixture["final_url"],
            error=fixture["error"],
            redirect_count=fixture["redirect_count"],
        )
        self.assertEqual(result["classification"], "redirect_loop")

    def test_offline_timeout(self) -> None:
        fixture = json.loads((FIXTURE_DIR / "timeout.json").read_text())
        result = classify_result(
            fixture["url"],
            error=fixture["error"],
        )
        self.assertEqual(result["classification"], "timeout")

    def test_selected_entries_and_source_lines(self) -> None:
        actual = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )
        self.assertEqual(compare_expected(actual), [])

    def test_missing_entry_raises(self) -> None:
        with self.assertRaisesRegex(AssertionError, "missing entry"):
            select_required_entries([])

    def test_failed_request_does_not_remove_entry(self) -> None:
        entries = select_required_entries(
            parse_entries(SOURCE_FILE.read_text(encoding="utf-8"))
        )

        def fake_check(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
            return {"url": url, "classification": "timeout"}

        with patch(f"{__name__}.check_url", side_effect=fake_check):
            results = verify_live(entries)
        self.assertEqual(len(entries), 3)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(result["classification"] == "timeout" for result in results))

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t022.py", "--self-test"]), patch(
            f"{__name__}.test_output",
            return_value=(False, "simulated assertion failure\n"),
        ), patch(f"{__name__}.write_evidence"), io_redirect(io.StringIO()) as output:
            self.assertEqual(main(), 1)


def io_redirect(stream: io.StringIO):
    from contextlib import redirect_stdout
    return redirect_stdout(stream)


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
        "target_file": "books/free-programming-books-vi.md",
        "target_section": "Go and Học máy",
        "selected_entries": list(SELECTED_ENTRIES),
        "limits": {
            "timeout_seconds": LIVE_TIMEOUT_SECONDS,
            "max_workers": LIVE_MAX_WORKERS,
            "max_redirects": MAX_REDIRECTS,
        },
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
    versions = (
        f"Python: {sys.version.splitlines()[0]}\n"
        f"Platform: {platform.platform()}\n"
        f"Git commit: {commit}\n"
        f"Git branch: {branch}\n"
        "urllib: Python standard library\n"
    )
    (EVIDENCE_DIR / "tool_versions.txt").write_text(versions, encoding="utf-8")

    report_lines = [
        "# R10-T022 checker report",
        "",
        "- Source: `books/free-programming-books-vi.md`",
        "- Selected entries: 3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Live request checks: {'run' if live_results is not None else 'not run'}",
        "",
        "## Extracted records",
        "",
        "| Line | Display name | Kind | Category | URL |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for entry in actual:
        report_lines.append(
            f"| {entry['line_number']} | {entry['display_name']} | "
            f"{entry['kind']} | {entry['category']} | `{entry['url']}` |"
        )
    if validation_error:
        report_lines.extend(["", f"Validation error: `{validation_error}`"])
    if live_results is not None:
        report_lines.extend(
            ["", "## Live observations", "", "Live requests are informational only."]
        )
        for result in live_results:
            report_lines.append(
                f"- {result['display_name']} (`{result['url']}`): "
                f"{result['classification']}; final `{result['final_url']}` "
                f"(observed {result['observation_date']})"
            )
    report_lines.extend(
        [
            "",
            "No catalogue correction was made: the three selected source entries match",
            "their exact URLs and are retained unless browser evidence proves removal is needed.",
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
        help="make informational GET requests to the three fixed URLs",
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

    if validation_error:
        print(f"r10-t022: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1
    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
