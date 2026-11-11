#!/usr/bin/env python3
"""R10-T052: verify redirects for selected entries of books/free-programming-books-ru.md."""
import datetime, http.client, json, re, socket, sys, time
import urllib.error, urllib.parse, urllib.request

CATALOGUE = "books/free-programming-books-ru.md"
SELECTED = [
    "https://mkurnosov.net/files/dsa-book-2020.pdf",
    "https://github.com/Cultus-Tenebrae/Markdown-documentation/releases/latest",
    "https://vseloved.github.io/pdf/os-ru.pdf",
]
MAX_HOPS = 5      # redirect budget per URL
TIMEOUT = 10      # seconds per request
DELAY = 1.0       # pause between URLs (sequential = concurrency 1)
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*(?P<meta>.*))?$")
LOGIN_HINTS = ("login", "signin", "sign-in", "accounts.google.com", "/auth")
PERMANENT = (301, 308)
ALLOWED_ACTIONS = {"keep", "update", "retry_later", "manual_review"}


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


def make_result(status, chain, detail, permanent=True):
    return {"status": status, "final_url": chain[-1], "hops": len(chain) - 1,
            "chain": chain, "permanent": permanent, "detail": detail}


def classify(url, fetch, max_hops=MAX_HOPS):
    chain, seen, cur, hops, permanent = [url], {url}, url, 0, True
    while True:
        try:
            code, loc = fetch(cur)
        except (socket.timeout, TimeoutError, urllib.error.URLError,
                http.client.HTTPException, OSError) as ex:
            return make_result("transient", chain, "request error: " + type(ex).__name__, permanent)
        if 300 <= code < 400 and loc:
            nxt = urllib.parse.urljoin(cur, loc)
            if nxt in seen:
                return make_result("redirect_loop", chain + [nxt], "revisited " + nxt, permanent)
            if hops >= max_hops:
                return make_result("redirect_budget_exceeded", chain, "more than %d hops" % max_hops, permanent)
            if code not in PERMANENT:
                permanent = False
            hops += 1
            seen.add(nxt)
            chain.append(nxt)
            cur = nxt
            continue
        if code in (401, 403):
            return make_result("login_wall", chain, "HTTP %d" % code, permanent)
        if code == 200:
            if cur != url and any(h in cur.lower() for h in LOGIN_HINTS):
                return make_result("login_wall", chain, "redirected to a login page", permanent)
            if hops == 0:
                return make_result("ok", chain, "HTTP 200", permanent)
            return make_result("moved", chain, "HTTP 200 after %d redirect(s)" % hops, permanent)
        if code in (404, 410):
            return make_result("not_found", chain, "HTTP %d" % code, permanent)
        if code == 429 or code >= 500:
            return make_result("transient", chain, "HTTP %d" % code, permanent)
        return make_result("unexpected_status", chain, "HTTP %d" % code, permanent)


def advise(res):
    s = res["status"]
    if s == "ok":
        return "keep", "reachable, no redirect"
    if s == "moved":
        if res["permanent"]:
            return "update", "permanent redirect; confirm the final URL is the official source before editing"
        return "keep", "temporary redirect; keep the original URL"
    if s == "login_wall":
        return "keep", "login or automated-access block; verify manually in a browser"
    if s == "transient":
        return "retry_later", "timeout or server error; repeat the check later"
    return "manual_review", "needs a human check; one automated result is not enough to remove a link"


def record(url, fetch, observed):
    res = classify(url, fetch)
    action, note = advise(res)
    res.update({"url": url, "observed": observed, "action": action, "note": note})
    return res


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def fetch_real(url):
    req = urllib.request.Request(url, headers={"User-Agent": "r10-t052-checker/1.0"})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")


def make_fetch(table):
    def fetch(url):
        v = table[url]
        if isinstance(v, BaseException):
            raise v
        return v
    return fetch


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def self_test(force_fail=False):
    T = {
        "https://ok.test/a": (200, None),
        "https://old.test/a": (301, "https://new.test/a"),
        "https://new.test/a": (200, None),
        "https://tmp.test/a": (302, "/b"),
        "https://tmp.test/b": (200, None),
        "https://loop.test/a": (302, "https://loop.test/b"),
        "https://loop.test/b": (302, "https://loop.test/a"),
        "https://slow.test/a": socket.timeout("timed out"),
        "https://err.test/a": (503, None),
        "https://login.test/a": (302, "https://login.test/login?next=a"),
        "https://login.test/login?next=a": (200, None),
        "https://forbidden.test/a": (403, None),
        "https://gone.test/a": (404, None),
    }
    for i in range(9):
        T["https://c%d.test/" % i] = (301, "https://c%d.test/" % (i + 1))
    T["https://c9.test/"] = (200, None)
    fetch = make_fetch(T)

    cases = [
        ("200 direct", "https://ok.test/a", "ok"),
        ("301 -> 200", "https://old.test/a", "moved"),
        ("302 -> 200", "https://tmp.test/a", "moved"),
        ("redirect loop", "https://loop.test/a", "redirect_loop"),
        ("timeout", "https://slow.test/a", "transient"),
        ("HTTP 503", "https://err.test/a", "transient"),
        ("redirect to login", "https://login.test/a", "login_wall"),
        ("HTTP 403", "https://forbidden.test/a", "login_wall"),
        ("HTTP 404", "https://gone.test/a", "not_found"),
        ("too many hops", "https://c0.test/", "redirect_budget_exceeded"),
    ]
    for label, url, expected in cases:
        r = record(url, fetch, "2026-11-10")
        print("%-18s expected=%-26s actual=%-26s action=%s" % (label, expected, r["status"], r["action"]))
        check(r["status"] == expected, "%s: expected %s, got %s" % (label, expected, r["status"]))
        check(r["action"] in ALLOWED_ACTIONS, label + ": link must never be removed from one request")

    r = record("https://old.test/a", fetch, "2026-11-10")
    check(r["final_url"] == "https://new.test/a" and r["hops"] == 1 and r["permanent"], "301 final URL/hops")
    check(r["observed"] == "2026-11-10" and r["action"] == "update", "record must hold observation date")
    r = record("https://tmp.test/a", fetch, "2026-11-10")
    check(r["final_url"] == "https://tmp.test/b" and r["action"] == "keep", "302 handling")

    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    for url in SELECTED:
        found = [e for e in real if e["url"] == url]
        check(len(found) == 1, "selected entry not found exactly once: " + url)
        print("catalogue line %d: %s" % (found[0]["line"], url))

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: %d redirect cases + %d catalogue entries" % (len(cases), len(SELECTED)))


def live():
    with open(CATALOGUE, encoding="utf-8") as fh:
        real = {e["url"]: e for e in parse(fh.read().splitlines())}
    today = datetime.date.today().isoformat()
    out = []
    for url in SELECTED:
        r = record(url, fetch_real, today)
        e = real.get(url, {})
        r["line"], r["name"] = e.get("line"), e.get("name")
        out.append(r)
        time.sleep(DELAY)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        elif "--live" in sys.argv:
            live()
        else:
            print("usage: r10-t052.py --self-test | --live")
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
