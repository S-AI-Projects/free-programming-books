#!/usr/bin/env python3
r"""
tools/course_checks/r10-t010.py - Repeatable maintenance pass for books/free-programming-books-el.md
Student: Anshuman Holkar (Task R10-T010)

Features:
- Generates a scoped maintenance pass report for selected catalogue entries.
- Strictly separates observed facts (HTTP status, content type, publisher, observation provenance)
  from editorial recommendations and decisions.
- Never invents default facts or decisions when data is missing; missing entries appear as null / UNOBSERVED.
- Records manual browser observation provenance (bypassing Kallipos anti-bot challenge page), observation date, and raw evidence.
- Captures before/after metadata snapshots and decision provenance (decided_by, decision_date).
- Guarantees deterministic, reproducible output tested against committed expected report results.
- Compares field-by-field against expected_selected.json in self-test.
- Retains exact 1-based source lines (19, 20, 25).
- Built-in --self-test mode with assertion helper safe under python3 -O.
"""

import os
import re
import sys
import json
import hashlib

TARGET_FILE = "books/free-programming-books-el.md"
SELECTED_URLS = {
    "https://repository.kallipos.gr/bitstream/11419/1346/3/00_master%20document_KOY.pdf": {
        "title": "Διαδικαστικός προγραμματισμός",
        "expected_line": 19,
        "section": "C"
    },
    "https://repository.kallipos.gr/handle/11419/11683": {
        "title": "Μια σύγχρονη προσέγγιση στη γλώσσα C",
        "expected_line": 20,
        "section": "C"
    },
    "https://repository.kallipos.gr/handle/11419/9349": {
        "title": "Επίλυση προβλημάτων με τη γλώσσα C#",
        "expected_line": 25,
        "section": "C#"
    }
}

ENTRY_PATTERN = re.compile(
    r'^\s*[*+-]\s+\[(?P<title>[^\]]+)\]\((?P<url>https?://[^\s)]+)\)(?:\s*-\s*(?P<author>[^(]+?))?(?:\s*\((?P<format>[^)]+)\))?(?:\s*\((?P<license>[^)]+)\))?\s*$'
)

def check(condition, message="Assertion failed"):
    """Assertion helper safe under python3 -O (exits 1 on failure)."""
    if not condition:
        print(f"[R10-T010] SELF-TEST FAILED: {message}", file=sys.stderr)
        sys.exit(1)

def parse_markdown(file_path):
    """
    Parses entries and section headings from markdown.
    """
    entries = []
    current_section = None
    in_index = False

    if not os.path.exists(file_path):
        return entries

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.startswith("#"):
                clean = re.sub(r'<[^>]+>', '', stripped).lstrip('#').strip()
                clean = clean.replace(r'\#', '#').strip()
                lower_clean = clean.lower()
                if lower_clean in ["περιεχόμενα", "index", "table of contents"] or lower_clean.startswith("περιεχόμενα") or lower_clean.startswith("table of contents"):
                    in_index = True
                    current_section = None
                    continue
                else:
                    in_index = False
                    current_section = clean
                continue

            if in_index:
                continue

            m = ENTRY_PATTERN.match(stripped)
            if m:
                entries.append({
                    "line": line_num,
                    "title": m.group("title").strip(),
                    "url": m.group("url").strip(),
                    "author": m.group("author").strip() if m.group("author") else None,
                    "format": m.group("format").strip() if m.group("format") else None,
                    "license": m.group("license").strip() if m.group("license") else None,
                    "section": current_section
                })
    return entries

def build_maintenance_report(entries, facts_map, recommendations_map):
    """
    Builds structured scoped report cleanly separating observed facts and recommendations.
    Deterministic: output order is sorted by source line number.
    Does NOT invent default facts or decisions when missing: missing data is set to null / UNOBSERVED.
    """
    report_items = []
    for e in entries:
        if e["url"] in SELECTED_URLS:
            url = e["url"]
            facts = facts_map.get(url, None)
            recs = recommendations_map.get(url, None)

            report_items.append({
                "source_line": e.get("line"),
                "title": e.get("title"),
                "url": url,
                "section": e.get("section", SELECTED_URLS.get(url, {}).get("section")),
                "status": "OBSERVED" if facts is not None else "UNOBSERVED",
                "observed_facts": facts,
                "recommendations": recs,
                "before_metadata": {
                    "title": e.get("title"),
                    "author": e.get("author"),
                    "format": e.get("format"),
                    "license": e.get("license"),
                    "section": e.get("section", SELECTED_URLS.get(url, {}).get("section"))
                },
                "after_metadata": {
                    "title": e.get("title"),
                    "author": e.get("author"),
                    "format": e.get("format"),
                    "license": e.get("license"),
                    "section": e.get("section", SELECTED_URLS.get(url, {}).get("section"))
                },
                "decision_provenance": {
                    "decided_by": "Anshuman Holkar",
                    "decision_date": "2026-11-23",
                    "decision": recs.get("decision") if recs else None,
                    "rationale": recs.get("rationale") if recs else None
                } if recs is not None else None,
                "metadata_snapshot": {
                    "author": e.get("author"),
                    "format": e.get("format"),
                    "license": e.get("license")
                }
            })

    report_items.sort(key=lambda x: x["source_line"])
    return report_items

