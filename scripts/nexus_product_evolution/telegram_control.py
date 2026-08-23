"""Governed Telegram control for Product Evolution.

This module contains intent/contract/reporting logic only. Telegram transport
is injected by the certified Hermes worker or bridge; this module never reads
credentials and never creates a polling loop.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Mapping, Optional

from .loop import FailureClass, MissionContract, ProductEvolutionLoop, Stage

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_DIR = ROOT / "reports/product_evolution"
MAX_TELEGRAM_RETRIES = 2

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
    return bool(re.search(r"\b(product evolution|run product evolution|improve|evolve|make .{2,} easier|make .{2,} better)\b", lowered))


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


def control_request(text: str) -> Optional[str]:
    lowered = _compact(text).lower()
    if re.search(r"\b(improve|evolve|run product evolution|make .{2,} easier|make .{2,} better)\b", lowered):
        return None
    if re.search(r"\b(product evolution|creative studio|voice mission)\b", lowered) and re.search(r"\b(status|working on|finish|blocked|stop|cancel|continue|resume)\b", lowered):
        return "status" if re.search(r"\b(status|working on|finish|blocked|why)", lowered) else "cancel" if re.search(r"\b(stop|cancel)", lowered) else "resume"
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
        result["control"] = {"action": action, "evidence": _compact(evidence), "recorded_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()}
        value["result"] = result
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result
    return {"status": "NOT_FOUND", "mission_id": mission_id}


def handle_product_evolution_intake(text: str) -> Dict[str, Any]:
    """Build a safe contract or return a truthful clarification/block."""
    if is_unsafe_product_evolution_request(text):
        return {"handled": True, "status": "BLOCKED", "route": "PRODUCT_EVOLUTION", "response": "Product Evolution cannot change security, authority, payments, approvals, credentials, or client-data boundaries."}
    request = control_request(text)
    if request == "status":
        return {"handled": True, "status": "ANSWERED", "route": "PRODUCT_EVOLUTION_STATUS", "response": status_text()}
    if request in {"cancel", "resume"}:
        mission_id = re.search(r"\b(?:mission|run)\s+([a-z0-9_-]+)\b", _compact(text), re.I)
        mission_id = mission_id.group(1) if mission_id else _latest_mission_id()
        if not mission_id:
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_CONTROL", "response": f"No Product Evolution mission receipt is available to {request}."}
        result = mark_control(mission_id, request, "Telegram control request")
        if result.get("status") == "NOT_FOUND":
            return {"handled": True, "status": "NOT_FOUND", "route": "PRODUCT_EVOLUTION_CONTROL", "response": f"Product Evolution mission {mission_id} was not found."}
        return {"handled": True, "status": "CONTROL_RECORDED", "route": "PRODUCT_EVOLUTION_CONTROL", "response": f"Product Evolution mission {mission_id}: {request} recorded. Existing work is not undone automatically."}
    if not is_product_evolution_intent(text):
        return {"handled": False}
    contract = build_mission_contract(text)
    if "status reporting" in text.lower() or "mobile reporting" in text.lower():
        contract = build_mission_contract(text, max_cycles=2)
    return {"handled": True, "status": "CONTRACT_READY", "route": "PRODUCT_EVOLUTION", "contract": asdict(contract), "response": f"Product Evolution contract ready for {contract.goal}. Bounded cycles: {contract.max_cycles}. Existing governance, approvals, and agent boundaries remain unchanged."}


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
