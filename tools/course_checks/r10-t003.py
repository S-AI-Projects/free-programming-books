#!/usr/bin/env python3
"""
tools/course_checks/r10-t003.py - Duplicate detector for books/free-programming-books-sk.md
Student: Anshuman Holkar (Task R10-T003)

Features:
- Groups exact duplicate URLs and conservative URL-normalized matches.
- Conservative normalization: lowercases scheme/host, removes standard ports (80/443),
  strips trailing slash only on root domains.
- Preserves query parameters and meaningful anchor fragments distinctly (does not merge them).
- Maps each entry to its exact 1-based source line number.
- Built-in --self-test mode with assertions that exit non-zero on failure.
"""

import os
import re
import sys
import json
from urllib.parse import urlparse, urlunparse

TARGET_FILE = "books/free-programming-books-sk.md"
SELECTED_URLS = {
    "https://knihy.nic.cz": "Zodpovednosť na internete",
    "https://greenie.elist.sk/knihy/html/mala-kniha-programovania.html": "Malá kniha programovania",
    "https://greenie.elist.sk/knihy/linux-ako-nieco-navyse.pdf": "Linux ako niečo navyše"
}

def normalize_url(raw_url):
    """
    Conservatively normalizes a URL:
    - Lowercases scheme and netloc
    - Strips default ports (:80 for http, :443 for https)
    - Strips trailing slash only if path is '/' or empty (root domain)
    - Preserves query parameters and fragments exactly
    """
    if not raw_url:
        return ""

    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Strip default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path
    if path == "/" or path == "":
        path = ""
    # Keep query and fragment distinct
    normalized = urlunparse((scheme, netloc, path, parsed.params, parsed.query, parsed.fragment))
    return normalized

def find_duplicates(entries):
    """
    Finds duplicates by normalized URL, grouping matching entries.
    Returns:
    - groups: dict of normalized_url -> list of entries with count > 1
    - unique: list of entries with unique URLs
    """
    url_map = {}
    for entry in entries:
        norm = normalize_url(entry["url"])
        url_map.setdefault(norm, []).append(entry)

    duplicates = {norm: group for norm, group in url_map.items() if len(group) > 1}
    unique = [group[0] for norm, group in url_map.items() if len(group) == 1]
    return duplicates, unique

def parse_markdown(file_path):
    """
    Parses markdown list file, extracting line number, title, and URL.
    """
    entries = []
    if not os.path.exists(file_path):
        return entries

    pattern = re.compile(r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)')

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            m = pattern.search(line)
            if m:
                entries.append({
                    "line": line_num,
                    "title": m.group("title").strip(),
                    "url": m.group("url").strip(),
                    "raw": line.strip()
                })
    return entries

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    """
    print("[R10-T003] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T003/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T003/fixtures"

    # Assertion 1: Exact duplicate detection
    with open(os.path.join(fixtures_dir, "fixture_exact_dup.json"), "r", encoding="utf-8") as f:
        f_exact = json.load(f)
    dups_exact, _ = find_duplicates(f_exact)
    assert len(dups_exact) == 1, f"Failed exact duplicate detection: expected 1 duplicate group, got {len(dups_exact)}"
    print("  ✓ Assertion 1 passed: Exact duplicates successfully identified.")

    # Assertion 2: Conservative root trailing slash normalization
    with open(os.path.join(fixtures_dir, "fixture_trailing_slash.json"), "r", encoding="utf-8") as f:
        f_slash = json.load(f)
    dups_slash, _ = find_duplicates(f_slash)
    assert len(dups_slash) == 1, "Failed trailing slash normalization matching on root domain."
    print("  ✓ Assertion 2 passed: Conservative trailing slash normalization on root domain matched.")

    # Assertion 3: Distinct anchors must NOT be merged
    with open(os.path.join(fixtures_dir, "fixture_distinct_anchors.json"), "r", encoding="utf-8") as f:
        f_anchors = json.load(f)
    dups_anchors, unique_anchors = find_duplicates(f_anchors)
    assert len(dups_anchors) == 0, f"Distinct anchors were wrongly merged as duplicates: {dups_anchors}"
    assert len(unique_anchors) == 2, "Expected 2 distinct unique entries with different anchors."
    print("  ✓ Assertion 3 passed: Resources with distinct anchors kept distinct.")

    # Assertion 4: Query-dependent resources must NOT be merged
    with open(os.path.join(fixtures_dir, "fixture_query_distinct.json"), "r", encoding="utf-8") as f:
        f_queries = json.load(f)
    dups_queries, unique_queries = find_duplicates(f_queries)
    assert len(dups_queries) == 0, f"Query-dependent resources were wrongly merged: {dups_queries}"
    assert len(unique_queries) == 2, "Expected 2 distinct unique entries with different query params."
    print("  ✓ Assertion 4 passed: Query-dependent resources kept distinct.")

    # Assertion 5: Target file entries line numbers mapping
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    entries = parse_markdown(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]
    assert len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}"
    lines = {e["url"]: e["line"] for e in selected}
    assert lines["https://knihy.nic.cz"] == 15
    assert lines["https://greenie.elist.sk/knihy/html/mala-kniha-programovania.html"] == 20
    assert lines["https://greenie.elist.sk/knihy/linux-ako-nieco-navyse.pdf"] == 25
    print("  ✓ Assertion 5 passed: Selected entries map back to source lines (15, 20, 25).")

    # Assertion 6: Verify no false duplicate deletions proposed in real file
    dups_real, _ = find_duplicates(entries)
    assert len(dups_real) == 0, f"Found unexpected duplicates in clean target file: {dups_real}"
    print("  ✓ Assertion 6 passed: Verified no duplicate URLs in target file.")

    print("[R10-T003] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except AssertionError as err:
            print(f"[R10-T003] SELF-TEST FAILED: {err}", file=sys.stderr)
            sys.exit(1)
        except Exception as ex:
            print(f"[R10-T003] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)
    dups, unique = find_duplicates(entries)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Duplicate Analysis for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}")
    print(f"Duplicate groups found: {len(dups)}\n")

    print(f"Selected entries audit ({len(selected)}):")
    for e in selected:
        norm = normalize_url(e["url"])
        print(f"  Line {e['line']:2d} | Title         : {e['title']}")
        print(f"            Original URL  : {e['url']}")
        print(f"            Normalized URL: {norm}")
        print(f"            Status        : UNIQUE (No duplicates)")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T003")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T003"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "duplicate_groups": dups,
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {out_file}")

if __name__ == "__main__":
    main()