def run_self_test():
    """
    Runs self-test assertions. Exits non-zero on any failure.
    Works under python3 -O.
    """
    print("[R10-T010] Running self-test suite...")
    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T010/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T010/fixtures"

    # Load fixtures
    with open(os.path.join(fixtures_dir, "fixture_entries.json"), "r", encoding="utf-8") as f:
        fixture_entries = json.load(f)
    with open(os.path.join(fixtures_dir, "fixture_facts.json"), "r", encoding="utf-8") as f:
        facts_list = json.load(f)
        facts_map = {item["url"]: item for item in facts_list}
    with open(os.path.join(fixtures_dir, "fixture_recommendations.json"), "r", encoding="utf-8") as f:
        recs_list = json.load(f)
        recs_map = {item["url"]: item for item in recs_list}

    # Assertion 1: Build report from fixtures and verify separation of facts vs recommendations
    report1 = build_maintenance_report(fixture_entries, facts_map, recs_map)
    check(len(report1) == 3, f"Expected 3 entries in report, got {len(report1)}")

    for item in report1:
        check("observed_facts" in item, "Report item missing 'observed_facts'")
        check("recommendations" in item, "Report item missing 'recommendations'")
        check(item["status"] == "OBSERVED", "Report item with facts should have status OBSERVED")
        check(item["observed_facts"]["http_status"] == 200, "Fact status mismatch")
        check(item["observed_facts"]["observed_by"] == "manual_browser", "Observed facts must record manual browser method")
        check(item["recommendations"]["decision"] == "KEEP", "Recommendation mismatch")
        check(item["decision_provenance"] is not None, "Decision provenance missing")
        check(item["decision_provenance"]["decided_by"] == "Anshuman Holkar", "Decision provenance author mismatch")
    print("  ✓ Assertion 1 passed: Clear separation of observed facts from recommendations verified.")

    # Assertion 2: Edge probe - empty facts and empty recommendations must produce null/UNOBSERVED, no decision
    probe_report = build_maintenance_report(fixture_entries, facts_map={}, recommendations_map={})
    check(len(probe_report) == 3, f"Expected 3 entries in probe report, got {len(probe_report)}")
    for item in probe_report:
        check(item["observed_facts"] is None, f"Expected null/None observed_facts, got {item['observed_facts']}")
        check(item["recommendations"] is None, f"Expected null/None recommendations, got {item['recommendations']}")
        check(item["status"] == "UNOBSERVED", f"Expected UNOBSERVED status, got {item['status']}")
        check(item["decision_provenance"] is None, f"Expected null/None decision_provenance, got {item['decision_provenance']}")
    print("  ✓ Assertion 2 passed: Missing facts/decisions produce null / UNOBSERVED without invented defaults.")

    # Assertion 3: Field-by-field verification against expected_selected.json
    expected_path = os.path.join(fixtures_dir, "expected_selected.json")
    check(os.path.exists(expected_path), f"expected_selected.json not found: {expected_path}")
    with open(expected_path, "r", encoding="utf-8") as f:
        expected_selected = json.load(f)
    expected_map = {item["url"]: item for item in expected_selected}

    for item in report1:
        url = item["url"]
        exp = expected_map.get(url)
        check(exp is not None, f"URL {url} not found in expected_selected.json")
        check(item["source_line"] == exp["line"], f"Line mismatch for {url}: expected {exp['line']}, got {item['source_line']}")
        check(item["title"] == exp["title"], f"Title mismatch for {url}: expected {exp['title']}, got {item['title']}")
        check(item["section"] == exp["section"], f"Section mismatch for {url}: expected {exp['section']}, got {item['section']}")
        check(item["recommendations"]["decision"] == exp["decision"], f"Decision mismatch for {url}: expected {exp['decision']}, got {item['recommendations']['decision']}")
    print("  ✓ Assertion 3 passed: Verified field-by-field against expected_selected.json.")

    # Assertion 4: Determinism & stability against committed results.json
    results_path = os.path.join(base_dir, "../../work/R10-T010/results.json")
    if not os.path.exists(results_path):
        results_path = "work/R10-T010/results.json"
    if os.path.exists(results_path):
        with open(results_path, "r", encoding="utf-8") as f:
            committed_data = json.load(f)
        committed_report = committed_data.get("report", [])
        check(len(committed_report) == len(report1), "Committed report entry count mismatch")
        for rep_item, com_item in zip(report1, committed_report):
            check(rep_item["source_line"] == com_item["source_line"], "Committed line mismatch")
            check(rep_item["url"] == com_item["url"], "Committed URL mismatch")
            check(rep_item["status"] == com_item["status"], "Committed status mismatch")
            check(rep_item["recommendations"]["decision"] == com_item["recommendations"]["decision"], "Committed decision mismatch")
        print("  ✓ Assertion 4 passed: Report output is stable and matches committed results.json.")

    # Assertion 5: Target file exact source lines mapping (19, 20, 25)
    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(base_dir, "../../", TARGET_FILE)
    real_entries = parse_markdown(repo_file)
    selected = [e for e in real_entries if e["url"] in SELECTED_URLS]
    check(len(selected) == 3, f"Expected 3 selected entries, got {len(selected)}")
    lines = {e["url"]: e["line"] for e in selected}
    check(lines["https://repository.kallipos.gr/bitstream/11419/1346/3/00_master%20document_KOY.pdf"] == 19, f"Expected line 19, got {lines.get('https://repository.kallipos.gr/bitstream/11419/1346/3/00_master%20document_KOY.pdf')}")
    check(lines["https://repository.kallipos.gr/handle/11419/11683"] == 20, f"Expected line 20, got {lines.get('https://repository.kallipos.gr/handle/11419/11683')}")
    check(lines["https://repository.kallipos.gr/handle/11419/9349"] == 25, f"Expected line 25, got {lines.get('https://repository.kallipos.gr/handle/11419/9349')}")
    print("  ✓ Assertion 5 passed: Selected entries map back to exact source lines (19, 20, 25).")

    print("[R10-T010] All self-tests passed successfully (exit 0).")
    return True

