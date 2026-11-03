#!/usr/bin/env python3
"""Query the local SearXNG service, save JSON results. stdlib only."""
import json, os, sys, time, urllib.parse, urllib.request
BASE = os.environ.get("SEARXNG_URL", "http://localhost:8888")
QUERY = os.environ.get("SEARCH_QUERY", "USDC bounty open source")
LIMIT = int(os.environ.get("SEARCH_LIMIT", "10"))
CATEGORIES = os.environ.get("SEARCH_CATEGORIES", "general,it")
OUT = os.environ.get("SEARCH_OUT", "results/results.json")
def wait_ready(timeout=150):
    s = time.time()
    while time.time() - s < timeout:
        try:
            with urllib.request.urlopen(BASE + "/", timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(3)
    return False
def search(q):
    url = BASE + "/search?" + urllib.parse.urlencode({"q": q, "format": "json", "categories": CATEGORIES})
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    return [{"title": it.get("title", ""), "url": it.get("url", ""), "content": (it.get("content", "") or "")[:300], "engine": it.get("engine", "")} for it in data.get("results", [])[:LIMIT]]
def main():
    if not wait_ready():
        print("SearXNG not ready", flush=True)
        sys.exit(1)
    items = search(QUERY)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"query": QUERY, "count": len(items), "items": items}, f, indent=2)
    print(f"saved {len(items)} results to {OUT}")
    for it in items:
        print(f"- {it['title']} :: {it['url']}")
if __name__ == "__main__":
    main()
