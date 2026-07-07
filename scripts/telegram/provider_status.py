#!/usr/bin/env python3
"""
Provider Status — Centralized web search provider detection.

Single source of truth for which search provider is active.
Used by /report, Hermes web search, Alpha research, retrieval gate, deeper research.
"""

import os


def get_web_provider_status():
    """
    Return the current web search provider status.
    Returns a dict with provider name and status string.
    """
    brave = os.environ.get("BRAVE_SEARCH_API_KEY", "").strip()
    tavily = os.environ.get("TAVILY_API_KEY", "").strip()
    serpapi = os.environ.get("SERPAPI_API_KEY", "").strip()
    searxng = os.environ.get("ALPHA_SEARXNG_URL", "").strip()

    if brave:
        return {"provider": "brave", "status": "ACTIVE_BRAVE", "available": True}
    if tavily:
        return {"provider": "tavily", "status": "ACTIVE_TAVILY", "available": True}
    if serpapi:
        return {"provider": "serpapi", "status": "ACTIVE_SERPAPI", "available": True}
    if searxng:
        return {"provider": "searxng", "status": "ACTIVE_SEARXNG", "available": True}

    return {"provider": None, "status": "LAYER_READY_PROVIDER_MISSING", "available": False}


def get_provider_display_name(provider_status):
    """Return a human-readable provider display name."""
    p = provider_status.get("provider")
    if p == "brave":
        return "Brave Search"
    if p == "tavily":
        return "Tavily"
    if p == "serpapi":
        return "SerpAPI"
    if p == "searxng":
        return "SearXNG"
    return "none"


def is_web_available():
    """Quick check if any web provider is active."""
    return get_web_provider_status()["available"]
