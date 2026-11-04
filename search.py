import json, os, time, urllib.request, urllib.parse

STREAM = os.environ.get("SEARCH_STREAM", "bot")
TARGETS = [t.strip() for t in os.environ.get("SEARCH_TARGET", "bountic-bot").split(",") if t.strip()]
LIMIT = int(os.environ.get("SEARCH_LIMIT", "10"))
GHTOKEN = os.environ.get("GITHUB_TOKEN", "")
RPCS = ["https://base-rpc.publicnode.com", "https://base.meowrpc.com"]
HEALTH_URLS = {
    "payanagent-api": "https://payanagent.com/api/v1/offers?sort=top&limit=1",
}


def gh_get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "agent-search"}
    if GHTOKEN:
        headers["Authorization"] = "Bearer " + GHTOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def rpc_post(url, method, params):
    payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": 1}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def health_targets():
    checks = []
    for name, url in HEALTH_URLS.items():
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agent-search-health"})
            with urllib.request.urlopen(req, timeout=10) as r:
                checks.append({"target": name, "alive": r.status == 200, "status": r.status})
        except Exception as e:
            checks.append({"target": name, "alive": False, "status": getattr(e, "code", "error")})
    return checks


def bot_targets(targets):
    items = []
    for name in targets:
        q = "commenter:app/%s is:open is:issue" % name
        url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(q) + "&per_page=%d" % LIMIT
        try:
            j = gh_get(url)
        except Exception:
            continue
        time.sleep(10)
        for it in (j.get("items") or [])[:LIMIT]:
            items.append({"stream": "bot:" + name, "title": it.get("title", ""),
                          "url": it.get("html_url", ""), "content": (it.get("body") or "")[:300]})
    return "bot-watch:" + ",".join(targets), items


def base_targets(addrs):
    cur = None
    rpc_url = None
    for ep in RPCS:
        try:
            b = rpc_post(ep, "eth_blockNumber", [])
            cur = int(b["result"], 16)
            rpc_url = ep
            break
        except Exception:
            continue
    if cur is None:
        return "base-watch:" + ",".join(addrs), []
    items = []
    for addr in addrs:
        try:
            g = rpc_post(rpc_url, "eth_getLogs",
                         [{"address": addr, "fromBlock": hex(cur - 2000), "toBlock": "latest"}])
            logs = g.get("result") or []
        except Exception:
            continue
        for l in logs[:LIMIT]:
            tx = l.get("transactionHash", "")
            items.append({"stream": "base:" + addr, "title": tx,
                          "url": "https://basescan.org/tx/" + tx,
                          "content": "block %s t0 %s" % (l.get("blockNumber"), (l.get("topics") or ["?"])[0])})
    return "base-watch:" + ",".join(addrs), items


if STREAM == "base":
    query, items = base_targets(TARGETS)
else:
    query, items = bot_targets(TARGETS)

health = health_targets()

os.makedirs("results", exist_ok=True)
with open("results/results.json", "w") as f:
    json.dump({"query": query, "count": len(items), "items": items, "health": health}, f, indent=2)
print("wrote %d items for %s health=%s" % (len(items), query, health))
