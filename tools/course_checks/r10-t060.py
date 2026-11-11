#!/usr/bin/env python3
"""R10-T060: one-command scoped maintenance report for books/free-programming-books-th.md.
Usage: r10-t060.py            -> offline report on the 3 selected entries (stable output)
       r10-t060.py --self-test -> offline fixtures; failing assertions exit non-zero
       r10-t060.py --live      -> optional live probe (10 s timeout, one request at a time)
The report names exact source lines, keeps observed facts apart from recommendations, and
records before/after metadata plus a manual decision field. No automated result removes a link."""
import datetime, http.client, json, re, socket, ssl, sys, time
import urllib.error, urllib.parse, urllib.request

CATALOGUE = "books/free-programming-books-th.md"
SELECTED_KEYS = ["JerryLead/SparkInternals", "marcuscode.com/lang/csharp", "eremes81/game-design-ai-practice-th"]
TIMEOUT = 10
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*)?(?P<meta>.*)$")


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
                            "category": category, "meta": m["meta"].strip(), "raw": line})
    return entries


def observe(url, probe):
    """probe(url) -> (code, location) or raises. Returns plain observed facts only."""
    try:
        code, loc = probe(url)
        return {"status": code, "location": loc, "error": None}
    except (socket.timeout, TimeoutError):
        return {"status": None, "location": None, "error": "timeout"}
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), socket.gaierror):
            return {"status": None, "location": None, "error": "dns"}
        return {"status": None, "location": None, "error": "connection_error"}
    except (ssl.SSLError, http.client.HTTPException, OSError):
        return {"status": None, "location": None, "error": "connection_error"}


def recommend(obs, url):
    """Recommendations are separate from observations and never remove a link."""
    code, loc, err = obs["status"], obs["location"], obs["error"]
    if err:
        return {"action": "retry_later", "reason": "request error (%s); one failure is not evidence" % err}
    if code and 200 <= code < 300:
        if url.startswith("http://"):
            return {"action": "manual_review", "reason": "reachable over http; check whether an https version exists"}
        return {"action": "keep", "reason": "reachable"}
    if code in (301, 308):
        return {"action": "manual_review", "reason": "permanent redirect to %s; confirm it is the official source" % loc}
    if code in (302, 303, 307):
        return {"action": "keep", "reason": "temporary redirect; keep the original URL"}
    if code in (401, 403, 429):
        return {"action": "keep", "reason": "blocked or rate limited, not missing; verify in a browser"}
    if code in (404, 410):
        return {"action": "manual_review", "reason": "missing resource needs manual confirmation before any removal"}
    if code and code >= 500:
        return {"action": "retry_later", "reason": "server error; repeat later"}
    return {"action": "manual_review", "reason": "unexpected result"}


def build_report(entries, probe, observed_date):
    items = []
    for e in sorted(entries, key=lambda x: x["line"]):
        obs = observe(e["url"], probe) if probe else None
        rec = recommend(obs, e["url"]) if obs else {"action": "not_checked", "reason": "offline report; no request made"}
        items.append({
            "source": {"file": CATALOGUE, "line": e["line"], "raw": e["raw"]},
            "before": {"name": e["name"], "url": e["url"], "category": e["category"], "meta": e["meta"]},
            "observed": obs if obs else {"status": None, "location": None, "error": None, "checked": False},
            "recommendation": rec,
            "after": {"name": e["name"], "url": e["url"], "category": e["category"], "meta": e["meta"]},
            "manual_decision": "pending",
        })
    return {"file": CATALOGUE, "observed_date": observed_date, "entries": items,
            "note": "observed = facts from a request; recommendation = suggested action. "
                    "after equals before unless a manual decision changes it. No link is removed automatically."}


def make_probe(table):
    def probe(url):
        v = table[url]
        if isinstance(v, BaseException):
            raise v
        return v
    return probe


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def probe_real(url):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "r10-t060-checker/1.0"})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        if e.code in (400, 403, 405, 501):
            req = urllib.request.Request(url, headers={"User-Agent": "r10-t060-checker/1.0"})
            try:
                with OPENER.open(req, timeout=TIMEOUT) as r:
                    return r.status, None
            except urllib.error.HTTPError as e2:
                return e2.code, e2.headers.get("Location")
        return e.code, e.headers.get("Location")


