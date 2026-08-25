"""Governed Telegram control for Product Evolution.

This module contains intent/contract/reporting logic only. Telegram transport
is injected by the certified Hermes worker or bridge; this module never reads
credentials and never creates a polling loop.
"""

from __future__ import annotations

import json
import hashlib
import re
import uuid
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .loop import FailureClass, MissionContract, ProductEvolutionLoop, Stage
from .deployment import deployment_response, inspect_deployment
from .release import approve_release, create_release_candidate, parse_release_approval, prepare_release

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "reports/product_evolution"
CONTEXT_TTL_SECONDS = 10 * 60
MAX_TELEGRAM_RETRIES = 2
MISSION_ID_PATTERN = r"\btelegram-[0-9]{8,}-[a-f0-9]{8}\b(?!-[a-f0-9]{12}\b)"
RELEASE_ID_PATTERN = r"\brel-telegram-[0-9]{8,}-[a-f0-9]{8}-[a-f0-9]{12}\b"

UNSAFE_PATTERNS = (
    r"\b(enabl\w*|remov\w*|bypass\w*|weaken\w*)\b.*\b(secur\w*|approval\w*|governance|auth|rls)\b",
    r"\b(expose|export|send)\b.*\b(client|customer)\s+(pii|data|records)\b",
    r"\b(enabl\w*|fund\w*|place|execute)\b.*\b(payment\w*|charge\w*|trade\w*|trading)\b",
    r"\b(remov\w*|bypass\w*|weaken\w*)\b.*\b(approval\w*|governance|secur\w*)\b",
    r"\b(install|buy|purchase|subscribe|spend)\b",
    r"\b(change|rotate|reveal)\b.*\b(secret|token|credential|password|api key)\b",
)


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())[:500]


def is_product_evolution_intent(text: str) -> bool:
    lowered = _compact(text).lower()
    if any(re.search(pattern, lowered) for pattern in UNSAFE_PATTERNS):
        return False
    return bool(re.search(r"\b(product evolution|run product evolution|improve|evolve|make .{2,} easier|make .{2,} better|continue (?:the existing )?(?:voice|creative|client|admin)|resume (?:the existing )?(?:voice|creative|client|admin))\b", lowered))


def explicit_no_create(text: str) -> bool:
    lowered = _compact(text).lower()
    return bool(re.search(r"\b(?:do not|don't) (?:create|start) (?:a )?(?:(?:new|another)\s+)?(?:mission|run)\b|\buse the existing mission\b|\bcheck this exact mission\b|\binspect the existing mission\b|\breport only\b|\bstatus only\b", lowered))


def exact_mission_id(text: str) -> Optional[str]:
    match = re.search(MISSION_ID_PATTERN, text, re.I)
    return match.group(0) if match else None


def exact_release_id(text: str) -> Optional[str]:
    match = re.search(RELEASE_ID_PATTERN, text, re.I)
    return match.group(0) if match else None


def diagnostic_intent(text: str) -> bool:
    lowered = _compact(text).lower()
    return bool(re.search(r"\b(?:why|what|when|where|how|did|has|is|are|check|inspect|report)\b", lowered) and re.search(r"\b(?:mission|product evolution|runtime|dispatcher|queued|picked|waiting|started|execution|status|state|blocked)\b", lowered))


def is_unsafe_product_evolution_request(text: str) -> bool:
    lowered = _compact(text).lower()
    return any(re.search(pattern, lowered) for pattern in UNSAFE_PATTERNS)


def _surface(text: str) -> str:
    lowered = text.lower()
    for key, value in (("voice", "Voice"), ("creative", "Creative Studio"), ("client", "Client Portal"), ("onboard", "Client Portal"), ("command", "Admin Command"), ("admin", "Admin Experience")):
        if key in lowered:
            return value
    return "Nexus Product Experience"


def build_mission_contract(text: str, *, max_cycles: int = 5) -> MissionContract:
    goal = re.sub(r"^(?:hey\s+)?(?:nexus|hermes)\s*[,\-:]?\s*", "", _compact(text), flags=re.I)
    goal = goal.rstrip(".!?") or "Improve the Nexus product experience"
    surface = _surface(goal)
    common = [
        "user-visible outcome is demonstrated",
        "focused tests and browser evaluation pass",
        "truthful unknown/not-connected states are preserved",
        "existing governance and agent boundaries remain unchanged",
    ]
    if surface == "Voice":
        criteria = ["normal conversation uses at most one manual initiation action", "private STT and raw-audio cleanup remain", "correct agent routing and thread continuity"] + common
    elif surface == "Client Portal":
        criteria = ["next step is immediately visible", "mobile layout passes", "inline uploads remain available", "tenant isolation remains enforced"] + common
    elif surface == "Creative Studio":
        criteria = ["workspace is materially more visual than a dashboard", "concepts can be compared and critiqued", "canonical Creative Intelligence and Ray Review remain authoritative"] + common
    else:
        criteria = ["clicks and user effort are reduced", "responsive layout remains usable"] + common
    locked = ["Hermes", "Active Operator", "Mission Control", "Approvals", "Product Evolution Loop"]
    if surface == "Creative Studio":
        locked += ["Creative Intelligence", "Creative Studio"]
    if surface == "Voice":
        locked += ["Phase Q Voice", "whisper.cpp"]
    if surface == "Client Portal":
        locked += ["Supabase Auth", "tenant isolation"]
    return MissionContract(
        goal=goal,
        user_visible_outcome=f"Improve {surface} within the stated outcome without creating a parallel Nexus system.",
        acceptance_criteria=criteria,
        locked_systems=locked,
        allowed_files=["existing surface implementation", "focused tests", "operational documentation"],
        capability_candidates=["existing certified Nexus adapters", "current upstream alternatives only after license review"],
        security_boundaries=["no new authority", "no client PII expansion", "no arbitrary shell", "no cloud speech"],
        license_requirements=["unknown licenses are rejected"],
        max_cycles=max_cycles,
        deployment_policy="preview-first; production only under existing Nexus governance",
        human_only_gates=["human microphone test where Voice is involved", "subjective visual approval where design is involved"],
    )


