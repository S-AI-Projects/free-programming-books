#!/usr/bin/env python3
"""R10-T055: verify entry metadata (title, url, optional description) for 3 selected entries.

  python3 tools/course_checks/r10-t055.py --self-test
  python3 tools/course_checks/r10-t055.py --self-test --demo-fail
  python3 tools/course_checks/r10-t055.py --file books/free-programming-books-subjects.md
  python3 tools/course_checks/r10-t055.py --file ... --live   (optional: 10s timeout, 1 request at a time)
"""
import argparse, json, re, sys, urllib.request

TOOL_VERSION = "1.1"
TARGETS = {
    "Atariarchives.org": "https://www.atariarchives.org",
    "Bento": "https://www.bento.io",
    "Bitsavers.org": "http://bitsavers.trailing-edge.com",
}
# Catalogue format: * [Title](url) - optional description
ENTRY_RE = re.compile(r"^\*\s+\[(?P<title>[^\]]*)\]\((?P<url>[^)]*)\)(?:\s+-\s+(?P<desc>.*))?\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def norm(u):
    return u.strip().rstrip("/").lower()


def parse(text):
    """Scan one file; keep original line numbers; ignore fenced code blocks."""
    entries, heading, fenced = [], None, False
    for no, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        h = HEADING_RE.match(line)
        if h:
            heading = h.group(2)
            continue
        m = ENTRY_RE.match(line)
        if m:
            d = m.groupdict()
            d.update(line=no, section=heading, raw=line, malformed=False)
            entries.append(d)
        elif any(norm(u) in line.lower() for u in TARGETS.values()):
            entries.append(dict(title="", url="", desc=None, line=no,
                                section=heading, raw=line, malformed=True))
    return entries


def check(entries):
    results = []
    for name, url in TARGETS.items():
        hits = [e for e in entries if norm(e["url"]) == norm(url)
                or (e["malformed"] and norm(url) in e["raw"].lower())]
        if not hits:
            results.append(dict(entry=name, source_url=url, status="MISSING", line=None))
            continue
        for e in hits:
            problems = []
            if not e["title"].strip():
                problems.append("missing title")
            if not re.match(r"^https?://\S+$", e["url"].strip()):
                problems.append("missing or invalid url")
            if e["desc"] is not None and not e["desc"].strip():
                problems.append("empty description")
            if len(hits) > 1:
                problems.append("duplicate entry")
            results.append(dict(
                entry=name, source_url=url, line=e["line"], section=e["section"],
                status="FAIL" if problems else "OK", problems=problems,
                observed=dict(title=e["title"], url=e["url"], description=e["desc"]),
                has_description=bool(e["desc"]),
                proposed=None))  # fill only when official docs prove a change is needed
    return results


def live(results):
    for r in results:
        try:
            req = urllib.request.Request(r["source_url"], method="HEAD")
            r["live"] = urllib.request.urlopen(req, timeout=10).status
        except Exception as ex:  # one failed request is NOT grounds for removal
            r["live"] = "unverified: %s" % ex
    return results


FIX_OK = """## Section
* [Atariarchives.org](https://www.atariarchives.org) - makes books available
* [Bento](https://www.bento.io)
* [Bitsavers.org](http://bitsavers.trailing-edge.com)
"""
FIX_BAD = """## Section
* [](https://www.bento.io)
* [Bitsavers.org]() - desc
* [Atariarchives.org](https://www.atariarchives.org) -
"""
FIX_FENCED = "```\n* [](https://www.bento.io)\n```\n"


def self_test(demo_fail=False):
    ok = check(parse(FIX_OK))
    assert all(r["status"] == "OK" for r in ok), "good fixture must pass"
    assert [r["line"] for r in ok] == [2, 3, 4], "line numbers retained"
    assert ok[1]["has_description"] is False and ok[1]["status"] == "OK", "description is optional"
    bad = {r["entry"]: r for r in check(parse(FIX_BAD))}
    assert "missing title" in bad["Bento"]["problems"], "missing title must fail"
    assert bad["Bento"]["status"] == "FAIL"
    assert bad["Atariarchives.org"]["status"] == "FAIL", "empty description must fail"
    assert bad["Bitsavers.org"]["status"] == "MISSING", "entry with empty url is not matched"
    fenced = check(parse(FIX_FENCED))
    assert all(r["status"] == "MISSING" for r in fenced), "fenced entries are ignored"
    print("fixture ok: 3 entries pass with original line numbers 2,3,4")
    print("fixture missing title: Bento FAIL (missing title)")
    print("fixture empty description: Atariarchives.org FAIL")
    print("fixture fenced entry ignored")
    if demo_fail:
        assert False, "deliberate failure (demo of non-zero exit)"
    print("self-test passed; version", TOOL_VERSION)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--demo-fail", action="store_true")
    a = ap.parse_args()
    try:
        if a.self_test:
            self_test(a.demo_fail)
            return 0
        if not a.file:
            ap.error("--file is required unless --self-test")
        with open(a.file, encoding="utf-8") as f:
            res = check(parse(f.read()))
        if a.live:
            res = live(res)
        print(json.dumps({"tool_version": TOOL_VERSION, "results": res}, indent=2))
        return 0 if all(r["status"] == "OK" for r in res) else 1
    except AssertionError as e:
        print("FAIL:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
