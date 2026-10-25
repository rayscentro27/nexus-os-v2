"""Deterministic, bounded dispositions for Phase 15 research candidates."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


def _identity(candidate: dict[str, Any]) -> str:
    url = str(candidate.get("source_url") or "").strip().lower().rstrip("/")
    title = " ".join(str(candidate.get("title") or "").lower().split())
    return url or title or str(candidate.get("candidate_id") or "unknown")


def build_research_decisions(
    candidates: Iterable[dict[str, Any]], *, session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify only the supplied candidate batch; never reads a corpus or calls AI."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(candidates):
        if not isinstance(raw, dict):
            continue
        candidate = {key: raw.get(key) for key in (
            "candidate_id", "title", "category", "source_url", "snippet",
            "evidence_classification", "freshness", "score", "query",
        ) if key in raw}
        identity = _identity(candidate)
        candidate_id = str(candidate.get("candidate_id") or "candidate_" + hashlib.sha256(identity.encode()).hexdigest()[:16])
        candidate["candidate_id"] = candidate_id
        if identity in seen:
            decision, reason = "DUPLICATE", "Duplicate identity in this bounded candidate batch."
        else:
            seen.add(identity)
            evidence = str(candidate.get("evidence_classification") or "UNKNOWN").upper()
            freshness = str(candidate.get("freshness") or "UNKNOWN").upper()
            if freshness in {"STALE", "EXPIRED"}:
                decision, reason = "STALE", "Candidate evidence is marked stale."
            elif not candidate.get("source_url") or evidence in {"UNKNOWN", "UNVERIFIED", "NONE"}:
                decision, reason = "NEEDS_MORE_EVIDENCE", "A source reference and evidence classification are required."
            elif evidence in {"OBSERVED", "VERIFIED", "PRIMARY_SOURCE"}:
                decision, reason = "ACCEPT", "A bounded candidate has a source reference and verified evidence classification."
            else:
                decision, reason = "WATCH", "Candidate is source-linked but evidence remains inferential."
        result = {**candidate, "decision": decision, "decision_reason": reason}
        if decision == "REJECT":
            result["rejection_reason"] = reason
        rows.append(result)
    counts = {key: sum(row["decision"] == key for row in rows) for key in ("ACCEPT", "WATCH", "REJECT", "DUPLICATE", "NEEDS_MORE_EVIDENCE", "STALE")}
    output = {
        "schema_version": "phase15-research-decisions.v1",
        "session": dict(session or {}),
        "decisions": rows,
        "counts": {
            "accept": counts["ACCEPT"], "watch": counts["WATCH"], "reject": counts["REJECT"],
            "duplicate": counts["DUPLICATE"], "needs_more_evidence": counts["NEEDS_MORE_EVIDENCE"], "stale": counts["STALE"],
        },
    }
    output["batch_hash"] = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return output