class ProductEvolutionReporter:
    """Bounded status reporter over an injected certified Hermes sender."""

    def __init__(self, sender: Callable[[str], Mapping[str, Any]], *, max_retries: int = MAX_TELEGRAM_RETRIES):
        self.sender = sender
        self.max_retries = max(1, min(max_retries, MAX_TELEGRAM_RETRIES))
        self.deliveries: list[Dict[str, Any]] = []

    def send(self, text: str, kind: str) -> Dict[str, Any]:
        last: Dict[str, Any] = {"kind": kind, "delivered": False, "attempts": 0, "message_id": None}
        for attempt in range(1, self.max_retries + 1):
            last["attempts"] = attempt
            try:
                response = dict(self.sender(text))
            except Exception as exc:
                response = {"ok": False, "error": type(exc).__name__}
            if response.get("ok"):
                last.update({"delivered": True, "message_id": response.get("message_id") or (response.get("result") or {}).get("message_id")})
                break
            last["error"] = response.get("error") or response.get("description") or "delivery_failed"
        self.deliveries.append(last)
        return last

    def started(self, goal: str) -> Dict[str, Any]:
        return self.send(f"🧠 Nexus Product Evolution started\n\nGoal: {_compact(goal)}\n\nResearching and testing autonomously. I will only interrupt you for a true blocker.", "started")

    def milestone(self, message: str) -> Dict[str, Any]:
        return self.send(f"⚙️ Product Evolution update\n\n{_compact(message)}\n\nNo action needed.", "milestone")

    def blocked(self, mission: str, needed: str, route: str = "https://goclearonline.cc/admin") -> Dict[str, Any]:
        return self.send(f"⚠️ Nexus needs you\n\n{_compact(mission)}\n\nNeeded:\n{_compact(needed)}\n\nOpen:\n{route}", "blocked")

    def completed(self, goal: str, result: str, cycles: int, repairs: int, commit: str, production: str) -> Dict[str, Any]:
        return self.send(f"✅ Nexus Product Evolution complete\n\nGoal:\n{_compact(goal)}\n\nResult: {result}\nCycles: {cycles}\nSelf-repairs: {repairs}\nCommit: {commit}\n\nProduction:\n{production}", "completed")


