"""Deterministic executive portfolio orchestration above existing loops.

The portfolio layer selects and parks work; existing Phase 15 loops, Product
Evolution, Alpha, and Builder remain the executors. It never approves,
deploys, sends outreach, trades live, or creates a second scheduler.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from nexus_agent_platform.phase15.common import ROOT, atomic_write_json, utc_now

PORTFOLIO_DIR = ROOT / "reports" / "phase16a"
PORTFOLIO_JSON = PORTFOLIO_DIR / "executive_portfolio_latest.json"
PORTFOLIO_BRIEF = PORTFOLIO_DIR / "executive_daily_brief.md"
LANE_WEIGHTS = {"PRODUCT": 40, "BUSINESS": 40, "RELIABILITY": 25, "INTELLIGENCE": 20, "RESEARCH": 10, "MAINTENANCE": 5}
STATUSES = {"BACKLOG", "READY", "ACTIVE", "WAITING_HUMAN", "BLOCKED_INTERNAL", "BLOCKED_EXTERNAL", "RECOVERING", "PARKED", "COMPLETED", "CANCELLED"}
BLOCKER_CLASSES = {"INTERNAL_REPAIRABLE", "INTERNAL_ARCHITECTURAL", "EXTERNAL_SERVICE", "CREDENTIAL_REQUIRED", "HUMAN_APPROVAL", "HUMAN_SUBJECTIVE_TEST", "SECURITY_GOVERNANCE", "DEPENDENCY", "CAPACITY", "UNKNOWN"}


def _stable_id(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class PortfolioObjective:
    objective_id: str
    title: str
    lane: str
    business: str
    surface: str
    goal: str
    expected_outcome: str
    priority: float = 0.0
    business_value: float = 0.0
    revenue_impact: float = 0.0
    product_impact: float = 0.0
    risk: float = 0.0
    urgency: float = 0.0
    dependency_ids: List[str] = field(default_factory=list)
    blocked_by: List[str] = field(default_factory=list)
    human_gate: bool = False
    human_gate_reason: str = ""
    autonomous_work_available: bool = True
    status: str = "BACKLOG"
    current_stage: str = "BACKLOG"
    repair_budget: int = 2
    repair_cycles_used: int = 0
    estimated_effort: float = 1.0
    actual_effort: float = 0.0
    staleness: float = 0.0
    last_material_change: str = "UNKNOWN"
    next_action: str = "ASSESS"
    assigned_capability: str = "UNKNOWN"
    receipt_refs: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def __post_init__(self) -> None:
        if self.lane not in LANE_WEIGHTS:
            raise ValueError(f"unsupported portfolio lane: {self.lane}")
        if self.status not in STATUSES:
            raise ValueError(f"unsupported portfolio status: {self.status}")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_blocker(value: Any) -> str:
    text = str(value or "").upper()
    if not text:
        return "UNKNOWN"
    if any(token in text for token in ("AUTH", "CREDENTIAL", "TOKEN")):
        return "CREDENTIAL_REQUIRED"
    if any(token in text for token in ("APPROVAL", "RAY", "HUMAN_GATE")):
        return "HUMAN_APPROVAL"
    if any(token in text for token in ("MICROPHONE", "SUBJECTIVE", "VISUAL")):
        return "HUMAN_SUBJECTIVE_TEST"
    if any(token in text for token in ("SECURITY", "RLS", "PROTECTED")):
        return "SECURITY_GOVERNANCE"
    if any(token in text for token in ("TIMEOUT", "CAPACITY", "BUSY")):
        return "CAPACITY"
    if any(token in text for token in ("URL", "PARSER", "RECEIPT", "CORS", "METADATA", "BUILD")):
        return "INTERNAL_REPAIRABLE"
    if any(token in text for token in ("DEPENDENCY", "MISSING")):
        return "DEPENDENCY"
    if any(token in text for token in ("PROVIDER", "NETLIFY", "EXTERNAL", "429")):
        return "EXTERNAL_SERVICE"
    return "UNKNOWN"


def portfolio_score(objective: PortfolioObjective) -> tuple[float, str]:
    readiness = 12.0 if objective.autonomous_work_available else -20.0
    dependency = 10.0 if not objective.dependency_ids and not objective.blocked_by else -15.0
    gate = -30.0 if objective.human_gate else 0.0
    blocked = -35.0 if objective.status in {"BLOCKED_EXTERNAL", "WAITING_HUMAN", "PARKED"} else 0.0
    monopoly_penalty = min(30.0, objective.repair_cycles_used * 12.0 + max(0.0, objective.actual_effort - objective.estimated_effort) * 4.0)
    safety_override = 25.0 if objective.risk >= 9.0 else 0.0
    score = (objective.business_value * 2.0 + objective.revenue_impact * 2.5 + objective.product_impact * 1.5 + objective.urgency * 1.5 + objective.staleness + readiness + dependency + gate + blocked - monopoly_penalty + safety_override)
    reason = "value/urgency/readiness"
    if monopoly_penalty:
        reason += "; diminishing effort/repair return"
    if objective.human_gate:
        reason += "; parked at Ray gate"
    return round(score, 3), reason


def _capability(objective: PortfolioObjective) -> str:
    if objective.surface.startswith("Voice") or objective.lane == "RELIABILITY":
        return "PRODUCT_EVOLUTION_OR_RELEASE_RECOVERY"
    if objective.lane == "INTELLIGENCE":
        return "ALPHA_RESEARCH"
    if objective.lane == "BUSINESS":
        return "REVENUE_OPPORTUNITY_LOOP"
    if objective.lane == "PRODUCT":
        return "PRODUCT_EVOLUTION_OR_BUILDER"
    return "EXISTING_DETERMINISTIC_LOOP"


def seed_objectives(receipt_root: Path | None = None) -> List[PortfolioObjective]:
    """Seed only objectives supported by current repository evidence."""
    root = receipt_root or (ROOT / "reports" / "product_evolution")
    voice_status, voice_stage, blocker = "READY", "READY", ""
    voice_receipt = root / "telegram-20260824172054-077bf5a7.json"
    try:
        value = json.loads(voice_receipt.read_text(encoding="utf-8"))["result"]
        blocker = str(value.get("blocker") or "")
        voice_stage = str(value.get("current_stage") or "UNKNOWN")
        if voice_stage == "HUMAN_GATE":
            voice_status = "WAITING_HUMAN"
        elif value.get("status") == "BLOCKED":
            voice_status = "BLOCKED_INTERNAL" if classify_blocker(blocker) == "INTERNAL_REPAIRABLE" else "BLOCKED_EXTERNAL"
        elif voice_stage in {"RELEASE_CANDIDATE_READY", "APPROVED_RELEASE_PENDING_DEPLOYMENT"}:
            voice_status = "WAITING_HUMAN"
    except (OSError, ValueError, KeyError, TypeError):
        voice_status, voice_stage = "BLOCKED_INTERNAL", "RECEIPT_UNKNOWN"
    now = _now()
    common = {"created_at": now, "updated_at": now}
    return [
        PortfolioObjective("reliability.voice_release_recovery", "Voice autonomous release recovery", "RELIABILITY", "GoClear", "Voice release", "Repair and prepare the bounded Voice release without production mutation.", "A tested governed candidate or truthful blocker.", business_value=7, product_impact=8, urgency=8, risk=9, status=voice_status, current_stage=voice_stage, blocked_by=[blocker] if blocker else [], human_gate=voice_status == "WAITING_HUMAN", human_gate_reason="Ray approval or microphone test" if voice_status == "WAITING_HUMAN" else "", repair_cycles_used=0, next_action="WAIT_FOR_RAY" if voice_status == "WAITING_HUMAN" else "RECOVER", receipt_refs=[str(voice_receipt)], **common),
        PortfolioObjective("reliability.mission_control_freshness", "Mission Control freshness", "RELIABILITY", "Nexus", "Mission Control", "Keep portfolio and loop read models truthful and fresh.", "Fresh read model or explicit STALE/UNKNOWN evidence.", business_value=6, product_impact=7, urgency=6, status="READY", current_stage="READ_MODEL", next_action="AUDIT", **common),
        PortfolioObjective("product.experience_2", "Experience 2.0 final certification", "PRODUCT", "GoClear", "Experience 2.0", "Advance the next bounded product experience certification.", "Tested product increment ready for its true gate.", business_value=8, product_impact=9, urgency=7, status="READY", current_stage="BACKLOG", next_action="PLAN", **common),
        PortfolioObjective("product.admin_ux", "Admin UX improvements", "PRODUCT", "GoClear", "Admin UX", "Improve admin clarity within protected product scope.", "Focused UX change with verification evidence.", business_value=7, product_impact=8, urgency=5, status="READY", current_stage="BACKLOG", next_action="RESEARCH", **common),
        PortfolioObjective("business.goclear_revenue", "GoClear revenue workflows", "BUSINESS", "GoClear", "Revenue", "Advance revenue-ready client and opportunity workflows.", "A measurable revenue or client-value advancement.", business_value=10, revenue_impact=10, urgency=8, status="READY", current_stage="BACKLOG", next_action="ADVANCE", **common),
        PortfolioObjective("business.opportunity_loop", "Opportunity and SEO movement", "BUSINESS", "GoClear", "Growth", "Continue deterministic opportunity and SEO evidence work.", "Fresh, deduped, provenance-backed opportunity output.", business_value=8, revenue_impact=8, urgency=6, status="READY", current_stage="BACKLOG", next_action="RUN_LOOP", assigned_capability="REVENUE_OPPORTUNITY_LOOP", **common),
        PortfolioObjective("intelligence.forex_foundation", "Forex Trading Knowledge foundation", "INTELLIGENCE", "Nexus", "Forex research", "Build research-only knowledge without live or funded trading.", "Provenance-backed research artifact.", business_value=5, product_impact=4, urgency=3, status="READY", current_stage="RESEARCH", next_action="RESEARCH", **common),
        PortfolioObjective("intelligence.creative", "Creative Intelligence 2.0 research", "INTELLIGENCE", "GoClear", "Creative Intelligence", "Develop research-backed creative capability.", "Research packet or bounded capability recommendation.", business_value=6, product_impact=6, urgency=4, status="READY", current_stage="RESEARCH", next_action="RESEARCH", **common),
    ]


def plan_portfolio(objectives: Sequence[PortfolioObjective], *, cycle_id: str = "executive-cycle") -> Dict[str, Any]:
    scored = []
    for objective in objectives:
        score, reason = portfolio_score(objective)
        scored.append((score, objective, reason))
    scored.sort(key=lambda item: (-item[0], item[1].objective_id))
    selected: List[Dict[str, Any]] = []
    parked: List[Dict[str, Any]] = []
    waiting: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    lane_selected: set[str] = set()
    for score, objective, reason in scored:
        row = {"objective_id": objective.objective_id, "lane": objective.lane, "score": score, "reason": reason, "capability": objective.assigned_capability or _capability(objective), "expected_artifact": objective.expected_outcome}
        if objective.human_gate or objective.status == "WAITING_HUMAN":
            waiting.append({**row, "required_action": objective.human_gate_reason or objective.next_action})
        elif objective.status in {"BLOCKED_INTERNAL", "BLOCKED_EXTERNAL", "PARKED"}:
            blocked.append({**row, "blocker": objective.blocked_by or [objective.next_action]})
        elif objective.status in {"READY", "RECOVERING", "ACTIVE"} and objective.autonomous_work_available and objective.lane not in lane_selected:
            selected.append(row)
            lane_selected.add(objective.lane)
        else:
            parked.append({**row, "reason": "bounded slot or dependency not ready"})
    counts = {lane: sum(1 for row in selected if row["lane"] == lane) for lane in LANE_WEIGHTS}
    return {
        "cycle_id": cycle_id,
        "generated_at": _now(),
        "selected": selected,
        "parked": parked,
        "waiting_human": waiting,
        "blocked": blocked,
        "deferred": [],
        "portfolio_balance": {"lane_selected": counts, "policy_weights": dict(LANE_WEIGHTS)},
        "cost_projection": {"model_calls": 0, "estimated_cost_usd": 0.0, "basis": "deterministic bounded slots"},
        "risk_summary": {"human_gates": len(waiting), "blocked": len(blocked), "selected": len(selected)},
    }


def build_trust_metrics(plan: Mapping[str, Any], objectives: Sequence[PortfolioObjective]) -> Dict[str, Any]:
    advanced = sum(1 for item in objectives if item.status in {"ACTIVE", "RECOVERING", "COMPLETED"})
    autonomous = sum(1 for item in objectives if item.autonomous_work_available and item.status not in {"WAITING_HUMAN", "BLOCKED_EXTERNAL", "PARKED"})
    selected = len(plan.get("selected") or [])
    return {
        "AUTONOMOUS_PROGRESS_RATE": round(advanced / autonomous, 3) if autonomous else 0.0,
        "HUMAN_INTERRUPT_RATE": round(len(plan.get("waiting_human") or []) / max(1, advanced), 3),
        "PORTFOLIO_STALL_RATE": 1.0 if not selected and autonomous else 0.0,
        "OBJECTIVE_MONOPOLY_RATE": round(1 / selected, 3) if selected == 1 else 0.0,
        "TRUST_LINE": "bounded_deterministic_portfolio_read_model",
    }


def render_daily_brief(plan: Mapping[str, Any], objectives: Sequence[PortfolioObjective], metrics: Mapping[str, Any]) -> str:
    names = {item.objective_id: item.title for item in objectives}
    def lines(rows: Iterable[Mapping[str, Any]], key: str = "objective_id") -> str:
        values = [f"- {names.get(row.get(key), row.get(key))}" for row in rows]
        return "\n".join(values) or "- None"
    return "\n".join([
        "# NEXUS DAILY OPERATING REPORT", "",
        "## Completed autonomously", "- None newly inferred by this deterministic cycle", "",
        "## Advanced / selected", lines(plan.get("selected") or []), "",
        "## Waiting for Ray", lines(plan.get("waiting_human") or []), "",
        "## Blocked", lines(plan.get("blocked") or []), "",
        "## Continuing / parked", lines(plan.get("parked") or []), "",
        "## Trust metrics", json.dumps(dict(metrics), sort_keys=True), "",
        "Source: Executive Portfolio Loop read model; no human result or production approval is inferred.", "",
    ])


def run_executive_portfolio_cycle(*, cycle_id: str = "canonical-phase15") -> Dict[str, Any]:
    objectives = seed_objectives()
    plan = plan_portfolio(objectives, cycle_id=cycle_id)
    metrics = build_trust_metrics(plan, objectives)
    receipt = {"cycle_id": cycle_id, "generated_at": utc_now(), "objectives": [item.to_dict() for item in objectives], "plan": plan, "metrics": metrics, "authority": {"production_approval": "RAY_ONLY", "live_trading": "DISABLED", "external_outreach": "DISABLED"}}
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    atomic_write_json(PORTFOLIO_JSON, receipt)
    PORTFOLIO_BRIEF.write_text(render_daily_brief(plan, objectives, metrics), encoding="utf-8")
    return receipt
