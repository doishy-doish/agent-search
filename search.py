#!/usr/bin/env python3
"""Query the local SearXNG service, save JSON results. stdlib only."""
import json, os, sys, time, traceback, urllib.error, urllib.parse, urllib.request
BASE = os.environ.get("SEARXNG_URL", "http://localhost:8888")
QUERY = os.environ.get("SEARCH_QUERY", "USDC bounty open source")
LIMIT = int(os.environ.get("SEARCH_LIMIT", "10"))
CATEGORIES = os.environ.get("SEARCH_CATEGORIES", "general,it")
OUT = os.environ.get("SEARCH_OUT", "results/results.json")
UA = {"User-Agent": "Mozilla/5.0 (agent-search)", "Accept": "application/json"}
def fetch(url, timeout, post=False):
    data = urllib.parse.urlencode({"q": QUERY, "format": "json", "categories": CATEGORIES}).encode() if post else None
    req = urllib.request.Request(url if not post else BASE + "/search", data=data, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read() + b"\nHDR:" + str(sorted(e.headers.items())).encode()
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
    url = BASE + "/search?" + urllib.parse.urlencode({"q": q, "format": "json", "categories": CATEGORIES})
    st, body = fetch(url, 30)
    if st == 403:
        st, body = fetch(url, 30, post=True)
    if st != 200:
        probe = {}
        for path in ["/config", "/healthz", "/stats/errors"]:
            try:
                pst, pbody = fetch(BASE + path, 10)
                probe[path] = [pst, pbody[:200]]
            except Exception as pe:
                probe[path] = ["exc", str(pe)[:150]]
        raise RuntimeError(f"search -> HTTP {st}: {body[:300]!r} PROBE={json.dumps(probe)[:800]}")
    try:
        data = json.loads(body)
    except Exception:
        raise RuntimeError(f"non-JSON response (HTTP {st}): {body[:300]!r}")
    return [{"title": it.get("title", ""), "url": it.get("url", ""), "content": (it.get("content", "") or "")[:300], "engine": it.get("engine", "")} for it in data.get("results", [])[:LIMIT]]
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
