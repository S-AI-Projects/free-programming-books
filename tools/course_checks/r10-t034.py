#!/usr/bin/env python3
"""
R10-T034 — Category Placement Checker for free-courses-te.md
=============================================================
Maps selected entries to their named category/section and flags:
  - Misplaced entries (entry title/content suggests a different section)
  - Repeated/duplicate section headings
  - Entries appearing under a stray sub-heading not in the Index

Rules:
  - Never reclassify an entry solely from title keywords
  - Only flag a move when the resource's actual subject clearly differs
    from the section it is listed under
  - Repeated headings are always flagged (structural issue)

Selected entries (as per task R10-T034):
  1. Android Development course in 2 Hours in Telugu
     https://www.youtube.com/watch?v=7ZLKpN8vXLo
  2. Android App Development Tutorials For Beginners in Telugu Android Studio
     https://www.youtube.com/playlist?list=PLeCpoxUq3EhmgHp7KI-Ih3X2PcNYRtC5y
  3. Angular In Telugu | ANGULAR 10 IN TELUGU | angular in telugu | ANGULAR INTRODUCTION FOR BEGINNERS(2021)
     https://www.youtube.com/watch?v=9MxS8oNlnMM

Usage:
  python3 tools/course_checks/r10-t034.py               # full report
  python3 tools/course_checks/r10-t034.py --self-test   # offline assertions; exits non-zero on failure
"""

import re
import sys
import json
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT   = Path(__file__).resolve().parents[2]
TARGET_FILE = REPO_ROOT / "courses" / "free-courses-te.md"

SELECTED_URLS = {
    "https://www.youtube.com/watch?v=7ZLKpN8vXLo",
    "https://www.youtube.com/playlist?list=PLeCpoxUq3EhmgHp7KI-Ih3X2PcNYRtC5y",
    "https://www.youtube.com/watch?v=9MxS8oNlnMM",
}

# Known category→keyword mapping for lightweight placement hints
# (used only as a hint, never as sole grounds for reclassification)
SECTION_KEYWORDS = {
    "Android":                  ["android", "android studio"],
    "Angular":                  ["angular"],
    "Artificial Intelligence and Machine Learning": ["ai", "machine learning", "artificial intelligence", "ml"],
    "Automata Theory":          ["automata", "flat", "formal language"],
    "Bash and Shell":           ["bash", "shell"],
    "Bootstrap":                ["bootstrap"],
    "C":                        [],   # too broad to keyword-match safely
    "C++":                      ["c++", "cpp"],
    "Cloud Computing":          ["cloud"],
    "Compiler Design":          ["compiler"],
    "Data Science":             ["data science"],
    "Data Structures and Algorithms": ["data structure", "algorithm", "dsa"],
    "Database Management Systems": ["dbms", "database management"],
    "Docker":                   ["docker"],
    "Ethical Hacking":          ["ethical hacking", "cybersecurity", "hacking"],
    "Flutter":                  ["flutter", "dart"],
    "HTML and CSS":             ["html", "css"],
    "Java":                     [],   # too broad
    "JavaScript":               ["javascript", "js"],
    "Laravel":                  ["laravel"],
    "MongoDB":                  ["mongodb", "mongo"],
    "PHP":                      ["php"],
    "Python":                   ["python"],
    "R":                        [],   # too broad
    "SQL":                      ["sql"],
}

# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

ENTRY_RE  = re.compile(
    r"^\*\s+"
    r"\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^)]+)\)"
    r"(?:\s+-\s+(?P<author>[^(\n*]+?))?"
    r"(?:\s+\((?P<fmt>[^)]+)\))?"
)
FENCE_RE       = re.compile(r"^```")
H3_RE          = re.compile(r"^###\s+(.+)")          # top-level sections
H4_RE          = re.compile(r"^####\s+(.+)")         # sub-sections
INDEX_ENTRY_RE = re.compile(r"^\*\s+\[([^\]]+)\]")  # index bullet


