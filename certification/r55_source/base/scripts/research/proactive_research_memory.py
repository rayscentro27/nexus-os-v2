"""Deterministic memory and progression controls for proactive Research.

Current state uses Research State v2 and history is partitioned externally;
this module does not schedule work or create a parallel queue.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.parse
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Any

from nexus_agent_platform.governed import persistence
from research import research_state_v2 as state_v2

try:
    from social import _supabase as supabase
except Exception:  # pragma: no cover
    supabase = None

OBJECTIVES = ("CUSTOMER_NEEDS", "BUSINESS_OPPORTUNITIES", "AFFILIATE_OPPORTUNITIES", "TRADING_IDEAS",
              "TECHNOLOGY_DISCOVERY", "MARKETING_TRENDS", "SEO_OPPORTUNITIES", "FUNDING_AND_GRANTS",
              "COMPETITOR_INTELLIGENCE", "VIRAL_TREND_DISCOVERY")
REPEAT_REASONS = {"FRESHNESS_EXPIRED", "FAST_CHANGING_TOPIC", "NEW_EVENT", "DEPARTMENT_REQUEST", "NEW_EVIDENCE", "SCHEDULED_REFRESH"}
STOP_WORDS = {"a", "an", "and", "about", "for", "in", "of", "on", "the", "to", "with", "how", "what", "find", "search"}
REMOTE_MEMORY_CONTROL_FIELDS = (
    "memory_id", "memory_kind", "objective_id", "query_family", "recorded_at",
    "query_id:payload->>query_id", "event_id:payload->>event_id", "case_id:payload->>case_id",
    "query:payload->>query", "run_at:payload->>run_at", "created_at:payload->>created_at",
    "source_strategy_id:payload->>source_strategy_id", "result_identity:payload->>result_identity",
    "objective_key:payload->>objective_key", "case_schema_version:payload->>case_schema_version",
    "continue_research:payload->>continue_research",
    "objective:payload->>objective", "objective_family:payload->>objective_family",
    "business_or_nexus_goal:payload->>business_or_nexus_goal",
    "primary_question:payload->>primary_question",
    "saturation_state:payload->>saturation_state", "status:payload->>status",
    "close_candidate_after:payload->>close_candidate_after", "parent_objective_id:payload->>parent_objective_id",
    "objective_type:payload->>objective_type", "topic:payload->>topic",
    "department_request:payload->>department_request", "business_priority:payload->>business_priority",
    "last_useful_at:payload->>last_useful_at", "last_novel_result_at:payload->>last_novel_result_at",
    "results_seen:payload->>results_seen", "new_results:payload->>new_results",
    "duplicate_results:payload->>duplicate_results", "sources_seen:payload->>sources_seen",
    "findings_created:payload->>findings_created", "novel_findings:payload->>novel_findings",
    "open_questions:payload->open_questions", "result_ids:payload->result_ids",
)
REMOTE_MEMORY_CONTROL_KINDS = (
    "PROACTIVE_QUERY", "PROACTIVE_OBJECTIVE", "PROACTIVE_RESEARCH_CASE", "REPEAT_QUERY_SKIP",
)


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or now()).isoformat()


def query_tokens(query: str) -> set[str]:
    aliases = {"complaints": "problem", "complaint": "problem", "problems": "problem", "issues": "problem",
               "funding": "finance", "financing": "finance", "finances": "finance"}
    return {aliases.get(word, word) for word in re.findall(r"[a-z0-9]+", query.lower()) if word not in STOP_WORDS}


def query_family(query: str) -> str:
    tokens = query_tokens(query)
    normalized = sorted(tokens)
    return "qf_" + hashlib.sha256(" ".join(normalized).encode()).hexdigest()[:20]


def semantically_equivalent(a: str, b: str, threshold: float = .72) -> bool:
    left, right = query_tokens(a), query_tokens(b)
    return bool(left and right and len(left & right) / len(left | right) >= threshold)


def _latest(kind: str) -> list[dict[str, Any]]:
    rows = [r for r in _read_recent_states() if r.get("memory_kind") == kind]
    latest: dict[str, dict[str, Any]] = {}
    for row in rows:
        if kind == "PROACTIVE_QUERY": key = str(row.get("query_id") or "")
        elif kind == "PROACTIVE_OBJECTIVE": key = str(row.get("objective_id") or "")
        elif kind == "PROACTIVE_RESEARCH_CASE": key = str(row.get("case_id") or "")
        else: key = str(row.get("memory_id") or row.get("event_id") or row.get("query_id") or "")
        if key:
            prior = latest.get(key)
            stamp = str(row.get("recorded_at") or row.get("run_at") or row.get("created_at") or "")
            prior_stamp = str((prior or {}).get("recorded_at") or (prior or {}).get("run_at") or (prior or {}).get("created_at") or "")
            if prior is None or stamp >= prior_stamp:
                latest[key] = row
    return list(latest.values())


def _read_recent_collection(collection: str, max_bytes: int = 2_000_000, max_records: int = 20_000,
                            *, include_full_payload: bool = False) -> list[dict[str, Any]]:
    """Read current Research memory from the indexed store; other collections retain their own readers."""
    if collection == "research_runtime_states":
        kinds = ("RESEARCH_CASE", "PROACTIVE_RESEARCH_CASE") if include_full_payload else (
            "PROACTIVE_QUERY", "PROACTIVE_OBJECTIVE", "PROACTIVE_RESEARCH_CASE", "REPEAT_QUERY_SKIP")
        return state_v2.list_current(kinds=kinds, limit=min(max(1, int(max_records)), 20_000),
                                     include_payload=include_full_payload,
                                     max_bytes=max_bytes if not include_full_payload else min(max_bytes, 1_500_000))
    """Legacy bounded tail reader for non-Research collections only."""
    path = persistence.collection_path(collection)
    try:
        with path.open("rb") as handle:
            handle.seek(0, 2)
            size = handle.tell()
            handle.seek(max(0, size - max_bytes))
            raw = handle.read(max_bytes)
    except OSError:
        size, raw = 0, b""
    lines = raw.splitlines()
    if size > max_bytes and lines: lines = lines[1:]
    rows = deque(maxlen=max_records)
    for line in lines:
        try:
            value = json.loads(line)
            if isinstance(value, dict): rows.append(value)
        except (ValueError, TypeError):
            continue
    local = list(rows)
    return local


def _read_recent_states(max_bytes: int = 2_000_000, max_records: int = 20_000,
                        *, include_full_payload: bool = False) -> list[dict[str, Any]]:
    return _read_recent_collection("research_runtime_states", max_bytes=max_bytes, max_records=max_records,
                                   include_full_payload=include_full_payload)


def hydrate_memory(memory_id: str) -> dict[str, Any] | None:
    """Explicitly load one full proactive memory item for a detailed task."""
    if (os.environ.get("NEXUS_RESEARCH_CASE_READ_LOCAL_ONLY") in {"1", "true", "yes"}
            and not os.environ.get("NEXUS_CERTIFICATION_RESEARCH_STATE_ROOT")):
        return None
    return state_v2.lookup_case(str(memory_id)) if memory_id else None


def persist_state(state: dict[str, Any]) -> dict[str, Any]:
    record = {**state, "schema_version": "nexus.proactive-research-memory.v1", "recorded_at": iso()}
    # Case lifecycle updates must upsert by case identity.  Prioritizing the
    # parent objective here caused distinct cases and their follow-up/closure
    # states to collide in durable memory.
    stable_id = (record.get("case_id") if record.get("memory_kind") in
                 {"PROACTIVE_RESEARCH_CASE", "RESEARCH_CASE"} else None)
    if stable_id:
        record["memory_id"] = str(stable_id)
    else:
        record["memory_id"] = str(record.get("memory_id") or record.get("query_id") or record.get("objective_id") or record.get("event_id") or ("mem_" + hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()[:20]))
    return state_v2.persist_state(record)


def record_query(*, objective_id: str, objective_type: str, topic: str, query: str,
                 results_seen: int = 0, new_results: int = 0, duplicate_results: int = 0,
                 sources_seen: int = 0, findings_created: int = 0, novel_findings: int = 0,
                 open_questions: list[str] | None = None, next_query_direction: str = "",
                 result_ids: list[str] | None = None, repeat_reason: str = "",
                 source_strategy_id: str | None = None) -> dict[str, Any]:
    run_at = iso()
    row = {"memory_kind": "PROACTIVE_QUERY", "query_id": "qry_" + hashlib.sha256(f"{objective_id}:{query}:{run_at}".encode()).hexdigest()[:18],
           "objective_id": objective_id, "objective_type": objective_type.upper(), "topic": topic,
           "query": query, "query_family": query_family(query), "run_at": run_at,
           "results_seen": int(results_seen), "new_results": int(new_results), "duplicate_results": int(duplicate_results),
           "sources_seen": int(sources_seen), "findings_created": int(findings_created), "novel_findings": int(novel_findings),
           "open_questions": list(open_questions or []), "next_query_direction": next_query_direction,
           "source_strategy_id": source_strategy_id,
           "saturation_state": "ACTIVE", "last_novel_result_at": run_at if new_results or novel_findings else None,
           "result_ids": sorted(set(result_ids or [])), "repeat_reason": repeat_reason.upper()}
    same_family = [r for r in _latest("PROACTIVE_QUERY") if r.get("query_family") == row["query_family"]]
    row["saturation_state"] = saturation_state(same_family + [row])
    persist_state(row)
    return row


def query_guard(query: str, *, history: list[dict[str, Any]] | None = None, repeat_reason: str = "",
                freshness_hours: int = 24, at: datetime | None = None,
                source_strategy_id: str | None = None) -> dict[str, Any]:
    rows = history if history is not None else _latest("PROACTIVE_QUERY")
    family = query_family(query)
    prior = next((r for r in reversed(rows) if r.get("query_family") == family or semantically_equivalent(query, str(r.get("query", "")))), None)
    if not prior:
        return {"allowed": True, "reason": "FIRST_QUERY", "query_family": family}
    if source_strategy_id and prior.get("source_strategy_id") != source_strategy_id:
        return {"allowed": True, "reason": "SOURCE_STRATEGY_CHANGED",
                "query_family": family, "prior_query": prior.get("query"),
                "prior_strategy_id": prior.get("source_strategy_id"),
                "source_strategy_id": source_strategy_id}
    age = (at or now()) - datetime.fromisoformat(str(prior["run_at"]).replace("Z", "+00:00"))
    reason = repeat_reason.upper()
    allowed = reason in REPEAT_REASONS and (reason != "FRESHNESS_EXPIRED" or age >= timedelta(hours=freshness_hours))
    result = {"allowed": allowed, "reason": reason if allowed else "REPEATED_QUERY_SKIPPED",
              "query_family": family, "prior_query": prior.get("query"), "age_seconds": max(0, int(age.total_seconds()))}
    if not allowed:
        persist_state({"memory_kind": "REPEAT_QUERY_SKIP", "event_id": "skip_" + hashlib.sha256(f"{family}:{iso()}".encode()).hexdigest()[:16],
                       "query_family": family, "query": query, "run_at": iso(), "reason": result["reason"]})
    return result


def canonical_result_id(result: dict[str, Any]) -> str:
    url = str(result.get("canonical_url") or result.get("url") or "")
    if url:
        p = urllib.parse.urlsplit(url.strip())
        query = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
        url = urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urllib.parse.urlencode(query), ""))
        if "youtu.be/" in url or "youtube.com/watch" in url:
            parsed = urllib.parse.urlsplit(url)
            video_id = urllib.parse.parse_qs(parsed.query).get("v", [parsed.path.rsplit("/", 1)[-1]])[0]
            return "youtube:" + video_id
        return "url:" + url
    if result.get("youtube_video_id"): return "youtube:" + str(result["youtube_video_id"])
    if result.get("content_hash"): return "hash:" + str(result["content_hash"])
    if result.get("source_id"): return "source:" + str(result["source_id"])
    text = re.sub(r"\s+", " ", str(result.get("title", "")).strip().lower())
    return "title:" + hashlib.sha256(text.encode()).hexdigest()[:24]


def novelty_gate(result: dict[str, Any], *, known_ids: set[str] | None = None,
                 relevance: float = 0.0, value: float = 0.0, known_source: bool = False,
                 new_information: bool = False) -> dict[str, Any]:
    identity = canonical_result_id(result)
    known = known_ids or set()
    if identity in known: classification = "DUPLICATE"
    elif relevance < .35 or value < .2: classification = "LOW_VALUE"
    elif value >= .8 and relevance >= .7: classification = "NEW_HIGH_VALUE"
    elif known_source and new_information: classification = "KNOWN_SOURCE_NEW_INFORMATION"
    else: classification = "NEW_RELEVANT"
    return {"identity": identity, "classification": classification,
            "create_research_case": classification in {"NEW_HIGH_VALUE", "NEW_RELEVANT", "KNOWN_SOURCE_NEW_INFORMATION"},
            "create_notebook_workspace": False}


def known_research_identities(*, max_records_per_collection: int = 2000) -> set[str]:
    """Collect bounded duplicate keys from existing Research sources/findings/memory."""
    known: set[str] = set()
    for row in _read_recent_states(max_records=max_records_per_collection):
        if row.get("memory_kind") == "PROACTIVE_RESEARCH_CASE" and row.get("result_identity"):
            known.add(str(row["result_identity"]))
    for collection in ("alpha_content", "research_v2_sources", "research_notebooklm_findings"):
        for row in _read_recent_collection(collection, max_records=max_records_per_collection):
            for key in ("canonical_url", "source_url", "url"):
                if row.get(key): known.add(canonical_result_id({"url": row[key]}))
            for key in ("youtube_video_id", "video_id"):
                if row.get(key): known.add("youtube:" + str(row[key]))
            if row.get("content_hash"): known.add("hash:" + str(row["content_hash"]))
            if row.get("source_id"): known.add("source:" + str(row["source_id"]))
    if supabase is not None:
        try:
            if supabase.configured():
                for table, params in (("research_sources", "select=url,metadata&limit=500"),
                                      ("research_findings", "select=source_url,content_hash&limit=500")):
                    status, rows = supabase.rest("GET", f"{table}?{params}")
                    if status != 200 or not isinstance(rows, list): continue
                    for row in rows:
                        if row.get("url") or row.get("source_url"):
                            known.add(canonical_result_id({"url": row.get("url") or row.get("source_url")}))
                        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                        video_id = metadata.get("video_id") or row.get("video_id")
                        if video_id: known.add("youtube:" + str(video_id))
                        if row.get("content_hash"): known.add("hash:" + str(row["content_hash"]))
        except Exception:
            pass
    return known


def notebook_gate(novelty: dict[str, Any], *, case_id: str | None, workspace_useful: bool) -> bool:
    return bool(case_id and workspace_useful and novelty.get("create_research_case") and
                novelty.get("classification") in {"NEW_HIGH_VALUE", "NEW_RELEVANT", "KNOWN_SOURCE_NEW_INFORMATION"})


def process_discovery_result(result: dict[str, Any], *, objective_id: str, objective_type: str,
                             topic: str, known_ids: set[str] | None = None,
                             relevance: float = 0.0, value: float = 0.0,
                             known_source: bool = False, new_information: bool = False,
                             case_objective: dict[str, Any] | None = None,
                             existing_case_id: str | None = None) -> dict[str, Any]:
    """Novelty-check first; optionally attach a source to an objective-level case.

    Legacy callers retain source-scoped behavior. Objective-aware callers join
    evidence to one case whose identity is the research objective, not the URL.
    """
    if known_ids is None:
        known_ids = known_research_identities()
    decision = novelty_gate(result, known_ids=known_ids, relevance=relevance, value=value,
                            known_source=known_source, new_information=new_information)
    case = None
    if case_objective and decision["create_research_case"]:
        from research.research_case_engine import add_source, open_or_join_case
        spec = dict(case_objective)
        opened = open_or_join_case(
            objective=str(spec.get("objective") or topic),
            objective_family=str(spec.get("objective_family") or objective_type),
            business_or_nexus_goal=str(spec.get("business_or_nexus_goal") or objective_id),
            owner_department=str(spec.get("owner_department") or "RESEARCH"),
            primary_question=str(spec.get("primary_question") or topic),
            priority=int(spec.get("priority", 50)), signal=spec.get("signal"),
            case_id=existing_case_id, originating_goal_id=spec.get("originating_goal_id"),
            requires_ray=bool(spec.get("requires_ray", False)), force_existing=bool(existing_case_id))
        case = opened.get("case")
        if case:
            case = add_source(str(case["case_id"]), {**result, "source_class": result.get("source_class") or result.get("source_type") or "UNKNOWN"}).get("case", case)
            decision["case_identity_scope"] = "OBJECTIVE"
            decision["case_joined"] = bool(opened.get("joined"))
            decision["case_gate"] = opened.get("gate")
    if decision["create_research_case"]:
        if case is None and not case_objective:
            cid = "case_" + hashlib.sha256(f"{objective_id}:{decision['identity']}".encode()).hexdigest()[:18]
            case = {"memory_kind": "PROACTIVE_RESEARCH_CASE", "case_id": cid,
                    "objective_id": objective_id, "objective_type": objective_type.upper(),
                    "topic": topic, "result_identity": decision["identity"],
                    "classification": decision["classification"], "status": "OPEN",
                    "source_id": result.get("source_id"), "canonical_url": result.get("canonical_url") or result.get("url"),
                    "created_at": iso()}
            persist_state(case)
        elif case is None and case_objective:
            decision["create_research_case"] = False
            decision["case_open_blocker"] = "MAX_ACTIVE_DEEP_CASES_REACHED_OR_PROMISING_GATE_FAILED"
    decision["case"] = case
    decision["create_notebook_workspace"] = notebook_gate(decision, case_id=case.get("case_id") if case else None,
                                                           workspace_useful=bool(result.get("workspace_useful")))
    return decision


def next_query(*, previous_query: str, open_questions: list[str], topic: str,
               direction: str = "", finding_summary: str = "") -> str:
    if open_questions:
        candidate = f"{topic}: evidence answering {open_questions[0]}"
    elif direction:
        candidate = f"{topic}: {direction}"
    elif finding_summary:
        candidate = f"independent evidence and counterexamples for {finding_summary}"
    else:
        candidate = f"{topic}: customer evidence, competitors, and monetization"
    return candidate if not semantically_equivalent(candidate, previous_query, .9) else f"{topic}: stronger independent evidence and implementation examples"


def branch_objectives(parent_id: str, case_id: str, discovery: str, branch_types: list[str], *, depth: int = 0, max_depth: int = 2, max_branches: int = 3) -> list[dict[str, Any]]:
    if depth >= max_depth: return []
    return [{"objective_id": "obj_" + hashlib.sha256(f"{parent_id}:{kind}:{case_id}".encode()).hexdigest()[:18],
             "objective_type": kind.upper(), "topic": discovery, "parent_objective_id": parent_id,
             "parent_case_id": case_id, "depth": depth + 1, "status": "ACTIVE"}
            for kind in branch_types[:max_branches]]


def persist_branches(parent_id: str, case_id: str, discovery: str, branch_types: list[str], *, depth: int = 0) -> list[dict[str, Any]]:
    branches = branch_objectives(parent_id, case_id, discovery, branch_types, depth=depth)
    for branch in branches:
        persist_state({"memory_kind": "PROACTIVE_OBJECTIVE", **branch, "created_at": iso()})
    return branches


def productive_cycle(outcome: dict[str, Any]) -> bool:
    """A repeat-only search is not productive completion."""
    return bool({"NEW_RELEVANT_SOURCE", "NEW_FINDING", "NEW_RESEARCH_QUESTION", "NEW_OPPORTUNITY_SIGNAL",
                 "USEFUL_CROSS_CHECK", "DEPARTMENT_HANDOFF", "QUERY_FAMILY_SATURATED_WITH_EVIDENCE"}
                & {str(item).upper() for item in outcome.get("outcomes", [])})


def saturation_state(history: list[dict[str, Any]], *, min_runs: int = 3, at: datetime | None = None,
                     freshness_days: int = 30, revisit_reason: str = "") -> str:
    if revisit_reason.upper() in {"FRESHNESS_EXPIRED", "NEW_EVENT", "DEPARTMENT_REQUEST", "NEW_EVIDENCE"}: return "ACTIVE"
    rows = sorted(history, key=lambda r: str(r.get("run_at", "")))[-min_runs:]
    if len(rows) < min_runs: return "ACTIVE"
    all_ids = [set(r.get("result_ids", [])) for r in rows]
    overlap = sum(len(a & b) / max(1, len(a | b)) for a, b in zip(all_ids, all_ids[1:])) / max(1, len(all_ids)-1)
    rates = [(int(r.get("new_results", 0)) / max(1, int(r.get("results_seen", 0)))) for r in rows]
    finding_rates = [(int(r.get("novel_findings", 0)) / max(1, int(r.get("findings_created", 0)))) for r in rows]
    last = datetime.fromisoformat(str(rows[-1]["run_at"]).replace("Z", "+00:00"))
    if (overlap >= .7 and sum(rates)/len(rates) <= .2 and sum(finding_rates)/len(finding_rates) <= .2):
        return "SATURATED" if (at or now()) - last < timedelta(days=freshness_days) else "REVISIT_ELIGIBLE"
    return "ACTIVE"


def rotate_objective(objectives: list[dict[str, Any]], *, at: datetime | None = None) -> dict[str, Any] | None:
    candidates = [o for o in objectives if str(o.get("status", "ACTIVE")).upper() in {"ACTIVE", "READY"}]
    if not candidates: return None
    moment = at or now()
    def score(o: dict[str, Any]) -> float:
        last = o.get("last_useful_at")
        age_days = 30 if not last else min(30, (moment - datetime.fromisoformat(str(last).replace("Z", "+00:00"))).total_seconds()/86400)
        return float(o.get("business_priority", 0))*3 + len(o.get("open_questions", []))*2 + bool(o.get("department_request"))*5 + age_days + float(o.get("recent_novelty", 0))*4
    return max(candidates, key=score)


def create_objective(objective_type: str, topic: str, *, query: str = "", department_request: str = "", priority: int = 1) -> dict[str, Any]:
    oid = "obj_" + hashlib.sha256(f"{objective_type}:{topic}:{department_request}".encode()).hexdigest()[:18]
    row = {"memory_kind": "PROACTIVE_OBJECTIVE", "objective_id": oid, "objective_type": objective_type.upper(),
           "topic": topic, "query": query, "department_request": department_request,
           "business_priority": int(priority), "status": "ACTIVE", "created_at": iso(), "open_questions": []}
    persist_state(row)
    return row


def status_snapshot(*, at: datetime | None = None) -> dict[str, Any]:
    moment = at or now(); cutoff = moment - timedelta(hours=24)
    sources = [r for r in persistence.read_records("alpha_source_registry")
               if r.get("monitor_mode") == "NEW_CONTENT_ONLY" and r.get("processing_intent") == "CONTINUOUS"]
    sources = list({str(r.get("source_id")): r for r in sources if r.get("source_id")}.values())
    recent_states = _read_recent_states()
    queries = [r for r in recent_states if r.get("memory_kind") == "PROACTIVE_QUERY" and datetime.fromisoformat(str(r["run_at"]).replace("Z", "+00:00")) >= cutoff]
    families = {r.get("query_family") for r in queries}
    objectives = _latest("PROACTIVE_OBJECTIVE")
    branches = [r for r in objectives if r.get("parent_objective_id") and r.get("status") == "ACTIVE"]
    return {"DESIGNATED_SOURCES_ACTIVE": sum(bool(r.get("enabled", r.get("status") == "ACTIVE")) for r in sources),
            "DESIGNATED_SOURCES_CHECKED_LAST_24H": sum(bool((r.get("last_checked_at") or "") and datetime.fromisoformat(str(r["last_checked_at"]).replace("Z", "+00:00")) >= cutoff) for r in sources),
            "NEW_MONITORED_ITEMS_LAST_24H": sum(1 for r in sources if r.get("last_item_seen_at") and datetime.fromisoformat(str(r["last_item_seen_at"]).replace("Z", "+00:00")) >= cutoff),
            "PROACTIVE_OBJECTIVES_ACTIVE": sum(r.get("status") == "ACTIVE" for r in objectives),
            "PROACTIVE_QUERIES_LAST_24H": len(queries), "UNIQUE_QUERY_FAMILIES_LAST_24H": len(families),
            "REPEATED_QUERY_SKIPS_LAST_24H": sum(1 for r in recent_states if r.get("memory_kind") == "REPEAT_QUERY_SKIP" and datetime.fromisoformat(str(r["run_at"]).replace("Z", "+00:00")) >= cutoff), "NOVEL_RESULTS_LAST_24H": sum(int(r.get("new_results", 0)) for r in queries),
            "DUPLICATE_RESULTS_LAST_24H": sum(int(r.get("duplicate_results", 0)) for r in queries),
            "SATURATED_QUERY_FAMILIES": sum(r.get("saturation_state") == "SATURATED" for r in _latest("PROACTIVE_QUERY")),
            "RESEARCH_BRANCHES_OPEN": len(branches)}


def close_due_research_cases(*, at: datetime | None = None, limit: int = 50) -> dict[str, Any]:
    """Advance expired follow-up windows to CLOSE_CANDIDATE without deleting evidence."""
    current = at or now()
    cases = _latest("PROACTIVE_RESEARCH_CASE")
    candidates = []
    for row in cases:
        if row.get("status") != "FOLLOWUP_WINDOW":
            continue
        due = row.get("close_candidate_after")
        try:
            when = datetime.fromisoformat(str(due).replace("Z", "+00:00")) if due else None
        except ValueError:
            when = None
        if when and when <= current:
            candidates.append(row)
    closed = []
    for row in candidates[:max(0, int(limit))]:
        closed.append(persist_state({**row, "status": "CLOSE_CANDIDATE",
            "close_candidate_at": iso(current),
            "next_action": "REOPEN_IF_NEW_EVIDENCE_OR_CONFIRM_CASE_CLOSURE",
            "durable_findings_retained": True, "notebook_deletion_performed": False}))
    return {"status": "PASS", "checked": len(cases),
            "close_candidates_created": len(closed),
            "case_ids": [row.get("case_id") for row in closed]}
