#!/usr/bin/env python3
"""Idempotent seed for the Nexus OS v2 premium foundation (migration 0003).

Uses SUPABASE_SERVICE_ROLE_KEY server-side. Never prints secrets. Re-runnable:
- registry tables upsert on their unique key (workspace_key, agent_key, etc.)
- proof rows (nexus_events / agent_jobs / telegram_messages / sample opp+brief) are inserted
  only if an equivalent row does not already exist
- system_health inserts only components not already present

No real Telegram sends, no social publish, no trading.

Run AFTER `supabase db push` (or applying 0001-0003). On macOS, if SSL fails:
    SSL_CERT_FILE="$(python3 -m certifi)" python3 scripts/seed_premium_foundation.py
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(errors="ignore").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = load_env()
URL = (ENV.get("SUPABASE_URL") or ENV.get("VITE_SUPABASE_URL") or "").rstrip("/")
KEY = ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")


def _req(method: str, path: str, body=None, extra=None):
    h = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}
    if extra:
        h.update(extra)
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(f"{URL}{path}", data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read().decode(errors="ignore")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        b = e.read().decode(errors="ignore")
        if KEY:
            b = b.replace(KEY, "<redacted>")
        return e.code, b[:200]


def upsert(table: str, rows: list[dict], on_conflict: str) -> str:
    # PostgREST bulk insert requires a uniform key set across all rows; fill missing keys.
    keys: set[str] = set()
    for r in rows:
        keys.update(r.keys())
    norm = [{k: r.get(k) for k in keys} for r in rows]
    st, _ = _req("POST", f"/rest/v1/{table}?on_conflict={on_conflict}", body=norm,
                 extra={"Prefer": "resolution=merge-duplicates,return=minimal"})
    return f"{table}: upsert {len(rows)} ({st})"


def insert_if_absent(table: str, col: str, value: str, row: dict) -> str:
    q = urllib.parse.quote(value, safe="")
    st, rows = _req("GET", f"/rest/v1/{table}?select=id&{col}=eq.{q}&limit=1")
    if isinstance(rows, list) and rows:
        return f"{table}: exists (skip)"
    st, _ = _req("POST", f"/rest/v1/{table}", body=[row], extra={"Prefer": "return=minimal"})
    return f"{table}: inserted ({st})"


def main() -> int:
    if not URL or not KEY:
        print("SETUP NEEDED: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY required in .env (not printed).")
        return 2

    out = []
    out.append(upsert("workspaces", [
        {"workspace_key": "nexus_internal", "name": "Nexus Internal", "workspace_type": "internal"},
        {"workspace_key": "goclear_apex", "name": "GoClear / Apex Funding", "workspace_type": "client"},
        {"workspace_key": "cloneforge", "name": "CloneForge", "workspace_type": "internal"},
        {"workspace_key": "trading_lab", "name": "Trading Lab", "workspace_type": "research"},
        {"workspace_key": "creative_studio", "name": "Creative Studio", "workspace_type": "internal"},
        {"workspace_key": "seo_marketing", "name": "SEO / Marketing OS", "workspace_type": "internal"},
    ], "workspace_key"))

    out.append(upsert("agent_registry", [
        {"agent_key": "hermes_operator", "name": "Hermes", "role": "plain_language_operator", "status": "active"},
        {"agent_key": "nexus_job_router", "name": "Nexus Job Router", "role": "executor_router", "status": "stubbed"},
        {"agent_key": "creative_strategist", "name": "Creative Strategist", "role": "creative", "status": "stubbed"},
        {"agent_key": "monetization_judge", "name": "Monetization Judge", "role": "monetization", "status": "stubbed"},
        {"agent_key": "opportunity_scout", "name": "Opportunity Scout", "role": "research", "status": "stubbed"},
        {"agent_key": "trading_researcher", "name": "Trading Researcher", "role": "trading_research", "status": "stubbed"},
        {"agent_key": "seo_marketing_agent", "name": "SEO Marketing Agent", "role": "seo", "status": "stubbed"},
        {"agent_key": "ops_doctor", "name": "Ops Doctor", "role": "ops", "status": "stubbed"},
        {"agent_key": "improvement_scout", "name": "Improvement Scout", "role": "improvement", "status": "stubbed"},
    ], "agent_key"))

    out.append(upsert("model_providers", [
        {"provider_key": "openrouter", "name": "OpenRouter", "provider_type": "cloud_aggregator", "secret_env_name": "OPENROUTER_API_KEY", "privacy_level": "public_ok"},
        {"provider_key": "nvidia_nim", "name": "NVIDIA NIM", "provider_type": "cloud", "secret_env_name": "NVIDIA_NIM_API_KEY", "privacy_level": "public_ok"},
        {"provider_key": "ollama", "name": "Ollama (local)", "provider_type": "local", "secret_env_name": "OLLAMA_URL", "privacy_level": "private"},
        {"provider_key": "local_llamacpp", "name": "llama.cpp (local)", "provider_type": "local", "privacy_level": "private"},
        {"provider_key": "chatgpt_manual", "name": "ChatGPT (manual)", "provider_type": "manual", "privacy_level": "manual"},
        {"provider_key": "claude_manual", "name": "Claude (manual)", "provider_type": "manual", "privacy_level": "manual"},
        {"provider_key": "gemini_manual", "name": "Gemini (manual)", "provider_type": "manual", "privacy_level": "manual"},
    ], "provider_key"))

    out.append(upsert("model_routes", [
        {"route_key": "hermes_reasoning", "task_type": "reasoning", "primary_provider_key": "claude_manual", "sensitive_data_allowed": True},
        {"route_key": "research_extraction", "task_type": "extraction", "primary_provider_key": "openrouter", "sensitive_data_allowed": False},
        {"route_key": "receipt_summarization", "task_type": "summarization", "primary_provider_key": "openrouter", "sensitive_data_allowed": False},
        {"route_key": "monetization_scoring", "task_type": "scoring", "primary_provider_key": "openrouter", "sensitive_data_allowed": False},
        {"route_key": "creative_drafting", "task_type": "creative", "primary_provider_key": "openrouter", "sensitive_data_allowed": False},
        {"route_key": "creative_qa", "task_type": "qa", "primary_provider_key": "claude_manual", "sensitive_data_allowed": False},
        {"route_key": "seo_analysis", "task_type": "seo", "primary_provider_key": "openrouter", "sensitive_data_allowed": False},
        {"route_key": "trading_research", "task_type": "trading", "primary_provider_key": "openrouter", "sensitive_data_allowed": False},
        {"route_key": "ops_diagnostics", "task_type": "ops", "primary_provider_key": "ollama", "sensitive_data_allowed": True},
    ], "route_key"))

    integrations = [
        ("meta_facebook", "Meta Facebook", "social", True, ["META_PAGE_ACCESS_TOKEN", "META_PAGE_ID"], "high"),
        ("meta_instagram", "Meta Instagram", "social", True, ["META_PAGE_ACCESS_TOKEN", "META_INSTAGRAM_ACCOUNT_ID"], "high"),
        ("telegram", "Telegram", "comms", True, ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"], "medium"),
        ("oanda_demo", "Oanda Demo", "trading", True, ["OANDA_API_KEY", "OANDA_ACCOUNT_ID"], "high"),
        ("github", "GitHub", "dev", True, ["GITHUB_TOKEN"], "medium"),
        ("youtube_transcripts", "YouTube Transcripts", "research", False, [], "low"),
        ("google_search_console", "Google Search Console", "seo", True, ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"], "medium"),
        ("google_analytics", "Google Analytics", "seo", True, ["GOOGLE_CLIENT_ID"], "medium"),
        ("dataforseo", "DataForSEO", "seo", True, ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"], "medium"),
        ("notebooklm_manual", "NotebookLM (manual)", "research", False, [], "low"),
        ("agent_reach", "Agent Reach", "outreach", False, [], "high"),
        ("wayland_reference", "Wayland (reference)", "reference", False, [], "low"),
        ("vibe_trading_reference", "Vibe Trading (reference)", "reference", False, [], "low"),
        ("markitdown", "MarkItDown", "research", False, [], "low"),
        ("firecrawl", "Firecrawl", "research", True, ["FIRECRAWL_API_KEY"], "medium"),
        ("browser_use", "Browser Use", "automation", False, [], "high"),
        ("graphrag", "GraphRAG", "research", False, [], "medium"),
        ("supermemory", "SuperMemory", "memory", True, ["SUPERMEMORY_API_KEY"], "medium"),
    ]
    out.append(upsert("integration_registry", [
        {"integration_key": k, "name": n, "category": c, "enabled": False, "status": "registered",
         "requires_secret": rs, "secret_env_names": envs, "risk_level": risk}
        for (k, n, c, rs, envs, risk) in integrations
    ], "integration_key"))

    out.append(upsert("trading_risk_rules", [
        {"rule_key": "paper_only_default", "description": "Default to paper/demo only.", "value": {"paper_only": True}},
        {"rule_key": "live_trading_disabled", "description": "Live trading is disabled.", "value": {"live": False}},
        {"rule_key": "approval_required_for_live", "description": "Live requires explicit approval.", "value": {"approval": True}},
        {"rule_key": "no_client_performance_claims_without_proof", "description": "No performance claims without proof + approval.", "value": {}},
        {"rule_key": "demo_trade_limit_required", "description": "Demo trades need a limit + SL/TP.", "value": {"sl_tp_required": True}},
    ], "rule_key"))

    out.append(upsert("partner_offers", [
        {"offer_key": "goclear_credit_monitoring", "name": "Credit Monitoring (partner)", "category": "credit",
         "why_it_matters": "Track readiness changes; not a guarantee.", "approval_status": "draft", "risk_level": "medium",
         "secret_env_name": "PARTNER_CREDIT_MONITORING_KEY"},
        {"offer_key": "goclear_business_formation", "name": "Business Formation (partner)", "category": "business_setup",
         "why_it_matters": "Entity + EIN readiness for fundability.", "approval_status": "draft", "risk_level": "low"},
    ], "offer_key"))

    # Sample opportunity / campaign / brief (idempotent by stable text/key)
    out.append(insert_if_absent("monetization_opportunities", "title", "Sample: Repurpose funding YouTube into a $97 readiness lead magnet",
        {"title": "Sample: Repurpose funding YouTube into a $97 readiness lead magnet",
         "money_angle": "Content → checklist CTA → $97 review → subscription ladder",
         "status": "captured", "decision": "needs_review", "overall_score": 72,
         "smallest_test": "One FB post + checklist comment CTA"}))
    out.append(upsert("creative_campaigns", [
        {"campaign_key": "goclear_q3_funding_readiness", "name": "GoClear Q3 Funding Readiness",
         "goal": "Drive $97 Starter Reviews", "audience": "new LLC owners seeking funding",
         "offer": "$97 Credit/Funding Readiness Starter Review", "status": "draft",
         "compliance_notes": "No guaranteed funding/approval/credit-repair claims."},
    ], "campaign_key"))
    out.append(insert_if_absent("creative_briefs", "title", "Sample brief: LLC was never the whole game",
        {"title": "Sample brief: LLC was never the whole game", "platform": "facebook",
         "audience": "denied LLC owners", "pain_point": "Denied despite having an LLC",
         "hook": "You have an LLC and still got denied? Here's why.",
         "angle": "bankability stack education", "cta": "Comment READY for the checklist",
         "compliance_notes": "No guarantees.", "status": "draft"}))

    # Sample approval (creative/social preview)
    out.append(insert_if_absent("approvals", "item_type", "creative_preview",
        {"lane": "creative", "item_type": "creative_preview", "status": "pending",
         "title": "Review sample creative brief before drafting assets",
         "summary": "Approve the 'LLC was never the whole game' brief direction (no publish).",
         "payload": {"campaign_key": "goclear_q3_funding_readiness"}}))

    # system_health — insert only components not present
    health = [
        ("auth", "ok", "admin auth user active"),
        ("dashboard", "ok", "premium shell live"),
        ("hermes_operator", "partial", "plain-language composer stubs jobs; no live model yet"),
        ("research_os", "stubbed", "research_runs/sources tables ready"),
        ("monetization", "ok", "opportunity lab + scoring schema ready"),
        ("creative", "ok", "campaigns/briefs/QA schema ready"),
        ("approvals", "ok", "approve/reject/request-changes wired to ledger"),
        ("trading_lab", "rebuild_needed", "research only; executor deferred"),
        ("seo_marketing", "stubbed", "sites/opportunities registered"),
        ("ops_doctor", "stubbed", "incidents/heartbeats schema ready"),
        ("model_router", "registered", "providers/routes seeded; calls stubbed"),
    ]
    _, existing = _req("GET", "/rest/v1/system_health?select=component")
    have = {r["component"] for r in existing} if isinstance(existing, list) else set()
    new_rows = [{"component": c, "status": s, "summary": m} for (c, s, m) in health if c not in have]
    if new_rows:
        _req("POST", "/rest/v1/system_health", body=new_rows, extra={"Prefer": "return=minimal"})
    out.append(f"system_health: +{len(new_rows)} new components")

    # proof rows — idempotent
    out.append(insert_if_absent("nexus_events", "action", "premium_foundation_seeded",
        {"lane": "system", "source": "premium_seed", "action": "premium_foundation_seeded",
         "status": "success", "title": "Premium foundation seeded",
         "summary": "Workspaces, agents, registries, sample campaign/brief/approval, proof rows."}))
    out.append(insert_if_absent("agent_jobs", "job_type", "command_route_stub",
        {"lane": "system", "job_type": "command_route_stub", "status": "stubbed",
         "input": {"note": "proves command/job routing path; no execution"}}))
    out.append(insert_if_absent("telegram_messages", "purpose", "dry_run_proof",
        {"purpose": "dry_run_proof", "chat_label": "war_room",
         "message_hash": "seed_dry_run", "body_preview": "Guard dry-run proof (no real send).",
         "status": "suppressed", "suppressed": True, "payload": {"dry_run": True}}))

    print("Premium foundation seed complete: workspaces + agents + registries + proof rows. "
          "No real sends, no social publish, no trading.")
    for line in out:
        print("  -", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
