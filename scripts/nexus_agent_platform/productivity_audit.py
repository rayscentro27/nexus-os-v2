"""Productivity audit attached to the canonical continuous kernel."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "data/runtime/productivity_audit_state.json"
AUDIT_DIR = ROOT / "reports/runtime/productivity_audits"
SESSION_REPORT = ROOT / "reports/research/NEXUS_CONTINUOUS_INTELLIGENCE_SESSION_2026-09-18.md"
STALL_SECONDS = int(os.environ.get("NEXUS_PRODUCTIVITY_STALL_SECONDS", "7200"))


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _records_since(path: Path, previous: str | None) -> list[dict[str, Any]]:
    try:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, ValueError):
        return []
    if not previous:
        return rows[-100:]
    try:
        cutoff = datetime.fromisoformat(previous.replace("Z", "+00:00"))
    except ValueError:
        return rows[-100:]
    result = []
    for row in rows:
        try:
            when = datetime.fromisoformat(str(row.get("at", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if when > cutoff:
            result.append(row)
    return result[-100:]


def _telegram(text: str) -> dict[str, Any]:
    try:
        try:
            from scripts.telegram.nexus_telegram_bridge import ALLOWED_CHAT_IDS, get_bot_token, telegram_send_message
        except ModuleNotFoundError:
            from telegram.nexus_telegram_bridge import ALLOWED_CHAT_IDS, get_bot_token, telegram_send_message
        token = get_bot_token()
        if not token or not ALLOWED_CHAT_IDS:
            return {"status": "UNAVAILABLE", "reason": "telegram_transport_unavailable"}
        receipts = []
        for chat_id in sorted(ALLOWED_CHAT_IDS):
            response = telegram_send_message(token, chat_id, text)
            receipts.append({"chat_id_masked": f"{str(chat_id)[:2]}***", "ok": bool(response and response.get("ok"))})
        return {"status": "DELIVERED" if receipts and all(row["ok"] for row in receipts) else "FAILED", "receipts": receipts}
    except Exception as exc:
        return {"status": "FAILED", "reason": type(exc).__name__}


def _summary_message(audit: dict[str, Any]) -> str:
    research = audit["research_summary"]; alpha = audit["alpha_summary"]; departments = audit["department_summary"]; yt = audit["youtube_summary"]
    status = audit["runtime_status"]
    return "\n".join([
        "NEXUS OPERATIONS AUDIT", "", f"Status: {status}",
        f"Since last audit: Research {research['productive_actions']} productive / {research['active_workers']} active",
        f"Alpha: {alpha['reviews_completed']} reviews / {alpha['followups_executed']} follow-ups",
        f"Departments: {departments['handoffs_created']} handoffs / {departments['completed']} completed",
        f"YouTube: {yt['channels_checked']}/4 checked, {yt['new_videos']} new videos",
        f"Current priority: {audit['next_work']['highest_priority']}",
        f"Blocked: {', '.join(audit['blockers']) or 'none'}",
        f"Next: {audit['next_work']['next_action']}",
        f"Audit: {audit['audit_id']}",
    ])


def run_productivity_audit(*, startup: bool = False, force: bool = False) -> dict[str, Any]:
    previous = _read(STATE_PATH, {})
    now = _now(); last_audit = previous.get("timestamp")
    if not force and last_audit:
        try:
            if (now - datetime.fromisoformat(last_audit.replace("Z", "+00:00"))).total_seconds() < 3600 and not startup:
                return {"status": "SKIPPED_INTERVAL", "audit_id": previous.get("audit_id")}
        except ValueError:
            pass
    queue = _read(ROOT / "data/runtime/research_work_queue.json", {"items": []})
    items = queue.get("items", []) if isinstance(queue, dict) else []
    active = [item for item in items if item.get("status") == "IN_PROGRESS"]
    completed = [item for item in items if item.get("status") == "COMPLETE"]
    heartbeat = _read(ROOT / "data/runtime/research_heartbeat.json", {})
    programs = _read(ROOT / "data/runtime/research_program_registry.json", [])
    sources = _read(ROOT / "data/runtime/alpha_source_registry.json", [])
    youtube = [row for row in sources if row.get("source_type") == "YOUTUBE_CHANNEL"]
    events = _records_since(ROOT / "data/runtime/research_execution_jobs.jsonl", last_audit)
    # EVIDENCE_READY means a source was actually acquired/processed. A
    # dispatch/heartbeat alone is intentionally excluded; duplicate evidence
    # is still a productive source check but is not counted as a new finding.
    productive = sum(1 for event in events if event.get("status") in {"EVIDENCE_READY", "COMPLETED", "SUCCEEDED"})
    previous_productive = previous.get("last_productive_at")
    last_productive = heartbeat.get("last_real_output") or previous_productive
    stalled = False
    if last_productive:
        try: stalled = (now - datetime.fromisoformat(str(last_productive).replace("Z", "+00:00"))).total_seconds() > STALL_SECONDS and not active
        except ValueError: pass
    audit = {
        "audit_id": f"productivity_audit_{uuid.uuid4().hex[:16]}", "timestamp": now.isoformat(), "previous_audit_id": previous.get("audit_id"),
        "runtime_status": "STALLED_RECOVERING" if stalled else "HEALTHY" if heartbeat.get("heartbeat") == "ACTIVE" else "DEGRADED",
        "productive_actions": productive, "research_summary": {"queue_depth": sum(1 for item in items if item.get("status") in {"QUEUED", "WAITING", "IN_PROGRESS"}), "active_workers": len(active), "completed_since_previous": productive, "failed_since_previous": sum(1 for event in events if "FAILED" in str(event.get("status"))), "new_needs": 0, "sources_checked": len([p for p in programs if p.get("last_run")]), "evidence_packages": 0, "stale_refreshed": 0, "productive_actions": productive},
        "youtube_summary": {"scheduler_ran": any("YOUTUBE" in str(event).upper() or event.get("lane_id") == "YOUTUBE_CONTENT" for event in events), "channels_checked": sum(1 for row in youtube if row.get("last_checked")), "new_videos": 0, "processed_videos": 0, "skipped_complete": 0, "transcripts_captured": 0, "transcript_failures": 0, "blocked_external": [row.get("name") for row in youtube if row.get("health") == "BLOCKED_EXTERNAL"], "next_check": min((row.get("next_check") for row in youtube if row.get("next_check")), default=None)},
        "alpha_summary": {"reviews_completed": 0, "qualify": 0, "research_more": 0, "reject": 0, "followups_executed": 0},
        "department_summary": {"handoffs_created": 0, "accepted": 0, "completed": 0, "failed": 0, "artifacts": 0},
        "monetization_summary": {"opportunities": 0, "qualified": 0, "needs_more_research": 0},
        "resource_summary": {"governor_mode": "SHADOW", "provider_blockers": ["KAGGLE_AUTH_UNAVAILABLE"], "resource_issues": []},
        "blockers": ["KAGGLE_AUTH_UNAVAILABLE"] if not stalled else ["PRODUCTIVITY_STALL"], "recovery_actions": [], "stalled": stalled,
        "next_work": {"highest_priority": heartbeat.get("selected_lane_name") or "assigned Research work / bounded discovery", "next_action": heartbeat.get("next_action") or "continue canonical continuous cycle"}, "telegram_delivery_status": "PENDING",
    }
    if startup and not previous.get("startup_canary_sent"):
        audit["startup_canary"] = _telegram("Nexus intelligence engine started. Continuous Research/Alpha operations are active. I will send evidence-based productivity audits and alert you only if human action is required.")
        audit["startup_canary_sent"] = audit["startup_canary"].get("status") == "DELIVERED"
    audit["telegram_delivery"] = _telegram(_summary_message(audit)) if force or (not startup and last_audit) else {"status": "STARTUP_CANARY_ONLY"}
    audit["telegram_delivery_status"] = audit["telegram_delivery"].get("status")
    _write(AUDIT_DIR / f"{audit['audit_id']}.json", audit)
    _write(STATE_PATH, {"audit_id": audit["audit_id"], "timestamp": audit["timestamp"], "last_productive_at": last_productive or (now.isoformat() if productive else None), "startup_canary_sent": previous.get("startup_canary_sent", False) or audit.get("startup_canary_sent", False)})
    SESSION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with SESSION_REPORT.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## Productivity audit {audit['timestamp']}\n\n- Status: `{audit['runtime_status']}`\n- Productive actions since prior audit: `{productive}`\n- Research queue depth: `{audit['research_summary']['queue_depth']}`\n- YouTube channels with recorded checks: `{audit['youtube_summary']['channels_checked']}/4`\n- Telegram delivery: `{audit['telegram_delivery_status']}`\n- Next: {audit['next_work']['next_action']}\n")
    return audit
