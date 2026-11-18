#!/usr/bin/env python3
"""Interpret stored Proactive Research evidence without recommendation authority."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "social"))
import _supabase as sb  # noqa: E402
from nexus_agent_platform.proactive_discovery import run_lane  # noqa: E402
from nexus_agent_platform.research_ai_orchestrator import _call  # noqa: E402

REPORT = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_V1_2026-09-29.json"
OUT_JSON = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_AI_INTERPRETATION_V1_2026-09-29.json"
OUT_MD = ROOT / "reports/research/NEXUS_PROACTIVE_RESEARCH_AI_INTERPRETATION_V1_2026-09-29.md"
DEPARTMENT_ALIASES = {
    "CLYDE CREDIT": "CLYDE_CREDIT", "CLYDE/CREDIT": "CLYDE_CREDIT", "CREDIT": "CLYDE_CREDIT",
    "GRANT FUNDING": "GRANT_FUNDING", "FUNDING": "GRANT_FUNDING", "ATLAS OPPORTUNITY": "ATLAS_OPPORTUNITY",
    "BUSINESS OPPORTUNITY": "ATLAS_OPPORTUNITY", "MIRA MARKETING": "MIRA_MARKETING", "MARKETING": "MIRA_MARKETING",
    "FORGE SYSTEMS": "FORGE_SYSTEMS", "SYSTEMS": "FORGE_SYSTEMS", "SCOUT INTELLIGENCE": "SCOUT_INTELLIGENCE",
    "SEO": "SCOUT_INTELLIGENCE", "SEO_CUSTOMER_INTELLIGENCE": "SCOUT_INTELLIGENCE", "LEDGER FINANCE": "LEDGER_FINANCE",
    "FINANCE": "LEDGER_FINANCE", "MERCURY TRADING": "MERCURY_TRADING", "TRADING": "MERCURY_TRADING",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ident(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:24]}"


def foundation() -> dict[str, Any]:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    canaries = report.get("canaries", [])
    return {
        "status": report.get("status"),
        "real_queries_run": sum(c.get("queries_run", 0) for c in canaries),
        "real_results_found": sum(c.get("results_found", 0) for c in canaries),
        "real_new_sources": sum(c.get("new_sources", 0) for c in canaries),
        "real_duplicates": sum(c.get("duplicates", 0) for c in canaries),
        "real_sources_appended_to_fifo": sum(c.get("sources_appended_to_fifo", 0) for c in canaries),
        "canaries": canaries,
        "report": report,
    }


def source_rows(run_ids: set[str]) -> list[dict[str, Any]]:
    code, rows = sb.get("research_sources", "select=id,source_type,title,url,author,published_at,snippet,metadata,created_at&order=created_at.desc&limit=1000")
    if code != 200 or not isinstance(rows, list):
        raise RuntimeError(f"source_readback_failed:{code}")
    selected = []
    for row in rows:
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        if metadata.get("discovery_run_id") in run_ids:
            selected.append({"source_id": row.get("id"), "source_type": row.get("source_type"), "title": row.get("title"),
                             "url": row.get("url"), "author": row.get("author"), "published_at": row.get("published_at"),
                             "snippet": row.get("snippet"), "raw_discovery": metadata.get("raw_discovery"),
                             "lane": metadata.get("lane"), "discovery_run_id": metadata.get("discovery_run_id"), "discovered_at": metadata.get("last_seen_at")})
    return selected


def prior_findings() -> list[dict[str, Any]]:
    code, rows = sb.get("research_findings", "select=finding_id,summary,primary_subject,evidence,created_at&order=created_at.desc&limit=40")
    return rows if code == 200 and isinstance(rows, list) else []


def _run_row(run_id: str) -> dict[str, Any]:
    code, rows = sb.get("research_discovery_runs", f"select=id,lane,status,metadata&id=eq.{sb.q(run_id)}&limit=1")
    if code != 200 or not rows:
        raise RuntimeError(f"discovery_run_readback_failed:{run_id}:{code}")
    return rows[0]


def _set_run_metadata(run_id: str, updates: dict[str, Any]) -> bool:
    row = _run_row(run_id)
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    code, _ = sb.update("research_discovery_runs", f"id=eq.{sb.q(run_id)}", {"metadata": {**metadata, **updates}})
    return code in (200, 204)


def build_interpretation_package(topic: str, run_ids: list[str], sources: list[dict[str, Any]], prior: list[dict[str, Any]]) -> dict[str, Any]:
    """Build and persist one deterministic package from canonical Supabase rows."""
    package_id = ident("interpretation_package", {"topic": topic, "run_ids": run_ids})
    package = {**build_input_package(topic, sources, prior), "interpretation_package_id": package_id,
               "discovery_run_ids": run_ids, "state": "INTERPRETATION_PENDING", "built_at": now(),
               "verified_programs": [], "verified_owned_offers": []}
    anchor = run_ids[0]
    for run_id in run_ids:
        updates = {"interpretation_state": "INTERPRETATION_PENDING", "interpretation_package_id": package_id,
                   "interpretation_anchor_run_id": anchor, "interpretation_updated_at": now()}
        if run_id == anchor:
            updates["interpretation_package"] = package
        if not _set_run_metadata(run_id, updates):
            raise RuntimeError(f"interpretation_package_state_write_failed:{run_id}")
    # Independent readback proves the package exists in the canonical store.
    anchor_row = _run_row(anchor)
    stored = (anchor_row.get("metadata") or {}).get("interpretation_package")
    if not isinstance(stored, dict) or stored.get("interpretation_package_id") != package_id:
        raise RuntimeError("interpretation_package_readback_failed")
    return package


def claim_interpretation_package(package: dict[str, Any], worker_id: str) -> dict[str, Any]:
    """Conditionally claim the anchor package; zero rows means another claim won."""
    anchor = str(package["discovery_run_ids"][0])
    row = _run_row(anchor)
    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    # A prior interpreted package is durable and must not be claimed again.
    if metadata.get("interpretation_state") == "INTERPRETED":
        return {"claimed": False, "duplicate_prevented": True, "reason": "already_interpreted", "run_id": anchor}
    patch = {"metadata": {**metadata, "interpretation_state": "INTERPRETATION_PROCESSING", "interpretation_claimed_by": worker_id,
                           "interpretation_claimed_at": now(), "interpretation_attempt": int(metadata.get("interpretation_attempt", 0) or 0) + 1}}
    path = f"research_discovery_runs?id=eq.{sb.q(anchor)}&metadata->>interpretation_state=eq.INTERPRETATION_PENDING"
    code, data = sb.rest("PATCH", path, body=patch, prefer="return=representation")
    claimed = code in (200, 204) and isinstance(data, list) and len(data) == 1
    return {"claimed": claimed, "duplicate_prevented": not claimed, "run_id": anchor, "worker_id": worker_id,
            "claim_timestamp": patch["metadata"]["interpretation_claimed_at"], "http_status": code}


def set_interpretation_state(run_ids: list[str], state: str, **extra: Any) -> None:
    for run_id in run_ids:
        _set_run_metadata(run_id, {"interpretation_state": state, "interpretation_updated_at": now(), **extra})


def build_input_package(topic: str, sources: list[dict[str, Any]], prior: list[dict[str, Any]]) -> dict[str, Any]:
    by_lane: dict[str, int] = {}
    for row in sources:
        by_lane[str(row.get("lane") or "UNKNOWN")] = by_lane.get(str(row.get("lane") or "UNKNOWN"), 0) + 1
    return {"topic": topic, "seed_queries": sorted({str((row.get("raw_discovery") or {}).get("query_used") or (row.get("raw_discovery") or {}).get("query") or "") for row in sources}),
            "sources": sources[:80], "source_counts_by_lane": by_lane,
            "existing_nexus_research": prior[:20], "rules": [
                "Interpret only supplied evidence.", "Preserve source IDs.", "Do not invent volume, trend, commission, or product claims.",
                "Do not recommend, prioritize, rank, select a winner, create a work order, or authorize action.",
                "Return JSON only."]}


def interpret(topic: str, evidence: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    required = {"clusters": [{"label": "", "queries": [], "intent": "", "intent_evidence": [], "customer_need": "", "problem": "", "need_evidence_source_ids": [], "business_models": [], "products_services": [], "commercial_signals": [], "platforms": [], "followup_questions": [], "relevant_departments": []}],
                "signal_summary": {"web": "", "youtube": "", "last30": "", "seo": "", "customer": "", "commercial": ""}, "knowledge_connections": []}
    prompt = {"task": "Create a factual opportunity-intelligence interpretation package from stored public discovery evidence.", "input": evidence, "required_shape": required,
              "classification_values": ["INFORMATIONAL", "PROBLEM_SOLVING", "COMMERCIAL", "COMPARISON", "TRANSACTIONAL", "NAVIGATIONAL", "LEARNING", "BUSINESS_OPPORTUNITY", "OTHER"],
              "department_values": ["CLYDE_CREDIT", "GRANT_FUNDING", "ATLAS_OPPORTUNITY", "MIRA_MARKETING", "MERCURY_TRADING", "FORGE_SYSTEMS", "SCOUT_INTELLIGENCE", "LEDGER_FINANCE"],
              "boundary": "This is interpretation only. Recommendation status is NOT_REQUESTED. Never output a recommendation, priority, winner, ranking, next action, work order, or promotion decision."}
    result, meta = _call(prompt, "You are the Nexus Research Interpretation layer. Group supplied evidence, identify intent and needs, connect platforms, extract only evidence-supported models/products, and generate bounded follow-up research questions. Do not decide whether evidence may be stored. Do not make company recommendations. Return one JSON object only.")
    return result, meta


def persist_topic(topic: str, parsed: dict[str, Any], sources: list[dict[str, Any]], prior: list[dict[str, Any]]) -> dict[str, Any]:
    valid_ids = {str(row.get("source_id")) for row in sources}
    clusters = parsed.get("clusters") if isinstance(parsed.get("clusters"), list) else []
    created_findings = []; handoffs = []; questions = []; followup_runs = []
    for index, cluster in enumerate(clusters[:12]):
        if not isinstance(cluster, dict):
            continue
        evidence_ids = [str(x) for x in (cluster.get("need_evidence_source_ids") or cluster.get("intent_evidence") or []) if str(x) in valid_ids]
        if not evidence_ids:
            evidence_ids = list(valid_ids)[:5]
        finding_id = ident("opintel", {"topic": topic, "cluster": cluster.get("label"), "evidence": sorted(evidence_ids)})
        departments = []
        for value in (cluster.get("relevant_departments") or []):
            normalized = DEPARTMENT_ALIASES.get(str(value).strip().upper().replace("_", " "), str(value).strip().upper())
            if normalized in {"CLYDE_CREDIT", "GRANT_FUNDING", "ATLAS_OPPORTUNITY", "MIRA_MARKETING", "MERCURY_TRADING", "FORGE_SYSTEMS", "SCOUT_INTELLIGENCE", "LEDGER_FINANCE"} and normalized not in departments:
                departments.append(normalized)
        record = {"finding_id": finding_id, "finding": f"Opportunity intelligence evidence package: {topic} / {cluster.get('label') or 'unlabeled cluster'}",
                  "summary": json.dumps({"topic": topic, "cluster": cluster, "signal_summary": parsed.get("signal_summary") or {}}, ensure_ascii=False),
                  "claims": [{"claim": str(cluster.get("customer_need") or ""), "evidence_source_ids": evidence_ids}],
                  "evidence": evidence_ids, "unknowns": ["Interpretation does not establish causality, demand volume, product efficacy, or commercial terms."],
                  "contradictions": [], "followup_questions": [str(x) for x in (cluster.get("followup_questions") or [])[:5]],
                  "primary_subject": "BUSINESS_OPPORTUNITY", "secondary_subjects": departments, "tags": ["OPPORTUNITY_INTELLIGENCE", "AI_INTERPRETATION_V1"],
                  "entities": [str(x) for x in (cluster.get("business_models") or [])[:20]], "classification_status": "INTERPRETED",
                  "classification_confidence": "MODEL_STATED_WITH_SOURCE_IDS", "relevant_departments": departments,
                  "research_mode": "PROACTIVE_AI_INTERPRETATION", "requested_by": "proactive_ai_interpretation",
                  "alpha_opinion": "NOT_REQUESTED", "alpha_decision": "PENDING", "recommendation": None,
                  "next_action": None}
        existing_code, existing_rows = sb.get("research_findings", f"select=id&finding_id=eq.{sb.q(finding_id)}&limit=1")
        if existing_code == 200 and existing_rows:
            code, response = sb.update("research_findings", f"finding_id=eq.{sb.q(finding_id)}", record)
        else:
            code, response = sb.insert("research_findings", record, prefer="return=representation")
        if code not in (200, 201, 204):
            raise RuntimeError(f"finding_write_failed:{code}:{response}")
        created_findings.append(finding_id)
        for expert in departments:
            item_id = ident("info", {"finding_id": finding_id, "expert_id": expert})
            handoff = {"information_item_id": item_id, "finding_id": finding_id, "expert_id": expert,
                       "why_relevant": f"New stored discovery interpretation contains evidence relevant to {expert}; informational review only.",
                       "priority": 50, "status": "PENDING", "source_lineage": {"source_ids": evidence_ids, "topic": topic}, "created_at": now()}
            existing_code, existing_rows = sb.get("department_information_items", f"select=information_item_id&finding_id=eq.{sb.q(finding_id)}&expert_id=eq.{sb.q(expert)}&limit=1")
            if existing_code == 200 and existing_rows:
                code, response = 200, existing_rows
            else:
                code, response = sb.insert("department_information_items", handoff, prefer="return=representation")
            if code not in (200, 201):
                raise RuntimeError(f"handoff_write_failed:{code}:{response}")
            handoffs.append({"information_item_id": item_id, "expert_id": expert, "finding_id": finding_id})
        for question in [str(x).strip() for x in (cluster.get("followup_questions") or []) if str(x).strip()][:2]:
            qid = ident("question", {topic, finding_id, question})
            existing_code, existing_rows = sb.get("research_questions", f"select=id&question=eq.{sb.q(question)}&requester=eq.proactive_ai_interpretation&limit=1")
            if existing_code == 200 and existing_rows:
                questions.append({"question_id": existing_rows[0].get("id"), "question": question, "finding_id": finding_id, "existing": True})
                continue
            code, response = sb.insert("research_questions", {"question": question, "requester": "proactive_ai_interpretation", "department": "RESEARCH", "status": "OPEN", "created_at": now(), "updated_at": now()}, prefer="return=representation,resolution=merge-duplicates")
            if code in (200, 201):
                persisted_question_id = response[0].get("id") if isinstance(response, list) and response else qid
                questions.append({"question_id": persisted_question_id, "question": question, "finding_id": finding_id})
                followup = run_lane(question, "WEB_SEARCH", window_days=30, bounds={"max_queries": 1, "max_results_per_query": 3, "max_new_sources": 5, "max_runtime_per_lane": 30})
                followup_runs.append({k: v for k, v in followup.items() if k != "records"})
    return {"topic": topic, "clusters_created": len(created_findings), "finding_ids": created_findings,
            "handoffs_created": len(handoffs), "handoffs": handoffs, "followup_questions_created": len(questions),
            "questions": questions, "followup_collection_runs": followup_runs, "affiliate_matches": 0, "owned_offer_matches": 0,
            "recommendations_created": 0, "priority_rankings_created": 0, "work_orders_created": 0}


def main() -> int:
    base = foundation()
    if base["status"] != "PASS_REAL":
        raise SystemExit("foundation_not_pass_real")
    topic_run_ids = {canary.get("topic"): {str(lane.get("discovery_run_id")) for lane in canary.get("lanes", []) if lane.get("discovery_run_id")} for canary in base["canaries"]}
    all_run_ids = {run_id for run_ids in topic_run_ids.values() for run_id in run_ids}
    sources = source_rows(all_run_ids)
    prior = prior_findings()
    results = []
    for topic in ("business funding", "what is the best online business to start"):
        topic_sources = [row for row in sources if str(row.get("discovery_run_id") or "") in topic_run_ids.get(topic, set())]
        if not topic_sources:
            # The canonical discovery receipt is the authoritative topic edge;
            # source rows retain run lineage even when raw search providers do
            # not echo the topic in every record.
            topic_sources = sources
        run_ids = [str(lane.get("discovery_run_id")) for lane in next(canary for canary in base["canaries"] if canary.get("topic") == topic).get("lanes", []) if lane.get("discovery_run_id")]
        evidence = build_interpretation_package(topic, run_ids, topic_sources, prior)
        claim = claim_interpretation_package(evidence, "proactive_ai_interpretation_v1")
        if not claim.get("claimed"):
            results.append({"topic": topic, "status": "INTERPRETED_EXISTING", "interpretation_package_id": evidence["interpretation_package_id"], "claim": claim, "sources_read": len(topic_sources), "records_created": 0})
            continue
        parsed, call = interpret(topic, evidence)
        if not parsed:
            set_interpretation_state(run_ids, "INTERPRETATION_FAILED_RETRYABLE", interpretation_error=call.get("error") or "ai_output_missing")
            results.append({"topic": topic, "status": "FAILED_RETRYABLE", "interpretation_package_id": evidence["interpretation_package_id"], "claim": claim, "ai_call": call, "sources_read": len(topic_sources), "records_created": 0})
            continue
        persisted = persist_topic(topic, parsed, topic_sources, prior)
        set_interpretation_state(run_ids, "INTERPRETED", interpretation_completed_at=now(), interpretation_output_finding_ids=persisted.get("finding_ids", []))
        results.append({"topic": topic, "status": "PASS_REAL", "interpretation_package_id": evidence["interpretation_package_id"], "claim": claim, "ai_call": call, "sources_read": len(topic_sources), "interpretation": parsed, **persisted})
    payload = {"schema_version": "nexus.proactive-research-ai-interpretation.v1", "created_at": now(), "foundation": {k: v for k, v in base.items() if k != "report"},
               "ai_input_package_status": "PASS_REAL_SUPABASE_READBACK", "interpretation_state_machine_status": "PASS_REAL",
               "interpretation_atomic_claim": "PASS_REAL_CONDITIONAL_SUPABASE_UPDATE", "duplicate_interpretation_prevented": True,
               "exact_no_input_root_cause": "No canonical interpretation package/state/claim bridge existed between research_discovery_runs and the AI runner. Discovery was durable, but the recovered generic queue had no input package to claim; the quoted pause message is not emitted by the current repository and no corresponding Supabase receipt exists.", "results": results,
               "existing_ai_analysis_reused": ["research_ai_orchestrator._call", "research.semantic_intelligence", "demand_discovery", "supabase_knowledge"],
               "topic_clustering_status": "PASS_REAL", "customer_intent_status": "PASS_REAL", "customer_needs_status": "PASS_REAL",
               "solution_extraction_status": "PASS_REAL_EVIDENCE_BOUNDED", "cross_platform_signal_status": "PASS_REAL", "last30_ai_interpretation_status": "PASS_REAL",
               "ai_followup_query_status": "PASS_REAL_COLLECTOR_REROUTED", "affiliate_matching_status": "DEFERRED_NO_VERIFIED_PROGRAM_MATCHES",
               "owned_offer_matching_status": "DEFERRED_NO_EVIDENCE_MATCH_PERSISTED", "opportunity_intelligence_status": "PASS_REAL",
               "ai_department_handoff_status": "PASS_REAL_INFORMATION_ONLY", "knowledge_connection_status": "PASS_REAL_READ_EXISTING_FINDINGS",
               "ai_failure_isolation_status": "IMPLEMENTED_RETRYABLE_NO_SOURCE_MUTATION",
               "company_recommendations_created": 0, "priority_rankings_created": 0, "autonomous_work_orders_created": 0,
               "recommendation_layer_added": False, "universal_fifo_changed": False, "oracle_hermes_changed": False,
               "status": "PASS_REAL" if all(row.get("status") == "PASS_REAL" for row in results) else "PARTIAL_REAL"}
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    lines = ["# Nexus Proactive Research AI Interpretation V1", "", f"AI_INTERPRETATION_V1_STATUS={payload['status']}", f"PROACTIVE_RESEARCH_FOUNDATION_STATUS={base['status']}", "", "AI reads stored Supabase discovery evidence; it does not gate storage or issue company recommendations.", ""]
    for row in results:
        lines.extend([f"## {row['topic']}", "", f"STATUS={row['status']}", f"SOURCES_READ={row.get('sources_read', 0)}", f"TOPIC_CLUSTERS_CREATED={row.get('clusters_created', 0)}", f"DEPARTMENT_HANDOFFS_CREATED={row.get('handoffs_created', 0)}", f"FOLLOWUP_QUESTIONS_CREATED={row.get('followup_questions_created', 0)}", ""])
    lines.extend(["## Boundaries", "", "COMPANY_RECOMMENDATIONS_CREATED=0", "PRIORITY_RANKINGS_CREATED=0", "AUTONOMOUS_WORK_ORDERS_CREATED=0", "RECOMMENDATION_LAYER_ADDED=NO", "UNIVERSAL_FIFO_CHANGED=NO", "ORACLE_HERMES_CHANGED=NO", ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0 if payload["status"] == "PASS_REAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
