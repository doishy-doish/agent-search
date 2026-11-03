#!/usr/bin/env python3
"""Query the local SearXNG service (HTML format; stock images only enable html), save JSON results. stdlib only."""
import html as ihtml
import json, os, sys, time, traceback, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser
BASE = os.environ.get("SEARXNG_URL", "http://localhost:8888")
QUERY = os.environ.get("SEARCH_QUERY", "USDC bounty open source")
LIMIT = int(os.environ.get("SEARCH_LIMIT", "10"))
CATEGORIES = os.environ.get("SEARCH_CATEGORIES", "general,it")
OUT = os.environ.get("SEARCH_OUT", "results/results.json")
UA = {"User-Agent": "Mozilla/5.0 (agent-search)", "Accept": "text/html"}
class ResultsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.cur = None
        self.in_h3 = False
        self.in_a = False
        self.in_content = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        if tag == "article" and "result" in cls.split():
            self.cur = {"title": "", "url": "", "content": "", "engine": ""}
        elif self.cur is not None:
            if tag == "h3":
                self.in_h3 = True
            elif tag == "a" and self.in_h3 and not self.cur["url"]:
                self.cur["url"] = a.get("href", "")
                self.in_a = True
            elif tag == "p" and "content" in cls.split():
                self.in_content = True
    def handle_data(self, data):
        if self.cur is None:
            return
        if self.in_a:
            self.cur["title"] += data
        elif self.in_content:
            self.cur["content"] += data
    def handle_endtag(self, tag):
        if tag == "a":
            self.in_a = False
        elif tag == "h3":
            self.in_h3 = False
        elif tag == "p" and self.in_content:
            self.in_content = False
        elif tag == "article" and self.cur is not None:
            c = self.cur
            c["title"] = ihtml.unescape(c["title"]).strip()
            c["content"] = ihtml.unescape(c["content"]).strip()[:300]
            if c["url"] and not c["url"].startswith(("http://", "https://", "/")):
                c["url"] = ""
            if c["title"] and c["url"]:
                self.items.append(c)
            self.cur = None
def fetch(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
def wait_ready(timeout=150):
    s = time.time()
    last = ""
    while time.time() - s < timeout:
        try:
            st, body = fetch(BASE + "/", 5)
            if st == 200:
                return True, ""
            last = f"root -> {st}"
        except Exception as e:
            last = f"{type(e).__name__}: {e}"
        time.sleep(3)
    return False, last
def search(q):
    url = BASE + "/search?" + urllib.parse.urlencode({"q": q, "categories": CATEGORIES})
    st, body = fetch(url, 30)
    if st != 200:
        raise RuntimeError(f"search -> HTTP {st}: {body[:200]!r}")
    p = ResultsParser()
    p.feed(body.decode("utf-8", "replace"))
    return p.items[:LIMIT]
def main():
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    try:
        ok, last = wait_ready()
        if not ok:
            raise RuntimeError(f"service not ready: {last}")
        items = search(QUERY)
        with open(OUT, "w") as f:
            json.dump({"query": QUERY, "count": len(items), "items": items}, f, indent=2)
        print(f"saved {len(items)} results to {OUT}")
        for it in items:
            print(f"- {it['title']} :: {it['url']}")
    except Exception:
        with open("results/debug.txt", "w") as f:
            f.write(traceback.format_exc())
        print(traceback.format_exc())
        sys.exit(1)
if __name__ == "__main__":
    main()
