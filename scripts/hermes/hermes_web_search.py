#!/usr/bin/env python3
"""
Hermes Web Search — Provider-abstracted safe web search layer.

Supports multiple search providers in priority order:
1. Brave Search (BRAVE_SEARCH_API_KEY)
2. Tavily (TAVILY_API_KEY)
3. SerpAPI (SERPAPI_API_KEY)
4. SearXNG (ALPHA_SEARXNG_URL) — existing Alpha connector
5. Safe fallback (no provider configured)

Usage:
  python3 scripts/hermes/hermes_web_search.py --query "best credit monitoring tools"
  python3 scripts/hermes/hermes_web_search.py --query "https://example.com" --url-mode
  python3 scripts/hermes/hermes_web_search.py --query "low-cost affiliate programs" --json
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
import ssl
from datetime import datetime, timezone

# SSL context for outbound requests
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

TIMEOUT = 12
MAX_RESULTS = 6
RECEIPT_DIR = "reports/hermes/web_search"


def _env(name):
    return os.environ.get(name, "").strip()


def _provider_priority():
    """Return ordered list of (name, env_key, available) tuples."""
    providers = []
    if _env("BRAVE_SEARCH_API_KEY"):
        providers.append(("brave", "BRAVE_SEARCH_API_KEY", True))
    if _env("TAVILY_API_KEY"):
        providers.append(("tavily", "TAVILY_API_KEY", True))
    if _env("SERPAPI_API_KEY"):
        providers.append(("serpapi", "SERPAPI_API_KEY", True))
    if _env("ALPHA_SEARXNG_URL"):
        providers.append(("searxng", "ALPHA_SEARXNG_URL", True))
    return providers


def _redact_error(err):
    """Remove potential secrets from error messages."""
    msg = str(err)
    for pattern in ["api_key", "token", "secret", "bearer", "sk-"]:
        msg = msg.replace(pattern, "[REDACTED]")
    return msg[:200]


def _save_receipt(query, provider, results, status, notes=None):
    """Save a search receipt (metadata only, no secrets)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = {
        "receipt_id": f"hermes_search_{ts}",
        "type": "web_search",
        "query": query[:200],
        "provider": provider,
        "status": status,
        "result_count": len(results),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "notes": notes or [],
    }
    os.makedirs(RECEIPT_DIR, exist_ok=True)
    path = os.path.join(RECEIPT_DIR, f"{receipt['receipt_id']}.json")
    with open(path, "w") as f:
        json.dump(receipt, f, indent=2)
    return receipt


# ── Brave Search ───────────────────────────────────────