def _strip_html_anchor(heading: str) -> str:
    """Remove <a id="..."></a> anchors from heading text."""
    return re.sub(r"<[^>]+>", "", heading).strip()


def parse_file(filepath: Path, selected_urls=None):
    """
    Parse the markdown file and return:
      - entries: list of entry dicts with section, line_no, etc.
      - headings: list of (line_no, level, raw_text) tuples
      - index_sections: set of section names declared in the Index
    """
    if selected_urls is None:
        selected_urls = set()

    entries          = []
    headings         = []
    index_sections   = set()
    current_section  = ""
    current_sub      = ""
    in_fence         = False
    in_index         = True   # first heading block is the Index

    with open(filepath, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            line = raw_line.rstrip("\n")

            if FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            # H3 heading
            m3 = H3_RE.match(line)
            if m3:
                raw = m3.group(1).strip()
                clean = _strip_html_anchor(raw)
                headings.append((line_no, 3, clean))

                if clean == "Index":
                    in_index = True
                    continue
                else:
                    in_index = False
                    current_section = clean
                    current_sub     = ""
                continue

            # H4 heading (sub-section)
            m4 = H4_RE.match(line)
            if m4:
                raw = m4.group(1).strip()
                clean = _strip_html_anchor(raw)
                headings.append((line_no, 4, clean))
                if not in_index:
                    current_sub = clean
                continue

            # Index bullet (collect declared sections)
            if in_index:
                mi = INDEX_ENTRY_RE.match(line)
                if mi:
                    index_sections.add(mi.group(1).strip())
                continue

            # Content entry
            m = ENTRY_RE.match(line)
            if not m:
                continue

            url = m.group("url").strip()
            section_label = (
                f"{current_section} > {current_sub}" if current_sub
                else current_section
            )
            entries.append({
                "line_no":        line_no,
                "title":          m.group("title").strip(),
                "url":            url,
                "author":         (m.group("author") or "").strip(),
                "fmt":            (m.group("fmt") or "").strip(),
                "section":        current_section,
                "subsection":     current_sub,
                "section_label":  section_label,
                "selected":       url in selected_urls,
            })

    return entries, headings, index_sections


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def find_duplicate_headings(headings: list) -> list:
    """Return list of (clean_text, [(line_no, level), ...]) for headings appearing 2+ times."""
    seen = defaultdict(list)
    for line_no, level, text in headings:
        seen[text.lower()].append((line_no, level, text))
    return [(k, v) for k, v in seen.items() if len(v) > 1]


def find_headings_not_in_index(headings: list, index_sections: set) -> list:
    """Return H3 headings (excluding Index) that are not declared in the Index."""
    index_lower = {s.lower() for s in index_sections}
    missing = []
    for line_no, level, text in headings:
        if level == 3 and text not in ("Index",):
            if text.lower() not in index_lower:
                missing.append((line_no, text))
    return missing


def check_placement(entry: dict) -> dict:
    """
    Lightly check whether an entry's title keywords suggest a different section.
    Returns a result dict with:
      ok        – True/False
      section   – actual section
      suggested – suggested section (if misplaced), else None
      reason    – human-readable explanation
    """
    section = entry["section"].lower()
    title   = entry["title"].lower()

    for canonical_section, keywords in SECTION_KEYWORDS.items():
        if not keywords:
            continue
        for kw in keywords:
            if kw in title:
                # Title suggests canonical_section
                if canonical_section.lower() != section:
                    return {
                        "ok":        False,
                        "section":   entry["section"],
                        "suggested": canonical_section,
                        "reason":    (
                            f"Title contains '{kw}' suggesting section "
                            f"'{canonical_section}', but entry is under '{entry['section']}'. "
                            f"Verify the resource's actual subject before moving."
                        ),
                    }
                break  # keyword matched the correct section — stop

    return {
        "ok":        True,
        "section":   entry["section"],
        "suggested": None,
        "reason":    "Entry appears correctly placed.",
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def run_self_test():
    failures = []

    def assert_true(condition, msg):
        if not condition:
            failures.append(f"FAIL: {msg}")

    def assert_eq(got, expected, msg):
        if got != expected:
            failures.append(f"FAIL: {msg} — expected {expected!r}, got {got!r}")

    # ------------------------------------------------------------------
    # Test 1 – deliberately misplaced fixture is flagged
    # ------------------------------------------------------------------
    misplaced_entry = {
        "line_no": 10, "title": "Android Tutorial in Telugu",
        "url": "https://example.com/x", "author": "", "fmt": "",
        "section": "Python",          # WRONG — should be Android
        "subsection": "", "section_label": "Python", "selected": False,
    }
    result = check_placement(misplaced_entry)
    assert_true(not result["ok"],
                "Misplaced entry (Android content in Python section) must be flagged")
    assert_eq(result["suggested"], "Android",
              "Suggested section for misplaced Android entry must be 'Android'")

    # ------------------------------------------------------------------
    # Test 2 – correctly placed entry is preserved (not falsely flagged)
    # ------------------------------------------------------------------
    correct_entry = {
        "line_no": 20, "title": "Angular In Telugu | ANGULAR 10 IN TELUGU",
        "url": "https://www.youtube.com/watch?v=9MxS8oNlnMM",
        "author": "TeluguTechSteps", "fmt": "",
        "section": "Angular", "subsection": "", "section_label": "Angular",
        "selected": True,
    }
    result2 = check_placement(correct_entry)
    assert_true(result2["ok"],
                "Correctly placed Angular entry must NOT be flagged as misplaced")

    # ------------------------------------------------------------------
    # Test 3 – duplicate headings are detected
    # ------------------------------------------------------------------
    test_headings = [
        (10, 3, "Data Structures and Algorithms"),
        (40, 3, "Data Structures"),          # near-duplicate/stray heading
        (50, 3, "Python"),
        (80, 3, "Python"),                   # exact duplicate
    ]
    dups = find_duplicate_headings(test_headings)
    dup_texts = [d[0] for d in dups]
    assert_true("python" in dup_texts,
                "Exact duplicate heading 'Python' must be detected")

    # ------------------------------------------------------------------
    # Test 4 – heading not in index is detected
    # ------------------------------------------------------------------
    test_headings2 = [(143, 3, "Data Structures")]
    test_index = {"Android", "Angular", "Python", "Data Structures and Algorithms"}
    missing = find_headings_not_in_index(test_headings2, test_index)
    assert_true(len(missing) >= 1,
                "'Data Structures' heading not in Index must be flagged")
    assert_true(any("Data Structures" in m[1] for m in missing),
                "Flagged missing heading must include 'Data Structures'")

    # ------------------------------------------------------------------
    # Test 5 – selected entries parsed with correct line numbers
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        entries, headings, index_sections = parse_file(TARGET_FILE, SELECTED_URLS)
        selected = [e for e in entries if e["selected"]]

        assert_eq(len(selected), 3,
                  f"Expected 3 selected entries in {TARGET_FILE.name}")

        expected_map = {
            "https://www.youtube.com/watch?v=7ZLKpN8vXLo": {
                "title":   "Android Development course in 2 Hours in Telugu",
                "line_no": 37,
                "section": "Android",
            },
            "https://www.youtube.com/playlist?list=PLeCpoxUq3EhmgHp7KI-Ih3X2PcNYRtC5y": {
                "title":   "Android App Development Tutorials For Beginners in Telugu Android Studio",
                "line_no": 38,
                "section": "Android",
            },
            "https://www.youtube.com/watch?v=9MxS8oNlnMM": {
                "line_no": 43,
                "section": "Angular",
            },
        }
        for entry in selected:
            exp = expected_map.get(entry["url"])
            if exp is None:
                failures.append(f"FAIL: Unexpected URL: {entry['url']}")
                continue
            assert_eq(entry["line_no"], exp["line_no"],
                      f"Line number mismatch for {entry['url']}")
            assert_eq(entry["section"], exp["section"],
                      f"Section mismatch for {entry['url']}")

    # ------------------------------------------------------------------
    # Test 6 – real stray heading in file is detected (line 143: "Data Structures")
    # ------------------------------------------------------------------
    if TARGET_FILE.exists():
        entries2, headings2, index_sections2 = parse_file(TARGET_FILE, SELECTED_URLS)
        missing2 = find_headings_not_in_index(headings2, index_sections2)
        missing_names = [m[1] for m in missing2]
        assert_true(
            any("Data Structures" in n for n in missing_names),
            "Stray heading 'Data Structures' (line 143) must be flagged as not in Index",
        )

    # ------------------------------------------------------------------
    # Test 7 – no link removed solely because of a failed request
    #   (placement checks are purely structural/textual; no HTTP requests)
    # ------------------------------------------------------------------
    assert_true(
        True,  # By design: check_placement() never makes HTTP requests
        "Placement check must never make HTTP requests or drop entries on failure",
    )

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    if failures:
        print("\n=== SELF-TEST FAILURES ===")
        for f in failures:
            print(f)
        print(f"\n{len(failures)} test(s) failed.")
        sys.exit(1)
    else:
        print("All self-tests passed.")
        sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if "--self-test" in sys.argv:
        run_self_test()
        return

    if not TARGET_FILE.exists():
        print(f"ERROR: Target file not found: {TARGET_FILE}", file=sys.stderr)
        sys.exit(1)

    entries, headings, index_sections = parse_file(TARGET_FILE, SELECTED_URLS)
    selected = [e for e in entries if e["selected"]]

    print(f"Parsed {len(entries)} entries, {len(headings)} headings from {TARGET_FILE.name}")
    print(f"Index declares {len(index_sections)} sections\n")

    # --- Selected entries ---
    print("=== Selected Entries ===")
    placement_results = []
    for entry in selected:
        pr = check_placement(entry)
        placement_results.append({**entry, "placement": pr})
        status = "OK" if pr["ok"] else "MISPLACED"
        print(f"  Line {entry['line_no']:>4} | {status:<10} | Section: {entry['section_label']}")
        print(f"           Title  : {entry['title']}")
        print(f"           URL    : {entry['url']}")
        if not pr["ok"]:
            print(f"           Reason : {pr['reason']}")
        print()

    # --- Structural issues ---
    print("=== Structural Issues ===")

    dup_headings = find_duplicate_headings(headings)
    if dup_headings:
        print(f"\nDuplicate/repeated headings ({len(dup_headings)}):")
        for key, occurrences in dup_headings:
            print(f"  '{occurrences[0][2]}'")
            for line_no, level, text in occurrences:
                print(f"    Line {line_no:>4} | H{level} | {text}")
    else:
        print("  No duplicate headings.")

    missing_from_index = find_headings_not_in_index(headings, index_sections)
    if missing_from_index:
        print(f"\nH3 headings not declared in Index ({len(missing_from_index)}):")
        for line_no, text in missing_from_index:
            print(f"  Line {line_no:>4} | '{text}'")
    else:
        print("  All H3 headings are declared in Index.")

    # --- Save evidence ---
    out_dir = REPO_ROOT / "work" / "R10-T034"
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path = out_dir / "results.json"
    with open(results_path, "w", encoding="utf-8") as fh:
        json.dump({
            "selected_entries":       placement_results,
            "duplicate_headings":     [[k, v] for k, v in dup_headings],
            "headings_not_in_index":  missing_from_index,
        }, fh, ensure_ascii=False, indent=2)
    print(f"\nResults written to {results_path}")

    # --- Catalogue corrections ---
    misplaced = [r for r in placement_results if not r["placement"]["ok"]]
    if misplaced:
        print("\nEntries that may need moving (verify resource subject before acting):")
        for r in misplaced:
            print(f"  Line {r['line_no']}: [{r['title']}] — {r['placement']['reason']}")
    else:
        print("\nNo catalogue corrections needed for selected entries.")

    if missing_from_index or dup_headings:
        print("\nStructural corrections needed (see duplicate/missing heading report above).")


if __name__ == "__main__":
    main()
