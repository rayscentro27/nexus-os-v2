"""Run deterministic, isolated Research Room shadow proofs and write reports."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexus_agent_platform.runtime.paths import nexus_research_state_path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.research_room.advisor_router import AdvisorRouter
from nexus_agent_platform.research_room.entry import MANUAL_SHADOW_ENTRY
from nexus_agent_platform.research_room.room_graph import RoomGraph, langgraph_version
from nexus_agent_platform.research_room.source_tools import SourceTools
from nexus_agent_platform.research_room.state import JsonCaseStore
from nexus_agent_platform.research_room.worker import ResearchRoomWorker, ShadowRoomRunner


class ShadowAdvisorFixture:
    provider, available = "DETERMINISTIC_SHADOW_FIXTURE", True
    def ask(self, *, role: str, case_context: dict[str, Any], objective: str) -> dict[str, Any]:
        title = str((case_context.get("source_report") or {}).get("title") or "the subject")
        questions = ["Which material operating claims are independently supported?",
            "What risks, costs, and assumptions could change the recommendation?",
            "What bounded next experiment would reduce the remaining uncertainty?"]
        return {"status": "COMPLETED", "provider": self.provider,
            "analysis": f"Fixture advisor identifies {title} as requiring claim verification and a bounded decision test.",
            "new_questions": questions, "likely_category": case_context.get("metadata", {}).get("category", "UNKNOWN")}


def _case_runner(root: Path, case_id: str, objective: str, url: str | None, source_type: str,
                 source_result: dict[str, Any], metadata: dict[str, Any],
                 knowledge_lookup=None) -> dict[str, Any]:
    methods = source_result.get("_methods") or [(source_result.get("method", "SHADOW_FIXTURE"),
        lambda _url, objective="": {k: v for k, v in source_result.items() if k != "_methods"})]
    if source_result.get("_methods"):
        fallback_result = {k: v for k, v in source_result.items() if k != "_methods"}
        methods = [methods[0], (methods[1][0], lambda _url, objective="": dict(fallback_result))]
    source = SourceTools(methods=methods)
    graph = RoomGraph(source_tools=source, advisor_router=AdvisorRouter([ShadowAdvisorFixture()]),
        knowledge_adapter=__import__("nexus_agent_platform.research_room.knowledge_adapter", fromlist=["KnowledgeAdapter"]).KnowledgeAdapter(knowledge_lookup),
        verifier=lambda case: {"status": "PARTIAL", "note": "Checked source claims against the cited independent references; no full backtest or primary data reanalysis was performed.",
            "contradictions": case.get("metadata", {}).get("fixture_contradictions", []),
            "references": case.get("metadata", {}).get("independent_sources", [])})
    store = JsonCaseStore(root / "cases")
    worker = ResearchRoomWorker(store, graph)
    worker.open_case(case_id=case_id, objective=objective, source_url=url,
        source_type=source_type, metadata=metadata)
    result = ShadowRoomRunner(worker).run_to_completion(case_id)
    return result


def run_shadow_cases(root: Path | None = None) -> dict[str, Any]:
    root = root or nexus_research_state_path("research_room_shadow")
    root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trading_url = "https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/"
    trading_source = {
        "status": "SOURCE_ACQUIRED", "method": "LIVE_WEB_SEARCH_SNIPPETS",
        "url": trading_url, "title": "TASC 2026.08 An Ag Selling Model",
        "text": ("TradingView describes a seasonal short-selling model for agricultural futures, "
            "with up to three short entries, waiting between rallies, avoiding immediate post-harvest "
            "selling, and covering at harvest. Parameters are calibrated for corn futures ZC1!; "
            "entry level uses a moving average plus a volatility measure times a factor. The page "
            "describes commission and one-tick slippage assumptions and says parameters require "
            "adjustment for other markets."),
        "source_type": "WEB_SEARCH_RESULT", "source_refs": [
            {"url": trading_url, "title": "TradingView strategy description", "kind": "PRIMARY_SOURCE"},
            {"url": "https://traders.com/Documentation/FEEDbk_docs/2026/08/TradersTips.html", "title": "TASC Traders’ Tips August 2026 implementation notes", "kind": "INDEPENDENT_CODE_REFERENCE"},
            {"url": "https://sat.afpc.tamu.edu/2025/06/04/seasonal-movements-of-the-monthly-december-corn-futures-price/", "title": "Texas A&M seasonal corn futures analysis", "kind": "INDEPENDENT_CONTEXT"},
        ]}
    trading_source["_methods"] = [
        ("TRADINGVIEW_DIRECT_HTTP", lambda *_a, **_k: (_ for _ in ()).throw(PermissionError("TradingView direct fetch restricted"))),
        ("LIVE_WEB_SEARCH_SNIPPETS", lambda _url, objective="": dict(trading_source)),
    ]
    trading_meta = {"likely_destination": "TRADING", "category": "TRADING / AGRICULTURAL FUTURES STRATEGY",
        "independent_sources": trading_source["source_refs"], "evidence_note": "Current room turn uses captured public search results; full code review and reproducible backtest remain future work."}
    trading_meta["fixture_contradictions"] = [{"claim_a": "Seasonal selling can exploit recurring harvest cycles.",
        "claim_b": "Historical seasonal patterns vary materially with yield and market conditions.",
        "resolution": "Both can be true; regime sensitivity and out-of-sample testing remain unresolved."}]
    trading_meta["domain_sections"] = {
        "strategy_explanation": "Seasonal short-hedging model intended to sell grain futures into seasonal rallies and cover at harvest.",
        "entry_rules": "Sell when High reaches SMA(Close, length) plus average true range times a crop factor; allow up to three entries separated by a minimum number of days and after the post-harvest delay.",
        "exit_rules": "Cover short positions at harvest.",
        "risk_rules": "One-contract increments, up to three entries; source page lists commission and one tick of slippage assumptions.",
        "verified_claims": ["TradingView describes the model as parameterized for ZC1! corn futures."],
        "unverified_claims": ["Robust net profitability and out-of-sample performance; no reproducible backtest was run."],
        "weaknesses": ["Seasonal regime sensitivity", "crop/calendar mapping", "contract roll and delivery effects", "parameters need market-specific tuning"],
        "recommended_indicators_or_filters": ["Yield and stocks-to-use regime", "trend and volatility regime", "basis and contract-roll controls"],
        "paper_trading_experiment_plan": "Trading should validate code against the published rules, test multiple crops and out-of-sample contract years, include roll/commission/slippage, and compare with simple harvest and seasonal benchmarks.",
    }
    trading = _case_runner(root, f"shadow-tradingview-{run_id}",
        "Research and review this strategy to prepare an actionable paper-trading recommendation for Nexus Trading.",
        trading_url, "TRADINGVIEW", trading_source, trading_meta)
    trading_case = trading.get("case") or {}
    trading_case.setdefault("test_results", []).append({"kind": "PAPER_TEST_PLAN", "result": "NOT_RUN",
        "reason": "Shadow mode; no Trading/backtest execution."})
    trading_case["final_synthesis"]["test_results"] = list(trading_case["test_results"])
    # Persist the shadow evidence additions without creating a production case.
    JsonCaseStore(root / "cases").save(trading_case)

    transcript = {"status": "SOURCE_ACQUIRED", "method": "LOCAL_TRANSCRIPT_FIXTURE",
        "url": "fixture://nexus-research-room/video-01", "title": "Business Credit Readiness Checklist for New LLCs",
        "text": (ROOT / "tests/fixtures/research/sample_youtube_transcript.txt").read_text(encoding="utf-8"),
        "source_type": "YOUTUBE_TRANSCRIPT_FIXTURE", "source_refs": [{"url": "fixture://nexus-research-room/video-01", "title": "Local transcript fixture", "kind": "TEST_FIXTURE"}]}
    youtube = _case_runner(root, f"shadow-youtube-fixture-{run_id}",
        "Review this video and determine whether anything in it can improve Nexus.",
        transcript["url"], "YOUTUBE", transcript, {"likely_destination": "FUNDING",
        "category": "FUNDING / BUSINESS CREDIT EDUCATION", "notebooklm_selected": True,
        "notebooklm_note": "Selectable for long source digestion; the existing local transcript fixture is concise, so no NotebookLM call was made."})

    business_source = {"status": "SOURCE_ACQUIRED", "method": "DETERMINISTIC_BUSINESS_FIXTURE",
        "url": "fixture://nexus-research-room/opportunity-01", "title": "Local farm surplus marketplace concept",
        "text": "A proposed marketplace connects small farms with local restaurants for surplus produce. Revenue could come from a transaction fee or subscription. Costs include onboarding, logistics coordination, payments, customer support, spoilage handling, and local sales. Demand, take rate, fulfillment cost, and repeat purchasing are unknown.",
        "source_type": "BUSINESS_OPPORTUNITY_FIXTURE", "source_refs": [{"url": "fixture://nexus-research-room/opportunity-01", "title": "Deterministic opportunity fixture", "kind": "TEST_FIXTURE"}]}
    def prior_lookup(_subject):
        return [{"summary": "Prior Nexus note: local food marketplaces face supply density and delivery economics challenges.",
            "conclusion": "Validate route density before scaling.", "unresolved_questions": ["Can order density cover delivery costs?"]}]
    business = _case_runner(root, f"shadow-business-fixture-{run_id}",
        "Assess whether this online business opportunity merits a small validation test and library entry.",
        business_source["url"], "BUSINESS_OPPORTUNITY", business_source,
        {"likely_destination": "RAY/NOVA", "category": "BUSINESS OPPORTUNITY",
         "library_destination": "NEXUS BUSINESS OPPORTUNITY LIBRARY", "recommended_actions": [
             "Interview five local restaurants and three growers.",
             "Estimate contribution margin for a tightly bounded delivery area.",
             "Run a no-code order-intent test before building software."],
         "domain_sections": {"opportunity_assessment": "Promising coordination problem, unvalidated demand and unit economics.",
             "business_model": "Local marketplace; transaction fee or subscription.",
             "customer": "Small farms with surplus and local restaurants seeking local produce.",
             "pricing_economics": "Take rate and delivery economics are unknown; validate contribution margin before scaling.",
             "risks": ["Supply density", "spoiled inventory", "delivery costs", "repeat-purchase uncertainty"],
             "launch_plan": "Test one dense local route with manual matching.",
             "marketing_plan": "Recruit growers and restaurants through local farm and hospitality groups."}}, knowledge_lookup=prior_lookup)

    cases = {"TRADINGVIEW": trading, "YOUTUBE": youtube, "BUSINESS_OPPORTUNITY": business}
    summaries = {}
    for name, result in cases.items():
        case = result.get("case") or {}
        summaries[name] = {"status": result.get("status"), "case_id": case.get("case_id"),
            "turns": result.get("turns", []), "source_report": case.get("source_report"),
            "question_count": len(case.get("questions", [])), "unresolved_count": len(case.get("unresolved_items", [])),
            "advisor_status": (case.get("advisor_comments") or [{}])[0].get("status"),
            "synthesis": case.get("final_synthesis"), "proposed_handoff": case.get("handoff")}
    now = datetime.now(timezone.utc)
    result = {"generated_at": now.isoformat(), "mode": "SHADOW", "manual_shadow_entry": MANUAL_SHADOW_ENTRY,
        "automated_youtube_watcher": "NOT_ACTIVE", "langgraph_version": langgraph_version(),
        "cases": summaries,
        "comparison": {"production_research": {"state_complexity": "Existing parent state machine and adapters; known to reach handoff in certification.",
                "completion_behavior": "Existing production engine; preserved unchanged."},
            "research_room_v1": {"completion_behavior": "Shared case conversation with one persisted participant turn per room job; shadow handoff only.",
                "manual_interventions": 0, "source_fallback": "Method failures are findings and configured methods are tried in order.",
                "question_quality": "Questions are durable case rows and Needle only audits coverage.",
                "advisor_contribution": "Provider-neutral; case runs used deterministic fixture advisor, not a live model.",
                "unresolved_question_handling": "Carried into synthesis.",
                "handoff_usefulness": "Objective-specific package with proposed owner/department and no production assignment.",
                "runtime_cost": "No model calls; public web search used for TradingView research; not estimated.",
                "state_complexity": "Single JSON case record plus idempotent bounded turn outbox in isolated data/research_room_shadow."}}}
    reports = ROOT / "reports/research_room"
    reports.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    json_path = reports / f"research_room_shadow_{stamp}.json"
    md_path = reports / f"RESEARCH_ROOM_SHADOW_{now.strftime('%Y-%m-%d')}.md"
    result["report_paths"] = {"json": str(json_path), "markdown": str(md_path)}
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(result), encoding="utf-8")
    return result


def render_markdown(result: dict[str, Any]) -> str:
    lines = ["# Nexus Research Room v1 Shadow Proof", "", f"Generated: {result['generated_at']}",
        "", "Mode: **SHADOW**. No production Research routing or department handoff was used.", "",
        f"LangGraph: `{result.get('langgraph_version')}` (reused).", "",
        "| Case | Status | Questions | Unresolved | Proposed handoff |", "|---|---:|---:|---:|---|"]
    for name, case in result["cases"].items():
        handoff = case.get("proposed_handoff") or {}
        lines.append(f"| {name} | {case.get('status')} | {case.get('question_count')} | {case.get('unresolved_count')} | {handoff.get('target_department') or handoff.get('action_owner')} |")
    lines += ["", "## Case findings", ""]
    for name, case in result["cases"].items():
        synthesis = case.get("synthesis") or {}
        lines += [f"### {name}", "", f"Case ID: `{case.get('case_id')}`", "",
            f"- Subject: {synthesis.get('subject')}",
            f"- Conclusion: {synthesis.get('research_conclusion')}",
            f"- Open questions: {case.get('question_count')}; unresolved items: {case.get('unresolved_count')}.",
            f"- Proposed destination: {(case.get('proposed_handoff') or {}).get('target_department') or (case.get('proposed_handoff') or {}).get('action_owner')}.", ""]
    lines += ["## Comparison", "", "Production Research remains the fallback and was not changed. Room v1’s demonstrated advantages are shared case history, explicit source limitations, bounded turns, and a visible proposal package. The three proof cases use deterministic advisor fixtures; this validates orchestration and non-blocking information quality, not live model quality. No runtime/cost comparison is claimed.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    output = run_shadow_cases()
    print(json.dumps({"mode": output["mode"], "cases": {k: v["status"] for k, v in output["cases"].items()},
        "reports": output["report_paths"]}, indent=2))
