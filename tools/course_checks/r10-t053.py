#!/usr/bin/env python3
"""R10-T053: detect exact and probable duplicate URLs in casts/free-podcasts-screencasts-pl.md.
Nothing is merged or deleted automatically; every proposal needs a manual review."""
import json, re, sys
from collections import defaultdict
from urllib.parse import urlsplit

CATALOGUE = "casts/free-podcasts-screencasts-pl.md"
SELECTED = ["Better Software Design", "Biznes My", "Chwila Dla Admina"]
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*(?P<meta>.*))?$")


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
            category = h.group(1)
            continue
        m = ENTRY.match(line)
        if m:
            entries.append({"line": n, "name": m["name"], "url": m["url"],
                            "category": category, "meta": (m["meta"] or "").strip()})
    return entries


def parts(url):
    """Conservative normalisation: ignore scheme, 'www.', default port, trailing slash.
    Query string and fragment are kept exactly as written."""
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if p.port and p.port not in (80, 443):
        host += ":%d" % p.port
    path = p.path.rstrip("/")
    return host + path, p.query, p.fragment


def norm(url):
    base, query, frag = parts(url)
    return base + "?" + query + "#" + frag


def make_group(kind, es):
    es = sorted(es, key=lambda e: e["line"])
    mergeable = kind in ("exact", "probable")
    g = {"kind": kind,
         "lines": [e["line"] for e in es],
         "names": [e["name"] for e in es],
         "urls": [e["url"] for e in es],
         "action": "manual_review" if mergeable else "keep_all"}
    if mergeable:
        g["proposed_deletion"] = {"keep_line": es[0]["line"], "delete_line": es[-1]["line"],
                                  "reviewed": False}
    else:
        g["proposed_deletion"] = None
    return g


def analyze(entries):
    groups = []
    raw = defaultdict(list)
    for e in entries:
        raw[e["url"]].append(e)
    for es in raw.values():
        if len(es) > 1:
            groups.append(make_group("exact", es))
    nm = defaultdict(list)
    for e in entries:
        nm[norm(e["url"])].append(e)
    for es in nm.values():
        if len({e["url"] for e in es}) > 1:
            groups.append(make_group("probable", es))
    # same page, different fragment: distinct anchors, never merged
    base_q = defaultdict(list)
    for e in entries:
        b, q, f = parts(e["url"])
        base_q[(b, q)].append(e)
    for es in base_q.values():
        if len({parts(e["url"])[2] for e in es}) > 1:
            groups.append(make_group("distinct_anchor", es))
    # same path, different query: query-dependent resources, never merged
    base = defaultdict(list)
    for e in entries:
        base[parts(e["url"])[0]].append(e)
    for es in base.values():
        if len({parts(e["url"])[1] for e in es}) > 1:
            groups.append(make_group("query_dependent", es))
    return groups


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def fixture_lines():
    f = chr(96) * 3
    return [
        "# Demo",
        "* [A](https://example.com/a) - x",
        "* [A again](https://example.com/a) - x",
        "* [B](http://www.example.com/b/) - y",
        "* [B2](https://example.com/b) - y",
        "* [C](https://example.com/doc#install) - z",
        "* [C2](https://example.com/doc#usage) - z",
        "* [P1](https://www.youtube.com/playlist?list=AAA) - p",
        "* [P2](https://www.youtube.com/playlist?list=BBB) - p",
        f,
        "* [Fake](https://example.com/a) - ignored",
        f,
    ]


def find(groups, kind, lines):
    return [g for g in groups if g["kind"] == kind and g["lines"] == lines]


def self_test(force_fail=False):
    entries = parse(fixture_lines())
    check(all(e["line"] != 11 for e in entries), "fenced fake link must be ignored")
    groups = analyze(entries)
    for g in groups:
        print("fixture %-16s lines=%s action=%s" % (g["kind"], g["lines"], g["action"]))
    check(find(groups, "exact", [2, 3]), "exact duplicate not found")
    check(find(groups, "probable", [4, 5]), "probable duplicate (http/www/trailing slash) not found")
    da = find(groups, "distinct_anchor", [6, 7])
    check(da and da[0]["proposed_deletion"] is None, "different fragments must stay distinct")
    qd = find(groups, "query_dependent", [8, 9])
    check(qd and qd[0]["proposed_deletion"] is None, "different query strings must stay distinct")
    check(not find(groups, "probable", [6, 7]) and not find(groups, "probable", [8, 9]),
          "anchors/queries must not be merged")
    for g in groups:
        check(g["action"] in ("manual_review", "keep_all"), "no automatic deletion allowed")
        d = g["proposed_deletion"]
        check(d is None or (d["reviewed"] is False and "keep_line" in d), "deletion needs a manual-review pair")

    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    for key in SELECTED:
        found = [e for e in real if e["name"].startswith(key)]
        check(len(found) == 1, "selected entry not found exactly once: " + key)
        print("catalogue line %d: %s -> %s" % (found[0]["line"], found[0]["name"], found[0]["url"]))

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: %d fixture groups + %d catalogue entries" % (len(groups), len(SELECTED)))


def report():
    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    groups = analyze(real)
    selected = [e for e in real if any(e["name"].startswith(k) for k in SELECTED)]
    sel_lines = {e["line"] for e in selected}
    out = {"file": CATALOGUE,
           "entries_parsed": len(real),
           "selected": selected,
           "groups_touching_selected": [g for g in groups if sel_lines & set(g["lines"])],
           "all_groups": groups}
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        elif "--report" in sys.argv:
            report()
        else:
            print("usage: r10-t053.py --self-test | --report")
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
