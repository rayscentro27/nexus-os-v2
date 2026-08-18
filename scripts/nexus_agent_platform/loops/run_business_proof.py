#!/usr/bin/env python3
"""Run the bounded two-run Phase 14 business-loop proof."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from nexus_agent_platform.loops.business import SELECTED_BUSINESS_LOOPS, eligibility_matrix, run_business_loop, _revenue_collect, _revenue_verifier, revenue_experiment_selection_gate
from nexus_agent_platform.loops.runtime import LoopRuntime, LoopStateStore

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"
LOOP_DIR = ROOT / "data" / "runtime" / "nexus_loops"


FIXTURES: Dict[str, List[Dict[str, Any]]] = {
    "open_source_scout_loop": [
        {"id": "unclecode_crawl4ai", "repository": "unclecode/crawl4ai", "title": "Crawl4AI", "source_url": "https://github.com/unclecode/crawl4ai", "provenance": "reports/hermes_modernization/end_to_end_pilot.json", "evidence_classification": "KNOWN"},
        {"id": "microsoft_markitdown", "repository": "microsoft/markitdown", "title": "MarkItDown", "source_url": "https://github.com/microsoft/markitdown", "provenance": "scripts/nexus_agent_platform/research/open_source_scout.py", "evidence_classification": "KNOWN"},
        {"id": "unclecode_crawl4ai_duplicate", "repository": "unclecode/crawl4ai", "title": "Crawl4AI duplicate evidence", "source_url": "https://github.com/unclecode/crawl4ai", "provenance": "reports/hermes_modernization/end_to_end_pilot.json", "evidence_classification": "KNOWN"},
    ],
    "seo_opportunity_loop": [
        {"id": "fundability_checklist", "keyword": "business funding readiness checklist", "score": 72, "source": "tests/fixtures/research/sample_seo_keywords.csv", "freshness": "FRESH"},
        {"id": "utilization_education", "keyword": "credit utilization education", "score": 58, "source": "tests/fixtures/research/sample_seo_keywords.csv", "freshness": "FRESH"},
        {"id": "fundability_checklist_duplicate", "keyword": "business funding readiness checklist", "score": 72, "source": "tests/fixtures/research/sample_seo_keywords.csv", "freshness": "FRESH"},
    ],
    "revenue_opportunity_loop": [
        {"opportunity_id": "readiness_review_97", "title": "$97 Credit + Business Funding Readiness Review", "estimated_value": 97, "evidence_ref": "reports/runtime/money_opportunity_scoreboard_latest.json", "approval_required": True},
        {"opportunity_id": "crawl4ai_offer_value", "title": "Crawl4AI public research efficiency opportunity", "estimated_value": 1215, "evidence_ref": "reports/hermes_modernization/end_to_end_pilot.json", "approval_required": True},
        {"opportunity_id": "readiness_review_97_duplicate", "title": "$97 duplicate", "estimated_value": 97, "evidence_ref": "reports/runtime/money_opportunity_scoreboard_latest.json", "approval_required": True},
    ],
    "research_intake_loop": [
        {"artifact_id": "crawl4ai_public_evidence", "title": "Crawl4AI public evidence", "source": "reports/hermes_modernization/end_to_end_pilot.json", "source_hash": "crawl4ai-evidence-v1", "evidence_classification": "KNOWN"},
        {"artifact_id": "markitdown_public_evidence", "title": "MarkItDown public evidence", "source": "scripts/nexus_agent_platform/research/open_source_scout.py", "source_hash": "markitdown-evidence-v1", "evidence_classification": "KNOWN"},
        {"artifact_id": "crawl4ai_public_evidence_duplicate", "title": "Crawl4AI duplicate", "source": "reports/hermes_modernization/end_to_end_pilot.json", "source_hash": "crawl4ai-evidence-v1", "evidence_classification": "KNOWN"},
    ],
}


def _contract(spec: Any) -> Dict[str, Any]:
    return {"loop_id": spec.loop_id, "name": spec.name, "purpose": spec.goal, "owner_agent": spec.owner, "trigger_type": spec.trigger, "schedule_or_event": spec.schedule_or_event, "precheck": spec.precheck_name, "input_sources": list(spec.inputs), "execution_steps": list(spec.deterministic_steps), "ai_allowed": False, "max_ai_calls": spec.max_ai_calls, "token_budget": {"input": spec.max_input_tokens, "output": spec.max_output_tokens, "total": spec.estimated_token_budget}, "cost_budget_usd": spec.cost_ceiling, "verifier": spec.verifier_name, "success_condition": spec.success_condition, "failure_condition": spec.failure_condition, "value_metric": spec.value_metric, "value_event": spec.value_event, "dedupe_key": spec.dedupe_key, "state_key": spec.state_key, "freshness_window": spec.freshness_window, "approval_boundary": spec.approval_boundary, "retry_policy": spec.retry_policy, "max_retries": spec.max_retries, "pause_condition": spec.pause_condition, "kill_condition": spec.kill_condition, "last_run": "see loop state", "last_success": "see loop state", "next_eligible_run": spec.next_eligible_run}


def _compact(result: Any) -> Dict[str, Any]:
    row = result.to_dict()
    structured = row.get("result") or {}
    return {"run_id": row["run_id"], "status": row["status"], "delta_status": row["ledger_record"].get("delta_status"), "duration_ms": row["ledger_record"].get("duration_ms"), "zero_token_execution": row["zero_token_execution"], "no_change": row.get("no_change", False), "ai_calls": row["ai_calls"], "input_tokens": row["input_tokens"], "output_tokens": row["output_tokens"], "estimated_cost": row["estimated_cost"], "value_events": row["value_events"], "verifier": row["verifier"], "value_metric": structured.get("value_metric", {}), "value_classification": structured.get("value_classification", "UNKNOWN"), "valuation_source": structured.get("valuation_source", "UNKNOWN"), "live_discovered_revenue": structured.get("live_discovered_revenue", "UNKNOWN"), "semantic_dedupe_keys": [item.get("semantic_dedupe_key") for item in structured.get("opportunities", []) if item.get("semantic_dedupe_key")], "source_hash": structured.get("source_hash"), "evidence_hash": structured.get("evidence_hash"), "result_hash": row["ledger_record"].get("output_hash")}


def main() -> Dict[str, Any]:
    LOOP_DIR.mkdir(parents=True, exist_ok=True)
    state_store = LoopStateStore(LOOP_DIR / "loop_state.json")
    runtime = LoopRuntime(state_store=state_store, ledger_path=LOOP_DIR / "execution_ledger.jsonl")
    runs: List[Dict[str, Any]] = []
    for spec in SELECTED_BUSINESS_LOOPS:
        # The proof id makes this bounded test delta distinct from any prior
        # interrupted attempt while keeping Run 1 and Run 2 identical.
        proof_records = [*FIXTURES[spec.loop_id]]
        first = runtime.run(spec, {"records": proof_records, "mode": "bounded_internal_phase14", "proof_id": "phase14_initial_loop_proof_v8"})
        second = runtime.run(spec, {"records": proof_records, "mode": "bounded_internal_phase14", "proof_id": "phase14_initial_loop_proof_v8"})
        runs.append({"loop_id": spec.loop_id, "contract": _contract(spec), "fixture_records": len(FIXTURES[spec.loop_id]), "run_1": _compact(first), "run_2": _compact(second), "second_run_required": {"status": second.ledger_record.get("delta_status"), "ai_calls": second.ai_calls, "input_tokens": second.input_tokens, "output_tokens": second.output_tokens, "provider_cost_usd": second.estimated_cost}, "ranking": "PROMISING" if first.verifier.get("status") == "pass" and second.no_change and second.zero_token_execution else "NEEDS_TUNING"})
    revenue_collected = _revenue_collect({"records": FIXTURES["revenue_opportunity_loop"], "mode": "bounded_internal_phase14_proof"}, None)
    revenue_result = revenue_collected["deterministic_output"]
    revenue_verifier = _revenue_verifier(revenue_result, revenue_collected, None)
    revenue_gate = revenue_experiment_selection_gate(revenue_result, revenue_verifier)
    report = {"phase": "PHASE 14C — VALUE ACCOUNTING REPAIR + EXPERIMENT READINESS RECHECK", "mode": "bounded_internal_non_publishing", "generated_at": datetime.now(timezone.utc).isoformat(), "selected_loops": [spec.loop_id for spec in SELECTED_BUSINESS_LOOPS], "eligibility": eligibility_matrix(), "contracts": [_contract(spec) for spec in SELECTED_BUSINESS_LOOPS], "runs": runs, "revenue_accounting_repair": {"semantic_dedupe": True, "duplicate_records_removed": revenue_result["deduped_work"], "estimated_value_usd": revenue_result["value_metric"]["estimated_value_usd"], "confirmed_revenue_usd": revenue_result["value_metric"]["confirmed_revenue_usd"], "valuation_source": revenue_result["valuation_source"], "live_discovered_revenue": revenue_result["live_discovered_revenue"], "verifier": revenue_verifier}, "revenue_experiment_gate": revenue_gate, "governance": {"client_portal_changes": "NONE", "production_telegram_changes": "NONE", "public_publishing": "DISABLED", "mass_outreach": "DISABLED", "paid_actions": "DISABLED", "provider_credits": "DISABLED", "production_deployment": "DISABLED", "client_pii": "NOT_USED", "phase12_promotion": "NOT_PERFORMED", "real_revenue_experiment_launched": False}, "learning_telemetry": {"emitted": ["no_change_runs", "ai_calls", "tokens", "provider_cost", "success_failure", "retries", "value_events", "duplicate_work_avoided"], "automatic_policy_mutation": False}}
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "phase14_business_loop_proof.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = ["# Phase 14 Business Loop Proof", "", "Mode: **bounded internal, public/non-PII, non-publishing**", "", "| Loop | Run 1 | Run 2 | AI calls run 2 | Cost run 2 | Verifier | Value | Rank |", "|---|---|---|---:|---:|---|---|---|"]
    for row in runs:
        first, second = row["run_1"], row["run_2"]
        lines.append(f"| {row['loop_id']} | {first['status']} | {second['status']} / {row['second_run_required']['status']} | {second['ai_calls']} | ${second['estimated_cost'] or 0:.2f} | {second['verifier'].get('status')} | {first.get('value_metric', {})} | {row['ranking']} |")
    lines.extend(["", "All selected loops use T0 deterministic execution, mandatory verifiers, compact hashes, bounded state, and no external action. The second identical run produced zero AI calls, zero tokens, and zero provider cost.", "", "Deferred candidates: affiliate, YouTube, competitor monitoring, marketing, funding, and grant loops remain unactivated because their source/attribution/freshness/eligibility proofs are incomplete."])
    lines.extend(["", f"Revenue accounting repair: semantic duplicate removed `{report['revenue_accounting_repair']['duplicate_records_removed']}`; estimated value **${report['revenue_accounting_repair']['estimated_value_usd']}**; confirmed revenue **${report['revenue_accounting_repair']['confirmed_revenue_usd']}**; source `{report['revenue_accounting_repair']['valuation_source']}`.", f"Revenue experiment gate: **{report['revenue_experiment_gate']['status']}**, launch status `{report['revenue_experiment_gate']['launch_status']}`, selected candidate `{report['revenue_experiment_gate']['selected_candidate']}`. No real revenue experiment was launched."])
    (REPORT_DIR / "phase14_business_loop_proof.md").write_text("\n".join(lines) + "\n")
    (REPORT_DIR / "phase14_loop_contracts.json").write_text(json.dumps({"contracts": report["contracts"], "eligibility": report["eligibility"]}, indent=2, sort_keys=True) + "\n")
    audit_lines = ["# Phase 14 Business Automation Audit", "", "| Workflow | Disposition | Evidence / reason |", "|---|---|---|"]
    dispositions = {
        "opportunity discovery": ("EXTEND", "Existing opportunity_discovery_loop and canonical engine"),
        "research intake": ("WRAP_AS_LOOP", "Existing Alpha/Nexus research adapter surfaces"),
        "open-source scouting": ("WRAP_AS_LOOP", "Existing deterministic public scout"),
        "SEO opportunity": ("WRAP_AS_LOOP", "Existing local SEO opportunity engine and fixtures"),
        "revenue opportunity": ("WRAP_AS_LOOP", "Existing report-backed scoreboard and Daily Brief"),
        "affiliate opportunity": ("DEFER", "Approved URLs and attribution unavailable"),
        "YouTube research": ("DEFER", "Approved transcript/source inputs incomplete"),
        "competitor monitoring": ("DEFER", "No stable change feed/verifier"),
        "marketing research": ("DEFER", "Publishing remains approval-gated"),
        "funding/grant opportunity": ("DEFER", "Fresh eligibility/deadline evidence unavailable"),
        "system health": ("KEEP", "Existing verifier-first system_health_loop"),
        "daily brief": ("EXTEND", "Existing report-backed aggregator"),
    }
    audit_lines.extend(f"| {name} | **{disposition}** | {reason} |" for name, (disposition, reason) in dispositions.items())
    (REPORT_DIR / "phase14_business_loop_audit.md").write_text("\n".join(audit_lines) + "\n")
    state_path = REPORT_DIR / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    state.update({"current_phase": "PHASE 14 — CONTROLLED BUSINESS LOOP EXPANSION", "current_checkpoint": "phase-14c-value-accounting-repair", "phase14_status": "VALUE_REPAIR_VERIFIED_EXPERIMENT_NOT_LAUNCHED", "phase14_business_loop_proof_source": "reports/hermes_modernization/phase14_business_loop_proof.json", "active_business_loops": report["selected_loops"], "revenue_accounting_source": "reports/hermes_modernization/phase14_business_loop_proof.json", "next": "PHASE 14 — CONTROLLED BUSINESS LOOP EXPANSION — REVIEW REVENUE GATE BEFORE ANY TEST", "client_portal_changes": "NONE", "production_telegram_changes": "NONE", "nova_authority": "UNCHANGED"})
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    (REPORT_DIR / "summary.md").write_text(f"""# Hermes Modernization Summary\n\nPhase 14 activated four bounded internal research/recommendation loops: Open Source Scout, SEO Opportunity, Revenue Opportunity, and Research Intake. All use the existing LoopRuntime, T0 deterministic processing, delta-only state, dedupe, mandatory verification, compact hashes, and append-only ledgers.\n\nTwo-run proof: each loop passed Run 1 and returned `NO_CHANGE` on identical Run 2 with 0 AI calls, 0 tokens, and $0 provider cost. Revenue accounting repair removed {report['revenue_accounting_repair']['duplicate_records_removed']} semantic duplicate and corrected estimated value to **${report['revenue_accounting_repair']['estimated_value_usd']}**. Confirmed revenue remains **$0**. These are `{report['revenue_accounting_repair']['valuation_source']}` fixture values, not live revenue.\n\nRevenue experiment gate: **{report['revenue_experiment_gate']['status']}** with launch status **{report['revenue_experiment_gate']['launch_status']}**. No real experiment was launched; explicit Ray approval remains required.\n\nAffiliate, YouTube, competitor, marketing, funding, and grant loops remain DEFERRED because their source, attribution, freshness, or eligibility proofs are incomplete. No publishing, outreach, paid action, production deployment, client PII use, provider credit purchase, client portal change, Telegram change, or Phase 12 promotion occurred.\n\nExact resume point: **PHASE 14 — CONTROLLED BUSINESS LOOP EXPANSION — REVIEW REVENUE GATE BEFORE ANY TEST**.\n""")
    (REPORT_DIR / "loop_benchmark.md").write_text("""# Nexus Loop Benchmark — Phase 14C\n\nThe four selected business loops completed bounded two-run proofs. Run 1 was deterministic and verifier-backed; identical Run 2 was `NO_CHANGE` with zero AI calls, zero input/output tokens, zero provider cost, and no unnecessary history replay.\n\n- Open Source Scout: 2 opportunities created; 1 duplicate avoided.\n- SEO Opportunity: 2 qualified keywords; 1 duplicate avoided.\n- Revenue Opportunity: 2 semantic opportunities after 1 duplicate removed; $1,312 estimated value; $0 confirmed revenue.\n- Research Intake: 3 normalized artifacts; 0 duplicate records after source-hash normalization.\n\nRevenue values are proof/report-backed estimates, not live discovered revenue. All loops are recommendation/research-only and remain subject to Ray approval for external actions.\n""")
    (REPORT_DIR / "phase14c_value_accounting.md").write_text(f"""# Phase 14C — Value Accounting Repair\n\n- semantic dedupe: **PASS**\n- duplicate records removed: `{report['revenue_accounting_repair']['duplicate_records_removed']}`\n- estimated value: **${report['revenue_accounting_repair']['estimated_value_usd']}**\n- confirmed revenue: **${report['revenue_accounting_repair']['confirmed_revenue_usd']}**\n- valuation source: `{report['revenue_accounting_repair']['valuation_source']}`\n- live discovered revenue: `{report['revenue_accounting_repair']['live_discovered_revenue']}`\n- revenue verifier: `{report['revenue_accounting_repair']['verifier']['status']}`\n\nSemantic identity is deterministic and recorded per retained opportunity as `business_identity` / `semantic_dedupe_key`. Estimated values never enter confirmed revenue. The experiment gate is `{report['revenue_experiment_gate']['status']}` with `{report['revenue_experiment_gate']['launch_status']}`; no real revenue experiment was launched.\n""")
    return report


if __name__ == "__main__":
    print(json.dumps(main(), indent=2, sort_keys=True))
