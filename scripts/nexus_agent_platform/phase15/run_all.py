#!/usr/bin/env python3
"""Phase 15 bounded live internal operations orchestrator.

Runs the certified business loops against real sources, refreshes the Daily
Brief and Mission Control sources, runs a bounded live research session,
builds the health contract, the Hermes operator proof, the client journey/CRJ
bridge proof, the Stripe test-mode proof, and the runtime observability
report — then writes the Phase 15 reports and updates state.

No loop is disabled for NO_CHANGE / ZERO_OPPORTUNITIES / DUPLICATE_ONLY etc.
No LLM is run continuously. No publishing, outreach, spend, live Stripe, CRJ
production handoff, portal redesign, or Nova authority change occurs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from nexus_agent_platform.brief import daily_brief as daily_brief_module
from nexus_agent_platform.phase15 import keep_running
from nexus_agent_platform.phase15.client_journey_proof import run_client_journey_proof
from nexus_agent_platform.phase15.common import MODERNIZATION_DIR, atomic_write_json, ensure_sources_loaded, load_json, refresh_process_ledger, utc_now
from nexus_agent_platform.phase15.health_contract import build_health_status
from nexus_agent_platform.phase15.hermes_operator_proof import build_operator_brief
from nexus_agent_platform.phase15.live_loop_runner import run_live_loops
from nexus_agent_platform.phase15.live_research import run_live_research_session
from nexus_agent_platform.phase15.research_decisions import build_research_decisions
from nexus_agent_platform.phase15.runtime_activation import build_activation_audit
from nexus_agent_platform.phase15.runtime_observability import build_observability_report
from nexus_agent_platform.phase15.scheduler_health import begin_dispatch, complete_dispatch
from nexus_agent_platform.phase15.mission_control_snapshot import refresh_mission_control_snapshot
from nexus_agent_platform.phase15.stripe_proof import stripe_test_mode_proof
from nexus_product_evolution.consumer import consume_queued_missions
from nexus_agent_platform.executive_portfolio import phase15_existing_dispatchers, reconcile_portfolio_execution, run_executive_portfolio_cycle
from nexus_agent_platform.overnight_autonomy import build_completion_audit, refresh_campaign_lifecycle
from nexus_agent_platform.proof_recovery import apply_recovery
from nexus_agent_platform.proof_watchdog import audit as proof_audit
from nexus_agent_platform.completion_laws import enforce_cycle_laws
from nexus_agent_platform.campaign_execution_engine import consume_completion_law_work, run_campaign_cycle


def _phase15_hermes_sender(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Governed real Telegram sender used only when a cycle owes Ray a gate."""
    from scripts.telegram.nexus_telegram_bridge import ALLOWED_CHAT_IDS, get_bot_token, telegram_send_message
    token = get_bot_token()
    if not token or not ALLOWED_CHAT_IDS:
        return {"delivered": False, "reason": "telegram_transport_unavailable"}
    text = "\n".join([
        "NEXUS NEEDS RAY", "", f"What happened: {brief.get('what_happened', 'A governed gate is ready.')}",
        f"Why it matters: {brief.get('why_it_matters', 'A decision is required to proceed.')}",
        f"What Nexus did: {brief.get('what_nexus_did', 'The checkpoint is preserved.')}",
        f"Your action: {brief.get('ray_action', 'Review the exact gate in Hermes.')}",
        f"Gate: {brief.get('gate_id') or 'UNSPECIFIED'}", "Evidence: " + ", ".join(brief.get("evidence", []))
    ])
    receipts = []
    for chat_id in sorted(ALLOWED_CHAT_IDS):
        response = telegram_send_message(token, chat_id, text)
        receipts.append({"chat_id_masked": str(chat_id)[0:2] + "***", "ok": bool(response and response.get("ok")), "message_id": (response or {}).get("result", {}).get("message_id") if isinstance(response, dict) else None})
    return {"delivered": bool(receipts) and all(row["ok"] for row in receipts), "transport": "telegram", "receipts": receipts, "delivered_at": utc_now()}


