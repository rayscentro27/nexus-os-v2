"""Integrations status feeder. Reads local/status rows only; never connects accounts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from feeders.common import ROOT, make_candidate, run_candidates, score_value, table_rows, text

FEEDER_ID = "integrations_status_feeder"
TASK_TYPE = "integration_status_project"
PROOF_EVENT = "integration_status_project_created"


def _integration(row: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(row.get("enabled"))
    status = "connected" if enabled else "needs_review"
    risk = text(row.get("risk_level"), "medium")
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="integrations", owner_tab="integrations", project_type="connector_status",
        unique_key=f"integration_registry:{row.get('id') or row.get('integration_key')}", source_kind="integration_registry",
        source_id=text(row.get("id") or row.get("integration_key")),
        title=f"Integration status: {text(row.get('name') or row.get('integration_key'), 'Connector')}",
        summary=text(row.get("purpose"), "Registered integration status row."),
        pros=["Reads registry only.", "No credentials are modified or printed."],
        cons=["Configuration changes require separate approval and secret handling."],
        recommendation="Review connector readiness; configure only through approved secure process." if not enabled else "Connector is marked enabled; continue monitoring through safe status reports.",
        proposed_schedule="Manual status review; scheduler activation requires approval.",
        next_action="Open Integrations and verify whether connector needs config, approval, or remains disabled.",
        score=70 if enabled else 40,
        status=status,
        approval_required=risk.lower() in {"high", "medium"},
        risk_triggers=["connector_requires_secret"] if row.get("requires_secret") else [],
    )


def _health(row: dict[str, Any]) -> dict[str, Any]:
    status = text(row.get("status"), "partial")
    needs = any(term in status.lower() for term in ("missing", "fail", "blocked", "partial"))
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="integrations", owner_tab="integrations", project_type="connector_status",
        unique_key=f"system_health:{row.get('id') or row.get('component')}", source_kind="system_health",
        source_id=text(row.get("id") or row.get("component")),
        title=f"System health connector: {text(row.get('component'), 'component')}",
        summary=text(row.get("summary"), f"System health status: {status}."),
        pros=["Uses existing local watch/status output.", "No external API is called here."],
        cons=["Status may be stale until `npm run nexus:watch` is run manually."],
        recommendation="Review missing/partial connector status and configure only through secure approved process." if needs else "Connector/status appears healthy in latest local row.",
        proposed_schedule="Manual watch/status review only.",
        next_action="Open Integrations or run the existing manual watch command when needed.",
        score=35 if needs else 70,
        status="needs_review" if needs else "summarized",
        approval_required=needs,
        risk_triggers=["connector_needs_config"] if needs else [],
    )


def _watch_report() -> dict[str, Any] | None:
    path = ROOT / "reports" / "runtime" / "nexus_watch_report_latest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(errors="ignore"))
    except Exception:
        return None
    missing = []
    for section in ("landing_page", "deploy_package"):
        missing.extend(data.get(section, {}).get("missing_env_names", []) or [])
    summary = f"Manual watch report ok={data.get('ok')}. Missing config names: {', '.join(sorted(set(missing))) or 'none'}."
    return make_candidate(
        feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
        department="integrations", owner_tab="integrations", project_type="connector_status",
        unique_key="runtime:nexus_watch_report_latest", source_kind="local_report", source_id=str(path.relative_to(ROOT)),
        title="Integration watch report summary",
        summary=summary,
        pros=["Uses local watch report only.", "No credentials are printed or changed."],
        cons=["Report is a point-in-time snapshot."],
        recommendation="Review missing config names and connector readiness; do not modify credentials in feeder runs.",
        proposed_schedule="Manual review after `npm run nexus:watch`.",
        next_action="Open Integrations and configure missing connectors only through approved secure process.",
        score=45 if missing else 70,
        status="needs_review" if missing else "summarized",
        approval_required=bool(missing),
        risk_triggers=["connector_needs_config"] if missing else [],
    )


def build_candidates(sb, limit: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in table_rows(sb, "integration_registry", f"select=*&order=integration_key.asc&limit={limit * 3}"):
        blob = " ".join([text(row.get("integration_key")), text(row.get("name")), text(row.get("category"))]).lower()
        if any(term in blob for term in ("trading", "trade", "oanda", "broker")):
            continue
        candidates.append(_integration(row))
    for row in table_rows(sb, "system_health", f"select=*&order=created_at.desc&limit={limit * 3}"):
        blob = " ".join([text(row.get("component")), text(row.get("summary"))]).lower()
        if any(term in blob for term in ("trading", "trade", "oanda", "broker")):
            continue
        candidates.append(_health(row))
    report = _watch_report()
    if report:
        candidates.append(report)
    return candidates


def run(sb, *, dry_run: bool, limit: int) -> dict[str, Any]:
    return run_candidates(sb, feeder_id=FEEDER_ID, task_type=TASK_TYPE, proof_event_type=PROOF_EVENT,
                          dry_run=dry_run, limit=limit, candidates=build_candidates(sb, limit))
