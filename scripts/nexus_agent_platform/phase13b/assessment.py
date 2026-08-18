"""Evidence-backed Phase 13B assessment.

This module translates existing certification results into bounded gap reports.
It does not install providers, call external services, change routing, or
promote capabilities.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task(task_id: str, name: str, status: str, reason: str, evidence: List[str], gap: str = "NONE", verifier: str = "UNKNOWN") -> Dict[str, Any]:
    return {"task_id": task_id, "task": name, "status": status, "reason": reason, "gap_classification": gap, "verifier": verifier, "evidence_refs": evidence}


HERMES_TASKS = [
    _task("H01", "Daily operator planning", "CERTIFIED", "Daily Brief and executive-priority paths produce a bounded next action from report-backed state.", ["reports/hermes_modernization/daily_brief.json", "tests/hermes_daily_brief.test.ts"], verifier="Daily Brief contract test"),
    _task("H02", "System health interpretation", "CERTIFIED", "System-health and failure-report paths are covered by existing runtime and conversation certification evidence.", ["reports/runtime/nexus_3_hermes_live_general_intelligence_certification.json", "tests/hermes_route_dominance_repair.test.ts"], verifier="general-intelligence certification"),
    _task("H03", "Opportunity prioritization", "PARTIAL", "Canonical Opportunity Engine scoring is proven, but a dedicated Hermes task-family fixture for ranking and explaining a current opportunity is not recorded.", ["reports/hermes_modernization/end_to_end_pilot.json", "scripts/nexus_agent_platform/opportunities/engine.py"], gap="TEST_NOT_EXECUTED", verifier="Opportunity Engine verifier only"),
    _task("H04", "Approved opportunity to work order", "PARTIAL", "Governed task creation is certified, but binding an approved canonical opportunity to a work-order fixture is not separately proven.", ["reports/runtime/hermes_capability_certification.json", "tests/hermes_general_intelligence_certification.test.ts"], gap="WORKFLOW_GAP", verifier="governed action tests"),
    _task("H05", "Approval routing", "CERTIFIED", "Approval-gated actions and explicit task separation are covered by the governed capability and conversation records.", ["reports/runtime/hermes_capability_certification.json", "tests/hermes_conversation_certification.test.ts"], verifier="approval/action separation"),
    _task("H06", "Builder delegation", "PARTIAL", "The local deterministic builder and verification contract are proven; no bounded external CodingWorker execute adapter is registered.", ["reports/hermes_modernization/builder_abstraction.md", "reports/hermes_modernization/end_to_end_pilot.json"], gap="MISSING_TOOL", verifier="builder verification contract"),
    _task("H07", "Builder-result interpretation", "UNTESTED", "No executed Hermes fixture evaluates a worker result, verification evidence, retry state, and next action as one task.", ["reports/hermes_modernization/builder_benchmark.md"], gap="TEST_NOT_EXECUTED"),
    _task("H08", "Cost/value interpretation", "CERTIFIED", "Daily Brief exposes confirmed, pending, blocked, token, cost, deterministic-share, and value-event facts without fabrication.", ["reports/hermes_modernization/daily_brief.json", "scripts/nexus_agent_platform/brief/daily_brief.py"], verifier="Daily Brief Python tests"),
    _task("H09", "Funding-readiness guidance", "PARTIAL", "Report-backed educational guidance exists, but client-dependent evidence is intentionally blocked and live client reads are not a certification source.", ["reports/runtime/nexus_3_hermes_live_general_intelligence_certification.json", "src/lib/hermesCapabilityRegistry.ts"], gap="GOVERNANCE_BLOCK", verifier="status-honesty tests"),
    _task("H10", "Business-foundation guidance", "PARTIAL", "The business-foundation domain exists, but client-specific data access is outside this protected certification and no isolated operator fixture is recorded.", ["src/lib/hermesCapabilityRegistry.ts", "reports/runtime/hermes_capability_certification.json"], gap="MISSING_DATA", verifier="UNKNOWN"),
    _task("H11", "Multi-step governed coordination", "CERTIFIED", "Existing founder/conversation certification reports a 116-turn local acceptance run with action separation and status honesty gates.", ["reports/runtime/nexus_3_hermes_production_certification.json", "tests/hermes_general_intelligence_certification.test.ts"], verifier="conversation certification"),
    _task("H12", "Daily Brief interpretation", "CERTIFIED", "Hermes reads the canonical Daily Brief adapter and preserves UNKNOWN/NOT_AVAILABLE boundaries.", ["src/lib/executive/hermesExecutiveAdvisor.ts", "tests/hermes_daily_brief.test.ts"], verifier="Daily Brief adapter test"),
    _task("H13", "Learning-proposal interpretation", "UNTESTED", "Phase 12 proposal records exist, but no Hermes task-family fixture proves explanation, approval boundary, and no-promotion behavior together.", ["reports/hermes_modernization/learning_proposals.json"], gap="TEST_NOT_EXECUTED"),
]

ALPHA_TASKS = [
    _task("A01", "Web research", "PARTIAL", "Mode routing is proven, but live provider execution is not a stable certification source; existing Alpha reports explicitly keep external providers disabled or bounded.", ["scripts/reports/runtime/shadow_evaluation/shadow_eval_latest.json", "reports/hermes_modernization/alpha_external_intelligence.md"], gap="ENVIRONMENT_BLOCK", verifier="mode-routing shadow evaluation"),
    _task("A02", "Source provenance", "CERTIFIED", "Phase 9 public evidence records retain source IDs, URLs, timestamps, classifications, and provenance.", ["reports/hermes_modernization/end_to_end_pilot.json", "reports/hermes_modernization/alpha_external_intelligence.md"], verifier="evidence schema and pilot record"),
    _task("A03", "Evidence classification", "CERTIFIED", "The public research pilot records KNOWN evidence and the canonical evidence contract restricts classifications.", ["reports/hermes_modernization/end_to_end_pilot.json", "scripts/nexus_agent_platform/opportunities/engine.py"], verifier="Opportunity Engine evidence contract"),
    _task("A04", "Research dedupe", "CERTIFIED", "The pilot collected 8 source records and removed 4 duplicates deterministically.", ["reports/hermes_modernization/end_to_end_pilot.json", "reports/hermes_modernization/learning_proposals.json"], verifier="dedupe counts"),
    _task("A05", "Competitive research", "UNTESTED", "No current executed competitive-research fixture with acceptance criteria and verifier result is recorded.", ["reports/hermes_modernization/alpha_external_intelligence_audit.md"], gap="TEST_NOT_EXECUTED"),
    _task("A06", "SEO research", "PARTIAL", "SEO opportunity code exists, but current certification records do not contain a bounded SEO research result with downstream verification.", ["src/hermes/alpha/alphaSeoMoneyOpportunityEngine.ts", "reports/hermes_modernization/alpha_external_intelligence_audit.md"], gap="TEST_NOT_EXECUTED"),
    _task("A07", "Affiliate research", "PARTIAL", "The Alpha phase-one harness covers an affiliate category using mock/local fixtures only; live source research is not proven.", ["reports/hermes_alpha/alpha_phase_1_evaluation_summary.md", "src/hermes/alpha/alphaEvaluationHarness.ts"], gap="ENVIRONMENT_BLOCK", verifier="mock harness"),
    _task("A08", "Open-source scouting", "CERTIFIED", "Nexus-first audit, source collection, dedupe, classification, and Crawl4AI opportunity handoff are proven.", ["reports/hermes_modernization/nexus_open_source_scout.md", "reports/hermes_modernization/end_to_end_pilot.json"], verifier="Phase 9 pilot"),
    _task("A09", "Opportunity discovery", "CERTIFIED", "The canonical opportunity candidate was produced from compact public evidence and scored without AI overwrite.", ["reports/hermes_modernization/end_to_end_pilot.json", "scripts/nexus_agent_platform/opportunities/engine.py"], verifier="deterministic score and pilot state"),
    _task("A10", "Research-to-Hermes handoff", "CERTIFIED", "The pilot records Alpha evidence as the Opportunity Engine input and Hermes-facing report source.", ["reports/hermes_modernization/alpha_external_intelligence.md", "reports/hermes_modernization/end_to_end_pilot.json"], verifier="pilot evidence refs"),
    _task("A11", "Freshness detection", "PARTIAL", "Freshness metadata exists, but no dedicated stale-source execution fixture with a verifier result is recorded.", ["reports/hermes_modernization/learning_proposals.json", "reports/hermes_modernization/alpha_external_intelligence_audit.md"], gap="TEST_NOT_EXECUTED"),
    _task("A12", "Contradictory-source handling", "UNTESTED", "No current Alpha contradiction fixture and resolution verifier is recorded.", ["reports/hermes_modernization/alpha_external_intelligence_audit.md"], gap="TEST_NOT_EXECUTED"),
]


def _counts(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
    return {status.lower(): sum(1 for task in tasks if task["status"] == status) for status in ("CERTIFIED", "PARTIAL", "FAILED", "UNTESTED")}


def build_phase13b_assessment() -> Dict[str, Any]:
    return {
        "phase": "PHASE 13B — CAPABILITY GAP REPAIR + WORKER REDUNDANCY",
        "generated_at": _now(),
        "hermes": {"tasks": HERMES_TASKS, "counts": _counts(HERMES_TASKS), "overall": "PARTIAL", "average_cost": "UNKNOWN", "average_tokens": "UNKNOWN", "verifier_coverage": "6/13 task records have explicit verifier evidence; partial/untested records are not promoted"},
        "alpha": {"tasks": ALPHA_TASKS, "counts": _counts(ALPHA_TASKS), "overall": "PARTIAL", "average_cost": "UNKNOWN", "average_tokens": "UNKNOWN", "verifier_coverage": "5/12 task records have explicit deterministic/evaluation evidence; live provider coverage remains partial"},
        "workers": {
            "codex": {"status": "AVAILABLE", "reason": "current verified checkpoint execution proof"},
            "mimo": {"status": "INSTALLED_UNPROVEN", "reason": "provider-specific command exists in adapter, but prior bounded execution did not prove success and no auth error was observed"},
            "kilo": {"status": "INSTALLED_UNPROVEN", "reason": "version 7.3.54 installed; no safe headless execution contract found locally"},
            "opencode": {"status": "UNAVAILABLE", "reason": "bounded run timed out; exact cause unresolved between interactive prompt/process hang/model configuration/network"},
            "local_python": {"status": "AVAILABLE", "reason": "deterministic isolated artifact execution and verification proven"},
        },
        "secondary_ai_worker": {"status": "NOT_AVAILABLE", "rationale": "No second AI coding worker has both harmless execution proof and a registered bounded execute adapter. Codex plus local deterministic fallback is currently sufficient for the proven internal artifact scope."},
        "crawl4ai": {"installed": False, "pilot": "NOT_RUN", "decision": "DEFER", "cost": "UNKNOWN", "reason": "Alpha certification exposed no material page-extraction gap for the proven public-repo pilot; existing Alpha path and deterministic evidence were sufficient. Revisit only for a measured JS-rendering/structured-extraction failure."},
        "openhands": {"installed": False, "decision": "DEFER", "cost": "UNKNOWN", "reason": "Codex health proof plus local deterministic builder cover current repo exploration, bounded edits, tests, worktrees, and verification; no long-horizon sandbox gap is evidenced."},
        "fallback_routing": {"status": "PASS", "cases": ["primary unavailable → next compatible certified worker if one exists", "no secondary AI execute adapter → local deterministic worker for compatible deterministic task", "worker self-report never bypasses verification"]},
        "phase14_readiness": {"decision": "NO-GO", "reason": "Hermes and Alpha remain bounded partial; no secondary AI coding worker is AVAILABLE; several required task families are untested."},
        "governance": {"client_portal_changes": "NONE", "production_telegram_changes": "NONE", "nova_authority": "UNCHANGED", "provider_installation": "NOT_PERFORMED", "provider_login": "NOT_PERFORMED", "production_routing": "UNCHANGED"},
    }


def _render_cert(title: str, subject: Dict[str, Any]) -> str:
    lines = [f"# {title}", "", f"Overall: **{subject['overall']}**", f"- certified: `{subject['counts']['certified']}`", f"- partial: `{subject['counts']['partial']}`", f"- failed: `{subject['counts']['failed']}`", f"- untested: `{subject['counts']['untested']}`", f"- average cost: `{subject['average_cost']}`", f"- average tokens: `{subject['average_tokens']}`", f"- verifier coverage: `{subject['verifier_coverage']}`", "", "| ID | Task | Status | Gap | Reason |", "|---|---|---|---|---|"]
    lines.extend(f"| {t['task_id']} | {t['task']} | **{t['status']}** | {t['gap_classification']} | {t['reason']} |" for t in subject["tasks"])
    lines.extend(["", "Certification is based on the cited executed reports/results, not architecture alone."])
    return "\n".join(lines) + "\n"


def write_phase13b_reports() -> Dict[str, Any]:
    assessment = build_phase13b_assessment()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "phase13b_assessment.json").write_text(json.dumps(assessment, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / "hermes_capability_certification.md").write_text(_render_cert("Hermes Capability Certification — Phase 13B", assessment["hermes"]), encoding="utf-8")
    (REPORT_DIR / "alpha_capability_certification.md").write_text(_render_cert("Alpha Capability Certification — Phase 13B", assessment["alpha"]), encoding="utf-8")
    return assessment
