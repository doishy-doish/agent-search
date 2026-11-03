import json, os, urllib.request, urllib.parse

STREAM = os.environ.get("SEARCH_STREAM", "bot")
TARGET = os.environ.get("SEARCH_TARGET", "bountic-bot")
LIMIT = int(os.environ.get("SEARCH_LIMIT", "10"))
GHTOKEN = os.environ.get("GITHUB_TOKEN", "")

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

def bot_stream():
    q = "commenter:app/%s is:open is:issue" % TARGET
    url = "https://api.github.com/search/issues?q=" + urllib.parse.quote(q) + "&per_page=%d" % LIMIT
    try:
        j = gh_get(url)
    except Exception as e:
        return "commenter:app/%s" % TARGET, []
    items = []
    for it in (j.get("items") or [])[:LIMIT]:
        items.append({"title": it.get("title", ""), "url": it.get("html_url", ""), "content": (it.get("body") or "")[:300]})
    return q, items

def base_stream():
    eps = ["https://base-rpc.publicnode.com"]
    cur = None
    for ep in eps:
        try:
            b = rpc_post(ep, "eth_blockNumber", [])
            cur = int(b["result"], 16)
            rpc_url = ep
            break
        except Exception:
            continue
    if cur is None:
        return "base-logs:%s" % TARGET, []
    frm = hex(cur - 2000)
    try:
        g = rpc_post(rpc_url, "eth_getLogs", [{"address": TARGET, "fromBlock": frm, "toBlock": "latest"}])
        logs = g.get("result") or []
    except Exception:
        logs = []
    items = []
    for l in logs[:LIMIT]:
        tx = l.get("transactionHash", "")
        items.append({"title": tx, "url": "https://basescan.org/tx/" + tx, "content": "block %s topics %s" % (l.get("blockNumber"), json.dumps(l.get("topics", [])))})
    return "base-logs:%s" % TARGET, items

if STREAM == "base":
    query, items = base_stream()
else:
    query, items = bot_stream()

os.makedirs("results", exist_ok=True)
with open("results/results.json", "w") as f:
    json.dump({"query": query, "count": len(items), "items": items}, f, indent=2)
print("wrote %d items for %s" % (len(items), query))
