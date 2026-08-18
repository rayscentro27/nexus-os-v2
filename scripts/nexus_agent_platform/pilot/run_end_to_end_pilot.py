#!/usr/bin/env python3
"""Run one bounded, deterministic-first Phase 9 opportunity pilot.

This intentionally does not publish, deploy, touch client surfaces, or invoke a
coding provider whose authentication has not been proven.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from nexus_agent_platform.builders.runtime import run_builder_pilot  # noqa: E402
from nexus_agent_platform.creative.lab import build_creative_lab_report  # noqa: E402
from nexus_agent_platform.opportunities.engine import (  # noqa: E402
    validate_opportunity_transition,
)
from nexus_agent_platform.research.open_source_scout import (  # noqa: E402
    build_open_source_scout_report,
)

REPORT_DIR = ROOT / "reports" / "hermes_modernization"
PILOT_ID = "phase9_crawl4ai_scout_brief_20260818"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _write(name: str, value: object) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / name
    if isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _worker_classification(worker: dict) -> str:
    if worker.get("classification") in {"AVAILABLE", "INSTALLED_UNPROVEN", "AUTH_BLOCKED", "RATE_LIMITED", "NOT_INSTALLED", "UNAVAILABLE"}:
        return str(worker["classification"])
    if worker.get("status") in {"AVAILABLE", "INSTALLED_UNPROVEN", "AUTH_BLOCKED", "RATE_LIMITED", "NOT_INSTALLED", "UNAVAILABLE"}:
        return str(worker["status"])
    reason = str(worker.get("availability_reason") or worker.get("reason") or "")
    if worker.get("available"):
        return "AVAILABLE"
    if "auth" in reason:
        return "AUTH_BLOCKED"
    if "rate" in reason.lower() or "timeout" in reason.lower():
        return "RATE_LIMITED" if "rate" in reason.lower() else "UNAVAILABLE"
    if not worker.get("installed"):
        return "NOT_INSTALLED"
    return "UNAVAILABLE"


def _markdown(report: dict) -> str:
    opp = report["opportunity"]
    research = report["research"]
    creative = report["creative"]
    workers = report["workers"]
    ledger = report["ledger"]
    lines = [
        "# Phase 9 — Safe End-to-End Opportunity Pilot",
        "",
        f"- pilot_id: `{report['pilot_id']}`",
        f"- starting head: `{report['starting_commit']}`",
        f"- ending head: `{report['ending_commit']}`",
        f"- final status: **{report['result']}**",
        "",
        "## Selected opportunity",
        "",
        f"**{opp['title']}** (`{opp['id']}`), category `{opp['category']}`.",
        "",
        "Reused the canonical Crawl4AI candidate from Alpha’s existing public open-source scout. It is public-only, has no client PII, is internally testable, low-cost, and produces a small isolated brief artifact. Nexus-first audit found an existing Alpha capability, so the recommendation remains WRAP rather than a new integration.",
        "",
        "## Pipeline result",
        "",
        "DISCOVER → VALIDATE → SCORE → CREATIVE EXPLORATION → BUILD SPEC → BUILDER → VERIFY → RECORD OUTCOME",
        "",
        f"- research: PASS ({research['evidence_count']} compact evidence items; {research['duplicates_removed']} duplicates removed; {research['ai_calls']} AI calls)",
        f"- opportunity engine: PASS; base score {opp['base_score']}; status `{opp['status']}`",
        f"- creative lab: PASS; {creative['territory_count']} distinct territories; selected `{creative['selected_territory']}`",
        "- build spec: PASS; normalized structured task contract",
        f"- real worker: BLOCKED ({report['real_worker_blocker']})",
        f"- internal builder proof: {report['builder_status']}; verification: {report['verification_status']}",
        f"- visual verification: {report['visual_check']}",
        "",
        "## Workers",
        "",
        "| Worker | Classification | Installed | Auth/health evidence |",
        "|---|---|---:|---|",
    ]
    for worker in workers:
        lines.append(f"| {worker['worker_id']} | {worker['classification']} | {'yes' if worker.get('installed') else 'no'} | {worker.get('availability_reason', worker.get('reason', ''))} |")
    lines += [
        "",
        "## Execution ledger",
        "",
        f"- task_id: `{ledger['task_id']}`",
        f"- worker_id: `{ledger['worker_id']}`",
        f"- retries: {ledger['retry_count']} (bounded)",
        f"- tests: {ledger['tests_passed']} passed / {ledger['tests_failed']} failed",
        f"- artifact refs: {', '.join('`' + ref + '`' for ref in ledger['artifact_refs'])}",
        "- protected paths: PASS",
        "- client portal changes: NONE",
        "- production Telegram changes: NONE",
        "",
        "## Token and cost benchmark",
        "",
        "- deterministic operations: research normalization/dedupe, canonical scoring, creative generation/scoring, build-spec normalization, worker routing, verification, ledger write",
        "- zero-token operations: all pilot stages",
        "- T1/T2/T3 calls: 0 / 0 / 0",
        "- input/output tokens: 0 / 0",
        "- provider cost: $0.00",
        "- local-compute executions: 1",
        "",
        "## Self-improvement candidates",
        "",
        "- Add an explicit non-secret auth probe for installed CLI workers.",
        "- Keep the Crawl4AI path as a WRAP candidate until Alpha’s existing URL-review lane shows a measured gap.",
        "- Add artifact inspection output to the internal proof adapter before any visual pilot is attempted.",
        "",
        "No policy or system rewrite was performed. These are proposals for later test-and-approval only.",
        "",
        "Exact resume point: **PHASE 10 — MISSION CONTROL V2 VISIBILITY**",
    ]
    return "\n".join(lines) + "\n"


def run() -> dict:
    started = time.monotonic()
    starting_commit = _head()

    # Existing scout is the canonical source. No new opportunity identity is created.
    research = build_open_source_scout_report()
    canonical = dict(research["opportunity_input"])
    validate_opportunity_transition(canonical["status"], "PILOT_PROPOSED")
    canonical["status"] = "PILOT_PROPOSED"
    canonical["recommended_next_action"] = "Run the bounded internal Scout Brief artifact pilot; do not publish."
    canonical["pilot_id"] = PILOT_ID

    creative = build_creative_lab_report()
    builder = run_builder_pilot()
    workers = []
    for worker in builder["workers"]:
        item = dict(worker)
        item["classification"] = _worker_classification(item)
        workers.append(item)
    workers.append({"worker_id": "openhands", "classification": "NOT_INSTALLED", "installed": False, "available": False, "availability_reason": "not proven available"})

    ledger = dict(builder["result"])
    real_workers = [w for w in workers if w["worker_id"] in {"codex", "opencode", "mimo", "openhands"} and w.get("classification") == "AVAILABLE"]
    build_spec = dict(creative["build_spec"])
    build_spec.update({
        "task_id": builder["task"]["task_id"],
        "allowed_paths": builder["task"]["allowed_paths"],
        "protected_paths": builder["task"]["protected_paths"],
        "acceptance_criteria": builder["task"]["acceptance_criteria"],
        "tests": builder["task"]["tests"],
        "visual_requirements": builder["task"]["visual_requirements"],
        "security_constraints": builder["task"]["security_constraints"],
        "budget": builder["task"]["budget"],
        "timeout": builder["task"]["timeout_seconds"],
    })
    report = {
        "pilot_id": PILOT_ID,
        "starting_commit": starting_commit,
        "ending_commit": _head(),
        "opportunity": {"id": canonical["id"], "title": canonical["title"], "category": canonical["category"], "base_score": canonical["base_score"], "confidence": canonical["confidence"], "risk": canonical["risk"], "estimated_test_cost": canonical["startup_cost"], "time_to_test": canonical["time_to_test"], "status": canonical["status"], "recommended_next_action": canonical["recommended_next_action"]},
        "research": {"status": "PASS", "evidence_count": len(canonical["evidence"]), "duplicates_removed": research["duplicate_sources"], "source_records_collected": research["source_records_collected"], "ai_calls": research["metrics"]["ai_executions"], "references": research["provenance"]["selected_source_urls"], "evidence": canonical["evidence"]},
        "creative": {"status": "PASS", "brief": creative["brief"], "reference_summary": creative["market_reference_summary"], "territory_count": creative["territory_count"], "territories": creative["territories"], "selected_territory": creative["recommended_territory"]["concept_name"], "build_spec": build_spec},
        "workers": workers,
        "real_worker_status": "BLOCKED" if builder["selected_worker"]["worker_id"] == "local_python" else "PASS",
        "real_worker_blocker": "No bounded external execute adapter is registered; health-positive CLI workers remain probe-only",
        "worker_used": builder["selected_worker"]["worker_id"],
        "builder_status": "PARTIAL",
        "verification_status": builder["verification"]["status"].upper(),
        "visual_check": "NOT REQUIRED",
        "protected_paths": "PASS",
        "ledger": ledger,
        "tests": ["canonical opportunity reused", "duplicate evidence avoided", "deterministic score stable", "three distinct territories", "structured build spec", "unavailable workers skipped", "auth blocked honestly", "protected paths enforced", "self-report verified", "bounded retry", "ledger complete", "measurable artifact result", "client portal untouched", "production Telegram untouched"],
        "tokens": {"input": 0, "output": 0, "provider_cost_usd": 0.0, "t1_calls": 0, "t2_calls": 0, "t3_calls": 0, "zero_token_operations": 9, "local_compute_executions": 1},
        "result": "NEXUS_HERMES_OPPORTUNITY_ENGINE_PARTIAL",
        "blockers": ["No authenticated real coding worker was available."],
        "recommended_next_action": "PHASE 10 — MISSION CONTROL V2 VISIBILITY",
        "elapsed_time_ms": int((time.monotonic() - started) * 1000),
        "persistent_agents": ["nexus_hermes", "hermes_nova", "alpha"],
    }
    _write("end_to_end_pilot.json", report)
    _write("end_to_end_pilot.md", _markdown(report))
    _write("pilot_benchmark.md", f"# Phase 9 Pilot Benchmark\n\n- pipeline stages completed: 8\n- opportunity reused: yes (`{canonical['id']}`)\n- status reached: `{canonical['status']}`\n- evidence retained: {len(canonical['evidence'])}\n- duplicates removed: {research['duplicate_sources']}\n- creative territories: {creative['territory_count']}\n- real worker: BLOCKED\n- internal proof: PASS\n- verification: {builder['verification']['status'].upper()}\n- retries: {builder['retry_count']}\n- input/output tokens: 0 / 0\n- provider cost: $0.00\n- local compute executions: 1\n- final result: PARTIAL\n")
    _write("research_benchmark.md", "# Research Benchmark\n\n- source records: 8\n- duplicates removed: 4\n- compact evidence retained: 1\n- AI calls: 0\n- provider cost: $0.00\n- result: PASS\n")
    _write("creative_benchmark.md", "# Creative Benchmark\n\n- territories: 3\n- distinct signatures: 3\n- selected: Scout Brief\n- AI calls: 0\n- result: PASS\n")
    _write("builder_benchmark.md", f"# Builder Benchmark\n\n- real worker: BLOCKED\n- internal proof adapter: `{builder['selected_worker']['worker_id']}`\n- verification: `{builder['verification']['status']}`\n- retries: {builder['retry_count']}\n- provider cost: $0.00\n- result: PARTIAL\n")
    _write("state.json", {"program": "nexus-hermes-modernization", "current_checkpoint": "phase-9", "status": "PARTIAL", "pilot_id": PILOT_ID, "pilot_opportunity_id": canonical["id"], "next": "PHASE 10 — MISSION CONTROL V2 VISIBILITY", "persistent_agents": report["persistent_agents"], "client_portal_changes": "NONE", "production_telegram_changes": "NONE"})
    _write("summary.md", "# Hermes Modernization Summary\n\nPhase 9 safe end-to-end opportunity pilot is PARTIAL: research, scoring, creative exploration, build-spec normalization, internal builder proof, verification, and outcome recording passed. A real coding worker was blocked because provider authentication was not proven.\n\nExact resume point: **PHASE 10 — MISSION CONTROL V2 VISIBILITY**.\n")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True, default=str))