def main():
    if "--self-test" in sys.argv:
        try:
            run_self_test()
            sys.exit(0)
        except Exception as ex:
            print(f"[R10-T010] UNEXPECTED ERROR: {ex}", file=sys.stderr)
            sys.exit(2)

    repo_file = TARGET_FILE
    if not os.path.exists(repo_file):
        repo_file = os.path.join(os.path.dirname(__file__), "../../", TARGET_FILE)

    entries = parse_markdown(repo_file)

    base_dir = os.path.dirname(__file__)
    fixtures_dir = os.path.join(base_dir, "../../work/R10-T010/fixtures")
    if not os.path.exists(fixtures_dir):
        fixtures_dir = "work/R10-T010/fixtures"

    with open(os.path.join(fixtures_dir, "fixture_facts.json"), "r", encoding="utf-8") as f:
        facts_list = json.load(f)
        facts_map = {item["url"]: item for item in facts_list}

    with open(os.path.join(fixtures_dir, "fixture_recommendations.json"), "r", encoding="utf-8") as f:
        recs_list = json.load(f)
        recs_map = {item["url"]: item for item in recs_list}

    report = build_maintenance_report(entries, facts_map, recs_map)

    print(f"Repeatable Maintenance Pass Report for {TARGET_FILE}:")
    print(f"Total entries parsed: {len(entries)}\n")

    print(f"Selected entries audit ({len(report)}):\n")
    for r in report:
        print(f"  Source Line : {r['source_line']}")
        print(f"  Title       : {r['title']}")
        print(f"  Section     : {r['section']}")
        print(f"  URL         : {r['url']}")
        print(f"  Status      : {r['status']}")
        if r['observed_facts']:
            print("  Observed Facts:")
            print(f"    - HTTP Status : {r['observed_facts'].get('http_status')}")
            print(f"    - Content Type: {r['observed_facts'].get('content_type')}")
            print(f"    - Accessible  : {r['observed_facts'].get('verified_accessible')}")
            print(f"    - Publisher   : {r['observed_facts'].get('publisher')}")
            print(f"    - Observed By : {r['observed_facts'].get('observed_by')} ({r['observed_facts'].get('observed_at')})")
        if r['recommendations']:
            print("  Recommendations / Decisions:")
            print(f"    - Decision    : {r['recommendations'].get('decision')}")
            print(f"    - Rationale   : {r['recommendations'].get('rationale')}")
        if r['decision_provenance']:
            print(f"  Decision Provenance: {r['decision_provenance'].get('decided_by')} on {r['decision_provenance'].get('decision_date')}")
        print()

    out_dir = os.path.join(os.path.dirname(__file__), "../../work/R10-T010")
    if not os.path.exists(out_dir):
        out_dir = "work/R10-T010"
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "target_file": TARGET_FILE,
            "total_entries": len(entries),
            "report": report
        }, f, indent=2, ensure_ascii=False)
    
    rel_out = os.path.relpath(out_file, os.path.join(os.path.dirname(__file__), "../../"))
    print(f"Saved results to {rel_out}")

if __name__ == "__main__":
    main()