def load_selected():
    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    return [x for x in real if any(k in x["url"] for k in SELECTED_KEYS)]


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def fixture_entries():
    return [
        {"line": 3, "name": "Ok Book", "url": "https://ok.test/", "category": "Demo", "meta": "(PDF)", "raw": "* [Ok Book](https://ok.test/) (PDF)"},
        {"line": 4, "name": "\u0e44\u0e17\u0e22", "url": "http://plain.test/", "category": "Demo", "meta": "", "raw": "* [\u0e44\u0e17\u0e22](http://plain.test/)"},
        {"line": 5, "name": "Moved", "url": "https://moved.test/", "category": "Demo", "meta": "", "raw": "* [Moved](https://moved.test/)"},
        {"line": 6, "name": "Gone", "url": "https://gone.test/", "category": "Demo", "meta": "", "raw": "* [Gone](https://gone.test/)"},
        {"line": 7, "name": "Slow", "url": "https://slow.test/", "category": "Demo", "meta": "", "raw": "* [Slow](https://slow.test/)"},
        {"line": 8, "name": "Blocked", "url": "https://blocked.test/", "category": "Demo", "meta": "", "raw": "* [Blocked](https://blocked.test/)"},
    ]


def self_test(force_fail=False):
    T = {
        "https://ok.test/": (200, None),
        "http://plain.test/": (200, None),
        "https://moved.test/": (301, "https://new.test/"),
        "https://gone.test/": (404, None),
        "https://slow.test/": socket.timeout("timed out"),
        "https://blocked.test/": (403, None),
    }
    probe = make_probe(T)
    entries = fixture_entries()
    r1 = json.dumps(build_report(entries, probe, "2026-11-11"), ensure_ascii=False, sort_keys=True)
    r2 = json.dumps(build_report(entries, probe, "2026-11-11"), ensure_ascii=False, sort_keys=True)
    check(r1 == r2, "output must be stable for the same fixtures")
    rep = json.loads(r1)
    expected = {3: "keep", 4: "manual_review", 5: "manual_review", 6: "manual_review", 7: "retry_later", 8: "keep"}
    for it in rep["entries"]:
        ln = it["source"]["line"]
        print("fixture line=%d observed=%s/%s recommendation=%-13s decision=%s" % (
            ln, it["observed"]["status"], it["observed"]["error"], it["recommendation"]["action"], it["manual_decision"]))
        check(it["recommendation"]["action"] == expected[ln], "line %d: expected %s, got %s" % (ln, expected[ln], it["recommendation"]["action"]))
        check(it["recommendation"]["action"] not in ("remove", "recommend_removal"), "no automated removal")
        check(it["manual_decision"] == "pending", "manual decision must start pending")
        check(it["before"] == it["after"], "after must equal before until a manual decision")
        check("source" in it and isinstance(it["source"]["line"], int), "exact source line required")
        check("observed" in it and "recommendation" in it, "facts and recommendations must be separate")
    check(rep["entries"][1]["before"]["name"] == "\u0e44\u0e17\u0e22", "non-English name preserved")
    off = build_report(entries, None, "2026-11-11")
    check(all(i["recommendation"]["action"] == "not_checked" for i in off["entries"]), "offline report makes no request")

    sel = load_selected()
    check(len(sel) == len(SELECTED_KEYS), "expected %d selected entries, found %d" % (len(SELECTED_KEYS), len(sel)))
    for x in sel:
        check("[%s](%s)" % (x["name"], x["url"]) in x["raw"], "markdown link not preserved")
        print("catalogue line %d: %s | category=%s" % (x["line"], x["name"], x["category"]))

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: %d fixture entries, stable output + %d catalogue entries" % (len(entries), len(sel)))


def main():
    sel = load_selected()
    if "--live" in sys.argv:
        out = []
        for e in sel:
            out.append(e)
        rep = build_report(out, probe_real, datetime.date.today().isoformat())
        time.sleep(0)
    else:
        rep = build_report(sel, None, "offline")
    for it in rep["entries"]:
        it["source"].pop("raw", None) if False else None
    print(json.dumps(rep, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        else:
            main()
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
