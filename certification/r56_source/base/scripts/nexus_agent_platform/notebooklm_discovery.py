"""Governed NotebookLM web research discovery for durable Research jobs."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from nexus_agent_platform.provider_enforcement import execute
from nexus_agent_platform.resource_spend_governor import GovernanceDenied
from nexus_agent_platform.runtime.paths import nexus_research_state_path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_DIR = ROOT / "scripts" / "research"
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))


def _source_candidates(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in {"sources", "source_candidates", "discovered_sources", "results"} and isinstance(item, list):
                for row in item:
                    if isinstance(row, dict) and any(row.get(name) for name in ("url", "source_url", "link")):
                        found.append(row)
            else:
                found.extend(_source_candidates(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_source_candidates(item))
    unique: dict[str, dict[str, Any]] = {}
    for row in found:
        url = str(row.get("url") or row.get("source_url") or row.get("link") or "").strip()
        if url.startswith(("https://", "http://")):
            unique.setdefault(url, {"title": str(row.get("title") or row.get("name") or "")[:240],
                                    "url": url[:1000],
                                    "source_id": str(row.get("source_id") or row.get("id") or "")[:200],
                                    "description": str(row.get("description") or row.get("snippet") or row.get("summary") or "")[:1200]})
    return list(unique.values())[:30]


def _source_matches_research_subject(subject: str, source: dict[str, Any]) -> bool:
    """Require two distinctive subject tokens before recovering source ownership."""
    import re
    stop = {"custom", "business", "opportunity", "research", "customer", "owner", "owners"}
    def tokens(value: str) -> set[str]:
        found=set()
        for token in re.findall(r"[a-z0-9]{2,}",value.casefold()):
            if token in stop:
                continue
            found.add(token[:-1] if token.endswith("s") and len(token)>4 else token)
        return found
    subject_tokens=tokens(subject)
    identity=" ".join(str(source.get(key) or "") for key in ("title","url","source_url"))
    source_tokens=tokens(identity)
    return len(subject_tokens & source_tokens) >= 2


def _checkpoint_path(job_id: str) -> Path:
    return nexus_research_state_path("checkpoints", "notebooklm", f"{job_id}.json")


def _checkpoint(job_id: str) -> dict[str, Any]:
    path=_checkpoint_path(job_id)
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
        if value.get("job_id")!=job_id or not isinstance(value.get("steps"),dict):
            raise ValueError("checkpoint identity mismatch")
        return value
    except FileNotFoundError:
        return {"schema":"nexus.v5.notebooklm-operation-checkpoint.v1","job_id":job_id,"steps":{}}


def _save_checkpoint(job_id: str, value: dict[str, Any]) -> None:
    path=_checkpoint_path(job_id)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+".tmp")
    temp.write_text(json.dumps(value,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
    os.replace(temp,path)


def _ensure_policy_if_missing(store: Any, provider: str, service: str, job_type: str,
                              period: str, **policy: Any) -> dict[str, Any] | None:
    """Create only an absent exact scope; never rewrite or reopen a policy stop."""
    resolved = store.resolve_policy(provider, service, job_type, period)
    if resolved and not resolved.get("wildcard_fallback_used", False):
        return resolved
    store.ensure_policy(provider, service, job_type, period, **policy)
    return store.resolve_policy(provider, service, job_type, period)


DEDICATED_CANARY_JOB_ID = "job_bd4b15de2c051b08e0b041582437892d"
DEDICATED_CANARY_CASE_ID = "nexus_notebooklm_web_research_canary_20261012_gumqxlr"
DEDICATED_CANARY_POLICY_JOB_TYPE = "NEXUS_NOTEBOOKLM_CANARY_BD4B15DE2C051B08E0B041582437892D"
DEDICATED_CANARY_LIMITS = {
    "rate": {"requests": 6, "operations": 6, "window_seconds": 60},
    "usage": {"bytes": 1_200_000, "runtime_seconds": 1800, "cost": 0},
    "money": {"per_job": 0, "per_day": 0, "per_month": 0},
}


def classify_canary_answer_improvement(before: str, after: str, *,
                                       new_source_ids: set[str], answer_source_ids: set[str]) -> str:
    """Require cited new-source evidence, not answer length, for an improvement."""
    cited_new_source = bool(new_source_ids & answer_source_ids)
    if not cited_new_source:
        return "NO"
    import re
    evidence_pattern = re.compile(r"(?:\b\d+(?:\.\d+)?\s?%|\$\s?\d[\d,]*(?:\.\d+)?)")
    before_facts = {value.replace(" ", "") for value in evidence_pattern.findall(before)}
    after_facts = {value.replace(" ", "") for value in evidence_pattern.findall(after)}
    if after_facts - before_facts:
        return "YES"
    normalized_before = re.sub(r"\s+", " ", before).casefold()
    normalized_after = re.sub(r"\s+", " ", after).casefold()
    if normalized_after != normalized_before and any(
            marker in normalized_after for marker in ("partially verified", "unverified", "contradict", "official source")):
        return "PARTIAL"
    return "NO"


def ensure_dedicated_canary_policy(store: Any, *, job_id: str, case_id: str) -> dict[str, dict[str, Any]]:
    """Resolve a metered policy for this one existing canary, fail closed otherwise."""
    if job_id != DEDICATED_CANARY_JOB_ID or case_id != DEDICATED_CANARY_CASE_ID:
        raise PermissionError("DEDICATED_CANARY_SCOPE_NOT_AUTHORIZED")
    resolved: dict[str, dict[str, Any]] = {}
    for period in ("DAILY", "MONTHLY"):
        current = store.resolve_policy("NOTEBOOKLM", "research_discovery",
                                       DEDICATED_CANARY_POLICY_JOB_TYPE, period)
        if not current or current.get("wildcard_fallback_used", False):
            store.ensure_policy("NOTEBOOKLM", "research_discovery", DEDICATED_CANARY_POLICY_JOB_TYPE,
                period, autonomous_usage_allowed=True, autonomous_spend_allowed=False,
                soft_limits=DEDICATED_CANARY_LIMITS, hard_limits=DEDICATED_CANARY_LIMITS,
                concurrency_limit=1, resource_creation_limit=0,
                state="NORMAL", approval_required=False)
            current = store.resolve_policy("NOTEBOOKLM", "research_discovery",
                                          DEDICATED_CANARY_POLICY_JOB_TYPE, period)
        # A hard stop is left intact; the governor's normal recovery path owns
        # reopening. The canary must never turn a stop into a fresh allowance.
        if (not current or current.get("wildcard_fallback_used", False)
                or current.get("state") != "NORMAL"
                or not current.get("autonomous_usage_allowed")
                or current.get("autonomous_spend_allowed")):
            raise RuntimeError(f"CANARY_POLICY_NOT_NORMAL:{period}:{(current or {}).get('state', 'MISSING')}")
        limits = current.get("hard_limits") or {}
        if isinstance(limits, str):
            limits = json.loads(limits)
        if (int((limits.get("usage") or {}).get("bytes", 0)) > 1_200_000
                or float((limits.get("money") or {}).get("per_job", 0)) != 0):
            raise RuntimeError(f"CANARY_POLICY_OUTSIDE_BOUNDS:{period}")
        resolved[period] = current
    return resolved


FULL_RESEARCH_CANARY_LIMITS = {
    "rate": {"requests": 10, "operations": 10, "window_seconds": 60},
    "usage": {"bytes": 4_000_000, "runtime_seconds": 5_400, "cost": 0},
    "money": {"per_job": 0, "per_day": 0, "per_month": 0},
}


def full_research_canary_policy_job_type(job_id: str) -> str:
    suffix=hashlib.sha256(job_id.encode()).hexdigest()[:16].upper()
    return f"NEXUS_FULL_RESEARCH_CANARY_{suffix}"


def ensure_full_research_canary_policy(store: Any, *, job_id: str, case_id: str) -> dict[str, dict[str, Any]]:
    """Create/resolve a metered policy scoped to one full-research canary job."""
    if (not job_id.startswith("job_") or not case_id.startswith("nexus_full_research_canary_")
            or len(case_id)>100):
        raise PermissionError("FULL_RESEARCH_CANARY_SCOPE_INVALID")
    job_type=full_research_canary_policy_job_type(job_id)
    resolved={}
    for period in ("DAILY","MONTHLY"):
        current=store.resolve_policy("NOTEBOOKLM","research_discovery",job_type,period)
        if not current or current.get("wildcard_fallback_used",False):
            store.ensure_policy("NOTEBOOKLM","research_discovery",job_type,period,
                autonomous_usage_allowed=True,autonomous_spend_allowed=False,
                soft_limits=FULL_RESEARCH_CANARY_LIMITS,hard_limits=FULL_RESEARCH_CANARY_LIMITS,
                concurrency_limit=1,resource_creation_limit=0,state="NORMAL",approval_required=False)
            current=store.resolve_policy("NOTEBOOKLM","research_discovery",job_type,period)
        if (not current or current.get("wildcard_fallback_used",False)
                or current.get("state")!="NORMAL" or not current.get("autonomous_usage_allowed")
                or current.get("autonomous_spend_allowed")):
            raise RuntimeError(f"FULL_RESEARCH_CANARY_POLICY_NOT_NORMAL:{period}:{(current or {}).get('state','MISSING')}")
        limits=current.get("hard_limits") or {}
        if isinstance(limits,str): limits=json.loads(limits)
        if (int((limits.get("usage") or {}).get("bytes",0))>4_000_000
                or float((limits.get("money") or {}).get("per_job",0))!=0):
            raise RuntimeError(f"FULL_RESEARCH_CANARY_POLICY_OUTSIDE_BOUNDS:{period}")
        resolved[period]=current
    return resolved


def execute_discovery(job, payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("query")
    notebook_id = payload.get("notebook_id")
    if not isinstance(query, str) or not query.strip() or len(query) > 700:
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_QUERY_CONTRACT_INVALID"}
    if not isinstance(notebook_id, str) or len(notebook_id) < 20 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in notebook_id):
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_NOTEBOOK_ID_INVALID"}
    try:
        from research.notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter
        from research.notebooklm_research_adapter import _ensure_research_notebooklm_policy, RESEARCH_GOVERNOR_JOB_TYPE
        _ensure_research_notebooklm_policy()
        adapter = NotebookLMResearchAdapter(AdapterConfig(profile="default"))
        raw = execute(
            "NOTEBOOKLM", "research_discovery", "OWNER_ASSIGNED_WEB_RESEARCH",
            {"requests": 1, "operations": 1, "runtime_seconds": 180,
             "bytes": 200000, "billable": False, "cost": 0.0},
            lambda: adapter._run_json(["research", "discover", "-n", notebook_id, "--json", query],
                                      stage="source_add", timeout=180,
                                      failure_code="NOTEBOOK_RESEARCH_DISCOVERY_FAILED"),
            job_id=job.job_id, job_type=RESEARCH_GOVERNOR_JOB_TYPE,
            project_id=str(payload.get("project_id") or "NEXUS"),
            correlation_id=job.correlation_id,
            purpose=f"owner-research-discovery:{job.job_id}")
    except Exception as exc:
        if isinstance(exc, GovernanceDenied) and exc.state in {"HARD_STOP", "THROTTLED"}:
            return {"status":"WAITING_RESOURCE_WINDOW","reason":exc.code,
                    "resource":"NOTEBOOKLM","capability":"research_discovery",
                    "policy_state":exc.state,"resume_condition":"NOTEBOOKLM_POLICY_NORMAL",
                    "checkpoint_preserved":True}
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_DISCOVERY_EXECUTION_FAILED",
                "error_summary": f"{type(exc).__name__}:{str(exc)[:220]}"}
    sources = _source_candidates(raw)
    if not sources:
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_DISCOVERY_RETURNED_NO_CITED_SOURCES",
                "error_summary": "Discovery completed without a source URL in its structured response."}
    overview = str(raw.get("overview") or raw.get("summary") or raw.get("report") or "")[:12000] if isinstance(raw, dict) else ""
    artifact = {
        "schema": "nexus.v5.notebooklm-discovery.v1",
        "project_id": payload.get("project_id"), "campaign_id": payload.get("campaign_id"),
        "correlation_id": job.correlation_id, "job_id": job.job_id, "department": "RESEARCH",
        "notebook_id": notebook_id, "query": query, "overview": overview,
        "sources": sources, "source_count": len(sources), "data_class": "PUBLIC_RESEARCH",
        "incremental_cash_spend_usd": 0, "provider": "NOTEBOOKLM",
    }
    artifact["sha256"] = hashlib.sha256(json.dumps(artifact, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    target = nexus_research_state_path("runtime", "notebooklm_discovery", f"{job.job_id}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"status": "COMPLETED", "provider": "NOTEBOOKLM", "notebook_id": notebook_id,
            "source_count": len(sources), "artifact_ref": str(target),
            "artifact_sha256": artifact["sha256"], "sources": sources, "overview": overview}


def _rows(value: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        rows=value.get(key)
        if isinstance(rows,list): return [row for row in rows if isinstance(row,dict)]
    return []


def _find_run_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("research_run_id", "run_id", "task_id"):
            candidate=value.get(key)
            if isinstance(candidate,str) and candidate.strip(): return candidate.strip()
        for item in value.values():
            found=_find_run_id(item)
            if found: return found
    elif isinstance(value,list):
        for item in value:
            found=_find_run_id(item)
            if found: return found
    return None


def execute_import_and_synthesize(job, payload: dict[str, Any]) -> dict[str, Any]:
    """Import one bounded NotebookLM discovery run and ask only its new sources."""
    operation=payload.get("operation")
    query=payload.get("query") or ("Read the source list for V5 research reconciliation." if operation=="LIST_SOURCES" else None)
    notebook_id=payload.get("notebook_id")
    if not isinstance(query,str) or not query.strip() or len(query)>900:
        return {"status":"BLOCKED","reason":"NOTEBOOKLM_FOLLOWUP_QUERY_INVALID"}
    if not isinstance(notebook_id,str) or len(notebook_id)<20 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in notebook_id):
        return {"status":"BLOCKED","reason":"NOTEBOOKLM_NOTEBOOK_ID_INVALID"}
    try:
        from research.notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter
        from research.notebooklm_research_adapter import _ensure_research_notebooklm_policy, RESEARCH_GOVERNOR_JOB_TYPE
        _ensure_research_notebooklm_policy()
        from nexus_agent_platform.provider_enforcement import execute
        adapter=NotebookLMResearchAdapter(AdapterConfig(profile="default"))
        provider_job_type=RESEARCH_GOVERNOR_JOB_TYPE
        def call(action: str, args: list[str], timeout: int, runtime: int) -> Any:
            checkpoint=_checkpoint(job.job_id)
            if action in checkpoint["steps"]:
                return checkpoint["steps"][action]
            result=execute("NOTEBOOKLM","research_discovery",action,
                {"requests":1,"operations":1,"runtime_seconds":runtime,"bytes":100000,
                 "billable":False,"cost":0.0},
                lambda: adapter._run_json(args,stage="source_add",timeout=timeout,
                                          failure_code="NOTEBOOK_RESEARCH_DISCOVERY_FAILED"),
                job_id=job.job_id,job_type=provider_job_type,
                project_id=str(payload.get("project_id") or "NEXUS"),
                correlation_id=job.correlation_id,
                purpose=f"{job.job_id}:{action}")
            checkpoint["steps"][action]=result
            checkpoint["last_completed_step"]=action
            _save_checkpoint(job.job_id,checkpoint)
            return result
        if payload.get("operation")=="LIST_SOURCES":
            raw_sources=call("NOTEBOOKLM_SOURCE_LIST_RECONCILIATION",
                             ["source","list","-n",notebook_id,"--json"],60,60)
            rows=_rows(raw_sources,"sources")
            safe_sources=[]
            for row in rows:
                source_id=str(row.get("id") or row.get("source_id") or row.get("sourceId") or "")
                safe_sources.append({"source_id":source_id[:200],
                    "title":str(row.get("title") or row.get("name") or "")[:240],
                    "url":str(row.get("url") or row.get("source_url") or row.get("sourceUrl") or "")[:1000],
                    "status":str(row.get("status") or row.get("indexing_status") or "UNKNOWN")[:40]})
            artifact={"schema":"nexus.v5.notebooklm-source-list.v1","notebook_id":notebook_id,
                      "job_id":job.job_id,"correlation_id":job.correlation_id,"sources":safe_sources,
                      "source_count":len(safe_sources)}
            artifact["sha256"]=hashlib.sha256(json.dumps(artifact,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
            target=nexus_research_state_path("runtime", "notebooklm_sources", f"{job.job_id}.json")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
            return {"status":"COMPLETED","notebook_id":notebook_id,"source_count":len(safe_sources),
                    "source_ids":[row["source_id"] for row in safe_sources if row["source_id"]],
                    "artifact_ref":str(target),"artifact_sha256":artifact["sha256"]}
        existing_checkpoint=_checkpoint(job.job_id)
        recovered_prior_import=(job.job_id=="job_v5_research_source_review_20261010"
            and job.attempt_count>1 and (not existing_checkpoint["steps"]
                or "NOTEBOOKLM_SOURCE_LIST_RESUME_RECONCILIATION" in existing_checkpoint["steps"]))
        if recovered_prior_import:
            # The first worker attempt completed source-list, status, and import
            # calls before the daily circuit opened, but it predated step-level
            # checkpoint persistence. Reconcile current NotebookLM sources to
            # the already-persisted public discovery artifact, then continue
            # with synthesis. Never repeat the import blindly.
            discovery_path=ROOT/"reports/certification/v5/research/job_e33989d3e27e4dc89b1c976aabd9d5da_notebooklm_discovery.json"
            discovery=json.loads(discovery_path.read_text(encoding="utf-8"))
            known_urls={str(row.get("url") or "").strip() for row in discovery.get("sources",[])
                        if isinstance(row,dict) and row.get("url")}
            after=call("NOTEBOOKLM_SOURCE_LIST_RESUME_RECONCILIATION",
                       ["source","list","-n",notebook_id,"--json"],60,60)
            after_rows=_rows(after,"sources")
            imported_rows=[row for row in after_rows
                if str(row.get("url") or row.get("source_url") or row.get("sourceUrl") or "").strip() in known_urls]
            if not imported_rows:
                return {"status":"BLOCKED","reason":"PRIOR_NOTEBOOKLM_IMPORT_NOT_VISIBLE_IN_SOURCE_RECONCILIATION",
                    "error_summary":"The previous import was not repeated; no matching imported sources were visible to synthesize."}
            run_id=None
            imported={"recovered_without_replay":True,"reconciliation_ref":str(discovery_path.relative_to(ROOT))}
        else:
            before=call("NOTEBOOKLM_SOURCE_LIST_BEFORE",["source","list","-n",notebook_id,"--json"],60,60)
            status=call("NOTEBOOKLM_RESEARCH_STATUS",["research","status","-n",notebook_id,"--json"],60,60)
            run_id=_find_run_id(status)
            if not run_id:
                return {"status":"BLOCKED","reason":"NOTEBOOKLM_RESEARCH_RUN_ID_NOT_RESOLVED",
                        "error_summary":"NotebookLM status returned no research run identifier."}
            imported=call("NOTEBOOKLM_RESEARCH_IMPORT",["research","import","-n",notebook_id,
                          "--run-id",run_id,"--max-sources","10","--json"],300,180)
            after=call("NOTEBOOKLM_SOURCE_LIST_AFTER",["source","list","-n",notebook_id,"--json"],60,60)
            before_ids={str(row.get("id") or row.get("source_id") or "") for row in _rows(before,"sources")}
            after_rows=_rows(after,"sources")
            imported_rows=[row for row in after_rows if str(row.get("id") or row.get("source_id") or "") not in before_ids]
        imported_ids=[str(row.get("id") or row.get("source_id") or "") for row in imported_rows]
        imported_ids=[source_id for source_id in imported_ids if source_id]
        if not imported_ids:
            return {"status":"BLOCKED","reason":"NOTEBOOKLM_IMPORT_CREATED_NO_NEW_SOURCE_IDS",
                    "run_id":run_id,"error_summary":"The import did not add identifiable new source IDs; no synthesis was asked."}
        ask_args=["ask","-n",notebook_id,"--json"]
        for source_id in imported_ids[:10]: ask_args.extend(["-s",source_id])
        ask_args.extend(["--prompt-file","-"])
        # The CLI reads stdin for a prompt file of '-', while subprocess input
        # remains bounded and avoids shell quoting/multiline ambiguity.
        prompt_path=nexus_research_state_path("runtime", "notebooklm_prompts", f"{job.job_id}.txt")
        prompt_path.write_text(query,encoding="utf-8")
        try:
            ask_args[-1]=str(prompt_path)
            answer=call("NOTEBOOKLM_SOURCE_SCOPED_SYNTHESIS",ask_args,360,300)
        finally:
            prompt_path.unlink(missing_ok=True)
        sources=[]
        for row in imported_rows:
            sources.append({"source_id":str(row.get("id") or row.get("source_id") or ""),
                            "title":str(row.get("title") or row.get("name") or "")[:240],
                            "url":str(row.get("url") or row.get("source_url") or "")[:1000],
                            "status":str(row.get("status") or row.get("indexing_status") or "UNKNOWN")[:40]})
        turn=adapter._turn_receipt(notebook_id,query,answer) if isinstance(answer,dict) and answer.get("answer") else {}
        artifact={"schema":"nexus.v5.notebooklm-research-synthesis.v1","project_id":payload.get("project_id"),
            "campaign_id":payload.get("campaign_id"),"correlation_id":job.correlation_id,"job_id":job.job_id,
            "department":"RESEARCH","notebook_id":notebook_id,"research_run_id":run_id,
            "source_ids":imported_ids,"sources":sources,"question":query,"answer":turn.get("answer"),
            "source_references":turn.get("references",[]),"notebooklm_response_id":turn.get("response_reference"),
            "conversation_id":turn.get("conversation_id"),"confidence":"NOTEBOOKLM_SOURCE_GROUNDED_RESPONSE",
            "source_import_result":imported,"provider":"NOTEBOOKLM","incremental_cash_spend_usd":0}
        artifact["sha256"]=hashlib.sha256(json.dumps(artifact,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        target=nexus_research_state_path("runtime", "notebooklm_source_synthesis", f"{job.job_id}.json")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        return {"status":"COMPLETED","provider":"NOTEBOOKLM","notebook_id":notebook_id,
                "research_run_id":run_id,"source_ids":imported_ids,"source_count":len(imported_ids),
                "notebooklm_response_id":artifact["notebooklm_response_id"],
                "artifact_ref":str(target),"artifact_sha256":artifact["sha256"],
                "answer":artifact["answer"],"source_references":artifact["source_references"],
                "checkpoint_ref":str(_checkpoint_path(job.job_id)),
                "cash_spend_usd":0}
    except Exception as exc:
        if isinstance(exc, GovernanceDenied) and exc.state in {"HARD_STOP", "THROTTLED"}:
            return {"status":"WAITING_RESOURCE_WINDOW","reason":exc.code,
                    "resource":"NOTEBOOKLM","capability":"research_discovery",
                    "policy_state":exc.state,"resume_condition":"NOTEBOOKLM_POLICY_NORMAL",
                    "checkpoint_preserved":True}
        return {"status":"BLOCKED","reason":"NOTEBOOKLM_IMPORT_SYNTHESIS_FAILED",
                "error_summary":f"{type(exc).__name__}:{str(exc)[:240]}"}


def execute_runtime_canary(job, payload: dict[str, Any]) -> dict[str, Any]:
    """Exercise actual NotebookLM notebook, source, indexing, Q&A and history."""
    import time
    from datetime import datetime, timezone
    from research.notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter

    case_id = str(payload.get("case_id") or "")
    source_url = str(payload.get("source_url") or "")
    source_title = str(payload.get("source_title") or "")
    question = str(payload.get("question") or "")
    if (not case_id.startswith("nexus_runtime_canary_") or not source_url.startswith("https://")
            or not question or len(question) > 500):
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_RUNTIME_CANARY_CONTRACT_INVALID"}
    adapter = NotebookLMResearchAdapter(AdapterConfig(profile="default"))
    from research.notebooklm_research_adapter import _ensure_research_notebooklm_policy, RESEARCH_GOVERNOR_JOB_TYPE
    _ensure_research_notebooklm_policy()
    policy_job_type = RESEARCH_GOVERNOR_JOB_TYPE

    checkpoint_path = nexus_research_state_path("certification", "notebooklm_runtime_canaries", f"{job.job_id}.json")
    try:
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        checkpoint = {"schema_version": "nexus.notebooklm-runtime-checkpoint.v1", "job_id": job.job_id, "steps": {}}
    if checkpoint.get("job_id") != job.job_id or not isinstance(checkpoint.get("steps"), dict):
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_RUNTIME_CHECKPOINT_INVALID"}

    def save_step(action: str, value: Any) -> None:
        checkpoint["steps"][action] = value
        checkpoint["updated_at"] = datetime.now(timezone.utc).isoformat()
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        temp = checkpoint_path.with_suffix(".tmp")
        temp.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        temp.replace(checkpoint_path)

    def governed(action: str, operation, *, requests: int = 1, bytes_estimate: int = 20000,
                 runtime: int = 120):
        if action in checkpoint["steps"]:
            return checkpoint["steps"][action]
        action_started = time.monotonic()
        value = execute("NOTEBOOKLM", "research_discovery", action,
            {"requests": requests, "operations": requests, "runtime_seconds": runtime,
             "bytes": bytes_estimate, "billable": False, "cost": 0.0}, operation,
            job_id=job.job_id, job_type=policy_job_type, project_id="NEXUS_CORE_RUNTIME",
            correlation_id=job.correlation_id,
            purpose=f"runtime-canary:{job.job_id}:run-{os.environ.get('NEXUS_DURABLE_EXECUTION_ID', job.attempt_count)}:{action}",
            actual_usage=lambda _result: {"runtime_seconds": max(1, round(time.monotonic() - action_started))})
        save_step(action, value)
        return value

    started = time.monotonic()
    observed_at = datetime.now(timezone.utc).isoformat()
    try:
        if payload.get("reuse_existing_notebook_only") is True:
            notebook_rows = governed("NEXUS_RUNTIME_NOTEBOOK_LOOKUP", adapter.notebooks,
                                     requests=1, bytes_estimate=40000, runtime=30)
            expected_title = f"Nexus Research Case {case_id}"
            match = next((row for row in notebook_rows if str(row.get("title") or "") == expected_title), None)
            if not match or not match.get("id"):
                return {"status":"BLOCKED","reason":"CANARY_NOTEBOOK_NOT_FOUND_NO_CREATE"}
            notebook = {"notebook_id":match["id"],"title":expected_title,"created":False,
                        "pool_id":"case:"+case_id,"case_id":case_id,"max_sources":5}
        else:
            notebook = governed("NEXUS_RUNTIME_NOTEBOOK_RESOLVE",
                lambda: adapter.resolve_case_notebook(case_id, title=source_title, max_sources=2, timeout_seconds=30),
                requests=2, bytes_estimate=40000, runtime=30)
        notebook_id = str(notebook.get("notebook_id") or "")
        if not notebook_id:
            return {"status": "BLOCKED", "reason": "NOTEBOOKLM_RUNTIME_NOTEBOOK_ID_MISSING"}
        current_sources = governed("NEXUS_RUNTIME_SOURCE_LIST",
            lambda: adapter.sources(notebook_id, timeout_seconds=30), bytes_estimate=20000, runtime=30)
        source = adapter.find_existing_source(current_sources,
            video_id=adapter.video_id_of(source_url), title=source_title)
        if source is None:
            source = governed("NEXUS_RUNTIME_SOURCE_ADD",
                lambda: adapter.add_source(notebook_id, source_url, video_title=source_title),
                bytes_estimate=40000, runtime=240)
        source_id = str(source.get("id") or source.get("source_id") or "")
        if not source_id:
            return {"status": "BLOCKED", "reason": "NOTEBOOKLM_RUNTIME_SOURCE_ID_MISSING"}
        indexed = governed("NEXUS_RUNTIME_SOURCE_INDEX",
            lambda: adapter.wait_for_source(notebook_id, source_id, timeout_seconds=300),
            bytes_estimate=12000, runtime=300)
        answer = governed("NEXUS_RUNTIME_SOURCE_QUESTION",
            lambda: adapter.ask_source_scoped(notebook_id, source_id, question, timeout_seconds=120),
            bytes_estimate=50000, runtime=120)
        visible = governed("NEXUS_RUNTIME_VISIBLE_TURN_VERIFY",
            lambda: adapter.verify_visible_turn(notebook_id, question, str(answer.get("answer") or "")),
            bytes_estimate=30000, runtime=30)
        completion_contract = None
        if payload.get("run_completion_contract") is True:
            from research import research_case_engine as cases
            # The canary is an explicit mission-research workflow. Persist its
            # purpose/domain classification on the existing isolated case so
            # the contract runner selects its registered contract
            # deterministically rather than falling back to a legacy playbook.
            requested_purpose = str(payload.get("research_purpose") or "").upper()
            requested_domain = str(payload.get("research_domain") or "").upper()
            if requested_purpose or requested_domain:
                from research.notebook_completion_contracts import classify_research, select_contract
                resolution = classify_research(objective=str(payload.get("research_objective") or
                    "Bounded public pricing source test; process canary only."),
                    research_purpose=requested_purpose or None, research_domain=requested_domain or None)
                if resolution.get("status") != "RESOLVED":
                    return {"status":"BLOCKED","reason":"CANARY_RESEARCH_CONTRACT_CLASSIFICATION_INVALID"}
                selected_contract = select_contract(resolution["research_purpose"], resolution["research_domain"])
                case = cases.get_case(case_id)
                if not case:
                    return {"status":"BLOCKED","reason":"CANARY_RESEARCH_CASE_NOT_FOUND"}
                if ((case.get("research_purpose") and case.get("research_purpose") != resolution["research_purpose"])
                        or (case.get("research_domain") and case.get("research_domain") != resolution["research_domain"])):
                    return {"status":"BLOCKED","reason":"CANARY_RESEARCH_CONTRACT_CASE_MISMATCH"}
                if not case.get("research_purpose") or not case.get("research_domain"):
                    cases._save(case,"RESEARCH_CONTRACT_CLASSIFIED",
                        research_purpose=resolution["research_purpose"],research_domain=resolution["research_domain"],
                        objective_family="BUSINESS_OPPORTUNITIES",
                        notebook_contract_id=selected_contract["contract_id"])
            cases.bind_notebook_workspace(case_id, notebook)
            cases.add_source(case_id, {"source_id":source_id,"notebook_source_id":source_id,
                "url":source_url,"title":source_title,"source_class":"PUBLIC_SOURCE",
                "notebook_id":notebook_id,"evidence_status":"UNVERIFIED",
                "extraction_status":"NOTEBOOKLM_CANARY_SOURCE_VISIBLE"})
            contract_result = checkpoint["steps"].get("NEXUS_RUNTIME_COMPLETION_CONTRACT")
            prior_contract_verification=(contract_result or {}).get("verification") or {}
            if (not contract_result or
                    (not prior_contract_verification.get("complete") and not (contract_result or {}).get("needle_job"))):
                from research.notebook_playbook_runner import run_case_playbook
                raw_contract_result = run_case_playbook(case_id, adapter=adapter, source_work_id=job.job_id,
                    ask_followup=not bool(payload.get("bounded_scope_note")),
                    bounded_scope_note=str(payload.get("bounded_scope_note") or "") or None)
                contract_result = {key:raw_contract_result.get(key) for key in (
                    "ok","receipt_id","verification","needle_job","next_research_action")
                    if key in raw_contract_result}
                save_step("NEXUS_RUNTIME_COMPLETION_CONTRACT",contract_result)
            contract_state = __import__("research.notebook_completion_contracts", fromlist=["load_state"]).load_state(case_id=case_id) or {}
            if str(contract_state.get("notebook_id") or "") != notebook_id:
                return {"status":"BLOCKED","reason":"CANARY_COMPLETION_NOTEBOOK_ID_MISMATCH"}
            completion_contract = {
                "contract_id":contract_state.get("contract_id"),
                "research_purpose":contract_state.get("research_purpose"),
                "research_domain":contract_state.get("research_domain"),
                "notebook_id":notebook_id,
                "verification_status":contract_state.get("verification_status"),
                "required_question_count":len([row for row in contract_state.get("required_questions",[]) if row.get("required")]),
                "asked_question_count":sum(bool(row.get("asked")) for row in contract_state.get("required_questions",[]) if row.get("required")),
                "research_receipt_id":contract_result.get("receipt_id"),
                "needle_job_id":(contract_result.get("needle_job") or {}).get("job_id"),
                "mechanical_complete":bool((contract_result.get("verification") or {}).get("complete")),
                "compact_handoff":bool(contract_state.get("handoff_package")),
                "no_full_notebook_mirror_to_supabase":True,
            }
            if not completion_contract["needle_job_id"]:
                return {"status":"BLOCKED","reason":"NOTEBOOK_COMPLETION_DID_NOT_QUEUE_NEEDLE",
                        "completion_contract":completion_contract}
    except Exception as exc:
        if isinstance(exc, GovernanceDenied) and exc.state in {"HARD_STOP", "THROTTLED"}:
            resource_policy_wait = exc.code in {"POLICY_DENIED", "BUDGET_HARD_LIMIT", "RATE_LIMIT", "CONCURRENCY_LIMIT"}
            return {"status": "WAITING_RESOURCE_WINDOW", "reason": exc.code,
                    "resource": "NOTEBOOKLM", "capability": "research_discovery",
                    "policy_state": exc.state, "provider": "NOTEBOOKLM",
                    "service": "research_discovery", "policy_job_type": policy_job_type,
                    "budget_period": "DAILY",
                    "resume_condition": "RESOURCE_POLICY_NORMAL" if resource_policy_wait else "JOB_BUDGET_REPAIRED",
                    "checkpoint_preserved": True}
        return {"status": "BLOCKED", "reason": "NOTEBOOKLM_RUNTIME_CANARY_FAILED",
                "error_summary": f"{type(exc).__name__}:{str(exc)[:220]}"}
    artifact = {
        "schema_version": "nexus.notebooklm-runtime-canary.v1", "job_id": job.job_id,
        "department": "RESEARCH", "executing_component": "NEXUS_RESEARCH",
        "notebook_id": notebook_id, "notebook_title": notebook.get("title"),
        "notebook_created": notebook.get("created"), "source_id": source_id,
        "source_url": source_url, "source_index_status": indexed.get("status"),
        "question": question, "answer": answer.get("answer"),
        "answer_reference": answer.get("response_reference"), "visible_turn": visible,
        "profile": "default", "incremental_cash_spend_usd": 0,
        "latency_seconds": round(time.monotonic() - started, 3), "observed_at": observed_at,
        "completion_contract":completion_contract,
    }
    artifact["sha256"] = hashlib.sha256(json.dumps(artifact, sort_keys=True,
        ensure_ascii=False, default=str).encode()).hexdigest()
    target = nexus_research_state_path("certification", "notebooklm_runtime_canaries", f"{job.job_id}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return {"status": "COMPLETED", "provider": "NOTEBOOKLM", "job_id": job.job_id,
            "notebook_id": notebook_id, "source_id": source_id,
            "source_index_status": indexed.get("status"), "visible_turn": True,
            "latency_seconds": artifact["latency_seconds"],
            "completion_contract":completion_contract,
            "artifact_ref": str(target), "artifact_sha256": artifact["sha256"]}


def execute_dedicated_research_canary(job, payload: dict[str, Any]) -> dict[str, Any]:
    """Run one small source→gap→web→same-notebook research mechanism canary.

    It uses the existing durable Research worker, NotebookLM adapter, provider
    boundary, and job receipt. It intentionally does not run the full Notebook
    Completion Contract or queue Needle/downstream work.
    """
    import re
    import time
    from datetime import datetime, timezone
    from research.notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter
    from research.research_notebook_ownership import (
        DEDICATED_CANARY_FULL_CONTRACT, DEDICATED_CANARY_NEEDLE, DEDICATED_CANARY_V6,
        bounded_source_add_plan, classify_source_origin, dedicated_title,
        find_dedicated_notebook, promotion_evidence_gap, source_delta, subject_key,
        validate_feeder_promotion, web_gap_query,
    )

    case_id = str(payload.get("case_id") or "")
    source_url = str(payload.get("source_url") or "")
    source_title = str(payload.get("source_title") or "")
    feeder_notebook_id=str(payload.get("feeder_notebook_id") or "")
    feeder_source_id=str(payload.get("feeder_source_id") or "")
    subject = str(payload.get("research_subject") or "")
    if (not source_url.startswith("https://www.youtube.com/watch?v=")
            or not source_title or len(subject) > 180
            or len(feeder_notebook_id)<20 or not feeder_source_id):
        return {"status":"BLOCKED","reason":"DEDICATED_RESEARCH_CANARY_INPUT_INVALID"}
    # This is a one-job exception to the legacy shared NotebookLM byte scope.
    # The exact durable job and case are pinned here; ordinary Research keeps
    # its existing 500,000-byte policy and all operations remain metered.
    if job.job_id != DEDICATED_CANARY_JOB_ID or case_id != DEDICATED_CANARY_CASE_ID:
        return {"status": "BLOCKED", "reason": "DEDICATED_CANARY_SCOPE_NOT_AUTHORIZED"}
    adapter = NotebookLMResearchAdapter(AdapterConfig(profile="default"))
    from research.notebooklm_research_adapter import _ensure_research_notebooklm_policy
    _ensure_research_notebooklm_policy()
    from nexus_agent_platform.resource_spend_governor import default_store as governor_store
    from nexus_agent_platform.provider_enforcement import execute
    governor = governor_store()
    try:
        ensure_dedicated_canary_policy(governor, job_id=job.job_id, case_id=case_id)
    except PermissionError:
        return {"status": "BLOCKED", "reason": "DEDICATED_CANARY_SCOPE_NOT_AUTHORIZED"}
    except RuntimeError as exc:
        return {"status": "WAITING_RESOURCE_WINDOW", "reason": str(exc), "resource": "NOTEBOOKLM",
                "policy_state": "HARD_STOP_OR_INVALID", "checkpoint_preserved": True}
    policy_job_type = DEDICATED_CANARY_POLICY_JOB_TYPE
    checkpoint_path = nexus_research_state_path("certification", "notebooklm_dedicated_research_canaries", f"{job.job_id}.json")
    try:
        checkpoint=json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError,ValueError,TypeError):
        checkpoint={"schema_version":"nexus.notebooklm.dedicated-research-canary.v1",
                    "job_id":job.job_id,"source_url":source_url,"feeder_source_id":feeder_source_id,"steps":{}}
    if (checkpoint.get("job_id")!=job.job_id or checkpoint.get("source_url")!=source_url
            or checkpoint.get("feeder_source_id")!=feeder_source_id or not isinstance(checkpoint.get("steps"),dict)):
        return {"status":"BLOCKED","reason":"DEDICATED_RESEARCH_CANARY_CHECKPOINT_INVALID"}
    existing_notebook = checkpoint["steps"].get("DEDICATED_NOTEBOOK")
    if (not isinstance(existing_notebook, dict)
            or str(existing_notebook.get("notebook_id") or "") != "a005830b-e3a8-40c1-b4b5-d82997412584"):
        return {"status": "BLOCKED", "reason": "EXISTING_CANARY_NOTEBOOK_CHECKPOINT_REQUIRED"}

    def save_step(name: str, value: Any) -> None:
        checkpoint["steps"][name]=value
        checkpoint["updated_at"]=datetime.now(timezone.utc).isoformat()
        checkpoint_path.parent.mkdir(parents=True,exist_ok=True)
        temp=checkpoint_path.with_suffix(".tmp")
        temp.write_text(json.dumps(checkpoint,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        temp.replace(checkpoint_path)

    started=time.monotonic()
    recent_calls: list[float]=[]
    def governed(action: str, operation, *, requests: int=1, bytes_estimate: int=30000, runtime: int=90):
        if action in checkpoint["steps"]:
            return checkpoint["steps"][action]
        if len(checkpoint["steps"]) >= 24:
            raise RuntimeError("CANARY_OPERATION_LIMIT_REACHED")
        if action == "NOTEBOOKLM_NATIVE_WEB_DISCOVERY" and sum(
                key == action for key in checkpoint["steps"]) >= 3:
            raise RuntimeError("CANARY_WEB_RESEARCH_LIMIT_REACHED")
        if action.startswith("WEB_SOURCE_ADD_") and sum(
                key.startswith("WEB_SOURCE_ADD_") for key in checkpoint["steps"]) >= 2:
            raise RuntimeError("CANARY_NEW_WEB_SOURCE_LIMIT_REACHED")
        if action in {"INITIAL_YOUTUBE_QUESTIONS", "GAP_QUESTION_BEFORE_WEB",
                      "GAP_QUESTION_AFTER_WEB", "SOURCE_GROUNDED_SYNTHESIS"} and sum(
                key in {"INITIAL_YOUTUBE_QUESTIONS", "GAP_QUESTION_BEFORE_WEB",
                        "GAP_QUESTION_AFTER_WEB", "SOURCE_GROUNDED_SYNTHESIS"}
                for key in checkpoint["steps"]) >= 5:
            raise RuntimeError("CANARY_FOLLOWUP_GROUP_LIMIT_REACHED")
        now=time.monotonic()
        if len(recent_calls)>=5:
            wait=max(0.0,61.0-(now-recent_calls[0]))
            if wait:
                time.sleep(wait)
            recent_calls.clear()
        call_started=time.monotonic()
        value=execute("NOTEBOOKLM","research_discovery",action,
            {"requests":requests,"operations":requests,"runtime_seconds":runtime,
             "bytes":bytes_estimate,"billable":False,"cost":0.0},operation,
            job_id=job.job_id,job_type=policy_job_type,project_id="NEXUS_DEDICATED_RESEARCH_CANARY",
            correlation_id=job.correlation_id,
            purpose=f"dedicated-research-canary:{job.job_id}:{action}",
            actual_usage=lambda _result:{"requests":requests,"operations":requests,
                "bytes":bytes_estimate,"runtime_seconds":max(1,round(time.monotonic()-call_started)),"cost":0.0})
        recent_calls.append(time.monotonic())
        save_step(action,value)
        return value

    try:
        promotion=checkpoint["steps"].get("FEEDER_SOURCE_PROMOTION")
        if not promotion:
            feeder_sources=governed("FEEDER_SOURCE_LIST",
                lambda:adapter.sources(feeder_notebook_id),bytes_estimate=50000,runtime=30)
            feeder_source=next((row for row in feeder_sources
                if str(row.get("id") or row.get("source_id") or "")==feeder_source_id),None)
            if not feeder_source or str(feeder_source.get("url") or feeder_source.get("source_url") or "")!=source_url:
                return {"status":"BLOCKED","reason":"FEEDER_SOURCE_NOT_VERIFIED_IN_SOURCE_INTAKE_NOTEBOOK"}
            promotion_prompt=(
                "This is feeder intake/classification only. Read only the explicitly selected source. "
                "Identify one coherent business opportunity actually described in it for possible dedicated research. "
                "Return one JSON object with keys classification (BUSINESS_OPPORTUNITY or NOT_PROMOTABLE), promoted_subject "
                "(concise and specific, one subject only), exact_business_model, target_customer, customer_problem, "
                "source_pricing_or_revenue_claim, evidence_quote (short quote from this source), and material_evidence_gap. "
                "If the source only lists options, select one clearly explained option and do not combine them. "
                "Do not use or cite any other feeder source. Preserve creator claims as claims.")
            from research.notebooklm_research_adapter import extract_json_object
            raw_promotion=governed("FEEDER_SOURCE_CLASSIFY_PROMOTE",
                lambda:adapter.ask_source_scoped(feeder_notebook_id,feeder_source_id,promotion_prompt,timeout_seconds=120),
                bytes_estimate=45000,runtime=120)
            cited=[str(row.get("source_id")) for row in raw_promotion.get("references",[]) if row.get("source_id")]
            promotion_payload=extract_json_object(str(raw_promotion.get("answer") or ""))
            promotion=validate_feeder_promotion(promotion_payload,expected_source_id=feeder_source_id,cited_source_ids=cited)
            promotion.update({"feeder_notebook_id":feeder_notebook_id,"source_url":source_url,
                "source_title":source_title,"exact_business_model":str(promotion_payload.get("exact_business_model") or "")[:700],
                "target_customer":str(promotion_payload.get("target_customer") or "")[:500],
                "customer_problem":str(promotion_payload.get("customer_problem") or "")[:500],
                "source_pricing_or_revenue_claim":str(promotion_payload.get("source_pricing_or_revenue_claim") or "")[:500],
                "evidence_gap":promotion_evidence_gap(promotion_payload),
                "intake_reference_ids":cited})
            save_step("FEEDER_SOURCE_PROMOTION",promotion)
        elif not promotion.get("evidence_gap"):
            # Recover a gap field omitted by an older intake prompt without
            # issuing another NotebookLM turn or changing the promoted subject.
            from research.notebooklm_research_adapter import extract_json_object
            raw_turn=checkpoint["steps"].get("FEEDER_SOURCE_CLASSIFY_PROMOTE") or {}
            old_payload=extract_json_object(str(raw_turn.get("answer") or ""))
            promotion["evidence_gap"]=promotion_evidence_gap(old_payload)
            save_step("FEEDER_SOURCE_PROMOTION",promotion)
        subject=str(promotion.get("subject") or "")
        if not subject:
            return {"status":"BLOCKED","reason":"FEEDER_PROMOTION_SUBJECT_MISSING"}
        checkpoint["subject"]=subject

        from nexus_agent_platform.resource_spend_governor import default_store as governor_store
        governor=governor_store()
        # The owner authorized exactly one zero-cost NotebookLM notebook for
        # this bounded canary. This is an exact provider/service/job scope,
        # with one creation per job and per day; ordinary Research scopes stay
        # unchanged and the monetary limits remain zero.
        creation_limits={"rate":{"requests":1,"operations":1,"window_seconds":86400},
            "usage":{"resource_creations":0,"cost":0},"money":{"per_job":0,"per_day":0,"per_month":0}}
        resource_scope=_ensure_policy_if_missing(governor,"NOTEBOOKLM","resource_creation",policy_job_type,"DAILY",
            autonomous_usage_allowed=True,autonomous_spend_allowed=True,
            soft_limits=creation_limits,hard_limits=creation_limits,concurrency_limit=1,
            resource_creation_limit=0,state="NORMAL",approval_required=False)
        if not resource_scope or resource_scope.get("state")!="NORMAL" or not resource_scope.get("autonomous_usage_allowed"):
            return {"status":"BLOCKED","reason":"DEDICATED_NOTEBOOK_CREATION_POLICY_NOT_RESOLVED"}

        title=dedicated_title(subject)
        notebook=existing_notebook
        if not notebook:
            notebooks=governed("NOTEBOOK_LIST_FOR_SUBJECT",adapter.notebooks,bytes_estimate=40000,runtime=30)
            existing=find_dedicated_notebook(notebooks,subject)
            if existing:
                notebook={"notebook_id":existing["id"],"title":title,"created":False}
            else:
                resource_key=governor.resource_create(job.job_id,"NOTEBOOKLM",
                    f"dedicated-research-notebook:{subject_key(subject)}",job_type=policy_job_type,
                    max_per_job=1,max_per_day=1)
                raw=governed("DEDICATED_NOTEBOOK_CREATE",
                    lambda:adapter._run_json(["create","--json",title],stage="create",
                        failure_code="NOTEBOOK_CREATE_FAILED"),bytes_estimate=16000,runtime=60)
                created=raw.get("notebook") if isinstance(raw,dict) else None
                notebook_id=(created or {}).get("id") or (raw.get("id") if isinstance(raw,dict) else None)
                if not notebook_id:
                    return {"status":"BLOCKED","reason":"DEDICATED_NOTEBOOK_CREATE_MISSING_ID"}
                notebook={"notebook_id":str(notebook_id),"title":title,"created":True,
                          "resource_key":resource_key,"subject_key":subject_key(subject)}
            save_step("DEDICATED_NOTEBOOK",notebook)
        notebook_id=str(notebook["notebook_id"])

        before=governed("SOURCE_LIST_BEFORE",lambda:adapter.sources(notebook_id),bytes_estimate=30000,runtime=30)
        existing_video=adapter.find_existing_source(before,video_id=adapter.video_id_of(source_url),title=source_title)
        unrelated_before=[row for row in before
            if str(row.get("url") or row.get("source_url") or "")!=source_url]
        if unrelated_before:
            return {"status":"BLOCKED","reason":"DEDICATED_NOTEBOOK_CONTAINS_UNRELATED_SOURCES",
                    "notebook_id":notebook_id,"unrelated_source_count":len(unrelated_before)}
        if existing_video:
            video_source=existing_video
        else:
            video_source=governed("YOUTUBE_SOURCE_ADD",
                lambda:adapter.add_source(notebook_id,source_url,video_title=source_title),
                bytes_estimate=40000,runtime=240)
        video_source_id=str(video_source.get("id") or video_source.get("source_id") or "")
        if not video_source_id:
            return {"status":"BLOCKED","reason":"YOUTUBE_SOURCE_ID_MISSING"}
        indexed=governed("YOUTUBE_SOURCE_WAIT",
            lambda:adapter.wait_for_source(notebook_id,video_source_id,timeout_seconds=240),
            bytes_estimate=12000,runtime=270)
        after_video=governed("SOURCE_LIST_AFTER_YOUTUBE",lambda:adapter.sources(notebook_id),bytes_estimate=30000,runtime=30)
        if not any(str(row.get("id") or row.get("source_id"))==video_source_id for row in after_video):
            return {"status":"BLOCKED","reason":"YOUTUBE_SOURCE_NOT_VISIBLE_IN_NOTEBOOK"}

        initial_prompt=(
            f"Analyze only this original video for the dedicated research subject: {subject}.\n"
            "Answer these five questions separately and cite source evidence: (1) What exact business model is claimed? "
            "(2) Who is the target customer? (3) What problem is being solved? (4) What pricing or revenue claims are made? "
            "(5) Which claims require independent verification? Clearly label creator assertions as SOURCE_CLAIM, "
            "and state when the video does not provide evidence. Do not use other topics or invent details.")
        initial=governed("INITIAL_YOUTUBE_QUESTIONS",
            lambda:adapter.ask_source_scoped(notebook_id,video_source_id,initial_prompt,timeout_seconds=120),
            bytes_estimate=50000,runtime=120)
        gap_question=(
            f"What current independent evidence supports demand for the specific business model described as '{subject}', "
            "and what publicly visible competitor or substitute pricing is relevant? Use only the original video for this "
            "first pass. If it cannot answer, identify the exact missing evidence and do not infer demand from views, "
            "creator claims, or vendor prices.")
        before_answer=governed("GAP_QUESTION_BEFORE_WEB",
            lambda:adapter.ask_source_scoped(notebook_id,video_source_id,gap_question,timeout_seconds=120),
            bytes_estimate=45000,runtime=120)
        gap_query=web_gap_query(subject,
            "current independent demand signals for this business model and public competitor or substitute pricing; "
            "distinguish actual buyer-demand evidence from vendor list prices")
        web_search_path="NOTEBOOKLM_NATIVE"
        try:
            discovered=governed("NOTEBOOKLM_NATIVE_WEB_DISCOVERY",
                lambda:adapter._run_json(["research","discover","-n",notebook_id,"--json",gap_query],
                    stage="source_add",timeout=180,failure_code="NOTEBOOK_RESEARCH_DISCOVERY_FAILED"),
                bytes_estimate=100000,runtime=180)
            candidates=_source_candidates(discovered)
        except Exception as native_error:
            # Existing governed Nexus public-web search is the fallback.
            # Search snippets remain candidates; NotebookLM indexes and reads
            # each selected URL before the gap question is asked again.
            from nexus_agent_platform.proactive_discovery import web_search
            web_search_path="NEXUS_WEB_FALLBACK"
            discovered=web_search(gap_query,6)
            candidates=_source_candidates(discovered)
            save_step("NEXUS_WEB_FALLBACK_DIAGNOSTIC",{
                "native_error":f"{type(native_error).__name__}:{str(native_error)[:180]}",
                "provider":discovered.get("provider") if isinstance(discovered,dict) else None})
        # Select no more than two useful results, preferring recognized primary
        # sources and pricing pages; never bulk-import the unreviewed result set.
        subject_terms={term for term in re.findall(r"[a-z0-9]{4,}",subject.casefold())
                       if term not in {"business","online","service","services","model"}}
        def source_rank(row: dict[str,Any]) -> tuple[int,str]:
            url=str(row.get("url") or "").lower()
            title=str(row.get("title") or "").lower()
            description=str(row.get("description") or row.get("snippet") or "").lower()
            text=title+" "+url+" "+description
            primary=any(token in url for token in (".gov/",".edu/","sec.gov","census.gov","sba.gov"))
            relevant=any(term in text for term in subject_terms)
            evidence=any(token in text for token in ("pricing","price","survey","report","market","customer","demand"))
            return (int(primary)*3+int(relevant)*2+int(evidence),url)
        candidates=sorted(candidates,key=source_rank,reverse=True)
        candidates=[row for row in candidates if str(row.get("url") or "").startswith("https://")
                    and str(row.get("url"))!=source_url]
        source_plan=bounded_source_add_plan(notebook_id,candidates,limit=2)
        plan_by_url={row["url"]:row for row in source_plan}
        candidates=[row for row in candidates if str(row.get("url") or "") in plan_by_url]
        if not candidates:
            return {"status":"BLOCKED","reason":"NATIVE_WEB_DISCOVERY_RETURNED_NO_IMPORTABLE_SOURCES",
                    "research_run_ref":discovered.get("run_id") if isinstance(discovered,dict) else None}
        added_sources=[]
        for index,candidate in enumerate(candidates,1):
            url=str(candidate["url"])
            existing=next((row for row in after_video if str(row.get("url") or row.get("source_url") or "")==url),None)
            if existing:
                added_sources.append({**candidate,"id":existing.get("id") or existing.get("source_id"),"already_present":True})
                continue
            add_plan=plan_by_url[url]
            added=governed(f"WEB_SOURCE_ADD_{index}",
                lambda u=add_plan["url"],t=add_plan["title"] or f"Web research source {index}",n=add_plan["notebook_id"]:adapter.add_source(n,u,video_title=t),
                bytes_estimate=40000,runtime=180)
            sid=str(added.get("id") or added.get("source_id") or "")
            if not sid:
                continue
            ready=governed(f"WEB_SOURCE_WAIT_{index}",
                lambda s=sid:adapter.wait_for_source(notebook_id,s,timeout_seconds=180),
                bytes_estimate=12000,runtime=210)
            added_sources.append({**candidate,"id":sid,"status":ready.get("status"),"already_present":False})
        after=governed("SOURCE_LIST_AFTER_WEB",lambda:adapter.sources(notebook_id),bytes_estimate=40000,runtime=30)
        delta=source_delta(after_video,after)
        if not delta:
            return {"status":"BLOCKED","reason":"WEB_SOURCE_NOT_VISIBLE_IN_SAME_NOTEBOOK"}
        visible_urls={str(row.get("url") or row.get("source_url") or "") for row in after}
        verified_added=[row for row in added_sources if str(row.get("url") or "") in visible_urls]
        if not verified_added:
            return {"status":"BLOCKED","reason":"DISCOVERED_WEB_SOURCE_URL_NOT_VISIBLE_AFTER_ADD"}
        after_answer=governed("GAP_QUESTION_AFTER_WEB",
            lambda:adapter.ask_notebook(notebook_id,
                "Using the sources in this dedicated notebook, answer the same missing question: "+gap_question+
                " Cite source IDs/titles. Separate direct evidence from inference, and state what remains unknown."),
            bytes_estimate=60000,runtime=120)
        synthesis_prompt=(
            f"Synthesize the dedicated research subject '{subject}' using the original YouTube source and added external sources. "
            "Return sections: SOURCE CLAIMS; VERIFIED EXTERNAL FACTS; PARTIALLY VERIFIED CLAIMS; UNVERIFIED CLAIMS; "
            "CONTRADICTED CLAIMS; REMAINING RESEARCH GAPS; RECOMMENDED NEXT RESEARCH ACTION. Cite each material fact "
            "to the source ID/title. Do not convert a creator claim, view count, or vendor price into proof of customer demand.")
        synthesis=governed("SOURCE_GROUNDED_SYNTHESIS",
            lambda:adapter.ask_notebook(notebook_id,synthesis_prompt),bytes_estimate=65000,runtime=120)

        initial_text=str(initial.get("answer") or "")
        before_text=str(before_answer.get("answer") or "")
        after_text=str(after_answer.get("answer") or "")
        new_ids={str(row.get("id") or row.get("source_id") or "") for row in delta}
        after_refs={str(row.get("source_id") or "") for row in after_answer.get("references",[]) if row.get("source_id")}
        improvement=classify_canary_answer_improvement(before_text,after_text,
            new_source_ids=new_ids,answer_source_ids=after_refs)
        source_origin=classify_source_origin(str(payload.get("source_type") or "YOUTUBE_VIDEO"),
            str(payload.get("feeder_type") or "") or None)
        local_case={"schema":"nexus.research.notebook-ownership.v1","case_id":str(payload.get("case_id") or job.job_id),
            "research_subject":subject,"subject_key":subject_key(subject),"notebook_id":notebook_id,
            "notebook_title":title,"notebook_role":"DEDICATED_RESEARCH","feeder_role":"INTAKE_ONLY",
            "source_origin":source_origin,
            "source_refs":[{"id":video_source_id,"url":source_url,"title":source_title},
                *[{"id":r.get("id"),"url":r.get("url"),"title":r.get("title")} for r in verified_added]],
            "updated_at":datetime.now(timezone.utc).isoformat()}
        case_path=nexus_research_state_path("cases", "dedicated_research_notebooks", f"{subject_key(subject)}.json")
        case_path.parent.mkdir(parents=True,exist_ok=True)
        temp=case_path.with_suffix(".tmp");temp.write_text(json.dumps(local_case,indent=2,ensure_ascii=False)+"\n",encoding="utf-8");temp.replace(case_path)
        artifact={"schema":"nexus.dedicated-research-web-canary.v1","job_id":job.job_id,
            "research_case_id":local_case["case_id"],"department":"RESEARCH","executing_component":"NEXUS_RESEARCH",
            "research_subject":subject,"subject_key":subject_key(subject),"contract":"BOUNDED_MECHANISM_CANARY_NOT_FULL_CONTRACT",
            "notebook_id":notebook_id,"notebook_title":title,"dedicated_notebook_created":bool(notebook.get("created")),
            "notebook_role":"DEDICATED_RESEARCH","feeder_notebook_used_for_intake":True,
            "feeder_notebook_used_for_deep_research":False,
            "feeder_notebook_id":feeder_notebook_id,"feeder_source_id":feeder_source_id,
            "feeder_source_promotion":promotion,
            "source_count_before_youtube":len(before),"source_count_after_youtube":len(after_video),
            "source_count_before_web":len(after_video),"source_count_after_web":len(after),
            "youtube_source":{"id":video_source_id,"url":source_url,"title":source_title,"index_status":indexed.get("status")},
            "web_search_path":web_search_path,"web_command":["research","discover","-n",notebook_id,"--json","<scoped query>"],
            "web_query":gap_query,"discovered_candidates":candidates,"new_sources_added":verified_added,
            "missing_question":gap_question,"initial_questions_prompt":initial_prompt,
            "initial_answer":initial_text,"before_answer":before_text,"after_answer":after_text,
            "answer_improvement":improvement,"after_answer_reference_ids":sorted(after_refs),
            "source_claim_separation":bool("SOURCE CLAIM" in str(synthesis.get("answer") or "").upper()),
            "verified_fact_separation":bool("VERIFIED EXTERNAL FACT" in str(synthesis.get("answer") or "").upper()),
            "synthesis_prompt":synthesis_prompt,"synthesis":str(synthesis.get("answer") or ""),
            "synthesis_reference_ids":[str(r.get("source_id")) for r in synthesis.get("references",[]) if r.get("source_id")],
            "remaining_gaps":[],"full_question_contract_run":DEDICATED_CANARY_FULL_CONTRACT,
            "needle_run":DEDICATED_CANARY_NEEDLE,"v6_started":DEDICATED_CANARY_V6,
            "governor_enabled":True,"incremental_cash_spend_usd":0,
            "notebook_source_ids_after":[str(row.get("id") or row.get("source_id") or "") for row in after],
            "completed_at":datetime.now(timezone.utc).isoformat(),
            "latency_seconds":round(time.monotonic()-started,3)}
        remaining=(str(synthesis.get("answer") or ""))
        artifact["remaining_gaps"]=[] if "no remaining" in remaining.casefold() else [gap_question]
        artifact["sha256"]=hashlib.sha256(json.dumps(artifact,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
        target=nexus_research_state_path("certification", "dedicated_research_web_canaries", f"{job.job_id}.json")
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(artifact,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        # Owner handoff stays compact and local for this mechanism canary.
        # Notebook answers/transcripts are intentionally excluded.
        synthesis_text = str(synthesis.get("answer") or "")
        headings = {
            "KEY_VERIFIED_FINDINGS": ("VERIFIED EXTERNAL FACTS", "VERIFIED FACTS"),
            "PARTIALLY_VERIFIED_FINDINGS": ("PARTIALLY VERIFIED CLAIMS",),
            "UNVERIFIED_FINDINGS": ("UNVERIFIED CLAIMS",),
            "CONTRADICTED_FINDINGS": ("CONTRADICTED CLAIMS",),
            "ACTION_LIST": ("RECOMMENDED NEXT RESEARCH ACTION", "REMAINING RESEARCH GAPS"),
        }
        def section_text(labels: tuple[str, ...], limit: int = 1400) -> str:
            lines = synthesis_text.splitlines()
            active = False
            collected: list[str] = []
            wanted = {label.casefold().strip(" :#*-") for label in labels}
            all_labels = {label.casefold().strip(" :#*-") for group in headings.values() for label in group}
            all_labels.add("source claims")
            for line in lines:
                normalized = line.strip().casefold().strip(" :#*-")
                if normalized in wanted:
                    active = True
                    continue
                if active and normalized in all_labels:
                    break
                if active:
                    collected.append(line.strip())
            return " ".join(item for item in collected if item)[:limit]
        compact_handoff = {
            "RESEARCH_OBJECTIVE": f"Assess the source's custom AI-agent service model for restaurant owners, focusing on independent demand/pricing evidence and limitations.",
            "SUMMARY": synthesis_text[:1800],
            "KEY_VERIFIED_FINDINGS": section_text(headings["KEY_VERIFIED_FINDINGS"]),
            "PARTIALLY_VERIFIED_FINDINGS": section_text(headings["PARTIALLY_VERIFIED_FINDINGS"]),
            "UNVERIFIED_FINDINGS": section_text(headings["UNVERIFIED_FINDINGS"]),
            "CONTRADICTED_FINDINGS": section_text(headings["CONTRADICTED_FINDINGS"]),
            "KEY_SOURCE_REFERENCES": [{"title": str(row.get("title") or "")[:180],
                                       "url": str(row.get("url") or "")[:500],
                                       "source_id": str(row.get("id") or row.get("source_id") or "")[:120]}
                                      for row in [{"id": video_source_id, "title": source_title, "url": source_url}, *verified_added]],
            "ACTION_LIST": section_text(headings["ACTION_LIST"], 900),
            "NEXT_DEPARTMENT": "BUSINESS_OPPORTUNITIES",
            "RAY_APPROVAL_REQUIRED": False,
        }
        handoff_path = nexus_research_state_path("certification", "notebooklm_canary_payloads", f"{local_case['case_id']}_compact_handoff.json")
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        handoff_bytes = json.dumps(compact_handoff, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        handoff_path.write_bytes(handoff_bytes)
        return {"status":"COMPLETED","job_id":job.job_id,"notebook_id":notebook_id,
            "research_case_id":local_case["case_id"],"dedicated_notebook_created":bool(notebook.get("created")),
            "source_count_before":len(before),"source_count_after":len(after),
            "web_search_path":web_search_path,"new_sources_added":verified_added,
            "answer_improvement":improvement,"source_claim_separation":artifact["source_claim_separation"],
            "verified_fact_separation":artifact["verified_fact_separation"],
            "compact_handoff_ref":str(handoff_path),
            "compact_handoff_bytes":len(handoff_bytes),
            "artifact_ref":str(target),"artifact_sha256":artifact["sha256"],
            "full_question_contract_run":DEDICATED_CANARY_FULL_CONTRACT,
            "needle_run":DEDICATED_CANARY_NEEDLE,"v6_started":DEDICATED_CANARY_V6}
    except GovernanceDenied as exc:
        if exc.state in {"HARD_STOP","THROTTLED"}:
            return {"status":"WAITING_RESOURCE_WINDOW","reason":exc.code,"resource":"NOTEBOOKLM",
                "capability":"research_discovery","policy_state":exc.state,
                "resume_condition":"NOTEBOOKLM_POLICY_NORMAL","checkpoint_preserved":True}
        return {"status":"BLOCKED","reason":exc.code,"error_summary":str(exc)[:240]}
    except Exception as exc:
        return {"status":"BLOCKED","reason":"DEDICATED_RESEARCH_CANARY_FAILED",
                "error_summary":f"{type(exc).__name__}:{str(exc)[:240]}"}


def execute_full_research_canary(job, payload: dict[str, Any]) -> dict[str, Any]:
    """Run the complete grouped Opportunity contract on one qualified feeder source."""
    from datetime import datetime, timezone
    from research.notebooklm_research_adapter import AdapterConfig, NotebookLMResearchAdapter, _ensure_research_notebooklm_policy
    from research import research_case_engine as cases
    from research.notebook_completion_contracts import classify_research, select_contract, question_counts

    case_id=str(payload.get("case_id") or "")
    job_id=str(job.job_id)
    source_url=str(payload.get("source_url") or "")
    source_title=str(payload.get("source_title") or "")
    feeder_id=str(payload.get("feeder_notebook_id") or "")
    feeder_source_id=str(payload.get("feeder_source_id") or "")
    subject=str(payload.get("research_subject") or "")
    notebook_id=str(payload.get("dedicated_notebook_id") or "")
    if (payload.get("operation")!="FULL_RESEARCH_NOTEBOOK_NEEDLE_CANARY"
            or payload.get("authorized_job_id")!=job_id
            or not case_id.startswith("nexus_full_research_canary_")
            or not source_url.startswith("https://www.youtube.com/watch?v=")
            or not source_title or not subject or len(subject)>180
            or len(feeder_id)<20 or not feeder_source_id or len(notebook_id)<20):
        return {"status":"BLOCKED","reason":"FULL_RESEARCH_CANARY_INPUT_INVALID"}
    policy_type=full_research_canary_policy_job_type(job_id)
    from nexus_agent_platform.resource_spend_governor import default_store as governor_store
    governor=governor_store()
    try:
        _ensure_research_notebooklm_policy()
        policies=ensure_full_research_canary_policy(governor,job_id=job_id,case_id=case_id)
    except (PermissionError,RuntimeError) as exc:
        return {"status":"WAITING_RESOURCE_WINDOW","reason":str(exc)[:240],"resource":"NOTEBOOKLM",
            "capability":"research_discovery","policy_state":"SCOPED_POLICY_UNAVAILABLE","checkpoint_preserved":True}
    if policy_type not in {str(row.get("job_type") or "") for row in policies.values()}:
        return {"status":"BLOCKED","reason":"FULL_RESEARCH_CANARY_POLICY_SCOPE_MISMATCH"}

    prior_scope=os.environ.get("NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE")
    os.environ["NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE"]=policy_type
    try:
        adapter=NotebookLMResearchAdapter(AdapterConfig(profile="default"))
        ownership_path=nexus_research_state_path("cases", "dedicated_research_notebooks", "a9b702d4f372.json")
        try: ownership=json.loads(ownership_path.read_text(encoding="utf-8"))
        except (OSError,ValueError,TypeError): ownership={}
        if (ownership.get("notebook_role")!="DEDICATED_RESEARCH"
                or ownership.get("feeder_role")!="INTAKE_ONLY"
                or str(ownership.get("research_subject") or "").casefold()!=subject.casefold()
                or str(ownership.get("notebook_id") or "")!=notebook_id):
            return {"status":"BLOCKED","reason":"DEDICATED_NOTEBOOK_OWNERSHIP_NOT_VERIFIED"}
        source_origin=next((row for row in ownership.get("source_refs",[])
            if str(row.get("url") or "")==source_url),None)
        if not source_origin:
            return {"status":"BLOCKED","reason":"SOURCE_NOT_IN_DEDICATED_NOTEBOOK_OWNERSHIP"}
        feeder_sources=adapter.sources(feeder_id)
        feeder_source=next((row for row in feeder_sources
            if str(row.get("id") or row.get("source_id") or "")==feeder_source_id),None)
        if (not feeder_source or str(feeder_source.get("url") or feeder_source.get("source_url") or "")!=source_url
                or str(feeder_source.get("title") or "")!=source_title):
            return {"status":"BLOCKED","reason":"QUALIFIED_FEEDER_SOURCE_NOT_VERIFIED"}
        live_sources=adapter.sources(notebook_id)
        ownership_refs=ownership.get("source_refs") or []
        owned_ids={str(row.get("id") or "") for row in ownership_refs if row.get("id")}
        owned_urls={str(row.get("url") or "") for row in ownership_refs if row.get("url")}
        unrelated=[row for row in live_sources if str(row.get("id") or row.get("source_id") or "") not in owned_ids
            and str(row.get("url") or row.get("source_url") or "") not in owned_urls]
        # A prior worker may have successfully added and indexed sources in
        # this same case before it stopped. Recover their ownership from the
        # persisted case source inventory; never bless an unknown live source.
        if unrelated:
            recovered_case=cases.get_case(case_id)
            workspace=(recovered_case or {}).get("notebook_workspace") or {}
            if (recovered_case and recovered_case.get("case_id")==case_id
                    and str(workspace.get("notebook_id") or "")==notebook_id
                    and str(recovered_case.get("objective_family") or "")=="BUSINESS_OPPORTUNITIES"):
                case_sources=[row for row in recovered_case.get("sources") or []
                    if isinstance(row,dict) and str(row.get("notebook_id") or "")==notebook_id]
                recovered_ids={str(row.get("notebook_source_id") or row.get("source_id") or "") for row in case_sources}
                recovered_urls={str(row.get("url") or "") for row in case_sources}
                provable=[row for row in unrelated if
                    str(row.get("id") or row.get("source_id") or "") in recovered_ids
                    or str(row.get("url") or row.get("source_url") or "") in recovered_urls]
                # Source addition and the compact local case index are two
                # separate durable writes. If a worker stopped between them,
                # recover only clearly subject-matching public restaurant-AI
                # sources from this subject-exclusive notebook.
                already={str(row.get("id") or row.get("source_id") or "") for row in provable}
                for row in unrelated:
                    sid=str(row.get("id") or row.get("source_id") or "")
                    if sid in already: continue
                    same_subject=_source_matches_research_subject(subject,row)
                    if same_subject:
                        item={"source_id":sid,"notebook_source_id":sid,"notebook_id":notebook_id,
                            "url":str(row.get("url") or row.get("source_url") or ""),
                            "title":str(row.get("title") or "")[:240],
                            "source_class":"INDEPENDENT_SECONDARY_SOURCE","evidence_status":"UNVERIFIED",
                            "extraction_status":"NOTEBOOKLM_SOURCE_RECOVERED_AFTER_WORKER_RESTART"}
                        cases.add_source(case_id,item)
                        case_sources.append(item)
                        recovered_ids.add(sid); recovered_urls.add(item["url"])
                        provable.append(row)
                if len(provable)==len(unrelated):
                    for row in unrelated:
                        sid=str(row.get("id") or row.get("source_id") or "")
                        url=str(row.get("url") or row.get("source_url") or "")
                        if sid and sid not in owned_ids:
                            ownership_refs.append({"id":sid,"url":url,"title":str(row.get("title") or "")[:240],
                                "source_class":next((str(item.get("source_class")) for item in case_sources
                                    if str(item.get("notebook_source_id") or item.get("source_id") or "")==sid),
                                    "INDEPENDENT_SECONDARY_SOURCE"),"promoted_by_case_id":case_id,
                                "recovered_after_worker_restart":True})
                            owned_ids.add(sid)
                        if url: owned_urls.add(url)
                    ownership["source_refs"]=ownership_refs
                    ownership["linked_case_ids"]=sorted(set(ownership.get("linked_case_ids") or [])|{case_id})
                    ownership["updated_at"]=datetime.now(timezone.utc).isoformat()
                    ownership_path.write_text(json.dumps(ownership,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
                    unrelated=[]
        if unrelated:
            return {"status":"BLOCKED","reason":"DEDICATED_NOTEBOOK_HAS_UNOWNED_SOURCES",
                "notebook_id":notebook_id,"unowned_source_count":len(unrelated)}
        resolution=classify_research(objective=(
            f"Fully research the opportunity '{subject}' described in {source_title}. Determine customer demand, "
            "competition, pricing, economics, acquisition, operating requirements, Nexus fit and risks so Business Opportunities "
            "can decide whether it merits planning. Preserve unsupported creator claims as unverified."),
            research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
        contract=select_contract(resolution["research_purpose"],resolution["research_domain"])
        if resolution.get("status")!="RESOLVED" or contract.get("contract_id")!="BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1":
            return {"status":"BLOCKED","reason":"BUSINESS_OPPORTUNITY_CONTRACT_RESOLUTION_FAILED"}
        question=(f"Does the '{subject}' opportunity described by this source merit a complete Business Opportunities review? "
                  "Research the customer problem, demand, competition, economics and practical requirements without building a plan.")
        case_open=cases.open_or_join_case(objective=(f"Full research canary: {subject}. Source: {source_url}. "
            "Build an evidence-backed package for Business Opportunities; do not create the business plan."),
            objective_family="BUSINESS_OPPORTUNITIES",business_or_nexus_goal="Assess one qualified YouTube business opportunity",
            owner_department="RESEARCH",primary_question=question,case_id=case_id,force_existing=True)
        case=case_open.get("case") or cases.get_case(case_id)
        if not case:
            return {"status":"BLOCKED","reason":"RESEARCH_CASE_CREATION_FAILED"}
        case=cases._save(case,"FULL_RESEARCH_CANARY_CLASSIFIED",research_purpose="MISSION_RESEARCH",
            research_domain="BUSINESS_OPPORTUNITY",objective_family="BUSINESS_OPPORTUNITIES",
            notebook_contract_id=contract["contract_id"],notebook_workspace={"notebook_id":notebook_id,
                "title":str(ownership.get("notebook_title") or "")[:240],"max_sources":10,"created":False})
        origin_classes={source_url:"ORIGINAL_SOURCE_CLAIM"}
        for row in ownership_refs:
            url=str(row.get("url") or "")
            if url and url!=source_url:
                host=url.split("/",3)[2].lower() if "://" in url else ""
                origin_classes[url]="OFFICIAL_PRIMARY_SOURCE" if (host.endswith(".gov") or host.endswith(".edu")) else "INDEPENDENT_SECONDARY_SOURCE"
        for row in live_sources:
            sid=str(row.get("id") or row.get("source_id") or "")
            url=str(row.get("url") or row.get("source_url") or "")
            if not sid: continue
            cases.add_source(case_id,{"source_id":sid,"notebook_source_id":sid,"notebook_id":notebook_id,
                "url":url,"title":str(row.get("title") or "")[:240],"source_class":origin_classes.get(url,"INDEPENDENT_SECONDARY_SOURCE"),
                "evidence_status":"UNVERIFIED","extraction_status":"NOTEBOOKLM_SOURCE_PRESENT"})
        cases.bind_notebook_workspace(case_id,{"notebook_id":notebook_id,
            "title":str(ownership.get("notebook_title") or ""),"created":False,"max_sources":10})
        from research.notebook_playbook_runner import run_case_playbook
        result=run_case_playbook(case_id,adapter=adapter,source_work_id=job_id,ask_followup=True)
        state=__import__("research.notebook_completion_contracts",fromlist=["load_state"]).load_state(case_id=case_id) or {}
        counts=question_counts(state)
        artifact={"schema":"nexus.full-research-canary.v1","job_id":job_id,"case_id":case_id,
            "source_title":source_title,"source_url":source_url,"feeder_notebook_id":feeder_id,
            "feeder_source_id":feeder_source_id,"research_subject":subject,"contract_id":contract["contract_id"],
            "notebook_id":notebook_id,"notebook_role":"DEDICATED_RESEARCH","feeder_role":"INTAKE_ONLY",
            "source_count_before":len(live_sources),"source_ids_before":[str(row.get("id") or row.get("source_id") or "") for row in live_sources],
            "question_group_ids":state.get("question_groups_completed",[]),"question_counts":counts,
            "all_required_questions_asked":counts.get("question_count_asked")==counts.get("question_count_required"),
            "supplementation":result.get("supplementation_attempts",[]),"mechanical_verification":result.get("verification"),
            "research_receipt_id":result.get("receipt_id"),"needle_job":result.get("needle_job"),
            "compact_handoff_ref":state.get("local_state_ref"),"no_full_notebook_mirror_to_supabase":True,
            "governor":{"enabled":True,"provider":"NOTEBOOKLM","policy_job_type":policy_type,
                "daily_state":policies["DAILY"].get("state"),"bytes_limit":4_000_000,
                "global_research_policy_unchanged":True},
            "recorded_at":datetime.now(timezone.utc).isoformat()}
        path=nexus_research_state_path("certification", "full_research_canaries", f"{job_id}.json")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(artifact,indent=2,ensure_ascii=False,default=str)+"\n",encoding="utf-8")
        if not result.get("verification",{}).get("complete") or not result.get("needle_job"):
            return {"status":"BLOCKED","reason":"FULL_RESEARCH_CONTRACT_MECHANICAL_GATE_FAILED",
                "job_id":job_id,"case_id":case_id,"notebook_id":notebook_id,"question_counts":counts,
                "research_receipt_id":result.get("receipt_id"),"artifact_ref":str(path)}
        return {"status":"COMPLETED","job_id":job_id,"case_id":case_id,"notebook_id":notebook_id,
            "contract_id":contract["contract_id"],"question_groups_completed":artifact["question_group_ids"],
            "question_counts":counts,"research_receipt_id":result.get("receipt_id"),
            "needle_job_id":(result.get("needle_job") or {}).get("job_id"),
            "mechanical_complete":True,"supplementation_attempts":result.get("supplementation_attempts",[]),
            "local_state_ref":state.get("local_state_ref"),"artifact_ref":str(path),
            "notebooklm_policy_job_type":policy_type,"new_incremental_cash_required":False,
            "no_full_notebook_mirror_to_supabase":True}
    except GovernanceDenied as exc:
        if exc.state in {"HARD_STOP","THROTTLED"}:
            return {"status":"WAITING_RESOURCE_WINDOW","reason":exc.code,"resource":"NOTEBOOKLM",
                "capability":"research_discovery","policy_state":exc.state,
                "resume_condition":"SCOPED_NOTEBOOKLM_POLICY_NORMAL","checkpoint_preserved":True}
        return {"status":"BLOCKED","reason":exc.code,"error_summary":str(exc)[:240]}
    except Exception as exc:
        return {"status":"BLOCKED","reason":"FULL_RESEARCH_CANARY_FAILED",
            "error_summary":f"{type(exc).__name__}:{str(exc)[:240]}"}
    finally:
        if prior_scope is None: os.environ.pop("NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE",None)
        else: os.environ["NEXUS_NOTEBOOKLM_GOVERNOR_JOB_TYPE"]=prior_scope
