#!/usr/bin/env python3
"""Verify selected Vietnamese book-list entries and classify redirects."""

import argparse
import json
import platform
import re
import socket
import ssl
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_FILE = REPO_ROOT / "books" / "free-programming-books-vi.md"
DEFAULT_WORK_DIR = REPO_ROOT / "work" / "R10-T022"
TARGET_CATEGORIES = ("Go", "Học máy")
LIVE_TIMEOUT_SECONDS = 8
LIVE_MAX_REDIRECTS = 5

SELECTED_ENTRIES = {
    "https://github.com/nainglinaung/the-little-go-book": {
        "expected_display_name": "The Little Go Book",
        "expected_category": "Go",
        "expected_line": 10,
        "expected_author": "Karl Seguin, `trl.:` Naing Lin Aung",
        "expected_format": None,
    },
    "https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md": {
        "expected_display_name": "HTML",
        "expected_category": "Go",
        "expected_line": 10,
        "expected_author": "Karl Seguin, `trl.:` Naing Lin Aung",
        "expected_format": "HTML",
        "expected_parent": "The Little Go Book",
    },
    "https://d2l.aivivn.com": {
        "expected_display_name": "Đắm chìm vào Học sâu",
        "expected_category": "Học máy",
        "expected_line": 15,
        "expected_author": "`trl.:` Nhóm dịch thuật Đắm chìm vào Học sâu",
        "expected_format": "HTML",
    },
}

FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{2,6})[ \t]+(.+?)\s*#*\s*$")
ENTRY_RE = re.compile(r"^\s*[*+-]\s+\[([^\]]+)\]\(([^)]+)\)(.*)$")
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
EMPTY_PARENS_RE = re.compile(r"\(\s*\)")
LOGIN_PATH_RE = re.compile(r"/(?:login|log-in|signin|sign-in|users/sign_in)(?:/|$)", re.I)
REDIRECT_CODES = {301, 302, 303, 307, 308}


def parse_metadata(raw_tail):
    links = [
        {"label": label.strip(), "url": url.strip()}
        for label, url in LINK_RE.findall(raw_tail)
    ]
    plain_text = EMPTY_PARENS_RE.sub("", LINK_RE.sub("", raw_tail)).strip()
    resource_format = None
    format_match = re.search(r"\(([^()]*)\)\s*$", plain_text)
    if format_match:
        resource_format = format_match.group(1).strip() or None
        plain_text = plain_text[: format_match.start()].strip()

    author = plain_text
    for prefix in ("- ", "– ", "— "):
        if author.startswith(prefix):
            author = author[len(prefix) :].strip()
            break
    return {
        "author": author or None,
        "format": resource_format,
        "related_links": links,
        "raw_metadata": raw_tail.strip() or None,
    }


