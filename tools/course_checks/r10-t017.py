#!/usr/bin/env python3
"""Classify bounded link checks for three entries in the cheatsheets list."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from concurrent.futures import ThreadPoolExecutor
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
SOURCE_FILE = REPOSITORY_ROOT / "more" / "free-programming-cheatsheets.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T017"
FIXTURE_FILE = EVIDENCE_DIR / "fixtures" / "http_responses.json"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2
USER_AGENT = "R10-T017 course-check/1.0"

EXPECTED_ENTRIES = (
    {
        "display_name": "Angular Cheat Sheet",
        "url": "https://angular.io/guide/cheatsheet",
        "category": "Angular",
        "line_number": 79,
    },
    {
        "display_name": "Angular Cheat Sheet",
        "url": "https://zerotomastery.io/cheatsheets/angular-cheat-sheet/",
        "category": "Angular",
        "line_number": 80,
    },
    {
        "display_name": "Angular Cheat Sheet – A Basic Guide to Angular",
        "url": "https://www.geeksforgeeks.org/angular-cheat-sheet-a-basic-guide-to-angular/",
        "category": "Angular",
        "line_number": 81,
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
            category = heading.group(1).strip()
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


def verify_live() -> list[dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=LIVE_MAX_WORKERS) as executor:
        return list(
            executor.map(
                lambda entry: check_url(entry["url"]), EXPECTED_ENTRIES
            )
        )


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

        # Ensure 200, 404, 429, HEAD-405/GET-200 and timeout produce different labels
        key_scenarios = ["200_ok", "404_not_found", "429_rate_limited", "head_405_get_200", "timeout"]
        unique_labels = {labels[k] for k in key_scenarios}
        self.assertEqual(len(unique_labels), len(key_scenarios))

    def test_only_manually_confirmed_missing_is_recommended_for_removal(self) -> None:
        res_404, _ = run_fixture(self.fixture_data["404_not_found"], self.url)
        res_429, _ = run_fixture(self.fixture_data["429_rate_limited"], self.url)

        # Before manual confirmation
        self.assertFalse(res_404["removal_recommendation"])
        self.assertFalse(res_429["removal_recommendation"])

        # After manual confirmation
        confirmed = apply_manual_confirmations([res_404, res_429], {self.url})
        self.assertTrue(confirmed[0]["removal_recommendation"])
        # Even if confirmed, non-missing resources are not recommended for removal
        self.assertFalse(confirmed[1]["removal_recommendation"])

    def test_source_entries_match_expected_fields(self) -> None:
        source_text = SOURCE_FILE.read_text(encoding="utf-8")
        entries = parse_selected_entries(source_text)
        failures = validate_source(entries)
        self.assertEqual(failures, [])

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t017.py", "--self-test"]), \
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
    failures = validate_source(actual)

    inputs = {
        "target_file": "more/free-programming-cheatsheets.md",
        "target_section": "Cheatsheets list; category: Angular",
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
        "actual": [
            {
                "display_name": entry["display_name"],
                "url": entry["url"],
                "category": entry["category"],
                "line_number": entry["line_number"],
            }
            for entry in actual
        ],
        "validation": {
            "status": "passed" if not failures and validation_error is None else "failed",
            "mismatches": failures,
            "error": validation_error,
        },
        "self_test": {"status": self_test_status},
        "live_results": live_results or [],
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
        "# R10-T017 failure classification report",
        "",
        "- Source: `more/free-programming-cheatsheets.md`",
        f"- Selected entries validated: {len(actual)}/3",
        f"- Source validation: {expected_vs_actual['validation']['status']}",
        f"- Self-test status: {self_test_status}",
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
    if validation_error:
        report_lines.extend(["", f"Validation error: `{validation_error}`"])
    report_lines.extend(
        [
            "",
            "Fixtures distinguish 200, 404, 429, HEAD-405/GET-200 fallback, and timeout conditions.",
            "Only manually confirmed missing resources are recommended for catalogue removal.",
            "No link is removed based solely on automated request errors.",
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
        help="optional live availability checks",
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
        actual = parse_selected_entries(source_text)
        failures = validate_source(actual)
        if failures:
            validation_error = json.dumps(failures, ensure_ascii=False)
    except (OSError, AssertionError) as error:
        validation_error = str(error)
        actual = []

    live_results = None
    if args.live and actual:
        live_results = verify_live()

    write_evidence(
        actual,
        validation_error,
        self_test_status,
        self_test_output,
        live_results,
    )

    if validation_error:
        print(f"r10-t017: {validation_error}", file=sys.stderr)
        return 1
    if not tests_passed:
        return 1

    if not args.self_test:
        print(json.dumps([e["expected"] for e in actual], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
