"""Department-directive lifecycle -> Nova proactive events (NEXUS_AUTOMATIC_DIRECTIVE_AND_CONTINUATION_R1).

Pure translation: durable ``nexus_durable_jobs`` DEPARTMENT_DIRECTIVE rows (their
``governance_context.directive.events``) become proactive events for the existing
governed notifier. Every message carries PROJECT_ID, DIRECTIVE_ID, DEPARTMENT,
STATUS and NEXT_ACTION. Dedupe relies on each event's unique ``source``.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime, timezone
from typing import Any

DIRECTIVE_EVENT_KINDS = ("DIRECTIVE_CREATED", "WORK_STARTED", "WORK_COMPLETED", "WORK_FAILED",
                         "APPROVAL_REQUIRED", "PROJECT_BLOCKED", "PROJECT_CONTINUED",
                         "CREATIVE_CREATED", "CAMPAIGN_CREATED", "COMMERCE_OFFER_CREATED",
                         "REA_WORK_STARTED", "REA_WORK_COMPLETED", "REA_WORK_FAILED")
CRITICAL_KINDS = {"WORK_FAILED", "PROJECT_BLOCKED", "APPROVAL_REQUIRED", "REA_WORK_FAILED"}
MATERIAL_KINDS = {"DIRECTIVE_CREATED", "WORK_STARTED", "WORK_COMPLETED", "PROJECT_CONTINUED",
                  "CREATIVE_CREATED", "CAMPAIGN_CREATED", "COMMERCE_OFFER_CREATED",
                  "REA_WORK_STARTED", "REA_WORK_COMPLETED"}
RELATED_ID_KEYS = ("campaign_id", "asset_ids", "offer_id", "rea_job_id", "child_directive_id", "parent_directive_id")
TITLES = {
    "DIRECTIVE_CREATED": "Nexus created a department directive",
    "WORK_STARTED": "Department work started",
    "WORK_COMPLETED": "Department work completed",
    "WORK_FAILED": "Department work failed",
    "APPROVAL_REQUIRED": "Approval needed",
    "PROJECT_BLOCKED": "Department work is blocked",
    "PROJECT_CONTINUED": "Project continued to the next department",
    "CREATIVE_CREATED": "Creative assets created",
    "CAMPAIGN_CREATED": "Campaign package created",
    "COMMERCE_OFFER_CREATED": "Commerce offer created",
    "REA_WORK_STARTED": "REA work started",
    "REA_WORK_COMPLETED": "REA work completed",
    "REA_WORK_FAILED": "REA work failed",
}
# Events before this instant are never sent (build-phase smoke runs predate activation).
NOTIFY_SINCE = "2026-11-16T04:00:00+00:00"
QUERY = ("nexus_durable_jobs?job_type=eq.DEPARTMENT_DIRECTIVE&created_at=gte.{since}"
         "&select=job_id,directive:governance_context->directive&order=created_at.asc&limit=20")


def query(since: str = NOTIFY_SINCE) -> str:
    return QUERY.format(since=urllib.parse.quote(since, safe=""))


def _after(ts: Any, since: str) -> bool:
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")) >= datetime.fromisoformat(since)
    except ValueError:
        return False


def events_from_rows(rows: list[dict], since: str = NOTIFY_SINCE) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows or []:
        d = row.get("directive") if isinstance(row, dict) else None
        if not isinstance(d, dict):
            continue
        for ev in (d.get("events") or [])[-16:]:
            kind = str(ev.get("kind") or "")
            if kind not in DIRECTIVE_EVENT_KINDS or not _after(ev.get("at"), since):
                continue
            event_id = ev.get("event_id") or f"{ev.get('directive_id')}:{kind}:{ev.get('at')}"
            related = " | ".join(f"{k.upper()}={','.join(map(str, v)) if isinstance(v, list) else v}"
                                 for k in RELATED_ID_KEYS if (v := ev.get(k)))
            ids = (f"EVENT_ID={event_id} | PROJECT_ID={ev.get('project_id')} | BUSINESS_ID={ev.get('business_id') or 'UNKNOWN'} | "
                   f"DIRECTIVE_ID={ev.get('directive_id')} | DEPARTMENT={ev.get('department')} | STATUS={ev.get('status')}"
                   + (f" | {related}" if related else ""))
            out.append({"kind": kind, "event_type": kind, "title": TITLES[kind],
                        "summary": f"{str(ev.get('summary') or '')[:600]}\n{ids}",
                        "next": f"NEXT_ACTION={ev.get('next') or 'none'}",
                        "required_action": ev.get("required_action"),
                        "project_id": ev.get("project_id"), "department": ev.get("department"), "status": ev.get("status"),
                        "event_id": event_id,
                        "source": f"department_directive:{event_id}" if ev.get("event_id") else f"department_directive:{ev.get('directive_id')}:{kind}:{ev.get('at')}",
                        "directive_id": ev.get("directive_id")})
    return out


def classify(kind: str) -> str | None:
    if kind in CRITICAL_KINDS:
        return "CRITICAL"
    if kind in MATERIAL_KINDS:
        return "MATERIAL"
    return None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()
