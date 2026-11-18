#!/usr/bin/env python3
"""Classify bounded link checks for three entries in the Persian cast list."""

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
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any
from unittest.mock import patch


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_FILE = REPOSITORY_ROOT / "casts" / "free-podcasts-screencasts-fa_IR.md"
EVIDENCE_DIR = REPOSITORY_ROOT / "work" / "R10-T027"
FIXTURE_FILE = EVIDENCE_DIR / "fixtures" / "http_responses.json"
LIVE_TIMEOUT_SECONDS = 5
LIVE_MAX_WORKERS = 2
USER_AGENT = "R10-T027 course-check/1.0"

EXPECTED_ENTRIES = (
    {
        "display_name": "پادکست کافه برنامه نویس",
        "url": "https://anchor.fm/codemy",
        "category": "Programming News",
    },
    {
        "display_name": "راکت کست",
        "url": "https://roocket.ir/podcast/",
        "category": "Programming News",
    },
    {
        "display_name": "پارس کلیک",
        "url": "https://anchor.fm/parsclick/",
        "category": "Technology",
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
        for field in ("display_name", "category"):
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
            isinstance(reason, OSError) and reason.errno == socket.EAI_AGAIN
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

    def test_only_assigned_entries_are_parsed_with_line_numbers(self) -> None:
        source = SOURCE_FILE.read_text(encoding="utf-8")
        entries = parse_selected_entries(source)
        self.assertEqual(validate_source(entries), [])
        self.assertEqual(
            [entry["url"] for entry in entries],
            [entry["url"] for entry in EXPECTED_ENTRIES],
        )
        self.assertEqual([entry["line_number"] for entry in entries], [11, 12, 17])

    def test_response_fixtures_have_distinct_outcomes(self) -> None:
        observed = {}
        for fixture in self.fixture_data:
            result, methods = run_fixture(fixture, self.url)
            self.assertEqual(result["status"], fixture["expected_label"])
            self.assertEqual(methods, [step["method"] for step in fixture["steps"]])
            observed[fixture["name"]] = result["status"]

        self.assertEqual(len(set(observed.values())), len(self.fixture_data))
        fallback = next(
            fixture
            for fixture in self.fixture_data
            if fixture["name"] == "head_405_get_200"
        )
        result, _ = run_fixture(fallback, self.url)
        self.assertTrue(result["head_fallback"])

    def test_403_and_404_are_not_mislabeled_as_rate_limits_or_success(self) -> None:
        self.assertEqual(classify_status(403, "HEAD"), "forbidden")
        self.assertEqual(classify_status(404, "HEAD"), "missing_resource")
        self.assertEqual(classify_status(429, "HEAD"), "rate_limited")

    def test_timeout_and_dns_errors_are_distinguished(self) -> None:
        timeout = classify_network_error(TimeoutError("timed out"))
        dns_error = urllib.error.URLError(
            socket.gaierror(socket.EAI_AGAIN, "fixture DNS failure")
        )
        self.assertEqual(timeout, "timeout")
        self.assertEqual(classify_network_error(dns_error), "dns_failure")

    def test_removal_requires_manual_confirmation_and_missing_label(self) -> None:
        result = {
            "url": self.url,
            "status": "missing_resource",
            "manual_confirmation": False,
            "removal_recommendation": False,
        }
        apply_manual_confirmations([result], set())
        self.assertFalse(result["removal_recommendation"])
        apply_manual_confirmations([result], {self.url})
        self.assertTrue(result["removal_recommendation"])

        result["status"] = "rate_limited"
        apply_manual_confirmations([result], {self.url})
        self.assertFalse(result["removal_recommendation"])

    def test_unassigned_url_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside the assigned entry list"):
            check_url("https://example.test/")

    def test_live_check_is_limited_to_the_fixed_entries(self) -> None:
        with patch(f"{__name__}.check_url", side_effect=lambda url: {"url": url}) as check:
            results = verify_live()
        self.assertEqual(
            [result["url"] for result in results],
            [entry["url"] for entry in EXPECTED_ENTRIES],
        )
        self.assertEqual(check.call_count, len(EXPECTED_ENTRIES))

    def test_failed_self_test_result_returns_nonzero(self) -> None:
        with patch.object(sys, "argv", ["r10-t027.py", "--self-test"]), patch(
            f"{__name__}.test_output",
            return_value=(False, "simulated assertion failure\n"),
        ), patch(f"{__name__}.write_evidence"), redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 1)


def test_output() -> tuple[bool, str]:
    stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CourseCheckTests)
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return result.wasSuccessful(), stream.getvalue()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_evidence(
    entries: list[dict[str, Any]],
    source_failures: list[dict[str, Any]],
    self_test_status: str,
    self_test_output: str,
    live_results: list[dict[str, Any]] | None,
) -> None:
    write_json(
        EVIDENCE_DIR / "inputs.json",
        {
            "target_file": "casts/free-podcasts-screencasts-fa_IR.md",
            "selected_entries": entries,
            "live_limits": {
                "timeout_seconds": LIVE_TIMEOUT_SECONDS,
                "max_workers": LIVE_MAX_WORKERS,
            },
            "offline_fixture_file": "work/R10-T027/fixtures/http_responses.json",
        },
    )
    write_json(
        EVIDENCE_DIR / "expected_vs_actual.json",
        {
            "source_validation": {
                "status": "passed" if not source_failures else "failed",
                "failures": source_failures,
            },
            "fixtures": [
                {
                    "name": fixture["name"],
                    "expected": fixture["expected_label"],
                    "actual": run_fixture(
                        fixture, EXPECTED_ENTRIES[0]["url"]
                    )[0]["status"],
                }
                for fixture in json.loads(FIXTURE_FILE.read_text(encoding="utf-8"))
            ],
            "self_test": {"status": self_test_status},
            "live_request_results": live_results,
            "catalogue_corrections": [],
        },
    )
    (EVIDENCE_DIR / "self-test-output.txt").write_text(
        self_test_output, encoding="utf-8"
    )

    git_version = subprocess.run(
        ["git", "--version"],
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
    (EVIDENCE_DIR / "tool_versions.txt").write_text(
        f"Python: {sys.version.splitlines()[0]}\n"
        f"Platform: {platform.platform()}\n"
        f"Git: {git_version}\n"
        f"Branch: {branch}\n",
        encoding="utf-8",
    )
    report = [
        "# R10-T027 failure-classification report",
        "",
        "- Source: `casts/free-podcasts-screencasts-fa_IR.md`",
        "- Source validation: " + ("passed" if not source_failures else "failed"),
        f"- Offline self-test: {self_test_status}",
        f"- Live checks: {'run' if live_results is not None else 'not run'}",
        "- Catalogue corrections: none; automated failures alone do not justify removal.",
        "",
        "## Selected entries",
        "",
    ]
    report.extend(
        f"- Line {entry['line_number']}: {entry['display_name']} "
        f"`{entry['url']}` ({entry['category']})"
        for entry in entries
    )
    report.extend(
        [
            "",
            "Offline fixtures cover success (200), missing resource (404), "
            "forbidden (403), rate-limited (429), HEAD-405/GET-200 fallback, "
            "timeout, and DNS failure. Only manually confirmed missing resources "
            "can receive a removal recommendation.",
            "",
        ]
    )
    if live_results is not None:
        report.extend(["## Live classifications", ""])
        report.extend(
            f"- `{result['url']}`: {result['status']} "
            f"({result['method']})"
            for result in live_results
        )
        report.append("")
    (EVIDENCE_DIR / "report.md").write_text("\n".join(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline fixture tests")
    parser.add_argument(
        "--live",
        action="store_true",
        help="make optional bounded requests to the three assigned URLs",
    )
    parser.add_argument(
        "--confirm-missing",
        action="append",
        choices=tuple(ENTRY_BY_URL),
        default=[],
        metavar="URL",
        help="record a manual browser confirmation for a missing URL",
    )
    args = parser.parse_args()
    if args.confirm_missing and not args.live:
        parser.error("--confirm-missing requires --live")

    tests_passed = True
    self_test_status = "not_run"
    self_test_output = ""
    if args.self_test:
        tests_passed, self_test_output = test_output()
        self_test_status = "passed" if tests_passed else "failed"
        print(self_test_output, end="")

    try:
        entries = parse_selected_entries(SOURCE_FILE.read_text(encoding="utf-8"))
    except OSError as error:
        print(f"r10-t027: cannot read source: {error}", file=sys.stderr)
        return 1
    source_failures = validate_source(entries)
    live_results = None
    if args.live:
        live_results = apply_manual_confirmations(
            verify_live(), set(args.confirm_missing)
        )

    write_evidence(
        entries,
        source_failures,
        self_test_status,
        self_test_output,
        live_results,
    )
    if source_failures:
        print(
            "r10-t027: selected source entries differ from the expected catalogue rows: "
            + json.dumps(source_failures, ensure_ascii=False),
            file=sys.stderr,
        )
        return 1
    if not tests_passed:
        return 1
    if not args.self_test:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
