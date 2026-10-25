"""Deterministic ownership rules for feeder and dedicated Research notebooks."""
from __future__ import annotations

import hashlib
import re
from typing import Any

DEDICATED_CANARY_FULL_CONTRACT = False
DEDICATED_CANARY_NEEDLE = False
DEDICATED_CANARY_V6 = False


def subject_key(subject: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(subject or "").casefold()).strip()
    if not normalized:
        raise ValueError("RESEARCH_SUBJECT_REQUIRED")
    return hashlib.sha256(normalized.encode()).hexdigest()[:12]


def dedicated_title(subject: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", str(subject or "")).strip()
    if not normalized:
        raise ValueError("RESEARCH_SUBJECT_REQUIRED")
    return f"Nexus Research — {normalized[:100]} [{subject_key(subject)}]"


def feeder_notebook_is_intake_only(notebook_role: str | None) -> bool:
    return str(notebook_role or "").strip().upper() in {
        "FEEDER", "FEEDER_NOTEBOOK", "SOURCE_INTAKE", "INTAKE_ONLY"
    }


def find_dedicated_notebook(notebooks: list[dict[str, Any]], subject: str) -> dict[str, Any] | None:
    """Match only the deterministic dedicated title; feeder notebooks never match."""
    title = dedicated_title(subject)
    for row in notebooks:
        if str(row.get("title") or "") == title and row.get("id"):
            return row
    return None


def source_delta(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[dict[str, Any]]:
    before_ids = {str(row.get("id") or row.get("source_id") or "") for row in before}
    return [row for row in after
            if str(row.get("id") or row.get("source_id") or "")
            and str(row.get("id") or row.get("source_id") or "") not in before_ids]


def bounded_source_add_plan(notebook_id: str, rows: list[dict[str, Any]], *, limit: int = 2) -> list[dict[str, str]]:
    """Return a small explicit URL plan whose destination is one notebook."""
    if not notebook_id:
        raise ValueError("DEDICATED_NOTEBOOK_ID_REQUIRED")
    result=[]
    seen=set()
    for row in rows:
        url=str(row.get("url") or row.get("source_url") or "").strip()
        if not url.startswith("https://") or url in seen:
            continue
        seen.add(url)
        result.append({"notebook_id":notebook_id,"url":url,
            "title":str(row.get("title") or "")[:240]})
        if len(result)>=max(1,min(int(limit),2)):
            break
    return result


def web_gap_query(subject: str, gap: str) -> str:
    if not str(gap or "").strip():
        raise ValueError("RESEARCH_GAP_REQUIRED")
    return (f"For the specific online business subject '{subject}', find current independent evidence "
            f"that answers this research gap: {gap}. Prefer official primary sources and credible "
            "market evidence. Return source titles, dates, URLs, and what each source does and does "
            "not establish. Do not treat creator claims as verified facts.")[:700]


def classify_source_origin(source_type: str, feeder_type: str | None = None) -> dict[str, str | bool]:
    """Classify persistent source intake without promoting feeder contents as a notebook."""
    return {
        "source_type": str(source_type or "UNKNOWN").upper(),
        "feeder_type": str(feeder_type or "").upper() or None,
        "intake_role": "FEEDER_INTAKE_ONLY" if feeder_type else "PERSISTED_RESEARCH_SOURCE",
        "deep_research_eligible": bool(str(source_type or "").upper().startswith("YOUTUBE")),
        "requires_dedicated_notebook": True,
    }


def validate_feeder_promotion(payload: dict[str, Any], *, expected_source_id: str,
                              cited_source_ids: list[str]) -> dict[str, str]:
    """Accept one source-derived business subject only when source scoped."""
    refs={str(value) for value in cited_source_ids if value}
    if not expected_source_id or refs - {str(expected_source_id)}:
        raise ValueError("FEEDER_PROMOTION_SOURCE_SCOPE_VIOLATION")
    if str(payload.get("classification") or "").upper() != "BUSINESS_OPPORTUNITY":
        raise ValueError("FEEDER_SOURCE_NOT_PROMOTABLE_AS_BUSINESS_OPPORTUNITY")
    subject=re.sub(r"\s+", " ", str(payload.get("promoted_subject") or "")).strip()
    if not subject or len(subject)>180:
        raise ValueError("FEEDER_PROMOTION_SUBJECT_INVALID")
    return {"subject":subject,"evidence_quote":str(payload.get("evidence_quote") or "")[:500],
        "source_id":str(expected_source_id),"classification":"BUSINESS_OPPORTUNITY"}


def promotion_evidence_gap(payload: dict[str, Any]) -> str:
    """Normalize the bounded gap field from source-scoped intake output."""
    for key in ("material_evidence_gap", "evidence_gap", "material_gap"):
        value = re.sub(r"\s+", " ", str(payload.get(key) or "")).strip()
        if value:
            return value[:700]
    return ""
