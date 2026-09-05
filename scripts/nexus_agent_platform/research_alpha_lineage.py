"""Read-only Research -> Alpha lineage projection.

This module deliberately projects the existing governed ``alpha_*`` stores.  It
does not create a second intelligence database and it does not infer an Alpha
score from an intake/challenge record.  Missing lineage stays explicit.
"""
from __future__ import annotations

import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
GOVERNED = ROOT / "data" / "governed"
LOCAL_ZONE = ZoneInfo("America/Phoenix")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                value = json.loads(line)
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict):
                rows.append(value)
    except OSError:
        return []
    return rows


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def _row_time(row: dict[str, Any]) -> datetime | None:
    for key in ("discovered_at", "first_seen_at", "retrieved_at", "created_at", "updated_at", "evaluated_at"):
        value = _timestamp(row.get(key))
        if value:
            return value
    return None


def _latest_by(rows: Iterable[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not value:
            continue
        current = result.get(str(value))
        if current is None or (_row_time(row) or datetime.min.replace(tzinfo=timezone.utc)) >= (_row_time(current) or datetime.min.replace(tzinfo=timezone.utc)):
            result[str(value)] = row
    return result


def _midnight_utc(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(LOCAL_ZONE)
    return datetime.combine(local.date(), time.min, tzinfo=LOCAL_ZONE).astimezone(timezone.utc)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else ([] if value in (None, "") else [value])


def _source_refs(content: dict[str, Any], claim: dict[str, Any] | None) -> list[str]:
    refs: list[str] = []
    for value in (content.get("canonical_url"), content.get("source_url"), (claim or {}).get("source_url")):
        if isinstance(value, str) and value and value not in refs:
            refs.append(value)
    for evidence in _as_list((claim or {}).get("evidence")) + _as_list((claim or {}).get("supporting_sources")):
        if isinstance(evidence, dict):
            value = evidence.get("url") or evidence.get("reference")
            if isinstance(value, str) and value and value not in refs:
                refs.append(value)
    return refs


def _evaluation_rows() -> list[dict[str, Any]]:
    """Read only explicitly named evaluation stores when they exist.

    Historical score JSON files are not joined to current Alpha content because
    they have no stable artifact lineage.  This prevents unrelated old scores
    from being presented as today's evaluation.
    """
    paths = (GOVERNED / "alpha_evaluations.jsonl", GOVERNED / "alpha_reviews.jsonl")
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(_read_jsonl(path))
    return rows


def query_lineage(*, since: datetime | None = None, until: datetime | None = None, limit: int = 20) -> dict[str, Any]:
    """Return evidence-backed Research output lineage for a bounded time window."""
    since = since or _midnight_utc()
    until = until or datetime.now(timezone.utc)
    content_rows = _read_jsonl(GOVERNED / "alpha_content.jsonl")
    claim_rows = _read_jsonl(GOVERNED / "alpha_claims.jsonl")
    research_rows = _read_jsonl(GOVERNED / "alpha_research.jsonl")
    outcome_rows = _read_jsonl(GOVERNED / "alpha_outcomes.jsonl")
    queue_rows = _read_jsonl(GOVERNED / "alpha_discovery_queue.jsonl")
    evaluation_rows = _evaluation_rows()

    claims = _latest_by(claim_rows, "content_id")
    research_by_claim: dict[str, list[dict[str, Any]]] = {}
    for row in research_rows:
        for claim_id in _as_list(row.get("claims")):
            research_by_claim.setdefault(str(claim_id), []).append(row)
    outcomes_by_research = _latest_by(outcome_rows, "research_id")
    queue_by_research = _latest_by(queue_rows, "research_id")

    outputs: list[dict[str, Any]] = []
    seen_content: set[str] = set()
    for content in content_rows:
        content_id = str(content.get("content_id") or "")
        discovered = _row_time(content)
        if not content_id or content_id in seen_content or not discovered or not (since <= discovered <= until):
            continue
        seen_content.add(content_id)
        claim = claims.get(content_id)
        linked_research: list[dict[str, Any]] = []
        if claim:
            linked_research = research_by_claim.get(str(claim.get("claim_id")), [])
        research = max(linked_research, key=lambda row: _row_time(row) or datetime.min.replace(tzinfo=timezone.utc), default=None)
        research_id = (research or {}).get("research_id")
        matching_evals = []
        for evaluation in evaluation_rows:
            refs = {str(evaluation.get(k)) for k in ("artifact_id", "content_id", "claim_id", "research_id") if evaluation.get(k)}
            if content_id in refs or (research_id and str(research_id) in refs):
                matching_evals.append(evaluation)
        evaluation = max(matching_evals, key=lambda row: _row_time(row) or datetime.min.replace(tzinfo=timezone.utc), default=None)
        outcome = outcomes_by_research.get(str(research_id)) if research_id else None
        queue = queue_by_research.get(str(research_id)) if research_id else None
        route = (outcome or {}).get("route") or (research or {}).get("routing") or None
        status = (outcome or {}).get("status") or (research or {}).get("status") or (content.get("status") or "DISCOVERED")
        outputs.append({
            "artifact_id": content_id,
            "research_id": research_id,
            "title": content.get("title") or content.get("canonical_url") or content_id,
            "finding": (claim or {}).get("claim") or (claim or {}).get("text") or "Persisted source observation; no normalized finding text was recorded.",
            "sources": _source_refs(content, claim),
            "discovered_at": content.get("first_seen_at") or content.get("retrieved_at") or content.get("created_at"),
            "objective": (research or {}).get("question") or "UNKNOWN",
            "verification_status": (claim or {}).get("verification_status") or (claim or {}).get("evidence_status") or "UNKNOWN",
            "confidence": (claim or {}).get("confidence") or "UNKNOWN",
            "category": (claim or {}).get("category") or (research or {}).get("theme") or "UNKNOWN",
            "research_record": research_id,
            "alpha_intake": {"status": (research or {}).get("status"), "record": research_id} if research else None,
            "alpha_evaluation": {
                "evaluated": True,
                "evaluation_id": evaluation.get("evaluation_id") or evaluation.get("id"),
                "score": evaluation.get("score"),
                "decision": evaluation.get("decision") or evaluation.get("status"),
                "reasoning": evaluation.get("reasoning") or evaluation.get("reason"),
                "confidence": evaluation.get("confidence"),
                "evaluated_at": evaluation.get("evaluated_at") or evaluation.get("created_at"),
            } if evaluation else {"evaluated": False, "evaluation_id": None, "score": None, "decision": None, "reasoning": None, "confidence": None, "evaluated_at": None},
            "routing": {"destination": route, "downstream_id": (outcome or {}).get("outcome_id") or (queue or {}).get("queue_id"), "status": status} if route else {"destination": None, "downstream_id": None, "status": status},
            "current_status": status,
            "provenance": ["data/governed/alpha_content.jsonl", "data/governed/alpha_claims.jsonl"],
        })
    outputs.sort(key=lambda row: row.get("discovered_at") or "", reverse=True)
    outputs = outputs[: max(1, int(limit))]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "since": since.isoformat(), "until": until.isoformat(),
        "research_output_count": len(outputs),
        "research_outputs": outputs,
        "alpha_evaluation_count": sum(1 for row in outputs if row["alpha_evaluation"]["evaluated"]),
        "unscored_count": sum(1 for row in outputs if not row["alpha_evaluation"]["evaluated"]),
        "source": "canonical governed alpha_content/alpha_claims/alpha_research/alpha_outcomes/alpha_discovery_queue",
        "read_only": True,
    }


def is_research_lineage_request(request: str) -> bool:
    """Recognize the semantic Research-output/Alpha-lineage query class."""
    text = str(request or "").lower()
    research = bool(__import__("re").search(r"\bresearch\b", text))
    output = bool(__import__("re").search(r"\b(find|found|produce|produced|output|outputs|discover|discovered|artifact|items?|pipeline|lineage|since midnight|overnight)\b", text))
    alpha = bool(__import__("re").search(r"\b(alpha|score|scored|evaluat|decision|reject|qualif|rout)\w*\b", text))
    return research and (output or alpha)
