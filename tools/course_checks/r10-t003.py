#!/usr/bin/env python3
"""
tools/course_checks/r10-t003.py - Duplicate detector for books/free-programming-books-sk.md
Student: Anshuman Holkar (Task R10-T003)

Features:
- Groups exact duplicate URLs and conservative URL-normalized matches.
- Conservative normalization: lowercases scheme/host, removes standard ports (80/443),
  strips trailing slash only on root domains.
- Preserves query parameters and meaningful anchor fragments distinctly (does not merge them).
- Emits structured proposed_deletions with manual review tracking.
- Compares field-by-field against expected_selected.json in self-test.
- Built-in --self-test mode that works under python3 -O with clear failure messages.
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

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T003] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

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

def build_proposed_deletions(duplicates):
    """
    Builds a list of proposed deletion pairs with manual review tracking.
    """
    proposed = []
    for norm_url, group in duplicates.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                proposed.append({
                    "line_a": group[i]["line"],
                    "title_a": group[i]["title"],
                    "line_b": group[j]["line"],
                    "title_b": group[j]["title"],
                    "normalized_url": norm_url,
                    "manual_review": "PROPOSED_DUPLICATE_REMOVE_SECONDARY"
                })
    return proposed

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
    Works under python3 -O.
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
    check(len(dups_exact) == 1, f"Failed exact duplicate detection: expected 1 duplicate group, got {len(dups_exact)}")
    deletions = build_proposed_deletions(dups_exact)
    check(len(deletions) == 1, "Failed proposed deletions generation")
    print("  ✓ Assertion 1 passed: Exact duplicates successfully identified and proposed deletion generated.")

    # Assertion 2: Conservative root trailing slash normalization
    with open(os.path.join(fixtures_dir, "fixture_trailing_slash.json"), "r", encoding="utf-8") as f:
        f_slash = json.load(f)
    dups_slash, _ = find_duplicates(f_slash)
    check(len(dups_slash) == 1, "Failed trailing slash normalization matching on root domain.")
    print("  ✓ Assertion 2 passed: Conservative trailing slash normalization on root domain matched.")

    # Assertion 3: Distinct anchors must NOT be merged
    with open(os.path.join(fixtures_dir, "fixture_distinct_anchors.json"), "r", encoding="utf-8") as f:
        f_anchors = json.load(f)
    dups_anchors, unique_anchors = find_duplicates(f_anchors)
    check(len(dups_anchors) == 0, f"Distinct anchors were wrongly merged as duplicates: {dups_anchors}")
    check(len(unique_anchors) == 2, "Expected 2 distinct unique entries with different anchors.")
    print("  ✓ Assertion 3 passed: Resources with distinct anchors kept distinct.")

    # Assertion 4: Query-dependent resources must NOT be merged
    with open(os.path.join(fixtures_dir, "fixture_query_distinct.json"), "r", encoding="utf-8") as f:
        f_queries = json.load(f)
    dups_queries, unique_queries = find_duplicates(f_queries)
    check(len(dups_queries) == 0, f"Query-dependent resources were wrongly merged: {dups_queries}")
    check(len(unique_queries) == 2, "Expected 2 distinct unique entries with different query params.")
    print("  ✓ Assertion 4 passed: Query-dependent resources kept distinct.")

    # Assertion 5: Target file entries line numbers mapping and expected_selected.json comparison
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    entries = parse_markdown(repo_file)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]
    check(len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}")
    
    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_list = json.load(f)
    expected_map = {item["url"]: item for item in expected_list}

    dups_real, _ = find_duplicates(entries)

    for e in selected:
        exp = expected_map.get(e["url"])
        check(exp is not None, f"Unexpected selected URL: {e['url']}")
        check(e["line"] == exp["line"], f"Line mismatch for {e['title']}: expected {exp['line']}, got {e['line']}")
        check(e["title"] == exp["title"], f"Title mismatch: expected {exp['title']}, got {e['title']}")
        computed_norm = normalize_url(e["url"])
        check(computed_norm == exp["normalized_url"], f"Normalized URL mismatch: expected {exp['normalized_url']}, got {computed_norm}")
        computed_status = "DUPLICATE" if computed_norm in dups_real else "UNIQUE"
        check(computed_status == exp["status"], f"Status mismatch: expected {exp['status']}, got {computed_status}")
    print("  ✓ Assertion 5 passed: Selected entries map to exact source lines (15, 20, 25) matching expected_selected.json.")

    print("[R10-T003] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T003] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)
    dups, unique = find_duplicates(entries)
    proposed_deletions = build_proposed_deletions(dups)
    selected = [e for e in entries if e["url"] in SELECTED_URLS]

    print(f"Duplicate Analysis for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}")
    print(f"Duplicate groups found: {len(dups)}\n")

    print(f"Selected entries audit ({len(selected)}):")
    for e in selected:
        norm = normalize_url(e["url"])
        computed_status = "DUPLICATE" if norm in dups else "UNIQUE (No duplicates)"
        print(f"  Line {e['line']:2d} | Title         : {e['title']}")
        print(f"            Original URL  : {e['url']}")
        print(f"            Normalized URL: {norm}")
        print(f"            Status        : {computed_status}")
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
            "proposed_deletions": proposed_deletions,
            "selected_entries": selected
        }, f, indent=2, ensure_ascii=False)
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
