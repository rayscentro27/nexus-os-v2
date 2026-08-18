import json

from nexus_agent_platform.brief.daily_brief import build_daily_brief


def test_daily_brief_is_report_backed_and_has_contract_fields():
    brief = build_daily_brief()
    required = {
        "brief_id", "generated_at", "scope", "status", "top_priority",
        "highest_value_next_action", "money_opportunity", "revenue_status",
        "revenue_risks", "opportunity_updates", "research_updates",
        "creative_updates", "builder_updates", "loop_updates",
        "marketing_updates", "client_attention", "approvals_needed",
        "system_health", "provider_health", "worker_health", "cost_summary",
        "token_summary", "deterministic_execution_share", "ai_execution_share",
        "blockers", "decisions_needed", "recommended_actions", "evidence_refs",
        "confidence", "freshness",
    }
    assert required <= brief.keys()
    assert brief["status"] == "REPORT_BACKED_PARTIAL"
    assert brief["freshness"]["live_supabase_read"] == "NOT_AVAILABLE"


def test_daily_brief_preserves_real_opportunity_and_cost_facts():
    brief = build_daily_brief()
    opportunity = brief["opportunity_updates"][0]
    revenue = brief["revenue_status"]
    cost = brief["cost_summary"]

    assert opportunity["id"] == "unclecode_crawl4ai"
    assert opportunity["status"] == "PILOT_PROPOSED"
    assert opportunity["change"] == "UNKNOWN"
    assert revenue["confirmed_revenue_usd"] == 0
    assert revenue["pending_test_revenue_usd"] == 97
    assert revenue["possible_offer_value_usd"] == 1215
    assert cost["deterministic_execution_share"] == 1.0
    assert cost["ai_execution_share"] == 0.0
    assert cost["input_tokens"] == 0
    assert cost["output_tokens"] == 0
    assert cost["provider_cost_usd"] == 0.0
    assert cost["zero_token_executions"] >= 1


def test_daily_brief_exposes_worker_health_without_secrets():
    brief = build_daily_brief()
    classifications = {row["worker_id"]: row["classification"] for row in brief["worker_health"]}
    assert classifications["codex"] == "AVAILABLE"
    assert classifications["opencode"] == "UNAVAILABLE"
    assert classifications["mimo"] == "INSTALLED_UNPROVEN"
    assert classifications["local_python"] == "AVAILABLE"
    assert classifications["openhands"] == "NOT_INSTALLED"

    serialized = json.dumps(brief).lower()
    assert "sk-" not in serialized
    assert "authorization: bearer" not in serialized