def parse_entries(markdown_text, source_file="<memory>"):
    entries = []
    fence_character = None
    fence_length = 0
    category = None

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
            if level == 3:
                title = re.sub(
                    r"</?a\b[^>]*>", "", heading_match.group(2), flags=re.I
                ).strip()
                category = title if title in TARGET_CATEGORIES else None
            elif level < 3:
                category = None
            continue
        if category is None:
            continue

        entry_match = ENTRY_RE.match(raw_line)
        if not entry_match:
            continue
        display_name, url, raw_tail = entry_match.groups()
        metadata = parse_metadata(raw_tail)
        main_entry = {
            "line_number": line_number,
            "source_file": source_file,
            "category": category,
            "display_name": display_name.strip(),
            "url": url.strip(),
            "metadata": metadata,
        }
        entries.append(main_entry)

        for related_link in metadata["related_links"]:
            entries.append(
                {
                    "line_number": line_number,
                    "source_file": source_file,
                    "category": category,
                    "display_name": related_link["label"],
                    "url": related_link["url"],
                    "metadata": {
                        "author": metadata["author"],
                        "format": related_link["label"],
                        "related_links": [],
                        "raw_metadata": metadata["raw_metadata"],
                        "parent_entry": display_name.strip(),
                    },
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
        matches = by_url.get(url, [])
        if not matches:
            errors.append(f"Missing selected URL: {url}")
            continue
        if len(matches) > 1:
            errors.append(f"Duplicate selected URL: {url}")
        found = matches[0]
        selected.append(found)
        if found["line_number"] != expected["expected_line"]:
            errors.append(
                f"Line mismatch for {url}: expected {expected['expected_line']}, "
                f"got {found['line_number']}"
            )
        if found["display_name"] != expected["expected_display_name"]:
            errors.append(f"Display-name mismatch for {url}")
        if found["category"] != expected["expected_category"]:
            errors.append(f"Category mismatch for {url}")
        if found["metadata"]["author"] != expected["expected_author"]:
            errors.append(f"Author mismatch for {url}")
        if found["metadata"]["format"] != expected["expected_format"]:
            errors.append(f"Format mismatch for {url}")
        if "expected_parent" in expected and (
            found["metadata"].get("parent_entry") != expected["expected_parent"]
        ):
            errors.append(f"Parent-entry mismatch for {url}")

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
    return verify_entries(parse_entries(content, source_file), source_file)


def _header(headers, name):
    name = name.lower()
    return next(
        (value for key, value in headers.items() if key.lower() == name),
        None,
    )


def _is_login_wall(url, status, headers):
    if status in (401, 407) or _header(headers, "WWW-Authenticate"):
        return True
    return bool(LOGIN_PATH_RE.search(urlsplit(url).path))


def probe_url(start_url, fetch, timeout=LIVE_TIMEOUT_SECONDS, max_redirects=LIVE_MAX_REDIRECTS):
    current_url = start_url
    visited = set()
    redirects = []
    request_count = 0
    status_code = None

    while True:
        if current_url in visited:
            return {
                "classification": "redirect_loop",
                "final_url": current_url,
                "status_code": status_code,
                "redirects": redirects,
                "request_count": request_count,
                "detail": None,
            }
        visited.add(current_url)
        request_count += 1
        try:
            response = fetch(current_url, timeout)
        except (TimeoutError, socket.timeout):
            return {
                "classification": "timeout",
                "final_url": current_url,
                "status_code": None,
                "redirects": redirects,
                "request_count": request_count,
                "detail": "request timed out",
            }
        except (URLError, OSError) as exc:
            reason = getattr(exc, "reason", exc)
            if isinstance(reason, ssl.SSLError):
                classification = "tls_error"
            elif isinstance(reason, (TimeoutError, socket.timeout)):
                classification = "timeout"
            else:
                classification = "transient"
            return {
                "classification": classification,
                "final_url": current_url,
                "status_code": None,
                "redirects": redirects,
                "request_count": request_count,
                "detail": str(reason),
            }

        status_code = response["status"]
        headers = response.get("headers", {})
        if status_code in REDIRECT_CODES:
            location = _header(headers, "Location")
            if not location:
                return {
                    "classification": "invalid_redirect",
                    "final_url": current_url,
                    "status_code": status_code,
                    "redirects": redirects,
                    "request_count": request_count,
                    "detail": "redirect response had no Location header",
                }
            next_url = urljoin(current_url, location)
            redirect = {
                "status_code": status_code,
                "from": current_url,
                "to": next_url,
            }
            if next_url in visited:
                redirects.append(redirect)
                return {
                    "classification": "redirect_loop",
                    "final_url": next_url,
                    "status_code": status_code,
                    "redirects": redirects,
                    "request_count": request_count,
                    "detail": None,
                }
            if len(redirects) >= max_redirects:
                return {
                    "classification": "too_many_redirects",
                    "final_url": current_url,
                    "status_code": status_code,
                    "redirects": redirects,
                    "request_count": request_count,
                    "detail": f"redirect limit reached before following {next_url}",
                }
            redirects.append(redirect)
            current_url = next_url
            continue

        if _is_login_wall(current_url, status_code, headers):
            classification = "login_wall"
        elif status_code in (408, 425, 429) or 500 <= status_code <= 599:
            classification = "transient"
        elif status_code == 404 or status_code == 410:
            classification = "not_found"
        elif status_code == 200:
            classification = "redirected" if redirects else "ok"
        else:
            classification = "http_error"
        return {
            "classification": classification,
            "final_url": current_url,
            "status_code": status_code,
            "redirects": redirects,
            "request_count": request_count,
            "detail": None,
        }


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def live_fetcher():
    opener = build_opener(NoRedirectHandler())

    def fetch(url, timeout):
        request = Request(
            url,
            headers={"User-Agent": "free-programming-books-r10-t022-check/1.0"},
        )
        try:
            response = opener.open(request, timeout=timeout)
        except HTTPError as exc:
            return {"status": exc.code, "headers": dict(exc.headers.items())}
        except URLError as exc:
            if isinstance(exc.reason, (TimeoutError, socket.timeout)):
                raise TimeoutError(str(exc.reason)) from exc
            raise
        with response:
            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
            }

    return fetch


def _fixture_fetcher(responses):
    def fetch(url, timeout):
        outcome = responses[url]
        if outcome.get("exception") == "timeout":
            raise TimeoutError("fixture timeout")
        if outcome.get("exception") == "connection":
            raise OSError("fixture connection reset")
        if outcome.get("exception") == "tls":
            raise URLError(ssl.SSLCertVerificationError("fixture certificate error"))
        return {"status": outcome["status"], "headers": outcome.get("headers", {})}

    return fetch


def _summary(result):
    return {
        key: result[key]
        for key in ("classification", "final_url", "status_code", "request_count")
    }


def run_self_test(target_file, work_dir):
    fixture_path = work_dir / "fixture_responses.json"
    failure_catalogue = work_dir / "fixture_catalogue_failure.md"
    fixture_data = json.loads(fixture_path.read_text(encoding="utf-8"))
    fixture_results = {}

    required_cases = {
        "direct_200",
        "redirect_301_to_200",
        "redirect_loop",
        "redirect_budget",
        "timeout",
        "login_wall",
        "transient_503",
        "tls_certificate_error",
    }
    assert set(fixture_data) == required_cases, (
        f"Expected exactly the offline cases {sorted(required_cases)}"
    )
    for case_name, fixture in fixture_data.items():
        actual = probe_url(
            fixture["start_url"],
            _fixture_fetcher(fixture["responses"]),
            timeout=1,
            max_redirects=3,
        )
        expected = fixture["expected"]
        assert _summary(actual) == expected, (
            f"{case_name}: expected {expected}, got {_summary(actual)}"
        )
        fixture_results[case_name] = {
            "input": fixture,
            "expected": expected,
            "actual": actual,
        }

    source_report = verify_selected_entries(target_file)
    expected_source_entries = [
        {
            "line_number": 10,
            "source_file": "books/free-programming-books-vi.md",
            "category": "Go",
            "display_name": "The Little Go Book",
            "url": "https://github.com/nainglinaung/the-little-go-book",
            "metadata": {
                "author": "Karl Seguin, `trl.:` Naing Lin Aung",
                "format": None,
                "related_links": [
                    {
                        "label": "HTML",
                        "url": "https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md",
                    }
                ],
                "raw_metadata": "- Karl Seguin, `trl.:` Naing Lin Aung ([HTML](https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md))",
            },
        },
        {
            "line_number": 10,
            "source_file": "books/free-programming-books-vi.md",
            "category": "Go",
            "display_name": "HTML",
            "url": "https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md",
            "metadata": {
                "author": "Karl Seguin, `trl.:` Naing Lin Aung",
                "format": "HTML",
                "related_links": [],
                "raw_metadata": "- Karl Seguin, `trl.:` Naing Lin Aung ([HTML](https://github.com/quangnh89/the-little-go-book/blob/master/vi/go.md))",
                "parent_entry": "The Little Go Book",
            },
        },
        {
            "line_number": 15,
            "source_file": "books/free-programming-books-vi.md",
            "category": "Học máy",
            "display_name": "Đắm chìm vào Học sâu",
            "url": "https://d2l.aivivn.com",
            "metadata": {
                "author": "`trl.:` Nhóm dịch thuật Đắm chìm vào Học sâu",
                "format": "HTML",
                "related_links": [],
                "raw_metadata": "- `trl.:` Nhóm dịch thuật Đắm chìm vào Học sâu (HTML)",
            },
        },
    ]
    assert source_report["passed"], (
        f"Source catalogue verification failed: {source_report['errors']}"
    )
    assert source_report["selected_entries"] == expected_source_entries, (
        "Selected catalogue entries did not match expected names, URLs, categories, "
        "metadata, and source lines"
    )

    failure_cli = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--file",
            str(failure_catalogue),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert failure_cli.returncode != 0, (
        "The checker CLI returned success for a catalogue missing selected entries"
    )

    git_version = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=True
    ).stdout.strip()
    evidence = {
        "task_id": "R10-T022",
        "tool_versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": git_version,
        },
        "offline_redirect_fixtures": fixture_results,
        "source_verification": {
            "input": source_report["target_file"],
            "expected_selected_entries": expected_source_entries,
            "actual": source_report,
        },
        "failure_cli": {
            "input": failure_catalogue.name,
            "expected_exit_code": "non-zero",
            "actual_exit_code": failure_cli.returncode,
            "stdout": failure_cli.stdout,
            "stderr": failure_cli.stderr,
        },
        "self_test_passed": True,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "results.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("SELF-TEST PASSED: all offline redirect and source assertions succeeded.")
    print(json.dumps(source_report, indent=2, ensure_ascii=False))
    return 0


