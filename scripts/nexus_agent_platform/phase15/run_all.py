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
from nexus_agent_platform.executive_portfolio import phase15_existing_dispatchers, run_executive_portfolio_cycle


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

    _write_policy_doc()
    results["product_evolution_dispatch"] = consume_queued_missions(scheduler_instance=str(scheduler_context.get("scheduler_instance", "UNKNOWN")))
    # Executive Portfolio is a bounded handoff layer above existing loops; it
    # records dispatch receipts but does not execute workers or create a scheduler.
    results["executive_portfolio"] = run_executive_portfolio_cycle(cycle_id=str(scheduler_context.get("scheduler_instance", "canonical-phase15")), dispatchers=phase15_existing_dispatchers())

    results["live_loops"] = run_live_loops()
    loop_report = results["live_loops"]

    results["live_research"] = run_live_research_session()
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