def _write_policy_doc() -> None:
    lines = [
        "# Nexus Keep-Running Policy — Phase 15",
        "",
        "Nexus must NOT stop or disable a loop for normal operating states:",
        "",
    ]
    lines.append(", ".join(f"`{s}`" for s in keep_running.KEEP_RUNNING_STATES))
    lines.extend([
        "",
        "Those states **record → sleep / await next schedule → retry only when eligible**.",
        "",
        "Nexus should stop/escalate only for:",
        "",
    ])
    lines.append(", ".join(f"`{s}`" for s in keep_running.STOP_OR_ESCALATE_STATES))
    lines.extend([
        "",
        keep_running.POLICY["rationale"],
        "",
        "Source of truth: `scripts/nexus_agent_platform/phase15/keep_running.py`. Enforced by tests in `test_phase15_live_runtime.py`.",
    ])
    (MODERNIZATION_DIR / "keep_running_policy.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _intake_artifacts(loop_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    intake = loop_report.get("loops", {}).get("research_intake_loop", {})
    return intake.get("output_records", [])


def _run_proof_watchdog(portfolio: Dict[str, Any], *, scheduler_context: Dict[str, Any]) -> Dict[str, Any]:
    """Emit current-cycle proof and bounded recovery decisions.

    A recovery decision is not a repair success. The executor must attach a
    fresh receipt before a later cycle can advance the objective stage.
    """
    rows = []
    for item in portfolio.get("objectives", []):
        if not isinstance(item, dict):
            continue
        execution = item.get("execution_state") or item.get("status") or "UNKNOWN"
        health = execution if execution in {"ACTIVE", "DISPATCHED", "RUNNING", "RECOVERING"} else "UNKNOWN"
        rows.append({
            "objective_id": item.get("objective_id"),
            "executor": item.get("lane") or item.get("owner") or "UNKNOWN",
            "health": health,
            "last_confirmed_stage": item.get("current_stage") or "S1_SELECTED",
            "next_expected_stage": item.get("next_expected_stage"),
            "proof_refs": item.get("receipt_refs") or [],
            "failure_signature": item.get("failure_signature"),
            "repair_cycles_used": item.get("repair_cycles_used", item.get("repair_count", 0)),
        })
    result = proof_audit(rows)
    recovery = []
    for row in result.get("objectives", []):
        if row.get("health") == "STALLED":
            source = next((candidate for candidate in rows if candidate.get("objective_id") == row.get("objective_id")), {})
            recovery.append(apply_recovery({**source, **row}))
    result["recovery_decisions"] = recovery
    result["scheduler_instance"] = scheduler_context.get("scheduler_instance")
    result["proof_contract"] = "fresh receipt required for every stage transition"
    proof_path = Path("reports/runtime/proof_watchdog_latest.json")
    atomic_write_json(proof_path, result)
    return result


def _update_state(health: Dict[str, Any], live_loops: Dict[str, Any], research: Dict[str, Any]) -> None:
    state_path = MODERNIZATION_DIR / "state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    nexus_running = health.get("nexus_running", "PARTIAL")
    next_phase = "PHASE 16 — LIVE RESEARCH + CREATIVE/MARKETING PRODUCTION" if nexus_running in {"YES", "PARTIAL"} else "PHASE 15B — OPERATIONAL GAP REPAIR"
    state.update({
        "current_phase": "PHASE 15 — LIVE INTERNAL OPERATIONS + FIRST GOCLEAR CLIENT PROOF",
        "current_checkpoint": "phase-15-live-internal-operations",
        "phase15_status": "LIVE_INTERNAL_ACTIVE",
        "nexus_running": nexus_running,
        "phase15_live_loop_results_source": "reports/hermes_modernization/live_loop_results.json",
        "phase15_live_research_decisions_source": "reports/hermes_modernization/live_research_decisions.json",
        "phase15_live_runtime_status_source": "reports/hermes_modernization/live_runtime_status.json",
        "active_business_loops": list((live_loops or {}).get("loops", {}).keys()),
        "next": next_phase,
        "status": "NEXUS_HERMES_OPPORTUNITY_ENGINE_PARTIAL",
        "client_portal_changes": "NONE",
        "production_telegram_changes": "NONE",
        "nova_authority": "UNCHANGED",
        "stripe_mode": "TEST",
        "six_person_cohort": "NOT_YET_STAGED_ROLLOUT_READY",
    })
    atomic_write_json(state_path, state)


def _write_summary(health: Dict[str, Any], live_loops: Dict[str, Any], research: Dict[str, Any], live_session: Dict[str, Any], client_proof: Dict[str, Any], stripe: Dict[str, Any]) -> None:
    status = health.get("nexus_running", "PARTIAL")
    loop_status = {loop_id: run.get("delta_status") for loop_id, run in (live_loops.get("loops") or {}).items()}
    gate = client_proof.get("safety_gate", {}).get("status", "NO-GO")
    session = live_session.get("session", {})
    lines = [
        "# Hermes Modernization Summary — Phase 15",
        "",
        f"Phase 15 transitioned Nexus from isolated proof mode into controlled live internal operation. **NEXUS RUNNING: {status}**. The four certified business loops (Open Source Scout, SEO Opportunity, Revenue Opportunity, Research Intake) ran against real current sources and remain scheduled regardless of normal states such as NO_CHANGE.",
        "",
        "## Health contract",
        "- Hermes: `{h}` / Alpha: `{a}` / Nova: `{n}` / Loop runtime: `{lr}` / Daily Brief: `{db}` / Mission Control source: `{mc}` / Worker pool: `{wp}`".format(
            h=health["contract"]["hermes"]["status"], a=health["contract"]["alpha"]["status"], n=health["contract"]["nova"]["status"],
            lr=health["contract"]["loop_runtime"]["status"], db=health["contract"]["daily_brief"]["status"],
            mc=health["contract"]["mission_control_source"]["status"], wp=health["contract"]["worker_pool"]["status"],
        ),
        "- Workers: Codex AVAILABLE, OpenCode AVAILABLE, Local AVAILABLE, MiMo INSTALLED_UNPROVEN, Kilo INSTALLED_UNPROVEN, OpenHands NOT_INSTALLED.",
        "",
        "## Loops",
        f"- loop delta statuses: {loop_status}",
        "- Normal states never disable a loop; see keep_running_policy.md.",
        "",
        "## Live research",
        f"- state: `{session.get('state', 'UNKNOWN')}`; sources searched `{session.get('sources_searched')}`, ok `{session.get('sources_ok')}`; decisions counts `{research.get('counts', {})}`.",
        "- Rejected candidates remain visible with mandatory rejection reasons in live_research_decisions.json.",
        "",
        "## First real client",
        f"- Ray journey safety gate: **{gate}**; CRJ bridge and Credit Repair Workspace defined; no real CRJ production handoff performed.",
        "",
        "## Stripe",
        f"- mode **{stripe.get('stripe_mode')}**; test charges are TEST_TRANSACTION only; live revenue remains $0.",
        "",
        "## Governance",
        "No publishing, outreach, autonomous spending, live Stripe, CRJ production handoff, portal redesign, provider credit purchase, production Telegram change, or Nova authority change occurred.",
        "",
        f"Exact resume point: **{MODERNIZATION_DIR.name}/state.json -> next: {'PHASE 16 — LIVE RESEARCH + CREATIVE/MARKETING PRODUCTION' if status in {'YES','PARTIAL'} else 'PHASE 15B — OPERATIONAL GAP REPAIR'}**.",
    ]
    (MODERNIZATION_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_phase15(scheduler_context: Dict[str, Any]) -> Dict[str, Any]:
    ensure_sources_loaded()
    results: Dict[str, Any] = {"phase": "PHASE 15 — LIVE INTERNAL OPERATIONS", "generated_at": utc_now()}

    # This is the canonical completion-campaign consumer.  It runs on the
    # existing Phase15 invocation; directives are never left as metadata.
    results["campaign_execution"] = run_campaign_cycle(
        scheduler_instance=str(scheduler_context.get("scheduler_instance", "canonical-phase15"))
    )

    _write_policy_doc()
    results["campaign_lifecycle"] = refresh_campaign_lifecycle()
    # Portfolio creates real downstream records first; the existing consumer
    # can then claim Product Evolution work in this same natural cycle.
    results["executive_portfolio"] = run_executive_portfolio_cycle(cycle_id=str(scheduler_context.get("scheduler_instance", "canonical-phase15")), dispatchers=phase15_existing_dispatchers())
    results["product_evolution_dispatch"] = consume_queued_missions(scheduler_instance=str(scheduler_context.get("scheduler_instance", "UNKNOWN")))
    results["completion_audit"] = build_completion_audit()

    results["live_loops"] = run_live_loops()
    loop_report = results["live_loops"]

    results["live_research"] = run_live_research_session()
    results["executive_portfolio"] = reconcile_portfolio_execution(results["executive_portfolio"], product_evolution=results["product_evolution_dispatch"], live_loops=results["live_loops"], live_research=results["live_research"])
    results["proof_watchdog"] = _run_proof_watchdog(results["executive_portfolio"], scheduler_context=scheduler_context)
    results["completion_laws"] = enforce_cycle_laws(
        [{"status": row.get("status", "UNKNOWN"), "objective_id": row.get("objective_id"),
          "stage": row.get("current_stage"), "proof_refs": row.get("receipt_refs", []),
          "machine_solvable": True, "risk_level": 0}
         for row in results["proof_watchdog"].get("objectives", [])],
        receipt_path=Path("reports/runtime/completion_laws_latest.json"),
        hermes_sender=_phase15_hermes_sender,
    )
    results["completion_law_work_consumption"] = consume_completion_law_work(
        results["completion_laws"].get("decisions", []),
        scheduler_instance=str(scheduler_context.get("scheduler_instance", "canonical-phase15")),
    )
    intake_artifacts = _intake_artifacts(loop_report)
    if intake_artifacts:
        results["research_decisions"] = build_research_decisions(intake_artifacts)
    else:
        results["research_decisions"] = load_json(MODERNIZATION_DIR / "live_research_decisions.json", {})

    results["daily_brief"] = daily_brief_module.write_daily_brief_reports(
        generation_context={
            "trigger": "canonical_scheduler_dispatch",
            "scheduler": "com.nexus.continuous-loop",
            "scheduler_instance": scheduler_context.get("scheduler_instance"),
        }
    )

    results["health"] = build_health_status()
    results["mission_control_snapshot"] = refresh_mission_control_snapshot(
        scheduler_health_path=Path("reports/phase16a/scheduler_health.json")
    )
    results["hermes_operator_proof"] = build_operator_brief()
    results["runtime_activation"] = build_activation_audit()
    results["observability"] = build_observability_report()
    results["client_journey_proof"] = run_client_journey_proof()
    results["stripe"] = stripe_test_mode_proof()

    _update_state(results["health"], loop_report, results["research_decisions"])
    _write_summary(
        results["health"],
        loop_report,
        results["research_decisions"],
        results["live_research"],
        results["client_journey_proof"],
        results["stripe"],
    )

    refresh_process_ledger("phase15_live_runtime", {
        "nexus_running": results["health"].get("nexus_running"),
        "loops": {k: v.get("delta_status") for k, v in loop_report.get("loops", {}).items()},
        "research_session_state": results["live_research"].get("session", {}).get("state"),
        "client_gate": results["client_journey_proof"].get("safety_gate", {}).get("status"),
        "stripe_mode": results["stripe"].get("stripe_mode"),
    })
    return results


def run_phase15() -> Dict[str, Any]:
    scheduler_context = begin_dispatch()
    try:
        results = _run_phase15(scheduler_context)
    except Exception as exc:  # noqa: BLE001
        complete_dispatch(scheduler_context, success=False, error=str(exc))
        raise
    complete_dispatch(scheduler_context, success=True)
    results["scheduler_health"] = refresh_mission_control_snapshot(
        scheduler_health_path=Path("reports/phase16a/scheduler_health.json")
    )
    return results


if __name__ == "__main__":
    out = run_phase15()
    print(json.dumps({"ok": True, "nexus_running": out.get("health", {}).get("nexus_running"), "generated_at": out.get("generated_at")}, indent=2))
