#!/usr/bin/env python3
"""R10-T056: offline, fixture-based checks for courses/free-courses-zh.md."""
import argparse, json, platform, re, socket, sys
from pathlib import Path
from urllib.parse import urlsplit

DEFAULT_FILE = "courses/free-courses-zh.md"
WORK_DIR = Path("work/R10-T056")

TARGETS = [
    "https://chinese.freecodecamp.org",
    "https://github.com/microsoft/Generative-AI-for-beginners-dotnet/tree/main/translations/zh",
    "https://zh.d2l.ai/index.html",
]

ENTRY = re.compile(
    r"^(?P<indent>\s*)[*+-]\s+\[(?P<title>[^\]]+)\]"
    r"\((?P<url>[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)\)(?P<rest>.*)$"
)
LIST_ROW = re.compile(r"^\s*[*+-]\s+")
BAD_PCT = re.compile(r"%(?![0-9A-Fa-f]{2})")


def parse(text):
    entries, malformed = [], []
    for n, line in enumerate(text.splitlines(), 1):
        if not LIST_ROW.match(line):
            continue
        m = ENTRY.match(line)
        if m:
            entries.append({"line": n, "title": m["title"], "url": m["url"]})
        elif "[" in line or "](" in line:
            malformed.append({"line": n, "text": line.strip(), "reason": "unparseable row"})
    return entries, malformed


def url_problem(url):
    if not url:
        return "empty url"
    if url.startswith("#"):
        return None  # in-page anchor, valid
    if re.search(r"[\s<>\"]", url):
        return "illegal character (space, <, > or quote)"
    if BAD_PCT.search(url):
        return "bad percent-encoding"
    p = urlsplit(url)
    if p.scheme not in ("http", "https"):
        return "scheme must be http/https"
    if not p.netloc:
        return "missing host"
    return None


def norm(u):
    return u.rstrip("/")


def check_text(text, targets=TARGETS):
    entries, malformed = parse(text)
    bad_urls = [
        {"line": e["line"], "url": e["url"], "reason": r}
        for e in entries if (r := url_problem(e["url"]))
    ]
    found = {t: [e["line"] for e in entries if norm(e["url"]) == norm(t)] for t in targets}
    return {
        "entry_count": len(entries),
        "malformed": [m["line"] for m in malformed],
        "bad_urls": [b["line"] for b in bad_urls],
        "targets": found,
    }


FIXTURES = {
    "valid_rows": (
        "### 示例\n\n"
        "* [freeCodeCamp](https://chinese.freecodecamp.org)\n"
        "* [初学者的生成式 AI .NET - 一门课程](https://github.com/microsoft/Generative-AI-for-beginners-dotnet/tree/main/translations/zh)\n"
        "* [动手学深度学习](https://zh.d2l.ai/index.html) - 张三\n",
        {"entry_count": 3, "malformed": [], "bad_urls": [],
         "targets": {TARGETS[0]: [3], TARGETS[1]: [4], TARGETS[2]: [5]}},
    ),
    "malformed_rows": (
        "* [Broken](https://example.org\n"
        "* [NoUrl]()\n"
        "* [Ok](https://example.org/ok)\n",
        {"entry_count": 2, "malformed": [1], "bad_urls": [2],
         "targets": {t: [] for t in TARGETS}},
    ),
    "anchor_links": (
        "* [Index](#chinese)\n"
        "* [Ok](https://example.org/ok)\n",
        {"entry_count": 2, "malformed": [], "bad_urls": [],
         "targets": {t: [] for t in TARGETS}},
    ),
    "unusual_url_chars": (
        "* [Paren](https://en.wikipedia.org/wiki/Foo_(bar))\n"
        "* [CJK path](https://example.org/课程/索引.html#章-1)\n"
        "* [Encoded](https://example.org/%E4%B8%AD%E6%96%87)\n"
        "* [BadPct](https://example.org/%ZZ)\n"
        "* [Space](https://exa mple.org/x)\n",
        {"entry_count": 4, "malformed": [5], "bad_urls": [4],
         "targets": {t: [] for t in TARGETS}},
    ),
}


def self_test(inject_failure=False):
    def _blocked(*a, **k):
        raise RuntimeError("network access disabled in self-test")
    real_socket = socket.socket
    socket.socket = _blocked
    results, failed = [], False
    try:
        for name, (text, expected) in FIXTURES.items():
            exp = json.loads(json.dumps(expected))
            if inject_failure and name == "valid_rows":
                exp["entry_count"] = 99
            actual = check_text(text)
            ok = actual == exp
            failed |= not ok
            results.append({"fixture": name, "input": text, "expected": exp,
                            "actual": actual, "pass": ok})
            print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    finally:
        socket.socket = real_socket
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    (WORK_DIR / "self-test-report.json").write_text(
        json.dumps({"python": platform.python_version(), "platform": platform.platform(),
                    "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report: {WORK_DIR / 'self-test-report.json'}")
    return 1 if failed else 0


def live(timeout=10):
    import urllib.request
    for t in TARGETS:
        try:
            req = urllib.request.Request(t, method="HEAD", headers={"User-Agent": "course-check"})
            code = urllib.request.urlopen(req, timeout=timeout).status
        except Exception as e:
            code = f"error: {e}"
        print(f"{t} -> {code}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--inject-failure", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--file", default=DEFAULT_FILE)
    a = ap.parse_args()

    if a.self_test:
        sys.exit(self_test(a.inject_failure))

    res = check_text(Path(a.file).read_text(encoding="utf-8"))
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if a.live:
        live()
    sys.exit(1 if res["malformed"] or res["bad_urls"] or any(not v for v in res["targets"].values()) else 0)


if __name__ == "__main__":
    main()