def _search_brave(query, max_results=MAX_RESULTS):
    api_key = _env("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return {"status": "not_configured", "provider": "brave", "results": [], "notes": ["BRAVE_SEARCH_API_KEY not set"]}

    try:
        params = urllib.parse.urlencode({"q": query, "count": min(max_results, 10)})
        url = f"https://api.search.brave.com/res/v1/web/search?{params}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in (data.get("web", {}).get("results", []))[:max_results]:
            results.append({
                "title": str(item.get("title", ""))[:200],
                "url": str(item.get("url", "")),
                "snippet": str(item.get("description", ""))[:500],
                "source": "brave",
                "published_at": item.get("page_age"),
            })

        return {
            "status": "ok",
            "provider": "brave",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "notes": [],
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "brave",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "notes": [_redact_error(e)],
        }


# ── Tavily Search ──────────────────────────────────────

def _search_tavily(query, max_results=MAX_RESULTS):
    api_key = _env("TAVILY_API_KEY")
    if not api_key:
        return {"status": "not_configured", "provider": "tavily", "results": [], "notes": ["TAVILY_API_KEY not set"]}

    try:
        payload = json.dumps({
            "api_key": api_key,
            "query": query,
            "max_results": min(max_results, 10),
            "search_depth": "basic",
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in (data.get("results", []))[:max_results]:
            results.append({
                "title": str(item.get("title", ""))[:200],
                "url": str(item.get("url", "")),
                "snippet": str(item.get("content", ""))[:500],
                "source": "tavily",
                "published_at": item.get("published_date"),
            })

        return {
            "status": "ok",
            "provider": "tavily",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "notes": [],
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "tavily",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "notes": [_redact_error(e)],
        }


# ── SerpAPI Search ─────────────────────────────────────

def _search_serpapi(query, max_results=MAX_RESULTS):
    api_key = _env("SERPAPI_API_KEY")
    if not api_key:
        return {"status": "not_configured", "provider": "serpapi", "results": [], "notes": ["SERPAPI_API_KEY not set"]}

    try:
        params = urllib.parse.urlencode({
            "q": query,
            "api_key": api_key,
            "engine": "google",
            "num": min(max_results, 10),
        })
        url = f"https://serpapi.com/search.json?{params}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in (data.get("organic_results", []))[:max_results]:
            results.append({
                "title": str(item.get("title", ""))[:200],
                "url": str(item.get("link", "")),
                "snippet": str(item.get("snippet", ""))[:500],
                "source": "serpapi",
                "published_at": item.get("date"),
            })

        return {
            "status": "ok",
            "provider": "serpapi",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "notes": [],
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "serpapi",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "notes": [_redact_error(e)],
        }


# ── SearXNG Search (existing Alpha connector) ──────────

def _search_searxng(query, max_results=MAX_RESULTS):
    base = _env("ALPHA_SEARXNG_URL")
    if not base:
        return {"status": "not_configured", "provider": "searxng", "results": [], "notes": ["ALPHA_SEARXNG_URL not set"]}

    try:
        params = urllib.parse.urlencode({"q": query, "format": "json"})
        url = f"{base.rstrip('/')}/search?{params}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "NexusHermes/1.0",
        })
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        results = []
        for item in (data.get("results", []))[:max_results]:
            results.append({
                "title": str(item.get("title", ""))[:200],
                "url": str(item.get("url", "")),
                "snippet": str(item.get("content", ""))[:500],
                "source": "searxng",
                "published_at": item.get("publishedDate"),
            })

        return {
            "status": "ok",
            "provider": "searxng",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": results,
            "notes": [],
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "searxng",
            "query": query,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
            "notes": [_redact_error(e)],
        }


# ── Safe Fallback ──────────────────────────────────────

def _fallback_not_configured(query):
    providers = _provider_priority()
    available = [p[0] for p in providers]
    missing = []
    if not _env("BRAVE_SEARCH_API_KEY"):
        missing.append("BRAVE_SEARCH_API_KEY")
    if not _env("TAVILY_API_KEY"):
        missing.append("TAVILY_API_KEY")
    if not _env("SERPAPI_API_KEY"):
        missing.append("SERPAPI_API_KEY")
    if not _env("ALPHA_SEARXNG_URL"):
        missing.append("ALPHA_SEARXNG_URL")

    return {
        "status": "not_configured",
        "provider": "none",
        "query": query,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": [],
        "notes": [
            f"No web search provider configured.",
            f"Available providers with keys: {', '.join(available) if available else 'none'}",
            f"Missing env vars: {', '.join(missing)}",
            "Add one key to enable live web search.",
        ],
    }


# ── Public API ─────────────────────────────────────────

def web_search(query, max_results=MAX_RESULTS):
    """
    Search the web using the best available provider.
    Returns a dict with status, provider, results, and notes.
    """
    providers = _provider_priority()

    if not providers:
        result = _fallback_not_configured(query)
        _save_receipt(query, "none", [], "not_configured", result["notes"])
        return result

    # Try providers in priority order
    search_fn = {
        "brave": _search_brave,
        "tavily": _search_tavily,
        "serpapi": _search_serpapi,
        "searxng": _search_searxng,
    }

    for name, env_key, available in providers:
        fn = search_fn.get(name)
        if fn:
            result = fn(query, max_results)
            if result["status"] == "ok":
                _save_receipt(query, name, result["results"], "ok")
                return result
            # If error, try next provider

    # All providers failed
    result = _fallback_not_configured(query)
    _save_receipt(query, "none", [], "all_providers_failed", result["notes"])
    return result


def url_review(url, topic=None):
    """
    Review a specific URL. Uses SearXNG or Brave to find context about the URL.
    Returns structured review data.
    """
    query = f"site:{url} {topic or ''}".strip()
    search_result = web_search(query, max_results=3)

    review = {
        "url": url,
        "topic": topic or "",
        "status": search_result["status"],
        "provider": search_result["provider"],
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "results": search_result["results"],
        "notes": search_result["notes"],
    }

    if search_result["status"] == "ok" and search_result["results"]:
        review["summary"] = search_result["results"][0].get("snippet", "")
        review["title"] = search_result["results"][0].get("title", "")
    else:
        review["summary"] = f"Could not retrieve live info for {url}"
        review["title"] = ""

    _save_receipt(url, search_result["provider"], search_result["results"], search_result["status"],
                  [f"url_review: {url}"])

    return review


def main():
    parser = argparse.ArgumentParser(description="Hermes Web Search")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--url-mode", action="store_true", help="URL review mode")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--max-results", type=int, default=MAX_RESULTS, help="Max results")
    args = parser.parse_args()

    if args.url_mode:
        result = url_review(args.query)
    else:
        result = web_search(args.query, args.max_results)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Provider: {result['provider']}")
        print(f"Status: {result['status']}")
        print(f"Results: {len(result['results'])}")
        for i, r in enumerate(result["results"][:5], 1):
            print(f"  {i}. {r['title'][:60]}")
            print(f"     {r['url'][:80]}")
        if result["notes"]:
            print(f"Notes: {'; '.join(result['notes'][:3])}")


if __name__ == "__main__":
    main()