def run_live(target_file, work_dir):
    source_report = verify_selected_entries(target_file)
    if not source_report["passed"]:
        raise ValueError(f"Source catalogue verification failed: {source_report['errors']}")

    fetch = live_fetcher()
    observed_at = datetime.now(timezone.utc)
    probes = []
    for entry in source_report["selected_entries"]:
        result = probe_url(
            entry["url"],
            fetch,
            timeout=LIVE_TIMEOUT_SECONDS,
            max_redirects=LIVE_MAX_REDIRECTS,
        )
        if result["classification"] in ("ok", "redirected"):
            recommendation = {
                "action": "review_final_url",
                "url": result["final_url"],
                "reason": "The URL resolved to HTTP 200; confirm the destination is the official resource before changing the catalogue.",
            }
        else:
            recommendation = {
                "action": "retain_source_for_review",
                "url": entry["url"],
                "reason": (
                    "A single automated result is not sufficient grounds to remove "
                    f"this resource ({result['classification']})."
                ),
            }
        probes.append(
            {
                "source_entry": entry,
                "observation_date": observed_at.date().isoformat(),
                "observed_at_utc": observed_at.isoformat(),
                "timeout_seconds": LIVE_TIMEOUT_SECONDS,
                "max_redirects": LIVE_MAX_REDIRECTS,
                "result": result,
                "recommendation": recommendation,
            }
        )

    report = {
        "task_id": "R10-T022",
        "observation_date": observed_at.date().isoformat(),
        "request_policy": {
            "entry_count": len(probes),
            "concurrency": 1,
            "timeout_seconds": LIVE_TIMEOUT_SECONDS,
            "max_redirects_per_entry": LIVE_MAX_REDIRECTS,
        },
        "source_verification": source_report,
        "probes": probes,
    }
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = work_dir / "live_observations.json"
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"Saved live observations to {output_path}", file=sys.stderr)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Extract selected Vietnamese book-list links and classify bounded "
            "redirect checks."
        )
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_TARGET_FILE)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument(
        "--live",
        action="store_true",
        help="Probe only the three selected URLs sequentially with bounded requests.",
    )
    args = parser.parse_args(argv)

    try:
        if args.self_test:
            return run_self_test(args.file, args.work_dir)
        if args.live:
            return run_live(args.file, args.work_dir)
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
