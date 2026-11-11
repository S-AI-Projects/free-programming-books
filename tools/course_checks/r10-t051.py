#!/usr/bin/env python3
"""R10-T051: parse entries of courses/free-courses-ne.md, keeping source line numbers."""
import re, sys, json
from urllib.parse import urlparse, parse_qs

CATALOGUE = "courses/free-courses-ne.md"
ENTRY = re.compile(r'^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-–—]\s*(?P<meta>.*))?$')
HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*#*\s*$')
FENCE = re.compile(r'^\s*(```|~~~)')

def parse(lines):
    entries, category, fence = [], None, None
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
            category = h.group(2)
            continue
        m = ENTRY.match(line)
        if m:
            entries.append({"line": n, "name": m["name"], "url": m["url"],
                            "category": category, "meta": (m["meta"] or "").strip()})
    return entries

FIXTURE = "\n".join([
    "# Demo Category",
    "* [Real One](https://example.com/page#frag) - Some Author",
    chr(96) * 3,
    "* [Fake](https://fake.example/should-be-ignored) - Nobody",
    chr(96) * 3,
    "* [Real Two](https://example.com/two) - Another Author",
]) + "\n"

def check(cond, msg):
    if not cond:
        raise AssertionError(msg)

def self_test(force_fail=False):
    e = parse(FIXTURE.splitlines())
    check(len(e) == 2, f"expected 2 entries, got {len(e)}")
    check(all("fake.example" not in x["url"] for x in e), "fenced fake link leaked")
    check(e[0]["url"] == "https://example.com/page#frag", "fragment not preserved")
    check(e[0]["line"] == 2 and e[1]["line"] == 6, "line numbers wrong")
    check(e[0]["category"] == "Demo Category", "category wrong")
    check(e[0]["meta"] == "Some Author", "metadata wrong")

    with open(CATALOGUE, encoding="utf-8") as fh:
        real = {x["line"]: x for x in parse(fh.read().splitlines())}
    for ln in (18, 19, 24):
        check(ln in real, f"line {ln} not found in {CATALOGUE}")

    a, b, c = real[18], real[19], real[24]
    check(a["name"].startswith("C Programming 1 Year Engineering"), "line 18 name")
    check("playlist?list=" in a["url"], "line 18 url")
    check(a["meta"] == "Nepali Education", "line 18 meta")

    check(b["name"].startswith("C Programming Full Course In Nepali"), "line 19 name")
    qb = parse_qs(urlparse(b["url"]).query)
    check(qb.get("v") == ["7WH8C48UNDU"] and qb.get("index") == ["3"] and "list" in qb, "line 19 url params")
    check(b["meta"] == "Technology Channel", "line 19 meta")

    check(c["name"].startswith("OOP Lecture"), "line 24 name")
    check("playlist?list=" in c["url"], "line 24 url")
    check(c["meta"] == "BKL Lectures", "line 24 meta")

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: fixture + 3 real entries (lines 18, 19, 24)")

if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        else:
            with open(CATALOGUE, encoding="utf-8") as fh:
                for x in parse(fh.read().splitlines()):
                    print(json.dumps(x, ensure_ascii=False))
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
