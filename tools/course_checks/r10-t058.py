#!/usr/bin/env python3
"""R10-T058: validate list syntax, heading hierarchy and ordering in
casts/free-podcasts-screencasts-uk.md. Malformed entries are rejected with their source line.
Non-English text and Markdown links are preserved. Nothing is edited automatically; every
proposal is for manual review. No live requests, so no link is removed by a failed request."""
import json, re, sys
from collections import defaultdict

CATALOGUE = "casts/free-podcasts-screencasts-uk.md"
SELECTED_KEYS = ["soundcloud.com/doupodcast", "id1528104095"]
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*)?(?P<meta>.*)$")
LISTLIKE = re.compile(r"^\s*[*-](\s|\[)")
RULE = re.compile(r"^\s*([*-]\s*){3,}$")


def parse(lines):
    entries, headings, malformed, cur, fence = [], [], [], None, None
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
            entries.append({"line": n, "name": m["name"], "url": m["url"], "meta": m["meta"].strip(),
                            "category": cur["text"] if cur else None,
                            "heading_line": cur["line"] if cur else None, "raw": line})
        elif LISTLIKE.match(line) and not RULE.match(line):
            malformed.append({"line": n, "text": line.strip()})
    return entries, headings, malformed


def sort_key(name):
    return name.casefold()


def validate(entries, headings, malformed):
    out = []
    for m in malformed:
        out.append({"kind": "malformed_entry", "line": m["line"], "detail": m["text"],
                    "action": "manual_review"})
    prev = None
    for h in headings:
        if prev is not None and h["level"] > prev["level"] + 1:
            out.append({"kind": "heading_skip", "line": h["line"],
                        "detail": "level %d directly after level %d" % (h["level"], prev["level"]),
                        "action": "manual_review"})
        prev = h
    groups = defaultdict(list)
    for e in entries:
        groups[e["heading_line"]].append(e)
    for es in groups.values():
        for a, b in zip(es, es[1:]):
            if sort_key(a["name"]) > sort_key(b["name"]):
                out.append({"kind": "out_of_order", "line": b["line"], "lines": [a["line"], b["line"]],
                            "detail": "%s should come before %s" % (b["name"], a["name"]),
                            "action": "manual_review"})
    return sorted(out, key=lambda x: x["line"])


def section_range(headings, total, lines_of_interest):
    starts, ends = [], []
    for ln in lines_of_interest:
        idx = None
        for i, h in enumerate(headings):
            if h["line"] <= ln:
                idx = i
        if idx is None:
            starts.append(1)
            ends.append(total)
            continue
        h = headings[idx]
        end = total
        for nxt in headings[idx + 1:]:
            if nxt["level"] <= h["level"]:
                end = nxt["line"] - 1
                break
        starts.append(h["line"])
        ends.append(end)
    return min(starts), max(ends)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def valid_fixture():
    return ["## Podcasts",
            "* [Apple](https://example.com/a) (podcast)",
            "* [Zeta](https://example.com/z) - Author",
            "* [\u0411\u043e\u0440\u0449](https://example.com/%D0%B1) (podcast)"]


def bad_fixture():
    f = chr(96) * 3
    return ["# Top",
            "### Deep",
            "* [Good](https://example.com/g)",
            "* [Broken](https://example.com/b",
            "*[NoSpace](https://example.com/n)",
            "* [Alpha](https://example.com/a)",
            f,
            "* [Fake](broken",
            f]


def self_test(force_fail=False):
    e, h, m = parse(valid_fixture())
    res = validate(e, h, m)
    print("valid fixture: %d entries, %d findings" % (len(e), len(res)))
    check(res == [], "valid fixture must produce no findings: %r" % res)
    check([x["name"] for x in e] == ["Apple", "Zeta", "\u0411\u043e\u0440\u0449"], "non-English name not preserved")
    check(e[2]["url"] == "https://example.com/%D0%B1", "percent-encoded URL not preserved")
    check(e[0]["meta"] == "(podcast)", "metadata not preserved")

    e, h, m = parse(bad_fixture())
    res = validate(e, h, m)
    for x in res:
        print("bad fixture %-16s line=%d action=%s" % (x["kind"], x["line"], x["action"]))
    check([x["line"] for x in res if x["kind"] == "malformed_entry"] == [4, 5], "malformed lines must be 4 and 5")
    check([x["line"] for x in res if x["kind"] == "heading_skip"] == [2], "heading skip must be line 2")
    ooo = [x for x in res if x["kind"] == "out_of_order"]
    check(len(ooo) == 1 and ooo[0]["lines"] == [3, 6], "out-of-order pair must be lines 3 and 6")
    check(all(x["line"] != 8 for x in res), "fenced fake entry must be ignored")
    check(all(x["action"] == "manual_review" for x in res), "no automatic edits allowed")
    check(all(isinstance(x["line"], int) for x in res), "every finding needs a source line")

    with open(CATALOGUE, encoding="utf-8") as fh:
        text = fh.read().splitlines()
    real, heads, mal = parse(text)
    for key in SELECTED_KEYS:
        found = [x for x in real if key in x["url"]]
        check(len(found) == 1, "selected entry not found exactly once: " + key)
        x = found[0]
        check("[%s](%s)" % (x["name"], x["url"]) in x["raw"], "markdown link not preserved: " + key)
        print("catalogue line %d: %s | category=%s" % (x["line"], x["name"], x["category"]))

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: valid + malformed fixtures + %d catalogue entries" % len(SELECTED_KEYS))


def report():
    with open(CATALOGUE, encoding="utf-8") as fh:
        text = fh.read().splitlines()
    real, heads, mal = parse(text)
    selected = [x for x in real if any(k in x["url"] for k in SELECTED_KEYS)]
    start, end = section_range(heads, len(text), [x["line"] for x in selected])
    allf = validate(real, heads, mal)
    out = {"file": CATALOGUE, "entries_parsed": len(real), "section_lines": [start, end],
           "selected": [{k: v for k, v in x.items() if k != "raw"} for x in selected],
           "findings_in_section": [f for f in allf if start <= f["line"] <= end],
           "findings_total": len(allf)}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        elif "--report" in sys.argv:
            report()
        else:
            print("usage: r10-t058.py --self-test | --report")
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
