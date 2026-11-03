# agent-search

Keyless web search for agents. A SearXNG instance runs as a service container
inside GitHub Actions; you dispatch a query, you get JSON back.

## Use

Actions tab -> searxng-search -> Run workflow. Inputs: query, limit, categories.
Output: `results/results.json` artifact, one row per hit (title, url, snippet, engine).

## Notes

- No API keys. Public repos get free Actions minutes.
- Search engines may captcha datacenter IPs; keyless engines (DDG, Mojeek) hold up best.
- Trigger programmatically: POST /repos/{owner}/agent-search/actions/workflows/search.yml/dispatches with ref main.
