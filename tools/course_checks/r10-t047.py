#!/usr/bin/env python3
"""Classify link failure types for selected Swedish programming book entries."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import platform
import re
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "books" / "free-programming-books-sv.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T047"
FIXTURE_FILE = EVIDENCE_DIR / "fixtures" / "http_responses.json"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2
USER_AGENT = "R10-T047 course-check/1.0"

EXPECTED_ENTRIES = (
    {
        "display_name": "C-programmering",
        "url": "https://sv.wikibooks.org/wiki/C-programmering",
        "category": "C",
        "line_number": 13,
    },
    {
        "display_name": "Programmera spel i C++ för nybörjare",
        "url": "https://sv.wikibooks.org/wiki/Programmera_spel_i_C%2B%2B_f%C3%B6r_nyb%C3%B6rjare",
        "category": "C++",
        "line_number": 18,
    },
    {
        "display_name": "Pro Git",
        "url": "https://git-scm.com/book/sv/v2",
        "category": "Git",
        "line_number": 23,
    },
)
ENTRY_BY_URL = {entry["url"]: entry for entry in EXPECTED_ENTRIES}
ENTRY_RE = re.compile(
    r"^ {0,3}[*+-]\s+\[(?P<display_name>[^\]]+)\]"
    r"\((?P<url>[^)\s]+)\)"
)
HEADING_RE = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$")


def parse_selected_entries(markdown: str) -> list[dict[str, Any]]:
    """Return only the three assigned rows, retaining their source line numbers."""
    entries = []
    category: str | None = None
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        heading = HEADING_RE.match(line)
        if heading:
            cleaned = re.sub(r"<[^>]*>", "", heading.group(1)).replace("\\#", "#").strip()
            category = cleaned
            continue

        match = ENTRY_RE.match(line)
        if match is None:
            continue
        url = match.group("url")
        expected = ENTRY_BY_URL.get(url)
        if expected is None:
            continue
        entries.append(
            {
                "display_name": match.group("display_name"),
                "url": url,
                "category": category,
                "line_number": line_number,
                "expected": expected,
            }
        )
    return entries


def validate_source(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report missing, duplicate, or changed selected catalogue rows."""
    failures = []
    actual_by_url: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        actual_by_url.setdefault(entry["url"], []).append(entry)

    for expected in EXPECTED_ENTRIES:
        matches = actual_by_url.get(expected["url"], [])
        if len(matches) != 1:
            failures.append(
                {
                    "url": expected["url"],
                    "expected_count": 1,
                    "actual_count": len(matches),
                }
            )
            continue
        actual = matches[0]
        for field in ("display_name", "category", "line_number"):
            if actual[field] != expected[field]:
                failures.append(
                    {
                        "url": expected["url"],
                        "field": field,
                        "expected": expected[field],
                        "actual": actual[field],
                    }
                )
    return failures


def classify_status(code: int, method: str) -> str:
    if 200 <= code < 300:
        return "success_head" if method == "HEAD" else "success_get_fallback"
    if code == 403:
        return "forbidden"
    if code == 404:
        return "missing_resource"
    if code == 429:
        return "rate_limited"
    return "http_error"


