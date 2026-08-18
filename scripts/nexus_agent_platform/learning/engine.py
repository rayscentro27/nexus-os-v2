"""Phase 12 deterministic learning and improvement proposal engine.

This module reads existing runtime evidence and emits observations plus
approval-gated proposal candidates. It never changes loop policy, worker
routing, model configuration, code, deployments, or production state.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[3]
REPORT_DIR = ROOT / "reports" / "hermes_modernization"
RUNTIME_DIR = ROOT / "reports" / "runtime"
LOOP_DIR = ROOT / "data" / "runtime" / "nexus_loops"
BUILDER_DIR = ROOT / "data" / "runtime" / "builder_execution_ledger"

NO_PROPOSAL = "NO_PROPOSAL"
STRUCTURED_PROPOSAL_CANDIDATE = "STRUCTURED_PROPOSAL_CANDIDATE"
UNKNOWN = "UNKNOWN"

PROPOSAL_TYPES = {
    "LOOP_CADENCE_CHANGE", "MODEL_TIER_CHANGE", "MAX_AI_CALLS_CHANGE",
    "TOKEN_BUDGET_CHANGE", "MATERIALITY_THRESHOLD_CHANGE", "CACHE_POLICY_CHANGE",
    "DEDUPE_POLICY_CHANGE", "VERIFIER_CHANGE", "WORKER_ROUTING_CHANGE",
    "OPPORTUNITY_WEIGHT_CHANGE", "RESEARCH_SOURCE_CHANGE",
    "CREATIVE_SCORING_WEIGHT_CHANGE",
}
PROPOSAL_STATUSES = {
    "PROPOSED", "TESTING", "TEST_PASSED", "TEST_FAILED", "AWAITING_APPROVAL",
    "APPROVED", "REJECTED", "PROMOTED", "ROLLED_BACK",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                value = json.loads(line)
            except ValueError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    except OSError:
        pass
    return rows


def _ref(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _stable_id(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _number(value: Any) -> Optional[float]:
    try:
        if value is None or isinstance(value, bool):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _freshness(source: Dict[str, Any]) -> str:
    timestamp = source.get("observed_at") or source.get("generated_at") or source.get("completed_at")
    if not timestamp:
        return UNKNOWN
    try:
        observed = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - observed.astimezone(timezone.utc)).total_seconds() / 86400)
        return "FRESH" if age_days <= 1 else "AGING" if age_days <= 7 else "STALE"
    except ValueError:
        return UNKNOWN


def _source(source_type: str, source_ref: str, observed_at: Any, evidence: str = "MEASURED") -> Dict[str, Any]:
    record = {"source_type": source_type, "source_ref": source_ref, "observed_at": observed_at or UNKNOWN, "evidence_classification": evidence}
    record["source_freshness"] = _freshness(record)
    return record


def _observation(
    *, source: Dict[str, Any], target_type: str, target_id: str, metric_name: str,
    baseline_value: Any, current_value: Any, delta: Any, threshold: Any,
    sample_size: int, pattern_type: str, materiality: str, confidence: str = "MEDIUM",
    requires_ai_interpretation: bool = False,
) -> Dict[str, Any]:
    payload = [pattern_type, target_type, target_id, metric_name, current_value, source.get("source_ref")]
    return {
        "observation_id": f"obs_{_stable_id(payload)}",
        "created_at": _now(),
        **source,
        "target_type": target_type,
        "target_id": target_id,
        "metric_name": metric_name,
        "baseline_value": baseline_value,
        "current_value": current_value,
        "delta": delta,
        "threshold": threshold,
        "sample_size": sample_size,
        "evidence_classification": source.get("evidence_classification", "MEASURED"),
        "freshness": source.get("source_freshness", UNKNOWN),
        "confidence": confidence,
        "pattern_type": pattern_type,
        "materiality": materiality,
        "requires_ai_interpretation": requires_ai_interpretation,
    }


def _proposal(
    *, observation: Dict[str, Any], proposal_type: str, target_type: str, target_id: str,
    current: Dict[str, Any], candidate: Dict[str, Any], hypothesis: str,
    benefit: str, cost_reduction: str, quality: str, reliability: str,
    risk: str, test_plan: List[str], success: List[str], failure: List[str], rollback: List[str],
) -> Dict[str, Any]:
    if proposal_type not in PROPOSAL_TYPES:
        raise ValueError(f"unsupported proposal type: {proposal_type}")
    return {
        "proposal_id": f"prop_{_stable_id([proposal_type, target_id, observation['observation_id']])}",
        "created_at": _now(),
        "proposal_type": proposal_type,
        "target_type": target_type,
        "target_id": target_id,
        "observation_ids": [observation["observation_id"]],
        "evidence_refs": [{"source_type": observation["source_type"], "source_ref": observation["source_ref"]}],
        "current_configuration": current,
        "candidate_configuration": candidate,
        "hypothesis": hypothesis,
        "expected_benefit": benefit,
        "expected_cost_reduction": cost_reduction,
        "expected_quality_change": quality,
        "expected_reliability_change": reliability,
        "risk": risk,
        "confidence": observation["confidence"],
        "sandbox_test_plan": test_plan,
        "success_criteria": success,
        "failure_criteria": failure,
        "rollback_plan": rollback,
        "baseline_metrics": {observation["metric_name"]: observation["baseline_value"]},
        "candidate_metrics": {},
        "comparison_result": UNKNOWN,
        "status": "PROPOSED",
        "approval_required": True,
        "approval_id": None,
        "recommended_action": "Review and authorize a bounded sandbox test; do not promote automatically.",
    }


def _no_proposal(detector: str, reason: str) -> Dict[str, Any]:
    return {"detector": detector, "result": NO_PROPOSAL, "reason": reason}


def detect_repeated_no_change_ai_use(loop_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in loop_rows:
        if int(row.get("ai_calls") or 0) > 0:
            grouped.setdefault(str(row.get("loop_id", UNKNOWN)), []).append(row)
    for loop_id, rows in grouped.items():
        hashes = [row.get("output_hash") for row in rows if row.get("output_hash")]
        if len(rows) >= 2 and len(set(hashes)) == 1 and hashes:
            source = _source("RUNTIME_LEDGER", "data/runtime/nexus_loops/execution_ledger.jsonl", rows[-1].get("completed_at"))
            observation = _observation(source=source, target_type="LOOP", target_id=loop_id, metric_name="unchanged_ai_outputs", baseline_value=0, current_value=len(rows), delta=len(rows), threshold=2, sample_size=len(rows), pattern_type="REPEATED_NO_CHANGE_AI", materiality="HIGH")
            return {"detector": "repeated_no_change_ai_use", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="MAX_AI_CALLS_CHANGE", target_type="LOOP", target_id=loop_id, current={"ai_calls": "observed"}, candidate={"max_ai_calls": 0, "deterministic_precheck": True}, hypothesis="Repeated identical AI output can be replaced by a deterministic precheck or cache.", benefit="Avoid repeated non-material AI execution.", cost_reduction="Expected provider token reduction.", quality="No expected change while output hash remains stable.", reliability="Expected stable or improved repeatability.", risk="A stale cache could hide a meaningful input change.", test_plan=["Run candidate on the same bounded fixture and a changed-input fixture."], success=["No changed-input regression", "At least one repeated call avoided"], failure=["Changed input receives stale output", "Quality or verifier result declines"], rollback=["Restore prior AI-call allowance and disable cache candidate"]) }
    return _no_proposal("repeated_no_change_ai_use", "No repeated AI outputs with sufficient runtime evidence.")


def detect_excessive_model_tier(loop_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    candidates = [row for row in loop_rows if str(row.get("model_tier", "")).startswith(("T2", "T3")) and int(row.get("ai_calls") or 0) > 0]
    quality = [row for row in candidates if int(row.get("value_events") or 0) == 0 and row.get("verifier_status") in {"pass", "passed"}]
    if len(quality) < 2:
        return _no_proposal("excessive_model_tier", "No repeated higher-tier executions with verified output and no measured value.")
    row = quality[-1]
    source = _source("RUNTIME_LEDGER", "data/runtime/nexus_loops/execution_ledger.jsonl", row.get("completed_at"))
    observation = _observation(source=source, target_type="LOOP", target_id=str(row.get("loop_id", UNKNOWN)), metric_name="higher_tier_no_value_rate", baseline_value=1.0, current_value=len(quality) / len(candidates), delta=0.0, threshold=0.5, sample_size=len(candidates), pattern_type="MODEL_TIER_EXCESS", materiality="MEDIUM")
    return {"detector": "excessive_model_tier", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="MODEL_TIER_CHANGE", target_type="LOOP", target_id=observation["target_id"], current={"model_tier": "T2_OR_T3"}, candidate={"model_tier": "T1_CHEAP_AI"}, hypothesis="A lower tier may preserve verified quality for this loop.", benefit="Reduce model cost and latency.", cost_reduction="Expected lower provider rate.", quality="Must remain verifier-passing.", reliability="No expected change if deterministic verifier passes.", risk="Lower reasoning quality on ambiguous inputs.", test_plan=["Shadow T1 against the existing higher-tier baseline."], success=["Verifier pass rate not lower than baseline", "Cost per success decreases"], failure=["Verifier pass rate declines", "Material output regression"], rollback=["Restore prior model tier"]) }


def detect_low_value_loop(loop_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in loop_rows:
        grouped.setdefault(str(row.get("loop_id", UNKNOWN)), []).append(row)
    for loop_id, rows in grouped.items():
        if len(rows) >= 2 and all(int(row.get("value_events") or 0) == 0 for row in rows) and all(row.get("result_status") in {"success", "pass"} for row in rows):
            source = _source("RUNTIME_LEDGER", "data/runtime/nexus_loops/execution_ledger.jsonl", rows[-1].get("completed_at"))
            observation = _observation(source=source, target_type="LOOP", target_id=loop_id, metric_name="value_events_per_execution", baseline_value=0, current_value=0, delta=0, threshold=1, sample_size=len(rows), pattern_type="ZERO_VALUE_LOOP", materiality="HIGH")
            return {"detector": "low_value_loop", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="LOOP_CADENCE_CHANGE", target_type="LOOP", target_id=loop_id, current={"cadence": "current"}, candidate={"cadence": "pause_or_reduce_pending_review"}, hypothesis="Repeated successful executions without value events may not justify the current cadence.", benefit="Reduce work with no measured business value.", cost_reduction="Expected local compute and token reduction.", quality="No quality claim until value definition is confirmed.", reliability="Fewer unnecessary executions.", risk="A real but delayed value event could be missed.", test_plan=["Run a bounded observation window with reduced cadence; do not alter production scheduler."], success=["No missed required health signal", "No material value loss", "Lower executions per period"], failure=["Required signal becomes stale", "Value event is missed"], rollback=["Restore existing cadence"]) }
    return _no_proposal("low_value_loop", "No repeated successful loop with zero value events.")


def detect_retry_heavy_worker(builder_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in builder_rows:
        grouped.setdefault(str(row.get("worker_id", UNKNOWN)), []).append(row)
    for worker_id, rows in grouped.items():
        retries = sum(int(row.get("retry_count") or 0) for row in rows)
        if len(rows) >= 2 and retries / len(rows) >= 2:
            source = _source("RUNTIME_LEDGER", "data/runtime/builder_execution_ledger/ledger.jsonl", rows[-1].get("finished_at"))
            observation = _observation(source=source, target_type="WORKER", target_id=worker_id, metric_name="retries_per_execution", baseline_value=0, current_value=round(retries / len(rows), 4), delta=round(retries / len(rows), 4), threshold=2, sample_size=len(rows), pattern_type="HIGH_RETRY_RATE", materiality="HIGH")
            return {"detector": "retry_heavy_worker", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="WORKER_ROUTING_CHANGE", target_type="WORKER", target_id=worker_id, current={"worker": worker_id}, candidate={"worker": "compare_available_worker"}, hypothesis="A retry-heavy worker may be a poor default for this task class.", benefit="Improve builder reliability and reduce retries.", cost_reduction="Reduce repeated local/provider execution.", quality="Must satisfy the same verification contract.", reliability="Expected higher first-attempt success.", risk="Alternative worker may be unavailable or differently governed.", test_plan=["Run identical isolated fixtures through eligible workers."], success=["Higher first-attempt pass rate", "No protected-path violations"], failure=["Lower verification pass rate", "New security or timeout failure"], rollback=["Restore prior deterministic routing"]) }
    return _no_proposal("retry_heavy_worker", "No worker has a measured retry rate at the proposal threshold.")


def detect_duplicate_research_source(pilot: Dict[str, Any]) -> Dict[str, Any]:
    research = pilot.get("research") or {}
    collected = _number(research.get("source_records_collected"))
    duplicates = _number(research.get("duplicates_removed"))
    if collected is None or duplicates is None or collected <= 0 or duplicates / collected < 0.5:
        return _no_proposal("duplicate_research_source", "Research duplicate rate is unavailable or below the threshold.")
    source = _source("CANONICAL_STRUCTURED_STATE", "reports/hermes_modernization/end_to_end_pilot.json", research.get("generated_at") or pilot.get("ending_commit"))
    observation = _observation(source=source, target_type="RESEARCH_SOURCE", target_id=str(pilot.get("opportunity", {}).get("id", UNKNOWN)), metric_name="duplicate_rate", baseline_value=0, current_value=round(duplicates / collected, 4), delta=round(duplicates / collected, 4), threshold=0.5, sample_size=int(collected), pattern_type="HIGH_DUPLICATE_RATE", materiality="MEDIUM")
    return {"detector": "duplicate_research_source", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="DEDUPE_POLICY_CHANGE", target_type="RESEARCH_SOURCE", target_id=observation["target_id"], current={"dedupe": "current"}, candidate={"dedupe": "source_hash_and_url_before_retrieval"}, hypothesis="Pre-retrieval source dedupe may avoid repeated research work.", benefit="Reduce duplicate evidence collection.", cost_reduction="Expected research compute reduction.", quality="Evidence coverage must not decline.", reliability="More stable compact evidence sets.", risk="Over-aggressive dedupe may suppress a legitimate updated source.", test_plan=["Replay the bounded evidence fixture with URL/hash dedupe."], success=["Duplicate rate below threshold", "No loss of unique evidence"], failure=["Unique evidence removed", "Provenance becomes ambiguous"], rollback=["Restore prior dedupe behavior"]) }


def detect_stale_opportunity(pilot: Dict[str, Any]) -> Dict[str, Any]:
    opportunity = pilot.get("opportunity") or {}
    timestamp = opportunity.get("updated_at") or opportunity.get("last_checked") or pilot.get("generated_at")
    if not timestamp:
        return _no_proposal("stale_opportunity", "No freshness timestamp is available for the canonical opportunity.")
    source = _source("CANONICAL_STRUCTURED_STATE", "reports/hermes_modernization/end_to_end_pilot.json", timestamp)
    if source["source_freshness"] != "STALE":
        return _no_proposal("stale_opportunity", "Canonical opportunity is not stale according to its available timestamp.")
    target_id = str(opportunity.get("id", UNKNOWN))
    observation = _observation(source=source, target_type="OPPORTUNITY", target_id=target_id, metric_name="opportunity_age", baseline_value=0, current_value=source["source_freshness"], delta=UNKNOWN, threshold="STALE", sample_size=1, pattern_type="STALE_OPPORTUNITY", materiality="MEDIUM")
    return {"detector": "stale_opportunity", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="OPPORTUNITY_WEIGHT_CHANGE", target_type="OPPORTUNITY", target_id=target_id, current={"status": opportunity.get("status", UNKNOWN)}, candidate={"action": "refresh_or_pause_review"}, hypothesis="A stale opportunity should be refreshed before receiving further priority.", benefit="Avoid decisions based on stale evidence.", cost_reduction="Avoid unnecessary execution on stale work.", quality="Improves evidence freshness.", reliability="Improves prioritization reliability.", risk="A useful opportunity may be paused prematurely.", test_plan=["Refresh public evidence in a bounded read-only run."], success=["Fresh evidence or explicit pause decision"], failure=["Refresh cannot establish current evidence"], rollback=["Keep prior opportunity status and record the failed refresh"]) }


def detect_high_tokens_per_success(loop_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [row for row in loop_rows if int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0) > 0 and int(row.get("successful_outputs") or 0) > 0]
    if len(rows) < 2:
        return _no_proposal("high_tokens_per_success", "Insufficient token-bearing successful executions.")
    tokens = sum(int(row.get("input_tokens") or 0) + int(row.get("output_tokens") or 0) for row in rows)
    successes = sum(int(row.get("successful_outputs") or 0) for row in rows)
    rate = tokens / successes if successes else 0
    if rate < 1000:
        return _no_proposal("high_tokens_per_success", "Measured tokens per success are below the threshold.")
    row = rows[-1]
    source = _source("RUNTIME_LEDGER", "data/runtime/nexus_loops/execution_ledger.jsonl", row.get("completed_at"))
    observation = _observation(source=source, target_type="LOOP", target_id=str(row.get("loop_id", UNKNOWN)), metric_name="tokens_per_success", baseline_value=0, current_value=rate, delta=rate, threshold=1000, sample_size=len(rows), pattern_type="HIGH_TOKENS_PER_SUCCESS", materiality="HIGH")
    return {"detector": "high_tokens_per_success", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="TOKEN_BUDGET_CHANGE", target_type="LOOP", target_id=observation["target_id"], current={"tokens_per_success": rate}, candidate={"action": "compact_delta_and_budget_review"}, hypothesis="A bounded token budget and compact delta may preserve quality at lower cost.", benefit="Reduce tokens per verified success.", cost_reduction="Expected token cost reduction.", quality="Verifier pass rate must hold.", reliability="Stable compact outputs.", risk="Over-compression may omit necessary context.", test_plan=["Compare compact-delta candidate against the current fixture."], success=["Lower tokens per success", "No verifier regression"], failure=["Verifier failure or missing required evidence"], rollback=["Restore current token budget"]) }


def detect_deterministic_candidate(loop_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [row for row in loop_rows if row.get("loop_id")]
    deterministic = [row for row in rows if int(row.get("ai_calls") or 0) == 0 and row.get("verifier_status") in {"pass", "passed"}]
    if len(deterministic) < 2:
        return _no_proposal("deterministic_candidate", "Insufficient verified deterministic executions.")
    loop_id = str(deterministic[-1].get("loop_id", UNKNOWN))
    source = _source("RUNTIME_LEDGER", "data/runtime/nexus_loops/execution_ledger.jsonl", deterministic[-1].get("completed_at"))
    observation = _observation(source=source, target_type="LOOP", target_id=loop_id, metric_name="deterministic_success_share", baseline_value=0, current_value=round(len(deterministic) / len(rows), 4), delta=round(len(deterministic) / len(rows), 4), threshold=0.8, sample_size=len(rows), pattern_type="DETERMINISTIC_CANDIDATE", materiality="MEDIUM")
    return {"detector": "deterministic_candidate", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="MAX_AI_CALLS_CHANGE", target_type="LOOP", target_id=loop_id, current={"max_ai_calls": "current"}, candidate={"max_ai_calls": 0}, hypothesis="Verified deterministic execution may be sufficient for this loop class.", benefit="Keep the loop zero-token and deterministic.", cost_reduction="Avoid unnecessary AI calls.", quality="Current verifier evidence supports the bounded candidate.", reliability="Deterministic output is easier to reproduce.", risk="Future ambiguous inputs may need escalation.", test_plan=["Replay representative fixtures with deterministic-only routing and an escalation fixture."], success=["Verifier pass rate holds", "No required escalation is suppressed"], failure=["Verifier failure on representative fixture", "Ambiguous case is mishandled"], rollback=["Restore prior AI-call policy"]) }


def detect_worker_routing_candidate(builder_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for row in builder_rows:
        task = str(row.get("task_class") or row.get("task_id", UNKNOWN))
        worker = str(row.get("worker_id", UNKNOWN))
        grouped.setdefault(task, {}).setdefault(worker, []).append(row)
    for task, workers in grouped.items():
        if len(workers) < 2:
            continue
        rates = {worker: sum(1 for row in rows if row.get("status") == "pass") / len(rows) for worker, rows in workers.items() if rows}
        if rates and max(rates.values()) - min(rates.values()) >= 0.3:
            source = _source("RUNTIME_LEDGER", "data/runtime/builder_execution_ledger/ledger.jsonl", max((row.get("finished_at") for rows in builder_rows), default=None))
            best = max(rates, key=rates.get)
            observation = _observation(source=source, target_type="BUILDER_TASK_CLASS", target_id=task, metric_name="worker_success_rate_gap", baseline_value=min(rates.values()), current_value=max(rates.values()), delta=max(rates.values()) - min(rates.values()), threshold=0.3, sample_size=sum(len(rows) for rows in workers.values()), pattern_type="WORKER_ROUTING_IMBALANCE", materiality="HIGH")
            return {"detector": "worker_routing_candidate", "result": STRUCTURED_PROPOSAL_CANDIDATE, "observation": observation, "proposal": _proposal(observation=observation, proposal_type="WORKER_ROUTING_CHANGE", target_type="BUILDER_TASK_CLASS", target_id=task, current={"worker_rates": rates}, candidate={"preferred_worker": best}, hypothesis="The higher-success worker may be a better route for this bounded task class.", benefit="Improve first-attempt builder success.", cost_reduction="Reduce retries.", quality="Verification contract remains mandatory.", reliability="Higher observed success rate.", risk="Sample sizes may be small or worker health may change.", test_plan=["Run equal isolated fixtures through both workers."], success=["Candidate wins without protected-path violations", "Verification pass rate improves"], failure=["Candidate does not reproduce advantage", "Security or verification regression"], rollback=["Restore prior deterministic routing"]) }
    return _no_proposal("worker_routing_candidate", "No task class has two workers with a measured success-rate gap.")


DETECTORS = (
    detect_repeated_no_change_ai_use, detect_excessive_model_tier, detect_low_value_loop,
    detect_retry_heavy_worker, detect_duplicate_research_source, detect_stale_opportunity,
    detect_high_tokens_per_success, detect_deterministic_candidate, detect_worker_routing_candidate,
)


def _load_sources() -> Dict[str, Any]:
    paths = {
        "pilot": REPORT_DIR / "end_to_end_pilot.json",
        "daily_brief": REPORT_DIR / "daily_brief.json",
        "loop_ledger": LOOP_DIR / "execution_ledger.jsonl",
        "builder_ledger": BUILDER_DIR / "ledger.jsonl",
    }
    return {
        "pilot": _read_json(paths["pilot"], {}),
        "daily_brief": _read_json(paths["daily_brief"], {}),
        "loop_rows": _read_jsonl(paths["loop_ledger"]),
        "builder_rows": _read_jsonl(paths["builder_ledger"]),
        "paths": paths,
    }


def run_detectors(sources: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    data = sources or _load_sources()
    inputs = [
        lambda: detect_repeated_no_change_ai_use(data.get("loop_rows", [])),
        lambda: detect_excessive_model_tier(data.get("loop_rows", [])),
        lambda: detect_low_value_loop(data.get("loop_rows", [])),
        lambda: detect_retry_heavy_worker(data.get("builder_rows", [])),
        lambda: detect_duplicate_research_source(data.get("pilot", {})),
        lambda: detect_stale_opportunity(data.get("pilot", {})),
        lambda: detect_high_tokens_per_success(data.get("loop_rows", [])),
        lambda: detect_deterministic_candidate(data.get("loop_rows", [])),
        lambda: detect_worker_routing_candidate(data.get("builder_rows", [])),
    ]
    return [detector() for detector in inputs]


def build_learning_report() -> Dict[str, Any]:
    sources = _load_sources()
    detector_results = run_detectors(sources)
    observations = [result["observation"] for result in detector_results if result.get("result") == STRUCTURED_PROPOSAL_CANDIDATE]
    proposals = [result["proposal"] for result in detector_results if result.get("result") == STRUCTURED_PROPOSAL_CANDIDATE]
    refs = [_ref(path) for path in sources["paths"].values() if path.exists()]
    return {
        "report_id": f"learning_report_{_stable_id([_now()[:10], len(sources['loop_rows']), len(sources['builder_rows'])])}",
        "generated_at": _now(),
        "phase": "PHASE 12 — GOVERNED LEARNING / IMPROVEMENT PROPOSAL ENGINE",
        "status": "PROPOSAL_ONLY_NO_AUTONOMOUS_MUTATION",
        "source_priority": ["LIVE_RUNTIME_LEDGER", "CANONICAL_STRUCTURED_STATE", "GOVERNED_SUPABASE_DATA", "GENERATED_STRUCTURED_REPORT", "NARRATIVE_SUMMARY"],
        "audit_disposition": {
            "runtime_and_builder_ledgers": "KEEP",
            "daily_brief": "EXTEND",
            "governed_recommendations_and_approvals": "WRAP",
            "phase9_outcome_record": "MERGE",
            "learning_observation_and_proposal_contract": "CREATE_NEW",
            "autonomous_mutation_and_promotion": "DEFER",
        },
        "detectors": detector_results,
        "observations": observations,
        "proposals": proposals,
        "proposal_count": len(proposals),
        "observation_count": len(observations),
        "evidence_refs": refs,
        "approval_policy": {"approval_required": True, "approval_id": None, "auto_promote": False, "auto_rewrite": False},
        "next_phase_gate": "Ray must approve a bounded sandbox test before any candidate can enter TESTING.",
    }


def render_learning_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Hermes Learning Proposal Report — Phase 12", "",
        f"- status: **{report['status']}**",
        f"- observations: `{report['observation_count']}`",
        f"- proposal candidates: `{report['proposal_count']}`",
        "- autonomous mutation: `DISABLED`",
        "- automatic promotion: `DISABLED`",
        "", "## Audit disposition", "",
    ]
    lines.extend(f"- `{key}` → `{value}`" for key, value in report["audit_disposition"].items())
    lines.extend(["", "## Detector results", ""])
    for result in report["detectors"]:
        lines.append(f"- `{result['detector']}` → **{result['result']}** — {result.get('reason', result.get('observation', {}).get('pattern_type', 'candidate'))}")
    lines.extend(["", "## Proposal gate", "", report["next_phase_gate"], "", "## Evidence", ""])
    lines.extend(f"- `{ref}`" for ref in report["evidence_refs"])
    return "\n".join(lines) + "\n"


def write_learning_reports() -> Dict[str, Any]:
    report = build_learning_report()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "learning_proposals.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (REPORT_DIR / "learning_proposals.md").write_text(render_learning_report(report), encoding="utf-8")
    return report
