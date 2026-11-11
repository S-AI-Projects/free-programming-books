#!/usr/bin/env python3
"""R10-T054: map entries to their category heading and flag misplaced or repeated headings
in books/free-programming-books-langs.md. Nothing is reclassified from keywords alone:
every proposed move needs the resource's actual subject, cited by a person."""
import json, re, sys
from collections import defaultdict

CATALOGUE = "books/free-programming-books-langs.md"
SELECTED = ["SAP AWS Technical Documentation", "SAP Code Style Guides", "A Guide to Ada for C"]
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*(?P<meta>.*))?$")


def slug(text):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def parse(lines):
    """Return (entries, headings). Each entry carries its category and the heading line it sits under."""
    entries, headings, cur, fence = [], [], None, None
    for n, line in enumerate(lines, start=1):
        f = FENCE.match(line)
        if f:
            if fence is None:
                fence = f.group(1)
            elif f.group(1) == fence:
                fence = None
            continue
        if fence:
            continue
        h = HEADING.match(line)
        if h:
            cur = {"line": n, "level": len(h.group(1)), "text": h.group(2)}
            headings.append(cur)
            continue
        m = ENTRY.match(line)
        if m:
            entries.append({"line": n, "name": m["name"], "url": m["url"],
                            "meta": (m["meta"] or "").strip(),
                            "category": cur["text"] if cur else None,
                            "heading_line": cur["line"] if cur else None})
    return entries, headings


def repeated_headings(headings):
    """Same heading text appearing more than once at the same level."""
    seen = defaultdict(list)
    for h in headings:
        seen[(h["level"], slug(h["text"]))].append(h)
    out = []
    for hs in seen.values():
        if len(hs) > 1:
            out.append({"kind": "repeated_heading", "text": hs[0]["text"],
                        "lines": [h["line"] for h in hs], "action": "manual_review"})
    return out


def check_placement(entries, expected):
    """expected maps a URL to the category a human has confirmed from the resource's subject.
    Entries not in the map are left alone, so valid categories are preserved."""
    findings = []
    for e in entries:
        want = expected.get(e["url"])
        if want is None:
            continue
        ok = slug(e["category"] or "") == slug(want)
        findings.append({"kind": "ok" if ok else "misplaced", "line": e["line"], "name": e["name"],
                         "url": e["url"], "current": e["category"], "expected": want,
                         "action": "keep" if ok else "manual_review",
                         "evidence": "subject confirmed by reviewer" if not ok else ""})
    return findings


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def fixture_lines():
    f = chr(96) * 3
    return [
        "### Python",
        "* [Learn Py](https://example.com/py) - A",
        "### Ada",
        "* [Ada Guide](https://example.com/ada) - B",
        "### Ada",
        "* [Fake Book](https://example.com/fake) - C",
        "### Rust",
        "* [Rust Book](https://example.com/rust) - D",
        "* [Ada Misfiled](https://example.com/ada2) - E",
        f,
        "### Fenced Heading",
        "* [Hidden](https://example.com/hidden) - F",
        f,
    ]


def self_test(force_fail=False):
    entries, headings = parse(fixture_lines())
    by_url = {e["url"]: e for e in entries}
    check("https://example.com/hidden" not in by_url, "fenced entry must be ignored")
    check(all(h["text"] != "Fenced Heading" for h in headings), "fenced heading must be ignored")
    check(by_url["https://example.com/py"]["category"] == "Python", "category mapping")
    check(by_url["https://example.com/py"]["line"] == 2, "line number preserved")

    reps = repeated_headings(headings)
    print("fixture repeated headings: %s" % [(r["text"], r["lines"]) for r in reps])
    check(len(reps) == 1 and reps[0]["text"] == "Ada" and reps[0]["lines"] == [3, 5], "repeated heading flagged")
    check(all(r["action"] == "manual_review" for r in reps), "repeated headings need manual review")

    expected = {
        "https://example.com/ada": "Ada",       # correct, must be preserved
        "https://example.com/ada2": "Ada",      # deliberately misplaced under Rust
    }
    res = {f["url"]: f for f in check_placement(entries, expected)}
    for f in res.values():
        print("fixture %-9s line=%d current=%s expected=%s action=%s" %
              (f["kind"], f["line"], f["current"], f["expected"], f["action"]))
    check(res["https://example.com/ada"]["kind"] == "ok", "valid category must be preserved")
    check(res["https://example.com/ada2"]["kind"] == "misplaced", "deliberate misplacement must be found")
    check(res["https://example.com/ada2"]["action"] == "manual_review", "no automatic move")
    check("https://example.com/rust" not in res, "entries without confirmed subject must not be reclassified")
    check(res["https://example.com/ada2"]["evidence"], "a proposed move must cite the actual subject")

    with open(CATALOGUE, encoding="utf-8") as fh:
        real, _ = parse(fh.read().splitlines())
    for key in SELECTED:
        found = [e for e in real if e["name"].startswith(key)]
        check(len(found) == 1, "selected entry not found exactly once: " + key)
        print("catalogue line %d: %s | category=%s" % (found[0]["line"], found[0]["name"], found[0]["category"]))
        check(found[0]["category"], "selected entry has no category")

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: fixture placement + repeated headings + %d catalogue entries" % len(SELECTED))


def report():
    with open(CATALOGUE, encoding="utf-8") as fh:
        real, headings = parse(fh.read().splitlines())
    selected = [e for e in real if any(e["name"].startswith(k) for k in SELECTED)]
    heading_lines = {e["heading_line"] for e in selected}
    reps = repeated_headings(headings)
    out = {"file": CATALOGUE, "entries_parsed": len(real), "headings": len(headings),
           "selected": selected,
           "repeated_headings_touching_selected": [r for r in reps if heading_lines & set(r["lines"])],
           "all_repeated_headings": reps}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        elif "--report" in sys.argv:
            report()
        else:
            print("usage: r10-t054.py --self-test | --report")
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
