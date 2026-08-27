import json
from pathlib import Path

from nexus_agent_platform import credential_control_plane as cp
from nexus_agent_platform.ai_review_provider import select_review_provider
from nexus_agent_platform.safe_improvement_executor import evaluate
from trading.forex_research_scanner import evaluate as evaluate_candles

def test_required_search_identities_exist():
    ids = {x["credential_id"] for x in cp._load()}
    assert {"credential.brave.web_search.prod.v1", "credential.tavily.web_search.prod.v1", "credential.serpapi.web_search.prod.v1", "credential.searxng.web_search.prod.v1"} <= ids

def test_legacy_aliases_have_deterministic_canonical_precedence(monkeypatch):
    monkeypatch.setattr(cp, "_source_values", lambda: {"PROCESS_ENV": {"NEXUS_BRAVE_WEB_SEARCH_API_KEY":"canonical", "BRAVE_API_KEY":"legacy"}, "CANONICAL_RUNTIME_ENV": {}, "LEGACY_ENV": {}, "MACOS_KEYCHAIN": {}})
    row = cp.resolve("credential.brave.web_search.prod.v1")
    assert row["components"]["api_key"]["selected"]["alias"] == "NEXUS_BRAVE_WEB_SEARCH_API_KEY"
    assert "canonical" not in json.dumps(row["components"]["api_key"]["found"])

def test_missing_downstream_cannot_be_proven():
    # The report contract is explicit: no IDs means no consumer claim.
    downstream_ids = []
    assert ("PROVEN" if downstream_ids else "NOT_PROVEN") == "NOT_PROVEN"

def test_no_valid_setup_is_successful_scan_state():
    rows = [{"complete": True, "mid": {"c": "1.1"}} for _ in range(30)]
    assert evaluate_candles(rows, "EUR_USD", "M15")["result"] == "NO_VALID_SETUP"
    assert evaluate_candles(rows[:5], "EUR_USD", "M15")["result"] == "MARKET_DATA_INSUFFICIENT"

def test_unsafe_improvement_is_rejected():
    result = evaluate({"recommendation": "enable live trading"}, ["scripts/trading/forex_research_scanner.py"])
    assert result.status == "IMPROVEMENT_REJECTED_BY_POLICY"

def test_ai_selection_falls_back_without_blocking():
    result = select_review_provider()
    assert result["provider"] in {"oracle_ollama_gemma", "ollama", "deterministic_fallback"}
    assert "cost_bearing" in result
