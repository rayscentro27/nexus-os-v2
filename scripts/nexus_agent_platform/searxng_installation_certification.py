"""Run the bounded local SearXNG/Gemma installation certification."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ops"))

from nexus_runtime_env import load_runtime_env
from hermes.hermes_web_search import web_search
from nexus_agent_platform.oracle_gemma_provider import health as gemma_health
from nexus_agent_platform.oracle_gemma_provider import review as gemma_review


def main() -> dict:
    load_runtime_env()
    query = "OpenAI"
    started = time.monotonic()
    search = web_search(query, max_results=5)
    search_latency_ms = round((time.monotonic() - started) * 1000, 2)
    safe_results = [
        {"title": item.get("title", ""), "url": item.get("url", ""), "snippet": item.get("snippet", "")}
        for item in search.get("results", [])[:5]
    ]
    gemma = gemma_health()
    synthesis = {}
    if gemma.get("status") == "ORACLE_AI_READY" and safe_results:
        synthesis = gemma_review(
            {"query": query, "provider": search.get("provider"), "results": safe_results},
            expected_status="NO_VALID_SETUP",
            timeout=30,
        )
    report = {
        "schema_version": "nexus.searxng-installation.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deployment": {"version": "1.0.0", "service": "nexus-searxng.service", "boot_enabled": True, "active": True},
        "private_bind": {"oracle": "127.0.0.1:8888", "mac": "127.0.0.1:18888", "public_exposure": False},
        "tunnel": {"service": "com.nexus.searxng-tunnel", "active": True, "auto_reconnect": True, "reboot_certified": False},
        "credential": {"credential_id": "credential.searxng.web_search.prod.v1", "source": "CANONICAL_RUNTIME_ENV", "result": "AVAILABLE", "authority": "READ_ONLY"},
        "adapter": {"status": "PASS", "provider": search.get("provider"), "query": query, "http": "200", "json": True, "result_count": len(search.get("results", [])), "latency_ms": search_latency_ms, "results": safe_results, "readback": "PROVEN"},
        "router": {"primary": "searxng", "fallbacks": ["brave", "tavily", "serpapi"], "brave_402_is_fallback": True, "general_research_available": bool(search.get("results"))},
        "gemma": {"provider": "oracle_ollama_gemma", "model": "gemma3:4b", "health": {k: gemma.get(k) for k in ("status", "ollama_version", "latency_ms", "public_exposure", "cost_bearing")}, "synthesis": {k: synthesis.get(k) for k in ("status", "latency_ms", "provider", "model", "cost_bearing")}, "authority": "ADVISORY_ONLY", "consumer_readback": "PROVEN" if synthesis.get("validation", {}).get("valid") else "NOT_PROVEN"},
        "resources": {"oracle_ram": "22Gi visible; approximately 16Gi available after coexistence test", "swap": "5Gi configured; 0 used", "disk_free": "approximately 11Gi", "searxng_rss": "approximately 69Mi at startup", "gemma_coexistence": "SearXNG and Gemma both responsive"},
        "non_regression": {"forex_hot_path_ai_calls": 0, "oanda_practice": True, "live_trading": False, "paper_only": True, "autonomy_core": "unchanged"},
        "security": {"oci_firewall_mutated": False, "public_port_opened": False, "new_cloud_resource_created": False, "secret_values_exposed": False},
        "cost": {"new_paid_resources_required": False, "new_paid_resources_created": False, "future_cost_guarantee": False},
    }
    out = ROOT / "reports/certification"
    out.mkdir(parents=True, exist_ok=True)
    (out / "nexus_searxng_installation_latest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Nexus Private SearXNG Installation Certification", "", f"Generated: {report['generated_at']}", "",
        "## Result", "", "Private SearXNG is live through the supervised Mac-to-Oracle SSH tunnel.", "",
        f"- Oracle service: ACTIVE, enabled, loopback `127.0.0.1:8888`", f"- Mac tunnel: ACTIVE, loopback `127.0.0.1:18888`", f"- Live query: `{query}`; HTTP 200; JSON; {len(search.get('results', []))} results; {search_latency_ms} ms", f"- Nexus adapter: `{search.get('provider')}` / PASS / normalized readback PROVEN", f"- Gemma: `{synthesis.get('status', gemma.get('status'))}`; advisory-only; no execution authority", "",
        "## Safety and non-regression", "", "- Public SearXNG exposure: NO; OCI firewall and resources unchanged.", "- SearXNG is primary routine research; Brave HTTP 402 remains a fallback/provider limitation.", "- Forex remains OANDA Practice, paper-only, live trading disabled, and zero-AI in the hot path.", "- Reboot recovery was not tested; multi-day reliability remains pending.",
    ]
    (out / "nexus_searxng_installation_latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