def classify_network_error(error: BaseException) -> str:
    if isinstance(error, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(error, socket.gaierror):
        return "dns_failure"
    if isinstance(error, urllib.error.URLError):
        reason = error.reason
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "timeout"
        if isinstance(reason, socket.gaierror) or (
            isinstance(reason, OSError) and getattr(reason, "errno", None) == socket.EAI_AGAIN
        ):
            return "dns_failure"
    return "request_error"


def _request(url: str, method: str, timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url, method=method, headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            code = response.status
            result = {
                "url": url,
                "status": classify_status(code, method),
                "http_status": code,
                "method": method,
                "final_url": response.geturl(),
            }
    except urllib.error.HTTPError as error:
        result = {
            "url": url,
            "status": classify_status(error.code, method),
            "http_status": error.code,
            "method": method,
        }
    except (TimeoutError, socket.timeout, socket.gaierror) as error:
        result = {
            "url": url,
            "status": classify_network_error(error),
            "method": method,
            "error": str(error),
        }
    except urllib.error.URLError as error:
        result = {
            "url": url,
            "status": classify_network_error(error),
            "method": method,
            "error": str(error),
        }
    except OSError as error:
        result = {
            "url": url,
            "status": classify_network_error(error),
            "method": method,
            "error": str(error),
        }
    return result


def check_url(url: str, timeout: int = LIVE_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Check one allowlisted URL; retry with GET when HEAD is unsupported."""
    if url not in ENTRY_BY_URL:
        raise ValueError(f"URL is outside the assigned entry list: {url}")

    result = _request(url, "HEAD", timeout)
    if result.get("http_status") in (405, 501):
        result = _request(url, "GET", timeout)
        result["head_fallback"] = True
    else:
        result["head_fallback"] = False
    result["manual_confirmation"] = False
    result["removal_recommendation"] = False
    return result


def apply_manual_confirmations(
    results: list[dict[str, Any]], confirmed_urls: set[str]
) -> list[dict[str, Any]]:
    """Recommend removal only for a missing URL the user confirmed manually."""
    for result in results:
        confirmed = result["url"] in confirmed_urls
        result["manual_confirmation"] = confirmed
        result["removal_recommendation"] = (
            confirmed and result["status"] == "missing_resource"
        )
    return results


def response(code: int, url: str) -> Any:
    class FakeResponse:
        status = code

        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def geturl(self) -> str:
            return url

    return FakeResponse()


def http_error(code: int, url: str, method: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "fixture", {}, None)


def run_fixture(fixture: dict[str, Any], url: str) -> tuple[dict[str, Any], Any]:
    steps = fixture["steps"]
    side_effect = []
    for step in steps:
        if "error" in step:
            if step["error"] == "timeout":
                side_effect.append(TimeoutError("fixture timeout"))
            elif step["error"] == "dns_failure":
                side_effect.append(
                    urllib.error.URLError(
                        socket.gaierror(socket.EAI_AGAIN, "fixture DNS failure")
                    )
                )
            continue
        if step["status"] >= 400:
            side_effect.append(http_error(step["status"], url, step["method"]))
        else:
            side_effect.append(response(step["status"], url))

    with patch("urllib.request.urlopen", side_effect=side_effect) as mocked:
        result = check_url(url)
    methods = [call.args[0].method for call in mocked.call_args_list]
    return result, methods


class CourseCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture_data = json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
        self.url = EXPECTED_ENTRIES[0]["url"]

    def test_fixtures_produce_different_labels(self) -> None:
        labels = {}
        for name, fixture in self.fixture_data.items():
            result, _ = run_fixture(fixture, self.url)
            self.assertEqual(result["status"], fixture["expected_status"])
            labels[name] = result["status"]

        key_scenarios = ["200_ok", "404_not_found", "429_rate_limited", "head_405_get_200", "timeout"]
        unique_labels = {labels[k] for k in key_scenarios}
        self.assertEqual(len(unique_labels), len(key_scenarios))

    def test_only_manually_confirmed_missing_is_recommended_for_removal(self) -> None:
        res_404, _ = run_fixture(self.fixture_data["404_not_found"], self.url)
        res_429, _ = run_fixture(self.fixture_data["429_rate_limited"], self.url)

        self.assertFalse(res_404["removal_recommendation"])
        self.assertFalse(res_429["removal_recommendation"])

        confirmed = apply_manual_confirmations([res_404, res_429], {self.url})
        self.assertTrue(confirmed[0]["removal_recommendation"])
        self.assertFalse(confirmed[1]["removal_recommendation"])

    def test_source_entries_match_expected_fields(self) -> None:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        entries = parse_selected_entries(source_text)
        failures = validate_source(entries)
        self.assertEqual(failures, [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t047.py", "--self-test"]), \
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
    validation_failures: list[dict[str, Any]],
    self_test_status: str,
    self_test_output: str,
    live_results: list[dict[str, Any]] | None,
) -> None:
    inputs = {
        "target_file": "books/free-programming-books-sv.md",
        "target_section": "Swedish programming books: C, C++, Git",
        "selected_entries": [
            {
                "display_name": entry["display_name"],
                "url": entry["url"],
                "category": entry["category"],
                "line_number": entry["line_number"],
            }
            for entry in EXPECTED_ENTRIES
        ],
    }
    expected_vs_actual = {
        "expected": list(EXPECTED_ENTRIES),
        "actual": actual,
        "validation": {
            "status": "passed" if not validation_failures else "failed",
            "failures": validation_failures,
        },
        "self_test": {"status": self_test_status},
        "live_results": live_results,
    }
    write_json(EVIDENCE_DIR / "inputs.json", inputs)
    write_json(EVIDENCE_DIR / "expected_vs_actual.json", expected_vs_actual)
    if self_test_output:
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
        "# R10-T047 failure classification report",
        "",
        "- Source: `books/free-programming-books-sv.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
        f"- Live check status: {'run' if live_results is not None else 'not run'}",
        "",
        "## Selected entries",
        "",
        "| Line | Display name | Category | URL |",
        "| ---: | --- | --- | --- |",
    ]
    for entry in actual:
        report_lines.append(
            f"| {entry['line_number']} | {entry['display_name']} | "
            f"{entry['category']} | `{entry['url']}` |"
        )
    if validation_failures:
        report_lines.extend(["", "### Validation Failures:", f"```json\n{json.dumps(validation_failures, indent=2)}\n```"])
    if live_results is not None:
        report_lines.extend(
            [
                "",
                "## Optional live reachability results",
                "",
                "Automated request failures never remove links without manual confirmation.",
                "",
            ]
        )
        for r in live_results:
            report_lines.append(f"- `{r['url']}`: status `{r.get('status')}` (HTTP {r.get('http_status', 'N/A')})")
    report_lines.extend(
        [
            "",
            "Offline fixtures for 200, 404, 429, HEAD-405/GET-200 fallback, and timeout produce distinct labels.",
            "Only manually confirmed missing resources (404) are flagged for removal.",
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
        help="optional live reachability check with 5s timeout",
    )
    args = parser.parse_args()

    self_test_status = "not_run"
    self_test_output = ""
    tests_passed = True
    if args.self_test:
        tests_passed, self_test_output = test_output()
        self_test_status = "passed" if tests_passed else "failed"
        print(self_test_output, end="")

    validation_failures = []
    actual = []
    try:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        actual = parse_selected_entries(source_text)
        validation_failures = validate_source(actual)
    except Exception as error:
        validation_failures = [{"error": str(error)}]

    live_results = None
    if args.live and actual:
        with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
            live_results = list(executor.map(lambda e: check_url(e["url"]), actual))

    write_evidence(
        actual,
        validation_failures,
        self_test_status,
        self_test_output,
        live_results,
    )

    if validation_failures:
        print(f"r10-t047: validation failures: {validation_failures}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps(actual, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
