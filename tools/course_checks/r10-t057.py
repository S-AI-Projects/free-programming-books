#!/usr/bin/env python3
"""R10-T057: classify link-check failures for casts/free-podcasts-screencasts-tr.md.
Distinguishes success, timeout, 403/429, missing resource and DNS failure, and uses a GET
fallback when HEAD is unsupported. Only a manually confirmed missing resource may be
recommended for removal; one automated result alone never removes a link."""
import datetime, http.client, json, re, socket, ssl, sys, time
import urllib.error, urllib.parse, urllib.request

CATALOGUE = "casts/free-podcasts-screencasts-tr.md"
SELECTED_HOSTS = ["codefiction.tech", "devpod.org", "kodpod.live"]
TIMEOUT = 10
DELAY = 1.0
HEAD_UNSUPPORTED = (400, 403, 405, 501)
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*)?(?P<meta>.*)$")
ALLOWED_ACTIONS = {"keep", "retry_later", "manual_review", "recommend_removal"}


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


def is_dns_error(ex):
    reason = getattr(ex, "reason", ex)
    return isinstance(reason, socket.gaierror)


def request(url, method, send):
    """Run one request through send(url, method). Returns (code, error_label)."""
    try:
        return send(url, method), None
    except urllib.error.HTTPError as e:
        return e.code, None
    except (socket.timeout, TimeoutError):
        return None, "timeout"
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), (socket.timeout, TimeoutError)):
            return None, "timeout"
        if is_dns_error(e):
            return None, "dns"
        return None, "connection_error"
    except socket.gaierror:
        return None, "dns"
    except (ssl.SSLError, http.client.HTTPException, OSError):
        return None, "connection_error"


def label_for(code):
    if 200 <= code < 300:
        return "ok"
    if 300 <= code < 400:
        return "redirect"
    if code in (403, 429):
        return "blocked_or_rate_limited"
    if code in (404, 410):
        return "missing_resource"
    if code >= 500:
        return "server_error"
    return "unexpected_status"


def classify(url, send):
    steps = []
    code, err = request(url, "HEAD", send)
    steps.append({"method": "HEAD", "code": code, "error": err})
    if err is None and code in HEAD_UNSUPPORTED:
        code, err = request(url, "GET", send)
        steps.append({"method": "GET", "code": code, "error": err})
    if err:
        label = {"timeout": "timeout", "dns": "dns_failure"}.get(err, "connection_error")
    else:
        label = label_for(code)
    return label, steps


def advise(label, confirmed_missing=False):
    if label == "ok":
        return "keep", "reachable"
    if label == "redirect":
        return "keep", "redirects; run the redirect check before changing anything"
    if label == "blocked_or_rate_limited":
        return "keep", "403/429 means blocked or rate limited, not missing; verify in a browser"
    if label in ("timeout", "server_error", "connection_error"):
        return "retry_later", "transient failure; repeat the check later"
    if label in ("missing_resource", "dns_failure"):
        if confirmed_missing:
            return "recommend_removal", "manually confirmed missing"
        return "manual_review", "needs manual confirmation; one automated result is not enough to remove a link"
    return "manual_review", "unexpected result; review manually"


def record(url, send, observed, confirmed_missing=False):
    label, steps = classify(url, send)
    action, note = advise(label, confirmed_missing)
    return {"url": url, "label": label, "action": action, "note": note,
            "observed": observed, "steps": steps}


def make_send(table):
    def send(url, method):
        v = table[(url, method)]
        if isinstance(v, BaseException):
            raise v
        if v >= 400:
            raise urllib.error.HTTPError(url, v, "status %d" % v, {}, None)
        return v
    return send


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def send_real(url, method):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "r10-t057-checker/1.0"})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as r:
            return r.status
    except urllib.error.HTTPError as e:
        if 300 <= e.code < 400:
            return e.code
        raise


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def self_test(force_fail=False):
    T = {
        ("https://ok.test/", "HEAD"): 200,
        ("https://gone.test/", "HEAD"): 404,
        ("https://limited.test/", "HEAD"): 429,
        ("https://noheadok.test/", "HEAD"): 405,
        ("https://noheadok.test/", "GET"): 200,
        ("https://noheadgone.test/", "HEAD"): 405,
        ("https://noheadgone.test/", "GET"): 404,
        ("https://slow.test/", "HEAD"): socket.timeout("timed out"),
        ("https://nodns.test/", "HEAD"): urllib.error.URLError(socket.gaierror(8, "nodename nor servname")),
        ("https://forbidden.test/", "HEAD"): 403,
        ("https://forbidden.test/", "GET"): 403,
        ("https://broken.test/", "HEAD"): 503,
    }
    send = make_send(T)
    cases = [
        ("200", "https://ok.test/", "ok"),
        ("404", "https://gone.test/", "missing_resource"),
        ("429", "https://limited.test/", "blocked_or_rate_limited"),
        ("HEAD-405/GET-200", "https://noheadok.test/", "ok"),
        ("HEAD-405/GET-404", "https://noheadgone.test/", "missing_resource"),
        ("timeout", "https://slow.test/", "timeout"),
        ("DNS failure", "https://nodns.test/", "dns_failure"),
        ("HEAD-403/GET-403", "https://forbidden.test/", "blocked_or_rate_limited"),
        ("HTTP 503", "https://broken.test/", "server_error"),
    ]
    seen = set()
    for label, url, expected in cases:
        r = record(url, send, "2026-11-10")
        print("%-18s expected=%-24s actual=%-24s action=%s" % (label, expected, r["label"], r["action"]))
        check(r["label"] == expected, "%s: expected %s, got %s" % (label, expected, r["label"]))
        check(r["action"] != "recommend_removal", label + ": removal needs manual confirmation")
        check(r["action"] in ALLOWED_ACTIONS, label + ": unknown action")
        seen.add(r["label"])
    check(len(seen) >= 6, "fixtures must produce different labels")

    r = record("https://noheadok.test/", send, "2026-11-10")
    check([s["method"] for s in r["steps"]] == ["HEAD", "GET"], "GET fallback must follow HEAD 405")
    r = record("https://ok.test/", send, "2026-11-10")
    check([s["method"] for s in r["steps"]] == ["HEAD"], "no GET fallback when HEAD works")
    r = record("https://gone.test/", send, "2026-11-10", confirmed_missing=True)
    check(r["action"] == "recommend_removal", "only a manually confirmed missing resource is recommended for removal")
    r = record("https://limited.test/", send, "2026-11-10", confirmed_missing=True)
    check(r["action"] == "keep", "429 is never a removal, even with confirmation flag")

    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    for host in SELECTED_HOSTS:
        found = [e for e in real if (urllib.parse.urlsplit(e["url"]).hostname or "").endswith(host)]
        check(len(found) == 1, "selected entry not found exactly once: " + host)
        print("catalogue line %d: %s -> %s" % (found[0]["line"], found[0]["name"], found[0]["url"]))

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: %d status cases + GET fallback + %d catalogue entries" % (len(cases), len(SELECTED_HOSTS)))


def live():
    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    today = datetime.date.today().isoformat()
    out = []
    for host in SELECTED_HOSTS:
        for e in real:
            if (urllib.parse.urlsplit(e["url"]).hostname or "").endswith(host):
                r = record(e["url"], send_real, today)
                r["line"], r["name"] = e["line"], e["name"]
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
            print("usage: r10-t057.py --self-test | --live")
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
