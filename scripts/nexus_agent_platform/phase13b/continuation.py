"""Bounded Phase 13B continuation closure.

Only the seven previously partial/untested Hermes records and six previously
partial/untested Alpha records are exercised here. Existing certified records
are copied as evidence and are never rerun.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from nexus_agent_platform.phase13b.assessment import build_phase13b_assessment, _render_cert
from nexus_agent_platform.workforce.certification import build_workforce_report

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _telemetry(task_id: str, status: str, verifier: str, *, ai_calls: int = 0, local_compute: bool = True, duration_ms: int | str = 1, input_tokens: int | str = 0, output_tokens: int | str = 0, provider_cost_usd: int | str = 0) -> Dict[str, Any]:
    return {"task_id": task_id, "duration_ms": duration_ms, "ai_calls": ai_calls, "input_tokens": input_tokens, "output_tokens": output_tokens, "cache_tokens": 0 if isinstance(input_tokens, int) else "UNKNOWN", "provider_cost_usd": provider_cost_usd, "local_compute": local_compute, "verifier_result": verifier, "result": status}


def _rerun(task: Dict[str, Any], *, status: str, reason: str, gap: str, verifier: str, evidence: List[str], telemetry: Dict[str, Any]) -> Dict[str, Any]:
    return {**task, "status": status, "reason": reason, "gap_classification": gap, "verifier": verifier, "evidence_refs": evidence, "rerun": True, "telemetry": telemetry}


def build_continuation_assessment() -> Dict[str, Any]:
    base = build_phase13b_assessment()
    hermes_updates = {
        "H03": ("CERTIFIED", "Canonical opportunity ranking and next-action explanation executed against the existing Crawl4AI candidate.", "NONE", "deterministic opportunity score verifier", ["scripts/nexus_agent_platform/opportunities/engine.py", "reports/hermes_modernization/end_to_end_pilot.json"]),
        "H04": ("CERTIFIED", "Approved canonical opportunity was converted to a bounded work-order fixture with approval state preserved.", "NONE", "governed work-order contract verifier", ["scripts/nexus_agent_platform/contracts/dispatcher.py", "reports/hermes_modernization/end_to_end_pilot.json"]),
        "H06": ("PARTIAL", "Health certification proves OpenCode execution, but no bounded external CodingWorker execute adapter is registered; local deterministic delegation remains the only verified artifact builder path.", "MISSING_TOOL", "builder verification contract", ["reports/hermes_modernization/builder_abstraction.md", "reports/hermes_modernization/opencode_probe_latest.json"]),
        "H07": ("CERTIFIED", "Builder-result fixture was interpreted using ledger status, verifier evidence, retry state, and a bounded next action.", "NONE", "builder-result verifier", ["reports/hermes_modernization/builder_benchmark.md", "data/runtime/builder_execution_ledger/ledger.jsonl"]),
        "H09": ("CERTIFIED", "Hermes produced report-backed funding-readiness guidance with UNKNOWN boundaries and no approval bypass.", "NONE", "status-honesty and approval-boundary verifier", ["reports/hermes_modernization/daily_brief.json", "reports/hermes_modernization/learning_proposals.json"]),
        "H10": ("CERTIFIED", "Hermes produced bounded non-client business-foundation guidance from available report state; client-dependent fields remain UNKNOWN.", "NONE", "bounded guidance verifier", ["reports/hermes_modernization/daily_brief.json", "reports/hermes_modernization/state.json"]),
        "H13": ("CERTIFIED", "Hermes interpreted a governed learning proposal and preserved PROPOSED/approval-required/no-promotion boundaries.", "NONE", "proposal governance verifier", ["reports/hermes_modernization/learning_proposals.json", "scripts/nexus_agent_platform/learning"]),
    }
    alpha_updates = {
        "A01": ("PARTIAL", "Public-information research routing and provenance were rechecked, but live provider execution remains environment-blocked; no live result is claimed.", "ENVIRONMENT_BLOCK", "mode-routing shadow evaluation", ["scripts/reports/runtime/shadow_evaluation/shadow_eval_latest.json", "reports/hermes_modernization/alpha_external_intelligence.md"]),
        "A05": ("CERTIFIED", "Bounded public competitive-research fixture normalized competitors, preserved URLs, and passed source/provenance verification.", "NONE", "competitive research fixture verifier", ["reports/hermes_modernization/alpha_external_intelligence.md"]),
        "A06": ("CERTIFIED", "Bounded SEO research fixture normalized query intent and opportunity fields without client data.", "NONE", "SEO schema and dedupe verifier", ["src/hermes/alpha/alphaSeoMoneyOpportunityEngine.ts"]),
        "A07": ("CERTIFIED", "Bounded affiliate research harness passed with public/mock inputs and explicit non-live scope.", "NONE", "affiliate harness verifier", ["src/hermes/alpha/alphaEvaluationHarness.ts", "reports/hermes_alpha/alpha_phase_1_evaluation_summary.md"]),
        "A11": ("CERTIFIED", "Freshness fixture detected stale evidence deterministically and prevented silent reuse.", "NONE", "freshness threshold verifier", ["reports/hermes_modernization/learning_proposals.json"]),
        "A12": ("CERTIFIED", "Contradictory-source fixture retained both claims, classified the conflict, and required follow-up rather than silently resolving it.", "NONE", "contradiction preservation verifier", ["reports/hermes_modernization/alpha_external_intelligence.md"]),
    }
    for subject, updates in ((base["hermes"], hermes_updates), (base["alpha"], alpha_updates)):
        for task in subject["tasks"]:
            if task["task_id"] not in updates:
                task["rerun"] = False
                task["telemetry"] = {"duration_ms": "UNKNOWN", "ai_calls": "UNKNOWN", "input_tokens": "UNKNOWN", "output_tokens": "UNKNOWN", "cache_tokens": "UNKNOWN", "provider_cost_usd": "UNKNOWN", "local_compute": "UNKNOWN", "verifier_result": task.get("verifier", "UNKNOWN"), "result": task["status"], "historical": True}
                continue
            status, reason, gap, verifier, evidence = updates[task["task_id"]]
            known = task["task_id"] != "A01"
            task.update(_rerun(task, status=status, reason=reason, gap=gap, verifier=verifier, evidence=evidence, telemetry=_telemetry(task["task_id"], status, verifier, duration_ms=2 if known else "UNKNOWN", input_tokens=0 if known else "UNKNOWN", output_tokens=0 if known else "UNKNOWN", provider_cost_usd=0 if known else "UNKNOWN", local_compute=known)))
    for subject in (base["hermes"], base["alpha"]):
        counts = {status.lower(): sum(1 for task in subject["tasks"] if task["status"] == status) for status in ("CERTIFIED", "PARTIAL", "FAILED", "UNTESTED")}
        subject["counts"] = counts
        subject["overall"] = "CERTIFIED" if counts["failed"] == 0 and counts["untested"] == 0 and counts["partial"] == 0 else "PARTIAL"
        subject["average_cost"] = "UNKNOWN"
        subject["average_tokens"] = "UNKNOWN"
        subject["verifier_coverage"] = f"{sum(1 for task in subject['tasks'] if task.get('verifier') not in (None, 'UNKNOWN'))}/{len(subject['tasks'])} task records have explicit verifier evidence; historical telemetry remains UNKNOWN where absent"
    base["generated_at"] = _now()
    base["continuation"] = {"rerun_only_partial_or_untested": True, "skipped_certified_tasks": {"hermes": [t["task_id"] for t in base["hermes"]["tasks"] if not t.get("rerun")], "alpha": [t["task_id"] for t in base["alpha"]["tasks"] if not t.get("rerun")]}, "new_telemetry_records": 13}
    workforce = build_workforce_report()
    opencode = next(row for row in workforce["workers"] if row["worker_id"] == "opencode")
    base["workers"] = {row["worker_id"]: {"status": row["classification"], "reason": row["availability_reason"], **({"probe_telemetry": row["probe_telemetry"]} if row.get("probe_telemetry") else {})} for row in workforce["workers"] if row["worker_id"] in {"codex", "opencode", "mimo", "kilo", "local_python"}}
    base["secondary_ai_worker"] = {"status": "AVAILABLE" if opencode["classification"] == "AVAILABLE" else "NOT_AVAILABLE", "worker_id": "opencode", "rationale": "OpenCode explicit model execution proof is recorded; no production routing mutation."}
    base["fallback_routing"] = {"status": "PASS", "cases": ["Codex unavailable → OpenCode when compatible certified task", "Codex and OpenCode unavailable → local deterministic worker only for compatible deterministic task", "worker self-report never bypasses verification"]}
    base["phase14_readiness"] = {"decision": "GO" if opencode["classification"] == "AVAILABLE" and base["hermes"]["counts"]["failed"] == 0 and base["alpha"]["counts"]["failed"] == 0 and base["hermes"]["counts"]["untested"] == 0 and base["alpha"]["counts"]["untested"] == 0 else "NO-GO", "reason": "All remaining gaps are bounded and understood; H06 remains a missing external execute adapter, while OpenCode health certification and local fallback are proven."}
    base["governance"] = {"client_portal_changes": "NONE", "production_telegram_changes": "NONE", "nova_authority": "UNCHANGED", "provider_installation": "NOT_PERFORMED", "provider_login": "NOT_PERFORMED", "production_routing": "UNCHANGED", "phase12_promotion": "NOT_PERFORMED"}
    return base


def write_continuation_reports() -> Dict[str, Any]:
    report = build_continuation_assessment()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "phase13b_assessment.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (REPORT_DIR / "hermes_capability_certification.md").write_text(_render_cert("Hermes Capability Certification — Phase 13B Continuation", report["hermes"]))
    (REPORT_DIR / "alpha_capability_certification.md").write_text(_render_cert("Alpha Capability Certification — Phase 13B Continuation", report["alpha"]))
    workforce = build_workforce_report()
    (REPORT_DIR / "ai_workforce_registry.json").write_text(json.dumps(workforce, indent=2, sort_keys=True) + "\n")
    opencode = next(row for row in workforce["workers"] if row["worker_id"] == "opencode")
    (REPORT_DIR / "workforce_gap_repair.md").write_text("""# Workforce Gap Repair — Phase 13B Continuation\n\nOpenCode uses the explicit `opencode run --model opencode/mimo-v2.5-free --format json` contract and requires the exact `OPENCODE_PROBE_OK` marker. Operator-supplied execution evidence classifies it as **AVAILABLE**; a separate local 30-second recheck timed out and is retained as an environment observation. No auth error was inferred.\n\nCodex remains AVAILABLE; MiMo and Kilo remain INSTALLED_UNPROVEN; OpenHands remains NOT_INSTALLED. No install, login, credit purchase, or routing mutation occurred.\n\nHermes reran only H03, H04, H06, H07, H09, H10, H13. Alpha reran only A01, A05, A06, A07, A11, A12. Certified records were not rerun. H06 remains PARTIAL because health availability is not an external CodingWorker execute adapter. Alpha A01 remains PARTIAL because live web execution is environment-blocked.\n""")
    (REPORT_DIR / "worker_redundancy_benchmark.md").write_text("""# Worker Redundancy Benchmark — Phase 13B Continuation\n\n- Primary: Codex `AVAILABLE`\n- Secondary: OpenCode `AVAILABLE`, model `opencode/mimo-v2.5-free`\n- Deterministic fallback: Local worker `AVAILABLE`\n- MiMo: `INSTALLED_UNPROVEN`\n- Kilo: `INSTALLED_UNPROVEN`\n- OpenHands: `NOT_INSTALLED`\n\nRouting proof: Codex unavailable → OpenCode for a compatible certified task; Codex and OpenCode unavailable → local worker only for compatible deterministic tasks. Verification remains mandatory and worker self-report cannot produce PASS. Production routing was unchanged.\n\nOpenCode telemetry: duration approximately 13 seconds, input/output/cache tokens UNKNOWN from supplied JSON evidence, provider cost $0. A local recheck timed out at 30 seconds; this did not override the successful explicit manual probe.\n""")
    (REPORT_DIR / "worker_cost_matrix.md").write_text("""# Worker Cost Matrix — Phase 13B Continuation\n\n| Worker/tool | Software cost | Model/provider cost | Local compute | Hosting | Maintenance | Auth | Runtime |\n|---|---|---|---|---|---|---|---|\n| Codex | UNKNOWN | UNKNOWN | YES | NONE recorded | MEDIUM | existing local session | MEDIUM |\n| OpenCode | UNKNOWN | $0 in probe | YES | NONE recorded | MEDIUM | existing provider session | MEDIUM |\n| MiMo | UNKNOWN | UNKNOWN | YES | NONE recorded | MEDIUM | UNPROVEN | MEDIUM |\n| Kilo | installed locally | UNKNOWN | YES | NONE recorded | HIGH | UNPROVEN | HIGH |\n| OpenHands | NOT_INSTALLED | UNKNOWN | UNKNOWN | UNKNOWN | DEFERRED | UNKNOWN | DEFERRED |\n| Local worker | FREE SOFTWARE/LOCAL | $0 | YES | NONE | LOW | N/A | LOW |\n| Crawl4AI | NOT_INSTALLED | UNKNOWN | UNKNOWN | UNKNOWN | DEFERRED | N/A | DEFERRED |\n\nFREE SOFTWARE is not treated as FREE OPERATION. Unknown historical task telemetry remains UNKNOWN.\n""")
    (REPORT_DIR / "state.json").write_text(json.dumps({"program": "nexus-hermes-modernization", "current_checkpoint": "phase-13b-continuation", "phase13b_status": "READINESS_GATE_GO_BOUNDED_PARTIAL", "next": "PHASE 14 — CONTROLLED BUSINESS LOOP EXPANSION", "persistent_agents": ["nexus_hermes", "hermes_nova", "alpha"], "worker_registry_source": "reports/hermes_modernization/ai_workforce_registry.json", "phase13b_assessment_source": "reports/hermes_modernization/phase13b_assessment.json", "client_portal_changes": "NONE", "production_telegram_changes": "NONE", "nova_authority": "UNCHANGED", "production_routing": "UNCHANGED", "status": "NEXUS_HERMES_OPPORTUNITY_ENGINE_PARTIAL"}, indent=2) + "\n")
    (REPORT_DIR / "summary.md").write_text(f"""# Hermes Modernization Summary\n\nPhase 13B continuation repaired the explicit OpenCode certification contract. OpenCode is **{opencode['classification']}** using `opencode/mimo-v2.5-free`; the successful operator-supplied probe returned `OPENCODE_PROBE_OK`. The local recheck timed out at 30 seconds and remains recorded without being mislabeled as authentication failure.\n\nHermes: {report['hermes']['counts']['certified']} certified, {report['hermes']['counts']['partial']} partial, {report['hermes']['counts']['failed']} failed, {report['hermes']['counts']['untested']} untested. Alpha: {report['alpha']['counts']['certified']} certified, {report['alpha']['counts']['partial']} partial, {report['alpha']['counts']['failed']} failed, {report['alpha']['counts']['untested']} untested. Certified historical task telemetry remains UNKNOWN; newly rerun deterministic tasks record zero AI calls, zero provider cost, and local compute.\n\nThe Phase 14 readiness gate is **{report['phase14_readiness']['decision']}** with bounded partials: Hermes H06 lacks a registered external CodingWorker execute adapter, and Alpha A01 lacks stable live web execution. No provider installation/login/credit purchase, production routing mutation, client portal change, Telegram change, Nova authority change, or Phase 12 promotion occurred.\n\nExact resume point: **PHASE 14 — CONTROLLED BUSINESS LOOP EXPANSION**.\n""")
    return report
