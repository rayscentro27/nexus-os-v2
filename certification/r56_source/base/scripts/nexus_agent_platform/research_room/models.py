"""Typed, serializable Research Room records."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RoomMessage:
    role: str
    content: str
    kind: str = "COMMENT"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass
class ResearchCase:
    case_id: str
    root_objective: str
    original_request: str
    source_references: list[dict[str, Any]] = field(default_factory=list)
    source_type: str = "UNKNOWN"
    room_messages: list[dict[str, Any]] = field(default_factory=list)
    questions: list[dict[str, Any]] = field(default_factory=list)
    answers: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    advisor_comments: list[dict[str, Any]] = field(default_factory=list)
    advisor_sessions: list[dict[str, Any]] = field(default_factory=list)
    test_results: list[dict[str, Any]] = field(default_factory=list)
    unresolved_items: list[dict[str, Any]] = field(default_factory=list)
    prior_nexus_knowledge: list[dict[str, Any]] = field(default_factory=list)
    source_report: dict[str, Any] | None = None
    knowledge_reconciliation: dict[str, Any] | None = None
    needle_result: dict[str, Any] | None = None
    questions_generated: bool = False
    followup_result: dict[str, Any] | None = None
    fact_check_completed: bool = False
    turn_jobs: list[dict[str, Any]] = field(default_factory=list)
    processed_turns: dict[str, dict[str, Any]] = field(default_factory=dict)
    final_synthesis: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None
    status: str = "OPEN"
    status_history: list[str] = field(default_factory=lambda: ["OPEN"])
    next_participant: str = "RESEARCH_LEAD"
    turn_count: int = 0
    metadata: dict[str, Any] = field(default_factory=lambda: {"shadow_mode": True})
    model_usage: dict[str, Any] = field(default_factory=lambda: {"calls": [], "total_model_calls": 0,
        "total_input_tokens": 0, "total_output_tokens": 0, "total_tokens": 0,
        "estimated_total_cost_usd": 0.0, "cache_hits": 0, "cache_misses": 0,
        "token_counts_complete": True, "cost_complete": True})
    advisor_cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    advisor_plan: dict[str, Any] = field(default_factory=dict)
    multi_advisor_comparison: dict[str, Any] | None = None
    cost_routing: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ResearchCase":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: value[key] for key in allowed if key in value})


def new_case(case_id: str, objective: str, source_url: str | None = None,
             source_type: str = "UNKNOWN", metadata: dict[str, Any] | None = None) -> ResearchCase:
    if not case_id or not objective.strip():
        raise ValueError("CASE_ID_AND_OBJECTIVE_REQUIRED")
    refs = [{"url": source_url, "type": source_type}] if source_url else []
    case = ResearchCase(case_id=case_id, root_objective=objective.strip(),
        original_request=objective.strip(), source_references=refs,
        source_type=source_type.upper(), metadata={"shadow_mode": True, **(metadata or {})})
    case.room_messages.append(asdict(RoomMessage("RAY", objective.strip(), "OBJECTIVE")))
    return case
