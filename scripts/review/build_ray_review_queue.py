#!/usr/bin/env python3
"""Build the Ray Review Queue from true decision candidates.

Dry-run by default. Live mode creates bounded `task_requests` rows with
`task_type=ray_review_item` and proof events only. It never approves, rejects, publishes, sends,
trades, deploys, starts schedulers, or calls external AI.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402

RUNTIME = ROOT / "reports" / "runtime" / "ray_review_queue_builder_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "nexus_ray_review_queue_latest.md"
TASK_TYPE = "ray_review_item"

AUTONOMOUS_TASK_TYPES = {
    "watched_resource",
    "watched_resource_update",
    "youtube_transcript_review",
    "affiliate_opportunity",
    "seo_keyword_opportunity",
    "seo_affiliate_content_plan",
    "research_experiment",
    "content_opportunity",
    "content_test_result",
    "trading_lab_research_project",
    "trading_lab_backtest_import",
    "hermes_decision_memory",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def text(value: Any, fallback: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    return fallback


def payload(row: dict[str, Any]) -> dict[str, Any]:
    p = row.get("payload")
    return p if isinstance(p, dict) else {}


def classify(row: dict[str, Any]) -> str:
    blob = f"{row.get('task_type', '')} {row.get('item_type', '')} {row.get('title', '')} {row.get('summary', '')} {json.dumps(payload(row))}".lower()
    if re.search(r"scheduler|cron|launchd|systemd", blob):
        return "scheduler_activation"
    if re.search(r"live trading|broker|auto_executor|funded", blob):
        return "trading_live_execution_blocked"
    if re.search(r"deploy|production", blob):
        return "production_change"
    if re.search(r"connector|oauth|integration|credential", blob):
        return "connector_setup"
    if "email" in blob:
        return "email_send"
    if re.search(r"social|facebook|instagram|tiktok|post|publish", blob):
        return "campaign_publish" if "campaign" in blob else "social_post"
    if re.search(r"lead|client|contact|dm|sms", blob):
        return "client_action" if "client" in blob else "lead_contact"
    if re.search(r"revenue|funding|goclear|apex|upgrade|purchase", blob):
        return "revenue_decision"
    if re.search(r"compliance|claim|guarantee|legal", blob):
        return "compliance_review"
    if re.search(r"experiment|test", blob):
        return "experiment_selection"
    if "report" in blob:
        return "report_review"
    return "high_value_strategy_choice"


def should_include(row: dict[str, Any]) -> tuple[bool, str]:
    p = payload(row)
    task_type = text(row.get("task_type") or p.get("task_type") or p.get("project_type"))
    if task_type == TASK_TYPE:
        return False, "already_review_queue_item"
    if task_type in AUTONOMOUS_TASK_TYPES and not (row.get("approval_required") is True or p.get("approval_required") is True or p.get("ray_decision_required") is True):
        return False, "autonomous_research"
    if row.get("approval_required") is True or p.get("approval_required") is True:
        return True, "approval_required"
    if row.get("ray_decision_required") is True or p.get("ray_decision_required") is True:
        return True, "ray_decision_required"
    if p.get("ready_for_publish") is True or p.get("ready_to_send") is True or p.get("ready_for_scheduler") is True:
        return True, "execution_ready"
    if p.get("strategic_decision") is True or p.get("hermes_strategic_decision") is True:
        return True, "strategic_decision"
    blob = f"{row.get('task_type', '')} {row.get('item_type', '')} {row.get('title', '')} {row.get('summary', '')} {json.dumps(p)}"
    if re.search(r"\b(publish|send|email|sms|dm|social|post|ad|spend|contact|client|lead|deploy|production|scheduler|cron|launchd|systemd|connector|oauth|live trading|broker|auto_executor)\b", blob, re.I):
        return True, "outbound_or_risky_keyword"
    return False, "autonomous_or_not_decision"


def priority(decision_type: str, row: dict[str, Any]) -> str:
    if decision_type in {"trading_live_execution_blocked", "production_change", "scheduler_activation"}:
        return "urgent"
    if row.get("approval_required") is True or payload(row).get("approval_required") is True:
        return "high"
    if decision_type in {"revenue_decision", "high_value_strategy_choice"}:
        return "high"
    return "medium"


def risk(decision_type: str) -> str:
    if decision_type == "trading_live_execution_blocked":
        return "critical"
    if decision_type in {"production_change", "scheduler_activation", "campaign_publish", "email_send", "social_post"}:
        return "high"
    if decision_type in {"lead_contact", "client_action", "compliance_review", "connector_setup"}:
        return "medium"
    return "low"


def options(decision_type: str) -> list[str]:
    if decision_type == "trading_live_execution_blocked":
        return ["Keep blocked", "Convert to paper-only research", "Request more risk review"]
    if decision_type == "scheduler_activation":
        return ["Keep manual only", "Approve scheduler plan later", "Request narrower schedule"]
    if decision_type in {"campaign_publish", "social_post", "email_send"}:
        return ["Approve prep only", "Request changes", "Park", "Create formal approval item"]
    return ["Proceed with internal prep", "Request changes", "Park", "Escalate to Approvals"]


DECISION_TYPE_TO_REASON = {
    "trading_live_execution_blocked": "trading_live_blocked",
    "scheduler_activation": "scheduler_activation_request",
    "connector_setup": "connector_activation_request",
    "production_change": "production_change_request",
    "campaign_publish": "campaign_ready",
    "social_post": "campaign_ready",
    "email_send": "send_ready",
    "lead_contact": "client_contact_ready",
    "client_action": "client_contact_ready",
    "revenue_decision": "spend_request",
}


def decision_reason(row: dict[str, Any], decision_type: str) -> str:
    """Automation-level decision reason. Level 3 escalates, never executes."""
    if decision_type == "trading_live_execution_blocked":
        return "trading_live_blocked"
    blob = f"{row.get('task_type', '')} {row.get('item_type', '')} {row.get('title', '')} {row.get('summary', '')} {json.dumps(payload(row))}".lower()
    if re.search(r"auto_executor|broker|funded|destructive|rls|broad scrape|media download|external ai.*(sensitive|private|customer)", blob):
        return "blocked_high_risk_escalation"
    if re.search(r"sensitive|private|customer data|credit-sensitive", blob):
        return "sensitive_data_request"
    if risk(decision_type) == "critical":
        return "blocked_high_risk_escalation"
    return DECISION_TYPE_TO_REASON.get(decision_type, "approval_gated_execution")


def candidate_from_row(row: dict[str, Any], source_table: str, reason: str) -> dict[str, Any]:
    p = payload(row)
    decision_type = classify(row)
    d_reason = decision_reason(row, decision_type)
    blocked_escalation_only = d_reason in ("blocked_high_risk_escalation", "trading_live_blocked")
    source_id = text(row.get("id"), text(p.get("source_id"), "local"))
    title = text(p.get("title"), text(row.get("title"), f"Ray decision: {decision_type.replace('_', ' ')}"))
    summary = text(p.get("summary"), text(row.get("summary"), text(row.get("result_summary"), reason)))
    return {
        "review_id": f"{source_table}:{source_id}:{decision_type}",
        "title": title,
        "decision_type": decision_type,
        "decision_reason": d_reason,
        "blocked_escalation_only": blocked_escalation_only,
        "department": text(p.get("department"), text(row.get("lane"), "command_center")),
        "source_table": source_table,
        "source_id": source_id,
        "source_url": text(p.get("source_url"), ""),
        "status": "pending_review",
        "priority": priority(decision_type, row),
        "risk_level": risk(decision_type),
        "approval_required": bool(row.get("approval_required") or p.get("approval_required")),
        "ray_decision_required": True,
        "due_at": p.get("due_at"),
        "summary": summary,
        "hermes_recommendation": text(p.get("hermes_recommendation"), f"Review this {decision_type.replace('_', ' ')} before any execution path."),
        "options": options(decision_type),
        "pros": p.get("pros") if isinstance(p.get("pros"), list) else ["Clarifies Ray's direction before risky or strategic work moves forward."],
        "cons": p.get("cons") if isinstance(p.get("cons"), list) else ["No outbound action should happen until the proper approval path is active."],
        "expected_outcome": text(p.get("expected_outcome"), "Decision guides internal prep only unless a separate execution approval is recorded."),
        "risk_notes": p.get("risk_notes") if isinstance(p.get("risk_notes"), list) else [reason],
        "proof_event_id": text(p.get("proof_event_id"), ""),
        "report_path": text(p.get("report_path"), ""),
        "created_at": text(row.get("created_at"), now()),
        "updated_at": text(row.get("updated_at"), text(row.get("created_at"), now())),
        "unique_key": f"{source_table}:{source_id}:{decision_type}",
    }


def load_rows(table: str, query: str) -> list[dict[str, Any]]:
    if not sb.configured():
        return []
    _status, rows = sb.get(table, query)
    return rows if isinstance(rows, list) else []


def local_report_candidates(limit: int) -> list[dict[str, Any]]:
    out = []
    for path in [ROOT / "reports" / "runtime" / "weekly_research_report_latest.json", ROOT / "reports" / "runtime" / "department_top_report_latest.json"]:
        if not path.exists():
            continue
        data = json.loads(path.read_text(errors="ignore"))
        top_items = data.get("top_items") if isinstance(data.get("top_items"), list) else []
        if top_items:
            out.append(candidate_from_row({
                "id": path.name,
                "task_type": "report_review",
                "title": data.get("title", "Research report review"),
                "summary": data.get("summary", "Review top research report direction."),
                "payload": {
                    "department": "command_center",
                    "report_path": str(path.relative_to(ROOT)),
                    "ray_decision_required": True,
                    "strategic_decision": True,
                    "hermes_recommendation": "Ask Hermes which direction to take from this report.",
                },
            }, "local_report", "weekly_or_department_report_ready"))
    return out[:limit]


def build_candidates(limit: int, department: str | None, decision_type: str | None) -> dict[str, Any]:
    scanned = 0
    skipped: dict[str, int] = {}
    candidates: list[dict[str, Any]] = []
    source_rows: list[tuple[str, dict[str, Any]]] = []
    source_rows += [("approvals", row) for row in load_rows("approvals", "select=*&order=created_at.desc&limit=100")]
    source_rows += [("task_requests", row) for row in load_rows("task_requests", "select=*&order=created_at.desc&limit=200")]
    for source_table, row in source_rows:
        scanned += 1
        include, reason = should_include(row)
        if not include:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        item = candidate_from_row(row, source_table, reason)
        if department and item["department"] != department:
            skipped["department_filter"] = skipped.get("department_filter", 0) + 1
            continue
        if decision_type and item["decision_type"] != decision_type:
            skipped["decision_type_filter"] = skipped.get("decision_type_filter", 0) + 1
            continue
        candidates.append(item)
    for item in local_report_candidates(limit):
        if department and item["department"] != department:
            continue
        if decision_type and item["decision_type"] != decision_type:
            continue
        candidates.append(item)
    # Dedupe within the dry-run list.
    seen = set()
    unique = []
    duplicates = 0
    for item in candidates:
        if item["unique_key"] in seen:
            duplicates += 1
            continue
        seen.add(item["unique_key"])
        unique.append(item)
    return {"scanned": scanned, "skipped": skipped, "duplicates": duplicates, "candidates": unique[:limit]}


def existing_review(unique_key: str) -> dict[str, Any] | None:
    _status, rows = sb.get("task_requests", f"select=id,status,payload&task_type=eq.{TASK_TYPE}&payload->>unique_key=eq.{sb.q(unique_key)}&limit=1")
    return rows[0] if isinstance(rows, list) and rows else None


def write_live(items: list[dict[str, Any]], limit: int) -> dict[str, Any]:
    counts = {"created": 0, "duplicates": 0, "failed": 0}
    results = []
    if not sb.configured():
        return {"ok": False, "error": "supabase_not_configured", **counts, "results": results}
    for item in items[: max(1, min(limit, 10))]:
        if existing_review(item["unique_key"]):
            counts["duplicates"] += 1
            results.append({"title": item["title"], "status": "duplicate"})
            continue
        task = {
            "task_type": TASK_TYPE,
            "requested_by": "build_ray_review_queue",
            "sensitivity": "internal_summary",
            "allowed_data_scope": ["internal_summary"],
            "forbidden_data": ["secrets", "cookies", "tokens", "raw_private_customer_data", "broker_credentials"],
            "assigned_worker_type": "ray_review_worker",
            "hermes_visibility": "summary",
            "status": "pending_review",
            "payload": item,
            "result_summary": item["hermes_recommendation"][:500],
        }
        _status, rows = sb.insert("task_requests", task)
        task_id = rows[0]["id"] if isinstance(rows, list) and rows else None
        if not task_id:
            counts["failed"] += 1
            results.append({"title": item["title"], "status": "failed"})
            continue
        _status, events = sb.insert("nexus_events", {
            "lane": "command",
            "source": "build_ray_review_queue",
            "action": "ray_review_item_created",
            "status": "pending",
            "title": item["title"][:80],
            "summary": item["hermes_recommendation"][:300],
            "payload": {"task_request_id": task_id, "unique_key": item["unique_key"], "decision_type": item["decision_type"], "no_external_ai": True},
        })
        counts["created"] += 1
        results.append({"title": item["title"], "status": "created", "task_request_id": task_id, "proof_event_id": events[0]["id"] if isinstance(events, list) and events else None})
    return {"ok": True, **counts, "results": results}


def write_report(report: dict[str, Any], path: str = "") -> None:
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [
        "# Nexus Ray Review Queue",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- dry_run: {report['dry_run']}",
        f"- ok: {report['ok']}",
        "- publish_send_trade_deploy: false",
        "- scheduler_started: false",
        "- external_ai_called: false",
        "",
        "## Counts",
    ]
    for key, value in report.get("counts", {}).items():
        lines.append(f"- {key}: {value}")
    lines += ["", "## Top Recommendations"]
    for item in report.get("candidates", [])[:10]:
        lines.append(f"- {item['priority']} / {item['decision_type']}: {item['title']} — {item['hermes_recommendation']}")
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    if path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2) if p.suffix == ".json" else "\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Ray Review Queue candidates.")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--department", default=None)
    parser.add_argument("--decision-type", default=None)
    parser.add_argument("--no-external-ai", action="store_true", default=True)
    parser.add_argument("--report-path", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    limit = max(1, min(args.limit, 50))
    built = build_candidates(limit, args.department, args.decision_type)
    live = {"created": 0, "duplicates": built["duplicates"], "failed": 0, "results": []}
    if args.no_dry_run:
        live = write_live(built["candidates"], min(limit, 10))
    counts = {
        "candidates_scanned": built["scanned"],
        "qualifies": len(built["candidates"]),
        "skipped_autonomous_or_other": sum(built["skipped"].values()),
        "duplicates": live.get("duplicates", 0),
        "created": live.get("created", 0),
        "failed": live.get("failed", 0),
    }
    report = {
        "title": "Nexus Ray Review Queue",
        "generated_at": now(),
        "ok": live.get("ok", True),
        "dry_run": not args.no_dry_run,
        "counts": counts,
        "skipped": built["skipped"],
        "candidates": built["candidates"],
        "write_results": live.get("results", []),
        "safety": {"publish_send_trade_deploy": False, "scheduler_started": False, "external_ai_called": False},
    }
    write_report(report, args.report_path)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Ray Review Queue report written: {RUNTIME.relative_to(ROOT)}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
