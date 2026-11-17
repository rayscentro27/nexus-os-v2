from __future__ import annotations

from urllib.parse import urlsplit

from scripts.nexus_agent_platform import proactive_discovery as discovery


def test_duckduckgo_result_title_and_snippet_are_parsed_into_candidates(monkeypatch):
    html = b'''<div class="results"><div class="result results_links">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.sba.gov%2Floans%2Flender-match%2F">SBA Lender Match</a>
      <a class="result__snippet">Prepare a business plan, amount and use of funds, credit history, financial projections, and compare rates and fees.</a>
    </div></div>'''
    calls = []
    def read(url, **kwargs):
        calls.append(urlsplit(url).hostname)
        return html
    monkeypatch.setattr(discovery, "_governed_public_get", read)
    result = discovery.web_search("small business funding readiness documents and lender terms", 5)
    assert result["status"] == "PASS"
    assert len(result["results"]) == 1
    row = result["results"][0]
    assert row["url"] == "https://www.sba.gov/loans/lender-match/"
    assert "financial projections" in row["snippet"].lower()
    assert calls == ["html.duckduckgo.com"]


def test_bing_fallback_parses_result_snippet_and_keeps_relevance_screen(monkeypatch):
    ddg = b'''<div class="result"><a class="result__a" href="https://unrelated.example/page">Unrelated result</a><a class="result__snippet">This page is about travel photography and recipes.</a></div>'''
    bing = b'''<li class="b_algo"><h2><a href="https://www.sba.gov/funding-programs/loans/7a-loans">SBA 7(a) Loans</a></h2><div class="b_caption"><p>Small businesses must be operating, creditworthy, and demonstrate a reasonable ability to repay.</p></div></li>'''
    calls = []
    def read(url, **kwargs):
        host = urlsplit(url).hostname
        calls.append(host)
        return ddg if host == "html.duckduckgo.com" else bing
    monkeypatch.setattr(discovery, "_governed_public_get", read)
    result = discovery.web_search("small business funding eligibility repayment", 5)
    assert result["status"] == "PASS"
    assert result["provider"] == "bing_html"
    assert result["results"][0]["url"] == "https://www.sba.gov/funding-programs/loans/7a-loans"
    assert "creditworthy" in result["results"][0]["snippet"].lower()
    assert calls == ["html.duckduckgo.com", "www.bing.com"]


def test_bing_rss_fallback_returns_structured_relevant_results(monkeypatch):
    ddg = b"<html><title>DuckDuckGo</title><body>challenge</body></html>"
    bing_html = b"<html><head><title>Search</title></head><body>interstitial</body></html>"
    bing_rss = b'''<?xml version="1.0"?><rss><channel><item>
      <title>SBA 7(a) loan eligibility</title>
      <link>https://www.sba.gov/funding-programs/loans/7a-loans</link>
      <description>Applicants must demonstrate creditworthiness and a reasonable ability to repay.</description>
    </item></channel></rss>'''
    calls = []
    def read(url, **kwargs):
        calls.append((urlsplit(url).hostname, urlsplit(url).query))
        if len(calls) == 1:
            return ddg
        if len(calls) == 2:
            return bing_html
        return bing_rss
    monkeypatch.setattr(discovery, "_governed_public_get", read)
    result = discovery.web_search("SBA 7(a) loan eligibility reasonable repayment", 5)
    assert result["status"] == "PASS"
    assert result["provider"] == "bing_rss"
    assert result["results"][0]["url"].startswith("https://www.sba.gov/")
    assert "creditworthiness" in result["results"][0]["snippet"].lower()
    assert "format=rss" in calls[-1][1]
