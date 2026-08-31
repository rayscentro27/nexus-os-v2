import json

from hermes import hermes_web_search as search


def test_canonical_searxng_url_is_primary(monkeypatch):
    monkeypatch.setenv("NEXUS_SEARXNG_WEB_SEARCH_BASE_URL", "http://127.0.0.1:18888")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "redacted-test-key")
    assert search._provider_priority()[0][0] == "searxng"


def test_brave_payment_limitation_does_not_hide_searxng(monkeypatch):
    monkeypatch.setenv("NEXUS_SEARXNG_WEB_SEARCH_BASE_URL", "http://private.test")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "redacted-test-key")
    monkeypatch.setattr(search, "_search_searxng", lambda query, max_results: {"status": "ok", "provider": "searxng", "results": [{"title": "fixture", "url": "https://example.test", "snippet": "fixture"}], "notes": []})
    monkeypatch.setattr(search, "_search_brave", lambda query, max_results: {"status": "provider_payment_required", "provider": "brave", "results": [], "notes": ["HTTP_402"]})
    result = search.web_search("fixture", max_results=1)
    assert result["provider"] == "searxng"
    assert result["results"]


def test_empty_searxng_and_paid_provider_continue_to_free_fallback(monkeypatch):
    monkeypatch.setenv("NEXUS_SEARXNG_WEB_SEARCH_BASE_URL", "http://private.test")
    monkeypatch.setenv("BRAVE_SEARCH_API_KEY", "redacted-test-key")
    monkeypatch.setattr(search, "_search_searxng", lambda query, max_results: {"status": "error", "provider": "searxng", "results": [], "notes": ["timeout"]})
    monkeypatch.setattr(search, "_search_brave", lambda query, max_results: {"status": "provider_payment_required", "provider": "brave", "results": [], "notes": ["HTTP_402"]})
    monkeypatch.setattr(search, "_search_duckduckgo_html", lambda query, max_results: {"status": "no_results", "provider": "duckduckgo_html", "results": [], "notes": ["no parsed results"]})
    monkeypatch.setattr(search, "_search_bing_html", lambda query, max_results: {"status": "ok", "provider": "bing_html", "results": [{"title": "fallback", "url": "https://example.test", "snippet": "free fallback"}], "notes": []})
    result = search.web_search("fixture", max_results=1)
    assert result["status"] == "ok"
    assert result["provider"] == "bing_html"
    assert result["results"]
    assert any(row["provider"] == "brave" and row["status"] == "provider_payment_required" for row in result["attempted_providers"])


def test_installation_report_is_redacted():
    report = json.loads(open("reports/certification/nexus_searxng_installation_latest.json", encoding="utf-8").read())
    assert report["security"]["secret_values_exposed"] is False
    assert "SEARXNG_SECRET" not in json.dumps(report)
