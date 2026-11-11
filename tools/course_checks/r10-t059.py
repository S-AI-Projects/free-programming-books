#!/usr/bin/env python3
"""R10-T059: check what access a resource needs (authentication, registration, payment,
particular environment) for courses/free-courses-bg.md, so the catalogue description can be
precise. Each access claim cites the official resource URL and the observation date.
No credential is ever stored or sent; cookies are not kept. An unavailable resource is
labelled 'unverified' - never 'free' and never 'broken'."""
import datetime, http.client, json, re, socket, ssl, sys, time
import urllib.error, urllib.parse, urllib.request

CATALOGUE = "courses/free-courses-bg.md"
SELECTED_KEYS = ["PL1zMmEDXa"]
TIMEOUT = 10
FENCE = re.compile(r"^\s*(" + chr(96) * 3 + r"|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
ENTRY = re.compile(r"^\s*[*-]\s+\[(?P<name>.+?)\]\((?P<url>\S+?)\)\s*(?:[-\u2013\u2014]\s*)?(?P<meta>.*)$")

PAYMENT = ("subscribe", "subscription", "premium", "paid", "pricing", "purchase", "checkout")
REGISTRATION = ("sign up", "signup", "register", "create an account", "create account")
LOGIN = ("login", "log in", "signin", "sign in", "sign-in")
ENVIRONMENT = ("download", "install", "windows only", "mac only", "requires")


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


def fetch_status(url, send):
    """Return (code, location, error). One request, no cookies, no credentials."""
    try:
        code, loc = send(url)
        return code, loc, None
    except (socket.timeout, TimeoutError):
        return None, None, "timeout"
    except urllib.error.URLError as e:
        if isinstance(getattr(e, "reason", None), socket.gaierror):
            return None, None, "dns"
        return None, None, "connection_error"
    except (ssl.SSLError, http.client.HTTPException, OSError):
        return None, None, "connection_error"


def classify_access(url, send, body_hint=""):
    """Return an access label. Only explicit evidence gives a claim; otherwise 'unverified'."""
    code, loc, err = fetch_status(url, send)
    evidence = {"url": url, "status": code, "location": loc, "error": err}
    if err or code is None:
        return "unverified", "request failed (%s); access cannot be claimed" % err, evidence
    if 300 <= code < 400 and loc:
        target = (loc or "").lower()
        if any(k in target for k in LOGIN):
            return "login_required", "redirects to a login page", evidence
        return "unverified", "redirect to %s; follow it before claiming anything" % loc, evidence
    if code in (401, 403):
        return "login_required", "HTTP %d without credentials" % code, evidence
    if code == 402:
        return "payment_required", "HTTP 402", evidence
    if code == 429:
        return "unverified", "rate limited; access not confirmed", evidence
    if code in (404, 410) or code >= 500:
        return "unverified", "HTTP %d; resource not available, so not claimed free or broken" % code, evidence
    if 200 <= code < 300:
        text = body_hint.lower()
        if any(k in text for k in PAYMENT):
            return "payment_possible", "page mentions payment terms; verify manually", evidence
        if any(k in text for k in REGISTRATION):
            return "registration_possible", "page mentions registration; verify manually", evidence
        return "open_no_login", "HTTP 200 without credentials; no login or payment wall seen", evidence
    return "unverified", "unexpected HTTP %d" % code, evidence


def record(entry, send, observed, body_hint=""):
    label, note, evidence = classify_access(entry["url"], send, body_hint)
    claim = {"unverified": "unverified",
             "open_no_login": "no authentication needed (observed)",
             }.get(label, label)
    return {"line": entry["line"], "name": entry["name"], "url": entry["url"], "label": label,
            "claim": claim, "note": note, "source": evidence["url"], "observed": observed,
            "evidence": evidence, "credentials_stored": False,
            "suggested_description": "manual_review" if label != "open_no_login" else "keep_as_is"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = urllib.request.build_opener(NoRedirect)


def send_real(url):
    req = urllib.request.Request(url, headers={"User-Agent": "r10-t059-checker/1.0"})
    try:
        with OPENER.open(req, timeout=TIMEOUT) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location")


def make_send(table):
    def send(url):
        v = table[url]
        if isinstance(v, BaseException):
            raise v
        return v
    return send


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def self_test(force_fail=False):
    T = {
        "https://open.test/": (200, None),
        "https://login.test/": (302, "https://login.test/login?next=/"),
        "https://forbidden.test/": (403, None),
        "https://paid.test/": (402, None),
        "https://gone.test/": (404, None),
        "https://slow.test/": socket.timeout("timed out"),
        "https://nodns.test/": urllib.error.URLError(socket.gaierror(8, "no name")),
        "https://limited.test/": (429, None),
        "https://moved.test/": (301, "https://other.test/"),
    }
    send = make_send(T)
    cases = [
        ("open", "https://open.test/", "", "open_no_login"),
        ("login redirect", "https://login.test/", "", "login_required"),
        ("HTTP 403", "https://forbidden.test/", "", "login_required"),
        ("HTTP 402", "https://paid.test/", "", "payment_required"),
        ("HTTP 404", "https://gone.test/", "", "unverified"),
        ("timeout", "https://slow.test/", "", "unverified"),
        ("DNS failure", "https://nodns.test/", "", "unverified"),
        ("HTTP 429", "https://limited.test/", "", "unverified"),
        ("plain redirect", "https://moved.test/", "", "unverified"),
        ("page mentions pricing", "https://open.test/", "see our pricing and premium plan", "payment_possible"),
        ("page mentions sign up", "https://open.test/", "please sign up to continue", "registration_possible"),
    ]
    for label, url, hint, expected in cases:
        e = {"line": 1, "name": "x", "url": url}
        r = record(e, send, "2026-11-11", hint)
        print("%-22s expected=%-22s actual=%-22s" % (label, expected, r["label"]))
        check(r["label"] == expected, "%s: expected %s, got %s" % (label, expected, r["label"]))
        check(r["source"] == url and r["observed"] == "2026-11-11", label + ": claim must cite source and date")
        check(r["credentials_stored"] is False, "no credential may be saved")
        if r["label"] == "unverified":
            check(r["claim"] == "unverified", "unavailable resource must be labelled unverified")
            check("free" not in r["claim"] and "broken" not in r["claim"], "unverified must not say free or broken")

    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    for key in SELECTED_KEYS:
        found = [x for x in real if key in x["url"]]
        check(len(found) == 1, "selected entry not found exactly once: " + key)
        x = found[0]
        check("[%s](%s)" % (x["name"], x["url"]) in x["raw"], "markdown link not preserved")
        print("catalogue line %d: %s | category=%s" % (x["line"], x["name"], x["category"]))

    if force_fail:
        check(False, "deliberate failure (demo of non-zero exit)")
    print("self-test OK: %d access cases + %d catalogue entries" % (len(cases), len(SELECTED_KEYS)))


def live():
    with open(CATALOGUE, encoding="utf-8") as fh:
        real = parse(fh.read().splitlines())
    today = datetime.date.today().isoformat()
    out = []
    for x in real:
        if any(k in x["url"] for k in SELECTED_KEYS):
            r = record(x, send_real, today)
            out.append(r)
            time.sleep(1.0)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        if "--self-test" in sys.argv:
            self_test(force_fail="--demo-fail" in sys.argv)
        elif "--live" in sys.argv:
            live()
        else:
            print("usage: r10-t059.py --self-test | --live")
    except AssertionError as ex:
        print("FAIL:", ex)
        sys.exit(1)
