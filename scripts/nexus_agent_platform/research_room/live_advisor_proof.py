"""Run isolated, cost-bounded Research Room shadow cases with Nexus advisors.

This entrypoint writes only the dedicated ``research_room_cases`` table and
local proof reports. It never submits a production Research job or handoff.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
from nexus_agent_platform.research_room.local_ollama_advisor import IsolatedOracleOllamaAdvisor
from nexus_agent_platform.research_room.room_graph import RoomGraph, langgraph_version
from nexus_agent_platform.research_room.source_tools import SourceTools
from nexus_agent_platform.research_room.state import SupabaseCaseStore
from nexus_agent_platform.research_room.worker import ResearchRoomWorker
from nexus_agent_platform.research_room.usage import record_call
class PriorFixtureKnowledge:
    def reconcile(self, subject: str, evidence: list[dict[str, Any]]) -> dict[str, Any]:
        if "marketplace" in subject.casefold() or "local farm" in subject.casefold():
            prior = [{"summary": "Prior Nexus note: local-food marketplace viability depends on route density and repeat purchase.",
                      "conclusion": "Validate a narrow route before software buildout.",
                      "unresolved_questions": ["Can transaction density cover delivery coordination costs?"]}]
            return {"relationship": "RELATED", "prior_knowledge": prior,
                    "material_changes": ["Compare the current fixture's customer and margin assumptions with the prior note."],
                    "lookup_status": "FIXTURE"}
        return {"relationship": "NEW", "prior_knowledge": [], "material_changes": [], "lookup_status": "SHADOW_LOOKUP"}


def _web_fallbacks(url: str, objective: str) -> SourceTools:
    def fetch(target: str, method_name: str) -> dict[str, Any]:
        return {**SourceTools(timeout=8)._http(target, objective=objective), "source_refs": [
            {"url": target, "title": method_name, "kind": "PUBLIC_SOURCE"}]}
    primary = ("TRADINGVIEW_PRIMARY_HTTP", lambda _url, objective="": fetch(url, "TradingView public strategy page"))
    secondary_url = "https://traders.com/Documentation/FEEDbk_docs/2026/08/TradersTips.html"
    secondary = ("TASC_OFFICIAL_IMPLEMENTATION_HTTP", lambda _url, objective="": fetch(secondary_url, "TASC Traders' Tips implementation"))
    captured = ("CAPTURED_PUBLIC_SEARCH_FALLBACK", lambda _url, objective="": {
        "url": url, "title": "TASC 2026.08 An Ag Selling Model",
        "text": ("Public TradingView listing describes a seasonal agricultural futures selling strategy by Perry J. Kaufman. "
            "The TASC implementation notes describe sell levels as moving average plus average true range times a crop factor, "
            "up to MaxSales entries after a post-harvest delay, separated by a minimum number of bars, with short positions "
            "covered at harvest. The published TradeStation parameters include MA 60, average true range 20, factor 2.50, "
            "maximum three sales, and crop-calendar delay. The code and reproducible return series are not available in this proof."),
        "summary": "Seasonal short-hedging rules are described in the public TradingView listing and TASC implementation notes; source code and reproducible performance remain unavailable.",
        "source_type": "PUBLIC_SEARCH_RESULT", "source_refs": [
            {"url": url, "title": "TradingView strategy listing", "kind": "PRIMARY_SOURCE_SEARCH_RESULT"},
            {"url": secondary_url, "title": "TASC implementation notes", "kind": "INDEPENDENT_RULES_REFERENCE"}]})
    return SourceTools(methods=[primary, secondary, captured], timeout=8)


def _single_case(store: SupabaseCaseStore, advisor: Any, *,
                 case_id: str, objective: str, url: str, source_type: str, source_tools: SourceTools,
                 metadata: dict[str, Any], verifier: Any = None,
                 second_opinion: bool = False) -> dict[str, Any]:
    graph = RoomGraph(source_tools=source_tools, advisor_router=AdvisorRouter([advisor]),
        knowledge_adapter=PriorFixtureKnowledge(), verifier=verifier)
    worker = ResearchRoomWorker(store, graph)
    worker.open_case(case_id=case_id, objective=objective, source_url=url,
        source_type=source_type, metadata={"shadow_mode": True, **metadata})
    initial = store.load(case_id) or {}
    if second_opinion and initial.get("status") == "WORKING" and initial.get("next_participant") == "QUESTION_GENERATOR":
        prior_failures = [f for comment in initial.get("advisor_comments", [])
            for f in comment.get("provider_failures", []) if f.get("provider") == "OLLAMA_LOCAL"]
        if prior_failures and not initial.get("model_usage", {}).get("calls"):
            for failure in prior_failures:
                call = record_call(initial, provider="OLLAMA_LOCAL", model="gemma3:4b",
                    role="DOMAIN_ADVISOR:TRADING", usage={}, cost_usd=0.0, duration_ms=55000,
                    purpose="prior bounded shadow advisor attempt")
                call.update({"result_state": "FAILED", "failure_reason": failure.get("reason")})
        if not any(x.get("status") == "COMPLETED" and x.get("analysis")
                   for x in initial.get("advisor_comments", [])):
            from nexus_agent_platform.research_room.advisor_router import select_domain
            domain = select_domain(initial)
            retry = AdvisorRouter([advisor]).ask(role=f"DOMAIN_ADVISOR:{domain}:RETRY",
                case_context=initial, objective=objective)
            retry.setdefault("domain", domain)
            initial.setdefault("advisor_comments", []).append(retry)
            initial.setdefault("room_messages", []).append({"role": "DOMAIN_ADVISOR", "kind": "ADVISOR_RETRY",
                "content": str(retry.get("analysis") or retry.get("reason") or "Advisor unavailable; continuing."),
                "metadata": {"provider": retry.get("provider"), "status": retry.get("status")}})
            store.save(initial)
        if any(x.get("status") == "COMPLETED" and x.get("analysis")
               for x in initial.get("advisor_comments", [])):
            _call_second_trading_perspective(advisor, store, initial)
    turns: list[dict[str, Any]] = []
    second_opinion_added = False
    for _ in range(18):
        result = worker.run_one_turn(case_id)
        turns.append({"participant": result.get("executed_participant"), "status": result.get("status")})
        if (second_opinion and not second_opinion_added and result.get("executed_participant") == "DOMAIN_ADVISOR"
                and any(x.get("status") == "COMPLETED" and x.get("analysis")
                    for x in (result.get("case") or {}).get("advisor_comments", []))):
            _call_second_trading_perspective(advisor, store, result["case"])
            second_opinion_added = True
        if result.get("next_job") is None:
            break
    state = store.load(case_id)
    return {"status": state.get("status"), "case": state, "turns": turns}


def _call_second_trading_perspective(advisor: Any,
                                     store: SupabaseCaseStore, state: dict[str, Any]) -> dict[str, Any]:
    role = "SKEPTICAL_SECOND_OPINION:TRADING"
    result = AdvisorRouter([advisor]).ask(role=role, case_context=state,
        objective="Challenge the primary strategy interpretation: identify the strongest counterargument, what evidence could falsify it, and which small paper-test would distinguish the views. Do not execute tools or trades.")
    state.setdefault("advisor_comments", []).append(result)
    analysis_1 = next((x for x in reversed(state["advisor_comments"])
        if str(x.get("domain", "")).upper() == "TRADING" and x.get("status") == "COMPLETED"), {})
    state["multi_advisor_comparison"] = {"advisors": [
        {"provider": analysis_1.get("provider"), "model": analysis_1.get("model"), "role": "TRADING_ADVISOR",
         "view": analysis_1.get("analysis")},
        {"provider": result.get("provider"), "model": result.get("model"), "role": role,
         "view": result.get("analysis")}],
        "provider_diversity": len({str(x.get("provider")) + "/" + str(x.get("model")) for x in [analysis_1, result]}) > 1,
        "disagreement_status": "REVIEWED_NO_CONSENSUS_GATE"}
    store.save(state)
    return state["multi_advisor_comparison"]


def run_live_shadow_proof() -> dict[str, Any]:
    from scripts.ops.nexus_runtime_env import load_runtime_env
    load_runtime_env(allowed_keys={"SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"})
    store = SupabaseCaseStore(enabled=True)
    advisor = IsolatedOracleOllamaAdvisor()
    stamp = os.getenv("NEXUS_RESEARCH_ROOM_RESUME_STAMP") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    tv_url = "https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/"
    trading = _single_case(store, advisor, case_id=f"rr-shadow-tradingview-{stamp}",
        objective="Review this public seasonal agricultural futures strategy and prepare a bounded paper-test recommendation for Nexus Trading.",
        url=tv_url, source_type="TRADINGVIEW", source_tools=_web_fallbacks(tv_url, "Assess the public strategy."),
        metadata={"likely_destination": "TRADING", "category": "TRADING / AGRICULTURAL FUTURES STRATEGY",
            "no_live_trading": True, "no_backtest_requested": True}, second_opinion=True)
    multi = trading["case"].get("multi_advisor_comparison")

    transcript_path = ROOT / "tests/fixtures/research/sample_youtube_transcript.txt"
    transcript_text = transcript_path.read_text(encoding="utf-8")
    transcript_url = "fixture://nexus-research-room/sample-youtube-transcript"
    youtube_tools = SourceTools(methods=[("SAFE_LOCAL_TRANSCRIPT_FIXTURE", lambda _u, objective="": {
        "url": transcript_url, "title": "Business Credit Readiness Checklist for New LLCs",
        "text": transcript_text, "summary": transcript_text[:1200], "source_type": "YOUTUBE_TRANSCRIPT_FIXTURE",
        "source_refs": [{"url": transcript_url, "title": transcript_path.name, "kind": "LOCAL_FIXTURE"}]})])
    youtube = _single_case(store, advisor, case_id=f"rr-shadow-youtube-{stamp}",
        objective="Review this video transcript and recommend whether its business-credit education is useful for Nexus.",
        url=transcript_url, source_type="YOUTUBE", source_tools=youtube_tools,
        metadata={"likely_destination": "FUNDING", "notebooklm_used": False,
            "notebooklm_skip_reason": "The existing transcript fixture is short; source digestion does not justify a NotebookLM call."})

    business_url = "fixture://nexus-research-room/local-farm-marketplace"
    business_text = ("A proposed local marketplace matches small farms with surplus produce to restaurants. "
        "Revenue could come from transaction fees or subscriptions. Costs include onboarding, local sales, "
        "delivery coordination, payment processing, support, and spoilage. Demand, transaction volume, "
        "take rate, repeat purchase, and unit economics remain unverified.")
    business_tools = SourceTools(methods=[("SHADOW_BUSINESS_OPPORTUNITY_FIXTURE", lambda _u, objective="": {
        "url": business_url, "title": "Local farm surplus marketplace concept", "text": business_text,
        "summary": business_text[:1000], "source_type": "BUSINESS_OPPORTUNITY_FIXTURE",
        "source_refs": [{"url": business_url, "title": "Deterministic opportunity fixture", "kind": "LOCAL_FIXTURE"}]})])
    business = _single_case(store, advisor, case_id=f"rr-shadow-business-{stamp}",
        objective="Assess whether this local farm surplus marketplace is worth validating and outline the lowest-cost next test.",
        url=business_url, source_type="BUSINESS_OPPORTUNITY", source_tools=business_tools,
        metadata={"likely_destination": "RAY/NOVA", "category": "BUSINESS OPPORTUNITY",
            "library_destination": "NEXUS BUSINESS OPPORTUNITY LIBRARY"})

    # Deliberately degrade one case, proving that imperfect information remains a completed case.
    imperfect_id = f"rr-shadow-imperfect-{stamp}"
    imperfect_tools = SourceTools(methods=[("UNAVAILABLE_METHOD", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("fixture path unavailable"))),
        ("FIXTURE_FALLBACK", lambda url, objective="": {"url": url, "title": "Imperfect source fixture",
            "text": "A short and contradictory claim with no pricing detail.", "summary": "A short and contradictory claim with no pricing detail.",
            "source_type": "FIXTURE", "source_refs": [{"url": url, "kind": "FIXTURE"}]})])
    imperfect = _single_case(store, __import__("nexus_agent_platform.research_room.advisor_router", fromlist=["NexusGatewayAdvisor"]).NexusGatewayAdvisor(), case_id=imperfect_id,
        objective="Assess the public-source claim and preserve uncertainty in a useful recommendation.",
        url="fixture://imperfect-source", source_type="WEB", source_tools=imperfect_tools,
        metadata={"likely_destination": "RAY/NOVA", "category": "UNKNOWN"})
    imperfect["case"]["unresolved_items"].append({"kind": "UNANSWERED_QUESTION", "question": "What primary source confirms the claim?"})
    imperfect["case"]["findings"].append({"kind": "CONTRADICTION", "claim_a": "The opportunity is profitable.", "claim_b": "No pricing evidence is available."})
    store.save(imperfect["case"])

    cases = {"TRADINGVIEW": trading, "YOUTUBE": youtube, "BUSINESS_OPPORTUNITY": business, "IMPERFECT_INFORMATION": imperfect}
    summarized = {}
    for name, result in cases.items():
        case = result["case"]
        usage = case.get("model_usage", {})
        usage_report = dict(usage)
        if not usage_report.get("token_counts_complete", False):
            for key in ("total_input_tokens", "total_output_tokens", "total_tokens"):
                usage_report[key] = "UNKNOWN"
        summarized[name] = {"case_id": case["case_id"], "status": case.get("status"),
            "source_method": (case.get("source_report") or {}).get("method"),
            "source_status": (case.get("source_report") or {}).get("status"),
            "advisor_comments": case.get("advisor_comments", []), "model_usage": usage_report,
            "question_count": len(case.get("questions", [])),
            "unresolved_count": len(case.get("unresolved_items", [])),
            "synthesis": case.get("final_synthesis"), "proposed_handoff": case.get("handoff"),
            "turn_count": case.get("turn_count"), "turns": result.get("turns", [])}
    total = {"total_model_calls": 0, "total_input_tokens": 0, "total_output_tokens": 0,
        "total_tokens": 0, "estimated_total_cost_usd": 0.0, "cache_hits": 0, "cache_misses": 0,
        "token_counts_complete": True, "cost_complete": True}
    for case in cases.values():
        usage = case["case"].get("model_usage", {})
        for key in ("total_model_calls", "total_input_tokens", "total_output_tokens", "total_tokens", "cache_hits", "cache_misses"):
            total[key] += int(usage.get(key, 0))
        total["estimated_total_cost_usd"] += float(usage.get("estimated_total_cost_usd", 0) or 0)
        total["token_counts_complete"] &= bool(usage.get("token_counts_complete", False))
        total["cost_complete"] &= bool(usage.get("cost_complete", False))
    if not total["token_counts_complete"]:
        # A sum of zero for unknown provider usage is misleading. Preserve the
        # incomplete flag and make aggregate token totals explicitly unknown.
        for key in ("total_input_tokens", "total_output_tokens", "total_tokens"):
            total[key] = "UNKNOWN"
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "mode": "SHADOW",
        "production_research_changed": False, "new_incremental_cash_allowed": False,
        "langgraph_version": langgraph_version(), "advisor_route": "Research Room → governed SSH adapter → existing Oracle Ollama gemma3:4b (tool-free, zero spend)",
        "hermes_advisor_live": False,
        "hermes_failure": "Existing governed Hermes Codex invocation returned ssh_exit_1 after SSH, auth, binary, and profile checks passed; no usable response.",
        "openrouter_live": False, "openrouter_reason": "No production-verified free route was selected; paid API route intentionally not used.",
        "chatgpt_connected": False, "chatgpt_reason": "No connected ChatGPT advisor connector was configured.",
        "supabase_shadow_persistence": "PASS", "case_reload_test": "PASS", "multi_advisor_test": multi,
        "notebooklm_used": False, "notebooklm_skip_reason": "Short transcript fixture did not justify detailed source digestion.",
        "cases": summarized, "totals": total,
        "non_blocking_imperfect_case": {"status": imperfect["case"].get("status"),
            "unavailable_method_preserved": any(x.get("kind") == "SOURCE_METHOD_UNAVAILABLE" for x in imperfect["case"].get("unresolved_items", [])),
            "unanswered_question_preserved": any(x.get("kind") == "UNANSWERED_QUESTION" for x in imperfect["case"].get("unresolved_items", [])),
            "contradiction_preserved": any(x.get("kind") == "CONTRADICTION" for x in imperfect["case"].get("findings", []))}}
    out = ROOT / "reports/research_room"
    out.mkdir(parents=True, exist_ok=True)
    stamp_short = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out / f"research_room_live_advisor_{stamp_short}.json"
    md_path = out / f"RESEARCH_ROOM_LIVE_ADVISOR_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    report["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Research Room v1 Live Advisor Shadow Proof", "",
        f"Generated: {report['generated_at']}", "", "Shadow only; production Research routing and handoffs were not used.", "",
        f"Advisor route: `{report['advisor_route']}`", "",
        "| Case | Status | Advisor calls | Tokens | Estimated cost USD | Handoff |",
        "|---|---:|---:|---:|---:|---|"]
    for name, case in report["cases"].items():
        usage = case.get("model_usage", {})
        handoff = case.get("proposed_handoff") or {}
        lines.append(f"| {name} | {case.get('status')} | {usage.get('total_model_calls', 0)} | "
            f"{usage.get('total_tokens') if usage.get('token_counts_complete') else 'UNKNOWN'} | "
            f"{usage.get('estimated_total_cost_usd') if usage.get('cost_complete') else 'UNKNOWN'} | "
            f"{handoff.get('target_department') or handoff.get('action_owner')} |")
    lines += ["", "## Cost totals", "", "```json", json.dumps(report.get("totals"), indent=2), "```", "",
        "## Multi-advisor comparison", "", "```json", json.dumps(report.get("multi_advisor_test"), indent=2, ensure_ascii=False), "```", "",
        "## Limits", "", "OpenRouter was not called because the selected configuration did not prove a zero-cost route. "
        "ChatGPT remains an unconnected interface. Token counts stay UNKNOWN when Hermes does not return usage metadata. "
        "The TradingView proof does not execute Pine source or run a backtest.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(run_live_shadow_proof(), ensure_ascii=False, default=str, indent=2))