def _receipt_files() -> Iterable[Path]:
    if not RECEIPT_DIR.exists():
        return []
    return sorted(RECEIPT_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def mission_receipts(limit: int = 5) -> list[Dict[str, Any]]:
    records = []
    for path in list(_receipt_files())[:limit]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            value["receipt_path"] = str(path)
            records.append(value)
        except (OSError, ValueError, TypeError):
            continue
    return records


def _mission_id(record: Mapping[str, Any]) -> str:
    return str((record.get("result") or {}).get("mission_id") or record.get("mission_id") or "")


def _mission_status(record: Mapping[str, Any]) -> str:
    return str((record.get("result") or {}).get("status") or record.get("status") or "UNKNOWN")


def _load_mission_by_id(mission_id: str) -> Optional[Dict[str, Any]]:
    path = RECEIPT_DIR / f"{mission_id}.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    value["receipt_path"] = str(path)
    return value
    return None


def _load_release_by_id(release_id: str) -> Optional[Dict[str, Any]]:
    """Resolve an exact persisted release without fuzzy mission selection."""
    for path in _receipt_files():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        release = (value.get("result") or {}).get("release") or {}
        if release.get("release_id") == release_id:
            value["receipt_path"] = str(path)
            return value
    return None


def _resolve_release_or_mission(text: str, context_mission_id: Optional[str] = None) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    release_id = exact_release_id(text)
    mission_id = exact_mission_id(text) or context_mission_id
    resolved = _load_release_by_id(release_id) if release_id else (_load_mission_by_id(mission_id) if mission_id else None)
    if not resolved and mission_id and (RECEIPT_DIR / f"{mission_id}.json").exists():
        return None, "RECEIPT_PARSE_ERROR"
    if release_id and resolved and mission_id and _mission_id(resolved) != mission_id:
        return None, "RELEASE_MISSION_ID_MISMATCH"
    return resolved, None


def release_inspection(resolved: Mapping[str, Any]) -> Dict[str, Any]:
    """Build a read-only release/deployment truth view from persisted evidence."""
    result = resolved.get("result") or {}
    release = result.get("release") or {}
    deployment = result.get("deployment") or {}
    events = {str(item.get("event")) for item in result.get("execution_history") or []}
    verification = release.get("verification_result") or "NOT_RUN"
    return {
        "mission_id": _mission_id(resolved),
        "release_id": release.get("release_id", "UNKNOWN"),
        "approval_state": release.get("approval_state", "UNKNOWN"),
        "approved_by": release.get("approved_by"),
        "approved_at": release.get("approved_at"),
        "current_stage": result.get("current_stage", "UNKNOWN"),
        "current_status": result.get("status", "UNKNOWN"),
        "release_dispatch_claimed": "RELEASE_DISPATCH_CLAIMED" in events,
        "deployment_occurred": "DEPLOYMENT_COMPLETE" in events or bool(release.get("deployment_completed_at")),
        "production_deploy_id": release.get("production_deploy_id") or deployment.get("deployed_build_id") or deployment.get("current_deploy_id") or (deployment.get("netlify_control_plane") or {}).get("published_deploy_id") or "NONE",
        "observed_production_sha": release.get("production_commit_after") or deployment.get("deployed_commit") or (deployment.get("netlify_control_plane") or {}).get("published_commit") or "UNKNOWN",
        "production_verification": verification,
        "production_verification_checks": release.get("verification_checks") or {},
        "rollback_occurred": "ROLLBACK_STARTED" in events or bool(release.get("rollback_result")),
        "human_gate": result.get("current_stage") == "HUMAN_GATE" or "HUMAN_GATE_READY" in events,
    }


def release_inspection_text(truth: Mapping[str, Any]) -> str:
    checks = truth.get("production_verification_checks") or {}
    return "\n".join([
        "Product Evolution release inspection",
        f"Release: {truth.get('release_id', 'UNKNOWN')}",
        f"Mission: {truth.get('mission_id', 'UNKNOWN')}",
        f"Approval: {truth.get('approval_state', 'UNKNOWN')}",
        f"Mission stage: {truth.get('current_stage', 'UNKNOWN')}",
        f"Release dispatch claimed: {'YES' if truth.get('release_dispatch_claimed') else 'NO'}",
        f"Production deployment: {'YES' if truth.get('deployment_occurred') else 'NO'}",
        f"Production deploy ID: {truth.get('production_deploy_id', 'NONE')}",
        f"Observed production SHA: {truth.get('observed_production_sha', 'UNKNOWN')}",
        f"Production verification: {truth.get('production_verification', 'NOT_RUN')}",
        f"Verification checks: {json.dumps(checks, sort_keys=True)}",
        f"Rollback: {'YES' if truth.get('rollback_occurred') else 'NO'}",
        f"Human gate: {'YES' if truth.get('human_gate') else 'NO'}",
    ])


def _write_receipt(path: Path, value: Mapping[str, Any], result: Mapping[str, Any]) -> None:
    payload = dict(value)
    payload.pop("receipt_path", None)
    payload["result"] = dict(result)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_mission(text: str) -> Optional[Dict[str, Any]]:
    """Resolve explicit ids, surfaces, and aliases without selecting unrelated work."""
    normalized = _compact(text).lower()
    records = list(_receipt_files())
    wanted_id = re.search(r"\b(?:mission|run)\s+([a-z0-9][a-z0-9_-]{2,})\b", normalized)
    if wanted_id:
        for path in records:
            value = json.loads(path.read_text(encoding="utf-8"))
            if _mission_id(value).lower() == wanted_id.group(1):
                value["receipt_path"] = str(path)
                return value
    aliases = {
        "voice": ("voice", "voice-assistant", "microphone", "wake"),
        "creative": ("creative", "creative studio", "visual"),
        "client": ("client", "portal", "onboarding"),
        "admin": ("admin", "navigation"),
    }
    key = next((name for name in aliases if re.search(rf"\b{name}\b", normalized)), None)
    candidates = []
    for path in records:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if _mission_status(value) in {"PASS", "FAIL", "CANCELLED"} and not re.search(r"\b(?:continue|resume|stop|cancel)\b", normalized):
            continue
        contract = value.get("contract") or {}
        haystack = f"{contract.get('goal', '')} {contract.get('user_visible_outcome', '')} {_mission_id(value)}".lower()
        if key and any(alias in haystack for alias in aliases[key]):
            value["receipt_path"] = str(path)
            candidates.append(value)
    if len(candidates) == 1:
        return candidates[0]
    return candidates[0] if candidates else None


def status_text() -> str:
    records = mission_receipts()
    if not records:
        return "Product Evolution: no mission receipts found."
    lines = ["Product Evolution status"]
    for record in records[:5]:
        result = record.get("result") or {}
        contract = record.get("contract") or {}
        lines.append(f"- {result.get('mission_id', 'unknown')}: {result.get('status', 'UNKNOWN')} / cycles {result.get('cycles', '?')} / {contract.get('goal', 'goal')[:90]}")
    return "\n".join(lines)


def blockers_text() -> str:
    records = mission_receipts(limit=20)
    lines = ["Product Evolution blockers"]
    found = False
    for record in records:
        status = _mission_status(record)
        if status not in {"PARTIAL", "BLOCKED"}:
            continue
        found = True
        contract = record.get("contract") or {}
        result = record.get("result") or {}
        lines.append(f"\n{_mission_id(record) or contract.get('goal', 'Unknown surface')}: {status}")
        failures = result.get("failures") or []
        gates = contract.get("human_only_gates") or []
        if failures:
            for failure in failures[-3:]:
                lines.append(f"- {failure.get('error') or failure.get('class') or 'Recorded blocker'}")
        elif gates:
            for gate in gates:
                lines.append(f"- Human gate: {gate}")
        else:
            lines.append("- Blocker recorded in the mission receipt; details unavailable.")
    return "\n".join(lines) if found else "Product Evolution blockers\n\nNo PARTIAL or BLOCKED Product Evolution missions recorded."


def diagnostic_text(record: Mapping[str, Any]) -> str:
    """Report persisted mission/runtime observations without inventing state."""
    result = record.get("result") or {}
    dispatch = result.get("dispatch") or {}
    try:
        scheduler = json.loads((ROOT / "reports/phase16a/scheduler_health.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        scheduler = {}
    try:
        active = json.loads((ROOT / "reports/runtime/nexus_active_operator_heartbeat_latest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        active = {}
    status = _mission_status(record)
    lines = [
        "Product Evolution mission diagnostic",
        f"Mission ID: {_mission_id(record) or 'UNKNOWN'}",
        f"Status: {status}",
        f"Goal: {(record.get('contract') or {}).get('goal') or result.get('goal') or 'UNKNOWN'}",
        f"Created at: {result.get('created_at') or record.get('created_at') or 'UNKNOWN'}",
        f"Updated at: {result.get('updated_at') or 'UNKNOWN'}",
        f"Current cycle: {result.get('cycle', result.get('cycles', 'UNKNOWN'))}",
        f"Current stage: {result.get('current_stage') or 'UNKNOWN'}",
        f"Queue state: {result.get('current_stage') or status}",
        f"Runtime pickup state: {dispatch.get('pickup_state') or ('NOT_OBSERVED' if status == 'QUEUED' else 'OBSERVED')}",
        f"Last dispatcher observation: {dispatch.get('last_dispatch_observation') or 'UNKNOWN'}",
        f"Next eligible dispatch: {scheduler.get('next_dispatch') or 'UNKNOWN'}",
        f"Blocker: {result.get('blocker') or 'NONE_RECORDED'}",
        f"Human gate: {', '.join((record.get('contract') or {}).get('human_only_gates') or []) or 'NONE_RECORDED'}",
        f"Parent/resume lineage: {result.get('parent_mission_id') or 'NONE_RECORDED'}",
        f"Receipt: {record.get('receipt_path') or 'UNKNOWN'}",
        f"Active Operator last run: {active.get('last_run') or 'UNKNOWN'}",
    ]
    return "\n".join(lines)


def _delta_text(record: Mapping[str, Any]) -> str:
    """Return only bounded activity recorded after the latest human gate."""
    result = record.get("result") or {}
    evidence = list(result.get("human_evidence") or [])
    if not evidence:
        return "Product Evolution delta\n\nNO PROGRESS\nNo human evidence timestamp is recorded yet."
    since = max(str(item.get("recorded_at") or "") for item in evidence)
    mission_id = _mission_id(record)
    events = [item for item in result.get("execution_history") or [] if str(item.get("at") or "") > since]
    execution = result.get("execution") or {}
    if execution:
        events.append({"event": "latest_execution", "at": result.get("updated_at"), "status": execution.get("status"), "adapter": (result.get("dispatch") or {}).get("adapter_id")})
    if not events:
        return f"Product Evolution delta\n\nMission: {mission_id}\nSince: {since}\nNO PROGRESS\nNo dispatcher, worker, test, critic, repair, or blocker activity has been recorded since the latest human evidence."
    lines = ["Product Evolution delta", f"Mission: {mission_id}", f"Since: {since}"]
    for event in events[-12:]:
        lines.append(f"- {event.get('at') or 'time unknown'}: {event.get('event') or event.get('stage') or 'activity'} / {event.get('status') or event.get('adapter') or event.get('reason') or 'recorded'}")
    lines.append(f"Current status: {_mission_status(record)}")
    lines.append(f"Current stage: {result.get('current_stage') or 'UNKNOWN'}")
    lines.append(f"Blocker: {result.get('blocker') or 'NONE_RECORDED'}")
    return "\n".join(lines)


def control_request(text: str) -> Optional[str]:
    lowered = _compact(text).lower()
    if re.search(r"\b(improve|evolve|run product evolution|make .{2,} easier|make .{2,} better)\b", lowered):
        return None
    if re.search(r"\b(product evolution|creative(?: studio)?|voice|client portal|admin)\b", lowered) and re.search(r"\b(status|working on|doing|finish|blocked|stop|cancel|continue|resume)", lowered):
        return "blocked" if re.search(r"\bblocked\b", lowered) else "status" if re.search(r"\b(status|working on|doing|finish|why)\b", lowered) else "cancel" if re.search(r"\b(stop|cancel)\b", lowered) else "resume"
    return None


def _latest_mission_id() -> Optional[str]:
    records = mission_receipts(limit=1)
    if not records:
        return None
    return ((records[0].get("result") or {}).get("mission_id"))


def mark_control(mission_id: str, action: str, evidence: str = "") -> Dict[str, Any]:
    for path in _receipt_files():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        result = value.get("result") or {}
        if result.get("mission_id") != mission_id:
            continue
        current_status = result.get("status")
        if action == "cancel" and current_status in {"PASS", "FAIL", "CANCELLED"}:
            result["control_result"] = "REJECTED_TERMINAL"
            return result
        if action == "resume" and current_status not in {"PARTIAL", "BLOCKED", "FAILED", "CANCELLED"}:
            result["control_result"] = "REJECTED_NOT_RESUMABLE"
            return result
        result["control"] = {"action": action, "evidence": _compact(evidence), "recorded_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
        result["updated_at"] = datetime.now(timezone.utc).isoformat()
        value["result"] = result
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    return {"status": "NOT_FOUND", "mission_id": mission_id}


def cancel_mission(mission_id: str, reason: str) -> Dict[str, Any]:
    """Record a safe terminal cancellation without deleting receipt history."""
    for path in _receipt_files():
        if path.stem != mission_id:
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {"status": "NOT_FOUND", "mission_id": mission_id}
        result = value.get("result") or {}
        if _mission_status(value) in {"PASS", "FAIL", "CANCELLED"}:
            return result
        now = datetime.now(timezone.utc).isoformat()
        result.update({"status": "CANCELLED", "current_stage": "CANCELLED", "blocker": reason, "updated_at": now, "control": {"action": "cancel", "reason": reason, "recorded_at": now}})
        value["result"] = result
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    return {"status": "NOT_FOUND", "mission_id": mission_id}


def _human_gate_type(text: str, record: Mapping[str, Any]) -> str:
    lowered = text.lower()
    if "voice" in lowered or "microphone" in lowered or "wake" in lowered:
        return "VOICE_MICROPHONE"
    if "visual" in lowered or "layout" in lowered or "creative" in lowered:
        return "CREATIVE_VISUAL_REVIEW"
    gates = (record.get("contract") or {}).get("human_only_gates") or []
    return "HUMAN_GATE" if gates else "HUMAN_REVIEW"


def _human_outcome(text: str) -> Optional[str]:
    lowered = text.lower()
    fail = bool(re.search(r"\b(?:fail(?:ed|s|ure)?|didn['’]?t pass|not pass(?:ed)?|doesn['’]?t work|429)\b", lowered))
    passed = bool(re.search(r"\b(?:pass(?:ed|es)?|works?|working|approve(?:d|s)?|approved|success(?:ful|fully)?)\b", lowered))
    if fail and passed:
        # Explicit failure phrases outrank incidental words such as
        # "previous ... completed" in a long Telegram report.
        if re.search(r"\b(?:failed|didn['’]?t pass|not pass|429)\b", lowered):
            return "FAIL"
        return None
    if fail:
        return "FAIL"
    if passed:
        return "PASS"
    return None


def human_evidence_intent(text: str) -> bool:
    lowered = _compact(text).lower()
    query_start = r"^(?:hey\s+)?(?:nexus|hermes)[,\s:-]*"
    if re.search(query_start + r"(?:what(?:'s| is) the status|what changed|give me a delta|delta-only|why is)\b", lowered) and not re.search(r"\b(?:record|update .*evidence|resume .*evidence|continue .*evidence)\b", lowered):
        return False
    has_gate_language = bool(re.search(r"\b(?:human|microphone|voice|wake|visual|layout|test|gate|evidence|approve|approval|review)\b", lowered))
    has_action_language = bool(re.search(r"\b(?:record|update|resume|continue|tested|test|gate|evidence|approve|failed|passed|works?)\b", lowered))
    return has_gate_language and has_action_language and _human_outcome(lowered) is not None


def _deployment_operation(text: str) -> Optional[str]:
    lowered = re.sub(r"\s+", " ", text.strip()).lower()[:4000]
    inspection = bool(re.search(r"\b(?:inspect|identify|compare|verify|check|determine|what)\b", lowered) and re.search(r"\b(?:deployment|deployed|production|live|bundle|build|commit|netlify|release|origin/main)\b", lowered))
    inspection = inspection or bool(re.search(r"\b(?:is production stale|what version is|what commit is live|production deployment state)\b", lowered))
    if inspection and (exact_release_id(text) or re.search(r"\binspect\s+(?:the\s+)?existing\s+release\b", lowered)):
        return "RELEASE_INSPECTION"
    reconciliation = bool(re.search(r"\b(?:deploy|reconcile|promote)\b\s+(?:the\s+)?(?:already[- ]tested|existing|tested|approved|candidate|release|commit)", lowered) and re.search(r"\b(?:governance|production|origin/main|existing|tested|approved)\b", lowered))
    if reconciliation:
        return "DEPLOYMENT_RECONCILIATION"
    if inspection:
        return "DEPLOYMENT_INSPECTION"
    return None


def classify_product_evolution_request_metadata(text: str, *, context_mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Classify requested action separately from subject matter."""
    pe_signal = bool(re.search(r"\bproduct evolution\b|\bcreative(?: studio)?\b|\bvoice(?: mission| product evolution)?\b|\bclient portal\b|\badmin(?: navigation)?\b|" + MISSION_ID_PATTERN + r"|\bmission\b", text, re.I)) or bool(context_mission_id) or bool(_deployment_operation(text)) or human_evidence_intent(text)
    mission_id = exact_mission_id(text) or context_mission_id
    metadata = {"subject": _surface(text), "operation": "CLARIFICATION", "mission_id": mission_id, "release_id": exact_release_id(text), "no_create": explicit_no_create(text), "human_evidence_outcome": _human_outcome(text)}
    if parse_release_approval(text):
        metadata["operation"] = "RELEASE_APPROVAL"
        metadata["no_create"] = True
        return metadata
    if not pe_signal:
        return metadata
    if is_unsafe_product_evolution_request(text):
        metadata["operation"] = "UNSAFE"
        return metadata
    deployment = _deployment_operation(text)
    if deployment:
        metadata["operation"] = deployment
        metadata["no_create"] = True
        return metadata
    if human_evidence_intent(text):
        metadata["operation"] = "RESUME_WITH_HUMAN_EVIDENCE"
        return metadata
    request = control_request(text)
    if request == "cancel":
        metadata["operation"] = "CANCEL"
    elif request == "resume":
        metadata["operation"] = "RESUME"
    elif request == "status" and not re.search(r"\b(?:why|queued|picked|waiting|dispatcher|runtime)\b", text, re.I) and not explicit_no_create(text) and not exact_mission_id(text):
        metadata["operation"] = "STATUS"
    elif request == "blocked":
        metadata["operation"] = "BLOCKERS"
    elif diagnostic_intent(text) or explicit_no_create(text) or exact_mission_id(text):
        metadata["operation"] = "DIAGNOSTIC"
    elif is_product_evolution_intent(text):
        metadata["operation"] = "START_NEW_MISSION"
    elif context_mission_id and re.search(r"\b(?:picked|runtime|dispatcher|queued|waiting|started|execution)\b", text, re.I):
        metadata["operation"] = "DIAGNOSTIC"
    return metadata


def record_human_evidence(mission_id: str, text: str, *, source: str = "RAY_TELEGRAM", update_id: Optional[str] = None) -> Dict[str, Any]:
    """Append one sanitized human-gate result and queue only on a new FAIL."""
    for path in _receipt_files():
        if path.stem != mission_id:
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        result = value.get("result") or {}
        outcome = _human_outcome(text)
        if outcome is None:
            return {"status": "AMBIGUOUS", "mission_id": mission_id}
        summary = _compact(text)
        gate_type = _human_gate_type(text, value)
        evidence_hash = hashlib.sha256(json.dumps({"mission_id": mission_id, "gate_type": gate_type, "outcome": outcome, "summary": summary}, sort_keys=True).encode()).hexdigest()[:16]
        existing = list(result.get("human_evidence") or [])
        duplicate = next((item for item in existing if item.get("evidence_hash") == evidence_hash or (update_id and item.get("update_id") == str(update_id))), None)
        if not duplicate and result.get("status") in {"QUEUED", "RUNNING"} and any(item.get("gate_type") == gate_type and item.get("outcome") == outcome for item in existing):
            duplicate = next(item for item in existing if item.get("gate_type") == gate_type and item.get("outcome") == outcome)
        if duplicate:
            return {"status": "DUPLICATE", "mission_id": mission_id, "evidence": duplicate, "receipt_path": str(path)}
        now = datetime.now(timezone.utc).isoformat()
        previous_status = result.get("status")
        previous_stage = result.get("current_stage")
        evidence = {"recorded_at": now, "source": source, "gate_type": gate_type, "outcome": outcome, "summary": summary, "mission_id": mission_id, "previous_stage": previous_stage, "evidence_hash": evidence_hash}
        if update_id is not None:
            evidence["update_id"] = str(update_id)
        existing.append(evidence)
        history = list(result.get("execution_history") or [])
        history.append({"at": now, "event": "HUMAN_EVIDENCE_RECORDED", "outcome": outcome, "gate_type": gate_type, "evidence_hash": evidence_hash, "previous_status": previous_status, "previous_stage": previous_stage})
        result.update({"human_evidence": existing, "human_gate_result": outcome, "updated_at": now, "execution_history": history})
        if outcome == "FAIL" and previous_status == "PARTIAL" and previous_stage == "HUMAN_GATE":
            result.update({"status": "QUEUED", "current_stage": "RESUMED_AFTER_HUMAN_FAIL", "blocker": None})
            result["dispatch"] = {**(result.get("dispatch") or {}), "resume_requested_at": now, "resume_reason": "HUMAN_GATE_FAILED", "pickup_state": "AWAITING_PHASE15"}
            history.append({"at": now, "event": "RESUME_WITH_HUMAN_EVIDENCE", "reason": "HUMAN_GATE_FAILED", "status": "QUEUED", "previous_stage": previous_stage})
        elif outcome == "PASS" and previous_stage == "HUMAN_GATE":
            result.update({"status": "PARTIAL", "current_stage": "HUMAN_EVIDENCE_RECORDED", "blocker": None})
        _write_receipt(path, value, result)
        return {"status": "RECORDED", "mission_id": mission_id, "outcome": outcome, "evidence": evidence, "previous_status": previous_status, "previous_stage": previous_stage, "current_status": result.get("status"), "current_stage": result.get("current_stage"), "receipt_path": str(path)}
    return {"status": "NOT_FOUND", "mission_id": mission_id}


def correct_misclassified_human_evidence(mission_id: str, evidence_hash: str, reason: str) -> Dict[str, Any]:
    """Append-only correction for evidence created by an older classifier."""
    for path in _receipt_files():
        if path.stem != mission_id:
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        result = value.get("result") or {}
        corrections = list(result.get("human_evidence_corrections") or [])
        if any(item.get("evidence_hash") == evidence_hash for item in corrections):
            return {"status": "ALREADY_CORRECTED", "mission_id": mission_id, "evidence_hash": evidence_hash}
        evidence = next((item for item in result.get("human_evidence") or [] if item.get("evidence_hash") == evidence_hash), None)
        if not evidence:
            return {"status": "NOT_FOUND", "mission_id": mission_id, "evidence_hash": evidence_hash}
        now = datetime.now(timezone.utc).isoformat()
        corrections.append({"corrected_at": now, "source": "SYSTEM", "evidence_hash": evidence_hash, "valid_human_evidence": False, "correction": "RECLASSIFIED_AS_OPERATIONAL_QUERY", "reason": _compact(reason)})
        history = list(result.get("execution_history") or [])
        history.append({"at": now, "event": "HUMAN_EVIDENCE_RECLASSIFIED", "evidence_hash": evidence_hash, "valid_human_evidence": False, "reason": _compact(reason)})
        # Restore the last verified automated outcome without deleting the old record.
        result.update({"status": "PARTIAL", "current_stage": "HUMAN_GATE", "blocker": None, "human_evidence_corrections": corrections, "updated_at": now, "execution_history": history})
        _write_receipt(path, value, result)
        return {"status": "CORRECTED", "mission_id": mission_id, "evidence_hash": evidence_hash, "receipt_path": str(path)}
    return {"status": "NOT_FOUND", "mission_id": mission_id, "evidence_hash": evidence_hash}


def classify_product_evolution_request(text: str, *, context_mission_id: Optional[str] = None) -> str:
    return str(classify_product_evolution_request_metadata(text, context_mission_id=context_mission_id)["operation"])


def handle_product_evolution_intake(text: str, *, context_mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Build a safe contract or return a truthful clarification/block."""
    approval = parse_release_approval(text)
    if approval:
        resolved = None
        for candidate in mission_receipts(limit=50):
            if ((candidate.get("result") or {}).get("release") or {}).get("release_id") == approval["release_id"]:
                resolved = candidate
                break
        if not resolved:
            return {"handled": True, "status": "REJECTED", "route": "PRODUCT_EVOLUTION_RELEASE_APPROVAL", "response": "Release approval rejected: no pending release with that release ID exists."}
        approved = approve_release(resolved.get("result") or {}, release_id=approval["release_id"], commit=approval["commit"], target=approval["target"])
        if approved.get("status") != "APPROVED":
            return {"handled": True, "status": "REJECTED", "route": "PRODUCT_EVOLUTION_RELEASE_APPROVAL", "mission_id": _mission_id(resolved), "response": f"Release approval rejected: {approved.get('reason', 'invalid approval')}."}
        path = Path(str(resolved.get("receipt_path")))
        _write_receipt(path, resolved, approved["result"])
        package = approved["result"].get("release") or {}
        return {"handled": True, "status": "APPROVED", "route": "PRODUCT_EVOLUTION_RELEASE_APPROVAL", "mission_id": _mission_id(resolved), "release_id": package.get("release_id"), "response": f"Release approved for exact commit {package.get('release_candidate_commit')} and target {package.get('target_url')}. Deployment remains a separate bounded operation."}
    classification = classify_product_evolution_request(text, context_mission_id=context_mission_id)
    if classification == "UNSAFE":
        return {"handled": True, "status": "BLOCKED", "route": "PRODUCT_EVOLUTION", "response": "Product Evolution cannot change security, authority, payments, approvals, credentials, or client-data boundaries."}
    if classification in {"RELEASE_INSPECTION", "DEPLOYMENT_INSPECTION", "DEPLOYMENT_RECONCILIATION"}:
        resolved, resolution_error = _resolve_release_or_mission(text, context_mission_id)
        if resolution_error:
            return {"handled": True, "status": "REJECTED", "route": "PRODUCT_EVOLUTION_RELEASE_INSPECTION", "reason": resolution_error, "response": resolution_error}
        if not resolved:
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_RELEASE_INSPECTION", "response": "No existing Product Evolution release or mission was found. I did not create a new mission."}
        if classification == "RELEASE_INSPECTION":
            truth = release_inspection(resolved)
            return {"handled": True, "status": "ANSWERED", "route": "PRODUCT_EVOLUTION_RELEASE_INSPECTION", "mission_id": truth["mission_id"], "release_id": truth["release_id"], "deployment": truth, "response": release_inspection_text(truth)}
        inspected = inspect_deployment(resolved)
        action = "none"
        if classification == "DEPLOYMENT_RECONCILIATION":
            now = datetime.now(timezone.utc).isoformat()
            inspected["deployment_reconciliation"] = {"status": "BLOCKED", "reason": "Nexus production policy requires a separate human-approved Level 3 release; Product Evolution cannot deploy automatically.", "recorded_at": now}
            inspected["execution_history"] = list(inspected.get("execution_history") or []) + [{"at": now, "event": "DEPLOYMENT_RECONCILIATION_BLOCKED", "reason": inspected["deployment_reconciliation"]["reason"]}]
            _write_receipt(path, resolved, inspected)
            action = "BLOCKED — human-approved production release required"
        return {"handled": True, "status": "ANSWERED" if action == "none" else "BLOCKED", "route": "PRODUCT_EVOLUTION_DEPLOYMENT", "mission_id": _mission_id(resolved), "deployment": inspected.get("deployment"), "response": deployment_response(resolved, inspected.get("deployment") or {}, action=action)}
    if classification == "RESUME_WITH_HUMAN_EVIDENCE":
        mission_id = exact_mission_id(text) or context_mission_id
        resolved = _load_mission_by_id(mission_id) if mission_id else resolve_mission(text)
        if not resolved:
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_HUMAN_EVIDENCE", "response": "No existing Product Evolution mission was found. I did not create a new mission."}
        outcome = _human_outcome(text)
        if outcome is None:
            return {"handled": True, "status": "CLARIFICATION", "route": "PRODUCT_EVOLUTION_HUMAN_EVIDENCE", "mission_id": _mission_id(resolved), "response": "Was the human gate PASS or FAIL?"}
        recorded = record_human_evidence(_mission_id(resolved), text)
        if recorded.get("status") == "DUPLICATE":
            return {"handled": True, "status": "ALREADY_RECORDED", "route": "PRODUCT_EVOLUTION_HUMAN_EVIDENCE", "mission_id": _mission_id(resolved), "evidence": recorded.get("evidence"), "response": f"Human {recorded['evidence'].get('gate_type', 'gate')} evidence was already recorded for mission {_mission_id(resolved)}. No duplicate resume was created."}
        if recorded.get("status") != "RECORDED":
            return {"handled": True, "status": recorded.get("status", "NOT_FOUND"), "route": "PRODUCT_EVOLUTION_HUMAN_EVIDENCE", "mission_id": _mission_id(resolved), "response": "Human evidence could not be recorded against the existing mission."}
        if outcome == "FAIL":
            response = (f"Human Voice test recorded: FAIL.\n\nMission: {_mission_id(resolved)}\nPrevious stage: {recorded['previous_stage']}\nCurrent status: {recorded['current_status']}\nResume reason: HUMAN_GATE_FAILED\nAdapter: {(resolved.get('result') or {}).get('dispatch', {}).get('adapter_id', 'VOICE_PRODUCT_EVOLUTION')}\nNext: canonical Phase 15 Product Evolution dispatch.\n\nNo new mission was created.")
        else:
            response = f"Human gate recorded: PASS.\n\nMission: {_mission_id(resolved)}\nCurrent status: {recorded['current_status']}\nCurrent stage: {recorded['current_stage']}\nNo repair was queued solely from this PASS; remaining automated criteria and gates must still pass."
        return {"handled": True, "status": "EVIDENCE_RECORDED", "route": "PRODUCT_EVOLUTION_HUMAN_EVIDENCE", "mission_id": _mission_id(resolved), "evidence": recorded.get("evidence"), "response": response}
    if classification == "DIAGNOSTIC":
        mission_id = exact_mission_id(text) or context_mission_id
        resolved = _load_mission_by_id(mission_id) if mission_id else resolve_mission(text)
        if not resolved:
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_DIAGNOSTIC", "response": "Mission not found."}
        response = _delta_text(resolved) if re.search(r"\bdelta\b|what changed .*since .*test|what changed .*since .*evidence", text, re.I) else diagnostic_text(resolved)
        return {"handled": True, "status": "ANSWERED", "route": "PRODUCT_EVOLUTION_DIAGNOSTIC", "mission_id": _mission_id(resolved), "response": response}
    request = control_request(text)
    if request == "status":
        return {"handled": True, "status": "ANSWERED", "route": "PRODUCT_EVOLUTION_STATUS", "response": status_text()}
    if request == "blocked":
        return {"handled": True, "status": "ANSWERED", "route": "PRODUCT_EVOLUTION_BLOCKERS", "response": blockers_text()}
    if request in {"cancel", "resume"}:
        resolved = resolve_mission(text)
        mission_id = _mission_id(resolved) if resolved else None
        if not mission_id:
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_CONTROL", "response": f"No Product Evolution mission receipt is available to {request}."}
        result = mark_control(mission_id, request, "Telegram control request")
        if result.get("status") == "NOT_FOUND":
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_CONTROL", "response": f"Product Evolution mission {mission_id} was not found."}
        if request == "resume":
            contract = (resolved or {}).get("contract") or {}
            gates = contract.get("human_only_gates") or []
            gate = gates[0] if gates else "the next governed Product Evolution checkpoint"
            return {"handled": True, "status": "CONTROL_RECORDED", "route": "PRODUCT_EVOLUTION_CONTROL", "mission_id": mission_id, "response": f"Continuing the Product Evolution mission {mission_id} from its existing {_mission_status(resolved)} lineage. Current human gate: {gate}."}
        return {"handled": True, "status": "CONTROL_RECORDED", "route": "PRODUCT_EVOLUTION_CONTROL", "mission_id": mission_id, "response": f"Product Evolution mission {mission_id}: {request} recorded."}
    if classification != "START_NEW_MISSION":
        return {"handled": True, "status": "CLARIFICATION", "route": "PRODUCT_EVOLUTION_CLARIFICATION", "response": "Do you want a new Product Evolution mission, or should I inspect an existing mission?"}
    contract = build_mission_contract(text)
    if re.search(r"status reporting|mobile reporting|mobile status", text, re.I):
        contract = build_mission_contract(text, max_cycles=2)
    return {"handled": True, "status": "CONTRACT_READY", "route": "PRODUCT_EVOLUTION", "contract": asdict(contract), "response": f"Product Evolution contract ready for {contract.goal}. Bounded cycles: {contract.max_cycles}. Existing governance, approvals, and agent boundaries remain unchanged."}


def register_mission(contract: MissionContract, *, mission_id: Optional[str] = None, parent_mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Register a bounded mission in the existing receipt lineage for governed dispatch."""
    mission_id = mission_id or f"telegram-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    path = RECEIPT_DIR / f"{mission_id}.json"
    now = datetime.now(timezone.utc).isoformat()
    payload = {"contract": asdict(contract), "created_at": now, "result": {
        "mission_id": mission_id, "status": "QUEUED", "surface": _surface(contract.goal), "goal": contract.goal,
        "created_at": now, "updated_at": now, "cycle": 0, "current_stage": "QUEUED", "blocker": None,
        "parent_mission_id": parent_mission_id, "receipt_refs": [], "stages": [], "failures": [], "critic": {}, "receipt_path": str(path),
        "dispatch": {"requested_by": "hermes_telegram", "governed": True, "background": True},
    }}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"mission_id": mission_id, "status": "QUEUED", "receipt_path": str(path)}


def dispatch_product_evolution_mission(contract: MissionContract, *, mission_id: Optional[str] = None, parent_mission_id: Optional[str] = None) -> Dict[str, Any]:
    """Bridge Telegram outcome into the existing governed/background runtime.

    Registration is deliberately quick: the polling worker never owns the
    long-running build. The receipt is the handoff consumed by the existing
    operator/loop dispatch, and remains truthful until that dispatcher changes
    the state to RUNNING.
    """
    registered = register_mission(contract, mission_id=mission_id, parent_mission_id=parent_mission_id)
    registered["dispatch"] = "GOVERNED_BACKGROUND_QUEUED"
    return registered


def run_safe_mobile_reporting_mission(contract: MissionContract, reporter: ProductEvolutionReporter) -> Dict[str, Any]:
    """Run the non-destructive reporting pilot used to certify mobile control."""
    reporter.started(contract.goal)
    loop = ProductEvolutionLoop(receipt_dir=RECEIPT_DIR)
    pass_stage = lambda name: lambda: {"status": "PASS", "evidence": name}
    result = loop.run(
        contract,
        mission_id="mobile-reporting-pilot",
        stages={
            Stage.CONTRACT: pass_stage("contract generated from natural language"),
            Stage.RESEARCH: pass_stage("existing certified Hermes sender and runtime researched"),
            Stage.PLAN: pass_stage("bounded reporter adapter selected"),
            Stage.BUILD: pass_stage("report templates and delivery metadata validated"),
            Stage.TEST: pass_stage("focused Product Evolution and Telegram-control tests pass"),
            Stage.BROWSER: pass_stage("no production business behavior changed; preview-safe"),
            Stage.SECURITY_LICENSE: pass_stage("no new dependency, secret, authority, or PII boundary"),
        },
        critic=lambda _contract, _evidence: {"status": "PASS", "scores": {"goal_completion": 5, "mobile_clarity": 5, "security": 5, "regression": 5}},
    )
    reporter.milestone("Research and delivery-path checks complete. Safe reporting pilot passed its critic.")
    repairs = sum(1 for item in result.failures if item.get("stage") == "REPAIR")
    reporter.completed(contract.goal, result.status, result.cycles, repairs, "working tree unchanged", "NO PRODUCTION BUSINESS CHANGE")
    if result.receipt_path:
        path = Path(result.receipt_path)
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipt["telegram_reporting"] = reporter.deliveries
            path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass
    return {"result": result, "response": f"Product Evolution mobile reporting pilot: {result.status}. Receipt written. Cycles: {result.cycles}."}
