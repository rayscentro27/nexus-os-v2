"""Case-bound NotebookLM playbook execution and follow-up persistence."""
from __future__ import annotations

import json
import hashlib
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/research"))

import research_case_engine as cases
from notebook_playbooks import analyze_answer, build_notebook_prompt, gap_source_classes, select_playbook
from notebooklm_research_adapter import NotebookLMResearchAdapter, AdapterConfig
from notebook_completion_contracts import (classify_research, select_contract, new_contract_state,
    load_state as load_completion_state, persist_state as persist_completion_state,
    build_required_question_prompt, build_question_group_prompt, question_groups,
    build_targeted_gap_prompt, build_synthesis_prompt,
    register_notebook_submission, record_gap_review, extract_deliverables, set_synthesis,
    question_counts, verify_completion, finalize_contract, persist_library_entry, compact_handoff,
    record_gap_out_of_scope)

from nexus_agent_platform.runtime.paths import nexus_research_state_path

RECEIPTS = nexus_research_state_path("governed", "notebook_playbook_runs.jsonl")


def _record(row: dict[str, Any]) -> None:
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _load_persisted_notebook_answer(case: dict[str, Any], *, question_type: str,
                                   notebook_id: str) -> dict[str, Any] | None:
    """Recover a verified local NotebookLM answer after a worker interruption."""
    for row in reversed(case.get("notebook_answers") or []):
        if (row.get("question_type") != question_type or str(row.get("notebook_id") or "") != str(notebook_id)
                or not row.get("response_persisted") or not row.get("local_artifact_ref")):
            continue
        target=(ROOT / str(row["local_artifact_ref"])).resolve()
        if not target.is_relative_to(ROOT.resolve()) or not target.is_file():
            continue
        try:
            artifact=json.loads(target.read_text(encoding="utf-8"))
            answer=artifact.get("answer")
        except (OSError,ValueError,TypeError):
            continue
        if not isinstance(answer,str) or hashlib.sha256(answer.encode()).hexdigest()!=str(row.get("response_hash") or ""):
            continue
        return {"answer":answer,"source_ids":[str(x) for x in row.get("source_ids",[]) if x],
            "response_reference":row.get("response_reference"),"response_id":row.get("response_id"),
            "local_artifact_ref":row.get("local_artifact_ref")}
    return None


def _synthesis_summary(answer: str) -> dict[str, str | None]:
    recommendation=re.search(r"\*\*Recommendation Class\*\*\s*:\s*([^\n]+)|Recommendation Class\s*:\s*([^\n]+)",answer,re.IGNORECASE)
    nxt=re.search(r"\*\*Next Action\*\*\s*:\s*\n?\s*(?:\*\s*)?([^\n]+)|Next Action\s*:\s*\n?\s*(?:\*\s*)?([^\n]+)",answer,re.IGNORECASE)
    clean=lambda m: re.sub(r"[`*]", "", next((x for x in m.groups() if x), "")).strip(" :")[:300] if m else None
    return {"recommendation_class":clean(recommendation),"next_action":clean(nxt),
            "grounding":"NOTEBOOKLM_CASE_SYNTHESIS; not independently validated"}


def build_case_handoff_packet(case_id: str) -> dict[str, Any]:
    """Build a source-linked department packet; it is not an execution order."""
    case=cases.get_case(case_id)
    if not case or not case.get("notebook_playbook"):
        return {"ok":False,"reason":"PLAYBOOK_CASE_REQUIRED"}
    from notebook_playbooks import load_registry
    playbook=load_registry()[case["notebook_playbook"]["case_type"]]
    sources=[{"source_id":x.get("source_id"),"title":x.get("title"),"url":x.get("url"),
              "source_class":x.get("source_class"),"extraction_status":x.get("extraction_status"),
              "source_claims_are_not_nexus_verified_facts":x.get("source_claims_are_not_nexus_verified_facts",False)}
             for x in (case.get("sources") or [])]
    synthesis=(case.get("notebook_playbook") or {}).get("synthesis_summary") or {}
    questions=[x.get("question") for x in (case.get("open_questions") or []) if x.get("question")]
    if playbook["case_type"]=="TRADING_STRATEGY":
        packet={"case_id":case_id,"destination":playbook["handoff_destination"],
            "objective":case.get("objective"),"strategy_name":"Wick Sequence Breakout",
            "source_supported_rules":[x.get("extracted_evidence") for x in (case.get("sources") or []) if x.get("extracted_evidence")],
            "test_assumptions":[],"market":"NotebookLM proposed BTC/USDT; Mercury must validate approved data availability",
            "timeframe":"NotebookLM proposed 30m; claim is not independently verified",
            "entry":"Source describes wick-sequence formation-box boundary breakout aligned with estimated volume dominance; numeric defaults remain unavailable.",
            "exit":"Indicator shows optional ATR/R-multiple target levels; execution/partial-exit semantics are unspecified.",
            "stop":"Source/video describes ATR stop variants; exact settings and execution require Mercury assumptions.",
            "target":"Optional displayed TP1-TP3 based on ATR or risk/reward; deterministic allocation is unspecified.",
            "source_refs":sources,"claims_to_verify":questions,
            "recommended_test":synthesis.get("next_action"),
            "continuation_contract":"Mercury returns a complete source-linked baseline or specific missing research inputs; no live trading.",
            "packet_status":"READY_FOR_MERCURY_DEVELOPMENT_REVIEW","backtest_ready":False,"live_trading":False}
    else:
        packet={"case_id":case_id,"destination":playbook["handoff_destination"],
            "objective":case.get("objective"),"customer_problem_and_evidence":[x.get("extracted_evidence") for x in (case.get("sources") or []) if x.get("extracted_evidence")],
            "customer_segment":"See NotebookLM case synthesis; local segment evidence remains incomplete.",
            "source_refs":sources,"unresolved_economic_questions":questions,
            "recommendation_class":synthesis.get("recommendation_class"),
            "recommended_next_action":synthesis.get("next_action"),
            "guardrail":"Research packet only; no customer outreach, spend, or pilot execution is authorized by this packet.",
            "packet_status":"READY_FOR_ATLAS_DEVELOPMENT_REVIEW"}
    packet["created_at"]=datetime.now(timezone.utc).isoformat()
    fresh=cases.get_case(case_id) or case
    cases._save(fresh,"NOTEBOOK_PLAYBOOK_HANDOFF_PACKET_BUILT",
        playbook_handoff_packet=packet,
        notebook_playbook={**(fresh.get("notebook_playbook") or {}),
            "handoff_destination":packet["destination"],"handoff_packet_status":packet["packet_status"],
            "ready_for_handoff":True})
    return {"ok":True,"packet":packet}


def dispatch_case_handoff(case_id: str) -> dict[str, Any]:
    """Route a completed playbook packet through the existing governed handoff store."""
    case=cases.get_case(case_id)
    packet=(case or {}).get("playbook_handoff_packet")
    if not case or not isinstance(packet,dict):
        return {"ok":False,"reason":"PLAYBOOK_HANDOFF_PACKET_REQUIRED"}
    from operations import nexus_handoff
    if not nexus_handoff.configured():
        return {"ok":False,"reason":"GOVERNED_HANDOFF_STORE_UNAVAILABLE"}
    target=str(packet.get("destination") or "")
    if not target:
        return {"ok":False,"reason":"HANDOFF_DESTINATION_MISSING"}
    source_ids=[str(x.get("source_id")) for x in (case.get("sources") or []) if x.get("source_id")]
    payload={"research_case_id":case_id,"case_objective":case.get("objective"),
        "playbook_id":(case.get("notebook_playbook") or {}).get("playbook_id"),
        "notebook_id":(case.get("notebook_playbook") or {}).get("notebook_id"),
        "packet":packet,"open_questions":case.get("open_questions") or [],
        "case_recommendation":(case.get("recommendations") or [{}])[-1],
        "continuation":{"owner_department":target,"parent_goal_id":case.get("originating_goal_id"),
            "next_action":"ACKNOWLEDGE_AND_CONTINUE_THIS_RESEARCH_CASE",
            "success_criteria":["department records a continuation status","strategy/opportunity assumptions and unknowns remain explicit","no live trading, spend, outreach, or external pilot is initiated"]}}
    result=nexus_handoff.create_handoff(source_department="RESEARCH",target_department=target,
        handoff_type="RESEARCH_CASE_PLAYBOOK_DEVELOPMENT",topic=str(case.get("objective") or case_id)[:180],
        payload=payload,source_ids=source_ids,
        artifact_refs=[str((case.get("notebook_playbook") or {}).get("notebook_id") or "")],
        logical_key=f"notebook-playbook:{case_id}:{(case.get('notebook_playbook') or {}).get('last_run_at','')}:{target}")
    if result.get("handoff_id"):
        handoff_ids=sorted(set([str(x) for x in case.get("handoff_ids",[]) if x]+[str(result["handoff_id"])]))
        updated_packet={**packet,"department_handoff_id":result["handoff_id"],
            "department_handoff_status":result.get("handoff_status") or result.get("status"),
            "department_handoff_created":bool(result.get("created")),
            "dispatched_at":datetime.now(timezone.utc).isoformat()}
        cases._save(case,"NOTEBOOK_PLAYBOOK_HANDOFF_DISPATCHED",handoff_ids=handoff_ids,
            playbook_handoff_packet=updated_packet,
            notebook_playbook={**(case.get("notebook_playbook") or {}),
                "department_handoff_id":result["handoff_id"],"department_handoff_status":updated_packet["department_handoff_status"]},
            next_department_action="RECEIVER_ACKNOWLEDGE_AND_CONTINUE_CASE")
    return {"ok":bool(result.get("handoff_id")),"handoff":result}


def _contract_purpose_domain(case: dict[str, Any]) -> dict[str, Any]:
    purpose = case.get("research_purpose")
    domain = case.get("research_domain")
    family = str(case.get("objective_family") or case.get("case_type") or "")
    if not purpose and "BUSINESS_CREATION" in family.upper():
        purpose = "LIBRARY_INTELLIGENCE"
        domain = domain or "BUSINESS_CREATION"
    if not purpose and "FUNDING_TECHNIQUE" in family.upper():
        purpose = "LIBRARY_INTELLIGENCE"
        domain = domain or "BUSINESS_FUNDING"
    if not purpose and "BUSINESS_OPPORTUNIT" in family.upper():
        purpose = "MISSION_RESEARCH"
        domain = domain or "BUSINESS_OPPORTUNITY"
    if not purpose and "FOREX" in family.upper():
        purpose = "MISSION_RESEARCH"
        domain = domain or "FOREX"
    if not purpose and ("LIBRARY" in family.upper() or case.get("library_intelligence") is True):
        purpose = "LIBRARY_INTELLIGENCE"
    if not purpose and "MISSION" in family.upper():
        purpose = "MISSION_RESEARCH"
    return classify_research(objective=str(case.get("objective") or case.get("business_or_nexus_goal") or ""),
        research_purpose=purpose, research_domain=domain,
        context={"objective_family":family,"owner_department":case.get("owner_department"),
            "business_or_nexus_goal":case.get("business_or_nexus_goal"),"primary_question":case.get("primary_question")})


def _contract_summary(state: dict[str, Any], verification: dict[str, Any] | None = None) -> dict[str, Any]:
    counts = question_counts(state)
    return {"contract_id":state.get("contract_id"),"research_purpose":state.get("research_purpose"),
        "research_domain":state.get("research_domain"),"notebook_id":state.get("notebook_id"),
        "verification_status":state.get("verification_status"),**counts,
        "supplementation_attempted":bool(state.get("supplementation_attempted")),
        "synthesis_present":bool(state.get("synthesis")),"action_statement_present":bool(state.get("action_statement")),
        "structured_extraction_present":bool(state.get("structured_extraction")),
        "needle_verification":state.get("needle_verification"),
        "unresolved_gap_count":sum(not bool(g.get("reviewed")) for g in state.get("evidence_gaps",[])),
        "verification_criteria":(verification or {}).get("criteria",{}),
        "local_state_ref":state.get("local_state_ref"),"updated_at":state.get("updated_at")}


def _record_dedicated_notebook_source(case_id: str, notebook_id: str, item: dict[str, Any]) -> bool:
    """Keep the subject notebook manifest aligned with successfully indexed sources."""
    directory=nexus_research_state_path("cases", "dedicated_research_notebooks")
    for path in directory.glob("*.json"):
        try: manifest=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,ValueError,TypeError): continue
        if (manifest.get("notebook_role")!="DEDICATED_RESEARCH"
                or str(manifest.get("notebook_id") or "")!=str(notebook_id)):
            continue
        refs=list(manifest.get("source_refs") or [])
        sid=str(item.get("notebook_source_id") or item.get("source_id") or "")
        url=str(item.get("url") or "")
        if not sid or not url: return False
        if not any(str(row.get("id") or "")==sid or str(row.get("url") or "")==url for row in refs):
            refs.append({"id":sid,"url":url,"title":str(item.get("title") or "")[:240],
                "source_class":item.get("source_class"),"promoted_by_case_id":case_id})
        manifest["source_refs"]=refs
        manifest["linked_case_ids"]=sorted(set(manifest.get("linked_case_ids") or [])|{case_id})
        manifest["updated_at"]=datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        return True
    return False


def _web_source_class(url: str, title: str = "") -> str:
    parsed=urlparse(url)
    host=(parsed.hostname or "").casefold()
    path=parsed.path.casefold()
    community=("reddit.com","capterra.com","g2.com","trustpilot.com","yelp.com","quora.com","facebook.com")
    if any(host==domain or host.endswith("."+domain) for domain in community):
        return "COMMUNITY_OR_REVIEW_SOURCE"
    if host.endswith(".gov") or host.endswith(".edu") or "/pricing" in path or "pricing" in str(title).casefold():
        return "OFFICIAL_PRIMARY_SOURCE"
    return "INDEPENDENT_SECONDARY_SOURCE"


def _reconcile_contract_group_statuses(case_id: str, state: dict[str, Any], case: dict[str, Any]) -> int:
    """Recover evidence labels from local NotebookLM answers before gap routing.

    NotebookLM answer artifacts are the research record; this deterministic
    reconciliation prevents a worker restart/parser upgrade from treating all
    previously answered questions as fresh web-research gaps.
    """
    from notebook_completion_contracts import _extract_statuses, _derive_gaps
    updates: dict[str, str] = {}
    refs: dict[str, set[str]] = {}
    for answer in case.get("notebook_answers") or []:
        kind = str(answer.get("question_type") or "")
        if not (kind.startswith("CONTRACT_GROUP:") or kind.startswith("CONTRACT_GAP:")):
            continue
        artifact_ref = str(answer.get("local_artifact_ref") or "")
        if not artifact_ref:
            continue
        path = (ROOT / artifact_ref).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            continue
        try:
            artifact = json.loads(path.read_text(encoding="utf-8"))
            statuses = _extract_statuses(str(artifact.get("answer") or ""))
        except (OSError, ValueError, TypeError):
            continue
        updates.update(statuses)
        for qid in statuses:
            refs.setdefault(qid, set()).update(str(value) for value in answer.get("source_ids", []) if value)
    changed = 0
    allowed = {row.get("question_id") for row in state.get("required_questions", [])}
    for row in state.get("required_questions", []):
        qid = row.get("question_id")
        status = updates.get(qid)
        if qid in allowed and status in {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"}:
            if row.get("evidence_status") != status:
                row["evidence_status"] = row["answer_status"] = status
                changed += 1
            row["source_refs"] = sorted(set(row.get("source_refs") or []) | refs.get(qid, set()))
    prior = {row.get("question_id"): row for row in state.get("evidence_gaps", [])}
    state["evidence_gaps"] = _derive_gaps(state.get("required_questions", []), prior)
    if changed:
        state["status_reconciled_from_local_notebook_turns"] = changed
        state["local_state_ref"] = persist_completion_state(state, case_id=case_id)
    return changed


def _run_one_needle_repair(case_id: str, *, state: dict[str, Any], adapter: NotebookLMResearchAdapter,
                           needle: dict[str, Any], max_added_sources: int = 2) -> dict[str, Any]:
    """Repair one Needle gap in place; never creates an objective or notebook."""
    from notebook_completion_contracts import _extract_statuses
    ids=[str(value) for value in needle.get("affected_question_ids",[]) if value]
    if not ids:
        return {"ok":False,"reason":"NEEDLE_REPAIR_HAS_NO_QUESTION_REFERENCE"}
    question_by_id={q["question_id"]:q for q in state.get("required_questions",[])}
    question=question_by_id.get(ids[0])
    if not question:
        return {"ok":False,"reason":"NEEDLE_REPAIR_QUESTION_NOT_FOUND"}
    case=cases.get_case(case_id)
    bound=((case or {}).get("notebook_workspace") or {}).get("notebook_id") or ((case or {}).get("notebook_playbook") or {}).get("notebook_id")
    if bound and str(bound)!=str(state.get("notebook_id")):
        return {"ok":False,"reason":"NEEDLE_REPAIR_NOTEBOOK_ID_MISMATCH"}
    repair_action=str(needle.get("requested_research_action") or question["question_text"])
    alpha_direction=needle.get("alpha_research_direction") if isinstance(needle.get("alpha_research_direction"),dict) else {}
    directed=[str(row.get("question") or "").strip() for row in alpha_direction.get("candidate_questions",[])
        if isinstance(row,dict) and str(row.get("question") or "").strip()]
    if directed:
        repair_action += " Alpha Research Director's bounded follow-up context (hypothesis only; verify, do not assume): " + " | ".join(directed[:2])
    state["alpha_research_direction"] = alpha_direction
    expansion=expand_case_from_best_gap(case_id,adapter=adapter,max_additions=max_added_sources,
        question_id=question["question_id"],question_text=repair_action)
    if not expansion.get("ok"):
        return {"ok":False,"reason":expansion.get("reason") or "NEEDLE_RESEARCH_EXPANSION_FAILED",
            "notebook_id":state.get("notebook_id")}

    # Always ask the exact canonical question again in the same notebook,
    # including when public-source expansion found no qualifying source.
    targeted=build_targeted_gap_prompt(state,[question["question_id"]])
    with adapter._job_slot():
        turn=adapter.ask_notebook(state["notebook_id"],targeted)
        refs=[str(x.get("source_id")) for x in turn.get("references",[]) if x.get("source_id")]
        current={str(x.get("id")) for x in adapter.sources(state["notebook_id"]) if x.get("id")}
        if any(ref not in current for ref in refs):
            return {"ok":False,"reason":"NEEDLE_REPAIR_SOURCE_CONTAMINATION","notebook_id":state.get("notebook_id")}
        answer=str(turn.get("answer") or "")
        register_notebook_submission(state,prompt=targeted,submission_confirmed=bool(turn.get("submission_confirmed")),
            response=answer,source_refs=refs)
        cases.record_notebook_answer(case_id,question_type="NEEDLE_TARGETED_REPAIR",answer=answer,
            notebook_id=state["notebook_id"],source_ids=refs,conversation_id=turn.get("conversation_id"),
            submission_attempted=turn.get("submission_attempted",False),submission_confirmed=turn.get("submission_confirmed",False),
            response_reference=turn.get("response_reference"),prompt=targeted,response_id=turn.get("correlation_id"))
    statuses=_extract_statuses(answer)
    record_gap_review(state,question_ids=ids,supplementation_attempted=True,
        source_refs=refs,unresolved_note="Needle requested one bounded targeted repair; any remaining uncertainty is explicitly retained.",
        answer_updates=statuses)
    # Refresh synthesis and extraction after the targeted repair.
    with adapter._job_slot():
        synthesis_prompt=build_synthesis_prompt(state)
        synthesis_turn=adapter.ask_notebook(state["notebook_id"],synthesis_prompt)
        synthesis_refs=[str(x.get("source_id")) for x in synthesis_turn.get("references",[]) if x.get("source_id")]
        current={str(x.get("id")) for x in adapter.sources(state["notebook_id"]) if x.get("id")}
        if any(ref not in current for ref in synthesis_refs):
            return {"ok":False,"reason":"NEEDLE_REPAIR_SYNTHESIS_SOURCE_CONTAMINATION","notebook_id":state.get("notebook_id")}
        synthesis_answer=str(synthesis_turn.get("answer") or "")
        cases.record_notebook_answer(case_id,question_type=f"CONTRACT_SYNTHESIS:{state['contract_id']}",
            answer=synthesis_answer,notebook_id=state["notebook_id"],source_ids=synthesis_refs,
            conversation_id=synthesis_turn.get("conversation_id"),submission_attempted=synthesis_turn.get("submission_attempted",False),
            submission_confirmed=synthesis_turn.get("submission_confirmed",False),response_reference=synthesis_turn.get("response_reference"),
            prompt=synthesis_prompt,response_id=synthesis_turn.get("correlation_id"))
        deliverables=extract_deliverables(synthesis_answer)
        set_synthesis(state,synthesis=deliverables.get("synthesis") or "",
            action_statement=deliverables.get("action_statement") or {},
            structured_extraction=deliverables.get("structured_extraction") or {})
    state["handoff_package"]=compact_handoff(state,receipt_id="pending_needle_recheck")
    state["local_state_ref"]=persist_completion_state(state,case_id=case_id)
    return {"ok":True,"question_id":question["question_id"],"notebook_id":state.get("notebook_id"),
        "sources_added":len(expansion.get("added_sources") or []),"expansion_receipt_id":expansion.get("receipt_id"),
        "targeted_question_confirmed":bool(turn.get("submission_confirmed")),"return_to_needle_verification":True}


def _supplement_contract_group_native(case_id: str, *, state: dict[str, Any], adapter: NotebookLMResearchAdapter,
                                      gaps: list[dict[str, Any]], source_budget: int) -> dict[str, Any]:
    """Research a coherent group's material gaps and feed selected URLs back."""
    from nexus_agent_platform.notebooklm_discovery import _source_candidates
    notebook_id=str(state.get("notebook_id") or "")
    question_ids=[str(gap.get("question_id") or "") for gap in gaps if gap.get("question_id")]
    question_texts=[str(gap.get("question_text") or "") for gap in gaps]
    query=("Find current independent evidence for these specific business opportunity research gaps: "
           + " | ".join(f"[{gap.get('question_id')}] {gap.get('question_text')}" for gap in gaps)
           + f". Subject: {state.get('objective')}. Prefer official or primary evidence and current product/pricing pages. "
           "Distinguish demand evidence from vendor claims; return relevant source URLs with titles and short descriptions.")[:1200]
    # Discovery only reads NotebookLM/web-research output. Keep its governor
    # accounting separate from the subsequent governed source-add mutations.
    discovery=adapter._run_json(["research","discover","-n",notebook_id,"--json",query],
        stage="research_discover",timeout=180,failure_code="NOTEBOOK_RESEARCH_DISCOVERY_FAILED")
    candidates=_source_candidates(discovery)
    before=adapter.sources(notebook_id)
    existing_urls={str(row.get("url") or row.get("source_url") or "").rstrip("/").casefold() for row in before}
    subject_terms={term for term in re.findall(r"[a-z0-9]{4,}",str(state.get("objective") or "").casefold())
                   if term not in {"business","opportunity","research","customer","online"}}
    def rank(row: dict[str, Any]) -> tuple[int,str]:
        url=str(row.get("url") or "").casefold(); title=str(row.get("title") or "").casefold()
        desc=str(row.get("description") or "").casefold(); blob=f"{url} {title} {desc}"
        primary=any(token in url for token in (".gov/",".edu/","sec.gov","census.gov","sba.gov"))
        relevant=any(term in blob for term in subject_terms)
        direct=any(token in blob for token in ("pricing","price","survey","report","market","customer","demand","restaurant"))
        return (int(primary)*4+int(relevant)*2+int(direct),url)
    ranked=sorted((row for row in candidates if str(row.get("url") or "").startswith("https://")
                   and str(row.get("url") or "").rstrip("/").casefold() not in existing_urls),key=rank,reverse=True)
    added=[]
    source_add_failures=[]
    from urllib.parse import urlparse
    for row in ranked[:max(0,min(2,int(source_budget)))]:
        url=str(row.get("url") or "")
        try:
            source=adapter.add_source(notebook_id,url,video_title=str(row.get("title") or url))
        except Exception as exc:
            # Some NotebookLM RPC failures are reported as unconfirmed even
            # when the source was committed. Verify by URL before deciding
            # whether the source is absent; never retry a corpus mutation
            # blindly or claim it was added without observing it.
            try:
                after_failure=adapter.sources(notebook_id)
            except Exception:
                after_failure=[]
            existing=next((item for item in after_failure
                if str(item.get("url") or item.get("source_url") or "").rstrip("/").casefold()
                    ==url.rstrip("/").casefold()),None)
            if existing:
                source=existing
            else:
                source_add_failures.append({"url":url,"title":str(row.get("title") or "")[:240],
                    "error":f"{type(exc).__name__}:{str(exc)[:240]}"})
                continue
        source_id=str(source.get("id") or source.get("source_id") or "")
        if not source_id:
            source_add_failures.append({"url":url,"title":str(row.get("title") or "")[:240],
                "error":"SOURCE_ID_MISSING_AFTER_ADD_OR_RECONCILIATION"})
            continue
        indexed=adapter.wait_for_source(notebook_id,source_id,timeout_seconds=300)
        if str(indexed.get("status") or "").upper() not in {"READY","INDEXED","COMPLETED","SUCCESS"}:
            continue
        item={"source_id":source_id,"notebook_source_id":source_id,"notebook_id":notebook_id,
            "url":url,"title":str(row.get("title") or "")[:240],
            "source_class":_web_source_class(url,str(row.get("title") or "")),
            "evidence_status":"UNVERIFIED","extraction_status":"NOTEBOOKLM_WEB_SOURCE_INDEXED"}
        cases.add_source(case_id,item)
        _record_dedicated_notebook_source(case_id,notebook_id,item)
        added.append(item)
    after=adapter.sources(notebook_id)
    visible={str(row.get("id") or row.get("source_id") or "") for row in after}
    added=[row for row in added if row.get("notebook_source_id") in visible]
    follow_prompt=build_targeted_gap_prompt(state,question_ids)
    follow=adapter.ask_notebook(notebook_id,
        follow_prompt+"\nUse the newly added external sources where relevant. For each claim distinguish original source claims from independent evidence, cite the actual source IDs/URLs, and preserve unresolved uncertainty.")
    refs=[str(row.get("source_id")) for row in follow.get("references",[]) if row.get("source_id")]
    foreign=[ref for ref in refs if ref not in visible]
    if foreign:
        return {"ok":False,"reason":"CONTRACT_GAP_SOURCE_CONTAMINATION","foreign_reference_ids":foreign,
                "added_sources":added,"notebook_id":notebook_id}
    answer=str(follow.get("answer") or "")
    register_notebook_submission(state,prompt=follow_prompt,submission_confirmed=bool(follow.get("submission_confirmed")),
        response=answer,source_refs=refs)
    # One answer may address several stable contract questions in the group.
    # Persist every ID deterministically; the singular `question_id` used here
    # previously was undefined and caused a post-NotebookLM NameError.
    cases.record_notebook_answer(case_id,question_type=f"CONTRACT_GAP:{','.join(question_ids)}",answer=answer,
        notebook_id=notebook_id,source_ids=refs,conversation_id=follow.get("conversation_id"),
        submission_attempted=follow.get("submission_attempted",False),submission_confirmed=follow.get("submission_confirmed",False),
        response_reference=follow.get("response_reference"),prompt=follow_prompt,response_id=follow.get("correlation_id"))
    try:
        from notebook_completion_contracts import _extract_statuses
        statuses=_extract_statuses(answer)
    except Exception:
        statuses={}
    record_gap_review(state,question_ids=question_ids,supplementation_attempted=True,source_refs=refs,
        unresolved_note="Targeted native web research and same-notebook follow-up completed; unresolved evidence remains explicit.",
        answer_updates=statuses)
    return {"ok":True,"question_ids":question_ids,"web_query":query,"candidate_count":len(candidates),
        "added_sources":added,"source_count_before":len(before),"source_count_after":len(after),
        "source_add_failures":source_add_failures,
        "execution_status":"COMPLETED_WITH_SOURCE_ADD_FAILURES" if source_add_failures else "COMPLETED",
        "targeted_question_confirmed":bool(follow.get("submission_confirmed")),"answer_statuses":{qid:statuses.get(qid) for qid in question_ids}}


def _material_gap_order(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prioritize evidence gaps that materially affect business viability or planning."""
    weights=(("demand",8),("pricing",8),("pay",8),("customer",6),("competitor",6),
        ("revenue",5),("acquisition",5),("startup cost",5),("cost",4),("margin",4),
        ("fail",4),("contradict",4),("legal",3),("compliance",3),("scale",2))
    def score(gap: dict[str, Any]) -> tuple[int,str]:
        text=str(gap.get("question_text") or "").casefold()
        return (sum(weight for token,weight in weights if token in text),str(gap.get("question_id") or ""))
    return sorted(gaps,key=score,reverse=True)


def _business_opportunity_director_review(state: dict[str, Any], *, case: dict[str, Any],
                                          event: str, findings: list[dict[str, Any]],
                                          adapter: NotebookLMResearchAdapter,
                                          max_questions: int = 12, operation: Any = None) -> dict[str, Any]:
    """Run Alpha's director role at a persisted Research checkpoint.

    Director outputs are hypotheses only. Questions become stable required
    contract rows and are asked against the already-bound dedicated notebook.
    This function deliberately uses the existing canonical router helper.
    """
    from nexus_agent_platform import business_opportunity_research_v2 as bo
    context = dict(state.get("opportunity_context") or {})
    if not context and case.get("opportunity_id"):
        context = next((row for row in bo.load_opportunity_contexts()
            if row.get("opportunity_id") == case.get("opportunity_id")), {})
    if not context:
        context = {"opportunity_id": case.get("opportunity_id"),
            "original_idea": case.get("objective"), "objective": case.get("objective"),
            "verified_findings": [], "partial_findings": [], "unverified_findings": [],
            "contradicted_findings": [], "open_questions": []}
    context.update({"research_director_mode": "RESEARCH_DIRECTOR",
        "notebook_id": state.get("notebook_id"), "notebook_role": "DEDICATED_RESEARCH"})
    if state.get("outside_advisor_feedback"):
        context["outside_advisor_feedback"] = state["outside_advisor_feedback"]
    try:
        plan = bo.execute_research_director(objective=str(state.get("objective") or case.get("objective") or ""),
            context=context, findings=findings, event=event, operation=operation)
    except Exception as exc:
        return {"ok": False, "reason": "ALPHA_RESEARCH_DIRECTOR_UNAVAILABLE",
            "event": event, "detail": f"{type(exc).__name__}:{str(exc)[:180]}"}
    if plan.get("status") != "PLANNED":
        return {"ok": False, "reason": "ALPHA_RESEARCH_DIRECTOR_UNAVAILABLE",
            "event": event, "detail": str(plan.get("error") or plan.get("status") or "invalid output")[:240]}
    if str(context.get("entry_type") or "").upper() == "VENDOR_LED" and event == "OPPORTUNITY_FORMATION":
        vendor = str(context.get("vendor_name") or context.get("original_idea") or state.get("objective") or "vendor")
        plan["candidate_questions"] = list(plan.get("candidate_questions") or []) + bo.vendor_reputation_questions(vendor)

    # Persist compact director metadata locally with the research contract.
    state.setdefault("director_reviews", []).append({"event": event,
        "candidate_question_count": len(plan.get("candidate_questions") or []),
        "alternatives": list(plan.get("alternatives") or [])[:8],
        "real_world_actions": [dict(row) for row in (plan.get("real_world_actions") or [])[:8]
            if isinstance(row, dict)], "model_execution": plan.get("model_execution"),
        "hypotheses_only": True})
    context["alpha_direction"] = {key: plan.get(key) for key in
        ("alternatives", "next_research_action") if plan.get(key) is not None}
    context["research_director_mode"] = "RESEARCH_DIRECTOR"
    if plan.get("real_world_actions"):
        context["external_research_actions"] = list(context.get("external_research_actions") or []) + [
            {**dict(row), "status": "RAY_ACTION_REQUIRED" if row.get("approval_required", True) else "PREPARED",
             "evidence_status": "UNVERIFIED"} for row in plan["real_world_actions"][:8] if isinstance(row, dict)]
    state["opportunity_context"] = context
    state["local_state_ref"] = persist_completion_state(state, case_id=str(case["case_id"]))

    existing = {str(row.get("question_text") or "").casefold() for row in state.get("required_questions", [])}
    additions = []
    remaining = max(0, max_questions - int(state.get("adaptive_question_count") or 0))
    for candidate in plan.get("candidate_questions") or []:
        question = str(candidate.get("question") or "").strip()
        if not question or question.casefold() in existing or len(additions) >= remaining:
            continue
        from notebook_completion_contracts import question_row
        row = question_row(str(state["contract_id"]), question)
        row.update({"discovery_question": True, "materiality_topic": candidate.get("materiality_topic"),
            "why_material": candidate.get("why_material"), "evidence_needed": candidate.get("evidence_needed"),
            "hypothesis_only_origin": "ALPHA_RESEARCH_DIRECTOR"})
        state.setdefault("required_questions", []).append(row)
        additions.append(row)
        existing.add(question.casefold())
    state["adaptive_question_count"] = int(state.get("adaptive_question_count") or 0) + len(additions)
    if additions:
        group_id = "ALPHA_ADAPTIVE_" + re.sub(r"[^A-Z0-9]+", "_", event.upper()).strip("_")[:32]
        prompt = build_targeted_gap_prompt(state, [row["question_id"] for row in additions])
        # The grouped runner holds the adapter's job slot across this case
        # execution; avoid nested flock acquisition here.
        turn = adapter.ask_notebook(str(state["notebook_id"]), prompt)
        refs = [str(x.get("source_id")) for x in turn.get("references", []) if x.get("source_id")]
        current_ids = {str(x.get("id")) for x in adapter.sources(str(state["notebook_id"])) if x.get("id")}
        if any(ref not in current_ids for ref in refs):
            return {"ok": False, "reason": "ALPHA_ADAPTIVE_SOURCE_CONTAMINATION", "event": event}
        answer = str(turn.get("answer") or "")
        register_notebook_submission(state, prompt=prompt,
            submission_confirmed=bool(turn.get("submission_confirmed")), response=answer, source_refs=refs)
        cases.record_notebook_answer(str(case["case_id"]), question_type=f"CONTRACT_GROUP:{state['contract_id']}:{group_id}",
            answer=answer, notebook_id=str(state["notebook_id"]), source_ids=refs,
            conversation_id=turn.get("conversation_id"), submission_attempted=turn.get("submission_attempted", False),
            submission_confirmed=turn.get("submission_confirmed", False),
            response_reference=turn.get("response_reference"), prompt=prompt, response_id=turn.get("correlation_id"))
        from notebook_completion_contracts import _extract_statuses, _derive_gaps
        statuses = _extract_statuses(answer)
        for row in additions:
            status = statuses.get(row["question_id"], "UNVERIFIED")
            row.update({"asked": bool(turn.get("submission_confirmed")), "answer_status": status,
                "evidence_status": status, "source_refs": refs, "supplementation_attempted": False})
        state["evidence_gaps"] = _derive_gaps(state.get("required_questions", []),
            {gap.get("question_id"): gap for gap in state.get("evidence_gaps", [])})
        state["adaptive_question_events"] = list(state.get("adaptive_question_events") or []) + [{
            "event": event, "group_id": group_id, "question_ids": [row["question_id"] for row in additions],
            "notebook_id": state["notebook_id"], "questions_asked": bool(turn.get("submission_confirmed"))}]
    state["local_state_ref"] = persist_completion_state(state, case_id=str(case["case_id"]))
    return {"ok": True, "event": event, "added_question_ids": [row["question_id"] for row in additions],
        "notebook_id": state.get("notebook_id"), "hypotheses_only": True}


def _run_completion_contract_case(case_id: str, *, case: dict[str, Any], contract_resolution: dict[str, Any],
                                  adapter: NotebookLMResearchAdapter, source_work_id: str | None,
                                  max_supplement_questions: int = 9, max_added_sources: int = 10,
                                  bounded_scope_note: str | None = None,
                                  adaptive_director: bool = True, director_operation: Any = None) -> dict[str, Any]:
    """Execute a bounded contract cycle against the same case notebook."""
    contract = select_contract(contract_resolution["research_purpose"], contract_resolution["research_domain"])
    binding = case.get("notebook_playbook") or {}
    existing_notebook = ((case.get("notebook_workspace") or {}).get("notebook_id")
        or binding.get("notebook_id") or case.get("notebook_id")
        or next((row.get("notebook_id") for row in case.get("sources") or [] if row.get("notebook_id")), None))
    with adapter._job_slot():
        if existing_notebook:
            # Notebook identity is durable case state. Reuse it directly after
            # worker recovery instead of repeating the same NotebookLM list /
            # discovery calls (which are separately governed and idempotent).
            notebook = {"notebook_id":str(existing_notebook),
                "title":str(binding.get("title") or case.get("objective") or f"Nexus Research Case {case_id}"),
                "created":False,"max_sources":5}
        else:
            notebook = adapter.resolve_case_notebook(case_id, title=str(case.get("objective") or f"Nexus Research Case {case_id}"), max_sources=5)
        if existing_notebook and str(existing_notebook) != str(notebook.get("notebook_id")):
            return {"ok":False,"reason":"CASE_NOTEBOOK_ID_MISMATCH","bound_notebook_id":existing_notebook,
                "resolved_notebook_id":notebook.get("notebook_id")}
        cases.bind_notebook_workspace(case_id, notebook)
        notebook_sources = []
        for row in case.get("sources") or []:
            if not isinstance(row,dict):
                continue
            if row.get("notebook_id") and str(row.get("notebook_id")) != str(notebook["notebook_id"]):
                continue
            source_id=row.get("notebook_source_id") or row.get("source_id")
            if source_id:
                notebook_sources.append({"id":str(source_id),"title":row.get("title"),"url":row.get("url")})
        if not notebook_sources:
            notebook_sources = adapter.sources(notebook["notebook_id"])
        state = load_completion_state(case_id=case_id)
        if not state or state.get("contract_id") != contract["contract_id"]:
            state = new_contract_state(objective=str(case.get("objective") or ""),
                research_purpose=contract["research_purpose"],research_domain=contract["research_domain"],
                notebook_id=notebook["notebook_id"],source_inventory=case.get("sources") or [],
                research_job_id=source_work_id)
        state["notebook_id"] = notebook["notebook_id"]
        state["research_job_id"] = source_work_id or state.get("research_job_id")
        if contract["research_domain"] == "BUSINESS_OPPORTUNITY":
            from nexus_agent_platform import business_opportunity_research_v2 as bo
            state["opportunity_context"] = next((row for row in bo.load_opportunity_contexts()
                if row.get("opportunity_id") == case.get("opportunity_id")
                or row.get("research_case_id") == case_id), state.get("opportunity_context") or {})
            try:
                registry = json.loads(nexus_research_state_path("runtime", "nova_live_capability_registry.json").read_text(encoding="utf-8"))
                capability_rows = registry.get("capabilities") if isinstance(registry,dict) else []
                capability_states = {str(row.get("capability")): {"status":str(row.get("status") or "UNAVAILABLE"),
                    "health":str(row.get("health") or "NOT_TESTED")} for row in capability_rows if isinstance(row,dict)}
                state["verified_nexus_capabilities"] = [name for name, value in capability_states.items()
                    if value["status"].upper() in {"ACTIVE","AVAILABLE","WORKING","CONNECTED"}]
                state["nexus_fast_validation"] = bo.fast_validation_path(
                    state["opportunity_context"],capabilities=capability_states)
                state["opportunity_context"]["verified_nexus_capabilities"] = state["verified_nexus_capabilities"]
                state["opportunity_context"]["fast_validation_model"] = state["nexus_fast_validation"]
            except (OSError,ValueError,TypeError):
                state["verified_nexus_capabilities"] = []
                state["nexus_fast_validation"] = {"status":"CAPABILITY_REGISTRY_UNAVAILABLE",
                    "capabilities_assumed_available":False}
            state["execution_model"] = {"workflow_first":True,"alpha_mode":"RESEARCH_DIRECTOR",
                "post_research_evaluator_separate":True,"feeder_role":"INTAKE_ONLY",
                "notebook_role":"DEDICATED_RESEARCH"}
        state["source_inventory"] = [{"source_id":x.get("source_id") or x.get("id"),"notebook_source_id":x.get("notebook_source_id") or x.get("id"),
            "url":x.get("url"),"title":x.get("title"),"source_class":x.get("source_class"),"source_date":x.get("source_date"),
            "last_verified_at":x.get("last_verified_at"),"evidence_status":x.get("evidence_status")} for x in (case.get("sources") or [])]
        if not state["source_inventory"]:
            state["source_inventory"]=[{"source_id":x.get("id"),"notebook_source_id":x.get("id"),
                "title":x.get("title"),"url":x.get("url")} for x in notebook_sources if x.get("id")]
        if contract["research_domain"] == "BUSINESS_OPPORTUNITY" and adaptive_director:
            # Alpha frames the mission before Research executes its first group.
            # The director may add only material questions; answers remain the
            # responsibility of NotebookLM/Research.
            if not state.get("initial_director_review_complete"):
                initial = _business_opportunity_director_review(state, case=case, event="OPPORTUNITY_FORMATION",
                    findings=[], adapter=adapter, operation=director_operation)
                if not initial.get("ok"):
                    cases._save(case, "ALPHA_RESEARCH_DIRECTOR_WAITING", status="WAITING_PROVIDER",
                        continue_research=True, next_research_action="RETRY_ALPHA_RESEARCH_DIRECTOR")
                    return {"ok":False,"reason":initial.get("reason"),"detail":initial.get("detail"),
                        "case_id":case_id,"notebook_id":notebook["notebook_id"],"same_notebook_reused":True}
                state["initial_director_review_complete"] = True
                state["initial_director_question_ids"] = initial.get("added_question_ids", [])
                state["local_state_ref"] = persist_completion_state(state, case_id=case_id)
        # Execute a known domain contract in coherent groups. Question IDs
        # remain the stable contract IDs; groups only bound NotebookLM prompts.
        pending_ids={row.get("question_id") for row in state.get("required_questions",[])
            if row.get("required") and not row.get("asked")}
        completed_groups=[]
        for group in question_groups(state):
            rows=[row for row in group["questions"] if row.get("question_id") in pending_ids]
            if not rows:
                continue
            prompt=build_question_group_prompt(state,group["group_id"],rows)
            turn=adapter.ask_notebook(notebook["notebook_id"],prompt)
            refs=[str(x.get("source_id")) for x in turn.get("references",[]) if x.get("source_id")]
            allowed_source_ids={str(x.get("id")) for x in notebook_sources if x.get("id")}
            foreign_refs=[ref for ref in refs if ref not in allowed_source_ids]
            if foreign_refs:
                return {"ok":False,"reason":"NOTEBOOK_COMPLETION_SOURCE_CONTAMINATION","foreign_reference_ids":foreign_refs}
            answer=str(turn.get("answer") or "")
            register_notebook_submission(state,prompt=prompt,submission_confirmed=bool(turn.get("submission_confirmed")),
                response=answer,source_refs=refs)
            cases.record_notebook_answer(case_id,question_type=f"CONTRACT_GROUP:{state['contract_id']}:{group['group_id']}",
                answer=answer,notebook_id=notebook["notebook_id"],source_ids=refs,conversation_id=turn.get("conversation_id"),
                submission_attempted=turn.get("submission_attempted",False),submission_confirmed=turn.get("submission_confirmed",False),
                response_reference=turn.get("response_reference"),prompt=prompt,response_id=turn.get("correlation_id"))
            completed_groups.append(group["group_id"])
            state["question_groups_completed"] = sorted(set(state.get("question_groups_completed",[]))|{group["group_id"]})
            state["local_state_ref"] = persist_completion_state(state,case_id=case_id)
            if contract["research_domain"] == "BUSINESS_OPPORTUNITY" and adaptive_director:
                # One bounded advisory critique at formation, after first
                # findings. Its suggestions are hypotheses; Alpha selects any
                # question that Research should verify.
                if group["group_id"] == "GROUP_A_DEFINITION" and not state.get("outside_advisor_formation_called"):
                    try:
                        from nexus_agent_platform.business_opportunity_research_v2 import execute_outside_advisor
                        advice = execute_outside_advisor(objective=str(state.get("objective") or ""),
                            context={"objective":state.get("objective"),"current_hypothesis":answer[:1800],
                                "verified_findings":[],"partial_findings":[],"unverified_findings":[],
                                "key_economics":{},"open_questions":state.get("evidence_gaps",[]),"major_risks":[]})
                        state["outside_advisor_feedback"] = {"event":"OPPORTUNITY_FORMATION",
                            "hypotheses_only":True,"evidence_created":False,"advice":advice.get("advice"),
                            "model_execution":advice.get("model_execution")}
                    except Exception as exc:
                        state["outside_advisor_feedback"] = {"event":"OPPORTUNITY_FORMATION",
                            "status":"UNAVAILABLE","error_class":type(exc).__name__,"hypotheses_only":True}
                    state["outside_advisor_formation_called"] = True
                    state["local_state_ref"] = persist_completion_state(state,case_id=case_id)
                finding = {"group_id":group["group_id"],"answer":answer[:3500],"source_refs":refs}
                review = _business_opportunity_director_review(state, case=case,
                    event=f"AFTER_{group['group_id']}", findings=[finding], adapter=adapter,
                    operation=director_operation)
                if not review.get("ok"):
                    cases._save(cases.get_case(case_id) or case, "ALPHA_RESEARCH_DIRECTOR_WAITING",
                        status="WAITING_PROVIDER", continue_research=True,
                        next_research_action="RETRY_ALPHA_RESEARCH_DIRECTOR")
                    return {"ok":False,"reason":review.get("reason"),"detail":review.get("detail"),
                        "case_id":case_id,"notebook_id":notebook["notebook_id"],
                        "completed_groups":completed_groups,"same_notebook_reused":True}

        # Reconcile responses already persisted by a previous attempt before
        # deciding which gaps require external supplementation. This is also
        # safe on a first attempt and remains deterministic.
        case = cases.get_case(case_id) or case
        _reconcile_contract_group_statuses(case_id, state, case)

    # Supplement only unresolved evidence after reconciling saved answers.
    pending = _material_gap_order([g for g in state.get("evidence_gaps",[]) if not g.get("reviewed")])
    question_to_group={row["question_id"]:group["group_id"] for group in question_groups(state)
        for row in group["questions"]}
    by_group: dict[str,list[dict[str,Any]]] = {}
    for gap in pending:
        by_group.setdefault(question_to_group.get(str(gap.get("question_id")),"GROUP_UNMAPPED_REMAINDER"),[]).append(gap)
    supplements=[]; source_budget=max(0,int(max_added_sources))
    gap_groups=list(by_group.items())
    gap_rank={gap.get("question_id"):index for index,gap in enumerate(pending)}
    gap_groups.sort(key=lambda item:min(gap_rank.get(gap.get("question_id"),999) for gap in item[1]))
    for group_id,gaps in gap_groups[:max(0,min(int(max_supplement_questions),9))]:
        try:
            result=_supplement_contract_group_native(case_id,state=state,adapter=adapter,gaps=gaps,
                source_budget=min(source_budget,2))
        except Exception as exc:
            result={"ok":False,"execution_status":"PROVIDER_FAILURE","provider_error":f"{type(exc).__name__}:{str(exc)[:180]}","added_sources":[]}
        added=result.get("added_sources") or result.get("added") or []
        source_budget=max(0,source_budget-len(added))
        supplements.append({"group_id":group_id,"question_ids":result.get("question_ids") or [g.get("question_id") for g in gaps],
            "execution_status":result.get("execution_status") or ("COMPLETED" if result.get("ok") else result.get("execution_status")),
            "web_query":result.get("web_query"),"sources_added":len(added),"source_count_before":result.get("source_count_before"),
            "source_count_after":result.get("source_count_after"),"targeted_question_confirmed":result.get("targeted_question_confirmed"),
            "answer_statuses":result.get("answer_statuses"),"source_add_failures":result.get("source_add_failures") or [],
            "attempted":True,"error":result.get("provider_error") or result.get("reason")})
        state["local_state_ref"] = persist_completion_state(state,case_id=case_id)

    if any(row.get("sources_added") for row in supplements):
        notebook_sources=adapter.sources(notebook["notebook_id"])
        case=cases.get_case(case_id) or case
        state["source_inventory"]=[{"source_id":x.get("source_id") or x.get("id"),
            "notebook_source_id":x.get("notebook_source_id") or x.get("id"),"url":x.get("url"),
            "title":x.get("title"),"source_class":x.get("source_class"),"source_date":x.get("source_date"),
            "last_verified_at":x.get("last_verified_at"),"evidence_status":x.get("evidence_status")}
            for x in (case.get("sources") or []) if not x.get("notebook_id") or str(x.get("notebook_id"))==str(notebook["notebook_id"])]
        state["local_state_ref"]=persist_completion_state(state,case_id=case_id)

    if bounded_scope_note:
        # A bounded process canary is not an opportunity assessment. Preserve
        # every out-of-scope answer as UNVERIFIED and mark why no further web
        # supplementation is appropriate for this canary's narrow question.
        for gap in state.get("evidence_gaps",[]):
            if not gap.get("reviewed"):
                record_gap_out_of_scope(state,question_id=str(gap.get("question_id") or ""),
                    reason=f"Out of scope for bounded canary: {bounded_scope_note}")
        state["local_state_ref"] = persist_completion_state(state,case_id=case_id)

    # Final synthesis is requested only after this cycle's source additions and
    # follow-up reads. If NotebookLM cannot return structured deliverables,
    # the contract stays incomplete rather than manufacturing them.
    with adapter._job_slot():
        final_prompt=build_synthesis_prompt(state)
        synthesis_type=f"CONTRACT_SYNTHESIS:{state['contract_id']}"
        prior_synthesis=_load_persisted_notebook_answer(case,question_type=synthesis_type,
            notebook_id=notebook["notebook_id"])
        if prior_synthesis:
            # Recover a response whose NotebookLM call completed before a
            # worker interruption, using its existing local artifact and hash.
            final_turn=prior_synthesis
            final_answer=prior_synthesis["answer"]
            final_refs=prior_synthesis["source_ids"]
        else:
            final_turn=adapter.ask_notebook(notebook["notebook_id"],final_prompt)
            final_answer=str(final_turn.get("answer") or "")
            final_refs=[str(x.get("source_id")) for x in final_turn.get("references",[]) if x.get("source_id")]
        # The case already carries verified source IDs for this bound notebook.
        # Re-listing after a successful NotebookLM answer is redundant and can
        # be rejected as an idempotent replay when resuming a durable job.
        current_ids={str(x.get("id")) for x in notebook_sources if x.get("id")}
        if any(ref not in current_ids for ref in final_refs):
            return {"ok":False,"reason":"NOTEBOOK_COMPLETION_SYNTHESIS_CONTAMINATION"}
        if not prior_synthesis:
            cases.record_notebook_answer(case_id,question_type=synthesis_type,answer=final_answer,
                notebook_id=notebook["notebook_id"],source_ids=final_refs,
                conversation_id=final_turn.get("conversation_id"),submission_attempted=final_turn.get("submission_attempted",False),
                submission_confirmed=final_turn.get("submission_confirmed",False),response_reference=final_turn.get("response_reference"),
                prompt=final_prompt,response_id=final_turn.get("correlation_id"))
        deliverables=extract_deliverables(final_answer)
        set_synthesis(state,synthesis=deliverables.get("synthesis") or "",action_statement=deliverables.get("action_statement") or {},
            structured_extraction=deliverables.get("structured_extraction") or {})
    if state.get("research_domain") == "BUSINESS_OPPORTUNITY":
        from nexus_agent_platform import business_opportunity_research_v2 as bo
        context = dict(state.get("opportunity_context") or {})
        extraction = state.get("structured_extraction") or {}
        action = state.get("action_statement") or {}
        context.update({"notebook_id":state.get("notebook_id"),"research_case_id":case_id,
            "research_job_id":source_work_id,"status":"RESEARCH_SYNTHESIZED",
            "verified_findings":extraction.get("key_verified_findings") or extraction.get("verified_findings") or [],
            "partial_findings":extraction.get("partially_verified_findings") or extraction.get("partial_findings") or [],
            "unverified_findings":extraction.get("unverified_findings") or [],
            "contradicted_findings":extraction.get("contradicted_findings") or [],
            "major_risks":extraction.get("major_risks") or [],
            "major_assumptions":extraction.get("major_assumptions") or [],
            "action_statement":action,"synthesis_summary":state.get("synthesis"),
            "next_department":"BUSINESS_OPPORTUNITIES","needle_status":"PENDING"})
        context["fastest_validation_model"] = action.get("FASTEST_VALIDATION_MODEL") or action.get("FASTEST_VALIDATION_PATH")
        context["fastest_launchable_version"] = action.get("FASTEST_LAUNCHABLE_VERSION")
        context["estimated_days_to_launch"] = action.get("ESTIMATED_DAYS_TO_LAUNCH")
        context["estimated_incremental_cash"] = action.get("ESTIMATED_INCREMENTAL_CASH")
        context["first_revenue_path"] = action.get("FIRST_REVENUE_PATH")
        context["success_signal"] = action.get("SUCCESS_SIGNAL")
        context["pivot_signal"] = action.get("PIVOT_SIGNAL")
        context["what_not_to_build_until_validated"] = action.get("WHAT_NOT_TO_BUILD_UNTIL_VALIDATED")
        if context.get("opportunity_id"):
            state["opportunity_context"] = bo.save_opportunity_context(context)
        else:
            state["opportunity_context"] = context

    state["local_state_ref"] = persist_completion_state(state,case_id=case_id)
    receipt_id="ncc_"+uuid.uuid4().hex[:18]
    state["verification_status"]="READY_FOR_HANDOFF"
    state["handoff_package"]=compact_handoff(state,receipt_id=receipt_id)
    state["local_state_ref"] = persist_completion_state(state,case_id=case_id)
    base_verification=verify_completion(state,web_supplementation_appropriate=bool(state.get("evidence_gaps")))
    library_entry=None; handoff=None; needle_result=None; needle_repair=None
    verification={"ok":False,"verification":base_verification}
    needle_job=None
    if base_verification.get("complete"):
        # Semantic review runs as its own bounded durable job. The Research
        # worker exits after this checkpoint; it does not call a model or
        # create the downstream handoff itself.
        from nexus_agent_platform.needle_research_workflow import enqueue_job
        state["verification_status"]="NEEDLE_VERIFICATION_QUEUED"
        state["handoff_package"]=compact_handoff(state,receipt_id=receipt_id)
        state["local_state_ref"]=persist_completion_state(state,case_id=case_id)
        needle_job=enqueue_job(case_id=case_id,job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
            completion_receipt_id=receipt_id,repair_attempt=int(state.get("needle_repair_count") or 0))
        verification={"ok":False,"verification":base_verification,
            "needle_verification_queued":True,"needle_job_id":needle_job.get("job_id")}
    elif not base_verification.get("complete"):
        state["verification_status"]="MECHANICAL_INCOMPLETE"
        verification={"ok":False,"verification":base_verification}
    state["local_state_ref"] = persist_completion_state(state,case_id=case_id)
    case=cases.get_case(case_id) or case
    cases._save(case,"NOTEBOOK_COMPLETION_CONTRACT_CHECKPOINT",
        notebook_completion_contract=_contract_summary(state,verification.get("verification")),
        notebook_playbook={**(case.get("notebook_playbook") or {}),"contract_id":state["contract_id"],
            "notebook_id":state["notebook_id"],"verification_status":state["verification_status"],
            "ready_for_handoff":bool(verification.get("ok"))},
        status="MORE_RESEARCH_REQUIRED" if not verification.get("ok") else "SYNTHESIZING",
        continue_research=not bool(verification.get("ok")),
        next_research_action=("WAIT_FOR_NEEDLE_VERIFICATION" if needle_job else
            "CONTINUE_BOUNDED_NOTEBOOK_GAP_SUPPLEMENTATION"))
    receipt={"receipt_id":state.get("completion_receipt_id"),"case_id":case_id,"source_work_id":source_work_id,
        "contract_id":state["contract_id"],"research_purpose":state["research_purpose"],"research_domain":state["research_domain"],
        "notebook_id":state["notebook_id"],"question_counts":question_counts(state),"supplementation_attempts":supplements,
        "verification":verification.get("verification"),"verification_status":state["verification_status"],
        "needle_job":needle_job,"needle_verification":state.get("needle_verification"),"needle_repair":state.get("needle_repair"),
        "library_entry_ids":(library_entry or {}).get("library_entry_ids",[]),"library_write_status":(library_entry or {}).get("status"),
        "handoff_id":(handoff or {}).get("handoff_id"),
        "no_full_notebook_mirror_to_supabase":True,"local_state_ref":state.get("local_state_ref"),
        "recorded_at":datetime.now(timezone.utc).isoformat()}
    _record(receipt)
    return {"ok":bool(verification.get("ok")),**receipt,"action_statement":state.get("action_statement"),
        "structured_extraction":state.get("structured_extraction"),"next_research_action":("WAIT_FOR_NEEDLE_VERIFICATION" if needle_job else
            "CONTINUE_BOUNDED_NOTEBOOK_GAP_SUPPLEMENTATION")}


def run_case_playbook(case_id: str, *, adapter: NotebookLMResearchAdapter | None = None,
                      ask_followup: bool = True, source_work_id: str | None = None,
                      bounded_scope_note: str | None = None, adaptive_director: bool = True,
                      director_operation: Any = None) -> dict[str, Any]:
    case = cases.get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND", "case_id": case_id}
    resolution=_contract_purpose_domain(case)
    if resolution.get("status")=="RESOLVED":
        adapter=adapter or NotebookLMResearchAdapter(AdapterConfig(profile="default"))
        return _run_completion_contract_case(case_id,case=case,contract_resolution=resolution,
            adapter=adapter,source_work_id=source_work_id,max_supplement_questions=9 if ask_followup else 0,
            max_added_sources=10 if ask_followup else 0,
            bounded_scope_note=bounded_scope_note, adaptive_director=adaptive_director,
            director_operation=director_operation)
    return _run_legacy_case_playbook(case_id,adapter=adapter,ask_followup=ask_followup,source_work_id=source_work_id)


def _run_legacy_case_playbook(case_id: str, *, adapter: NotebookLMResearchAdapter | None = None,
                      ask_followup: bool = True, source_work_id: str | None = None) -> dict[str, Any]:
    case = cases.get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND", "case_id": case_id}
    binding = case.get("notebook_playbook") or {}
    playbook = select_playbook(objective_family=case.get("objective_family", ""),
        owner_department=case.get("owner_department", ""), current_goal=case.get("business_or_nexus_goal", ""),
        case_context=case.get("objective", ""))
    if binding.get("case_type"):
        from notebook_playbooks import load_registry
        playbook = load_registry()[binding["case_type"]]
    adapter = adapter or NotebookLMResearchAdapter(AdapterConfig(profile="default"))
    sources = list(case.get("sources") or [])
    notebook_id = ((case.get("notebook_workspace") or {}).get("notebook_id")
                   or next((row.get("notebook_id") for row in sources if row.get("notebook_id")), None))
    notebook_title = f"Nexus Research Case {case_id}"
    with adapter._job_slot():
        notebook = adapter.resolve_case_notebook(case_id, title=str(case.get("objective") or notebook_title), max_sources=5)
        if notebook_id and notebook_id != notebook["notebook_id"]:
            return {"ok": False, "reason": "CASE_NOTEBOOK_ID_MISMATCH", "case_id": case_id,
                    "bound_notebook_id": notebook_id, "resolved_notebook_id": notebook["notebook_id"]}
        cases.bind_notebook_workspace(case_id, notebook)
        notebook_sources = adapter.sources(notebook["notebook_id"])
        known_ids = {str(row.get("id")) for row in notebook_sources}
        attached = {str(row.get("notebook_source_id") or row.get("research_source_id") or row.get("source_id"))
                    for row in sources}
        if attached and not (attached & known_ids):
            return {"ok": False, "reason": "CASE_NOTEBOOK_SOURCE_BINDING_UNVERIFIED", "case_id": case_id,
                    "notebook_id": notebook["notebook_id"], "notebook_source_count": len(notebook_sources)}
        prompt = build_notebook_prompt(playbook, case)
        first = adapter.ask_notebook(notebook["notebook_id"], prompt)
        answer = str(first["answer"])
        allowed_ids = {str(row.get("id")) for row in notebook_sources if row.get("id")}
        foreign_refs = [str(row.get("source_id")) for row in (first.get("references") or [])
                        if row.get("source_id") and str(row.get("source_id")) not in allowed_ids]
        if foreign_refs:
            return {"ok": False, "reason": "NOTEBOOK_PLAYBOOK_SOURCE_CONTAMINATION",
                    "foreign_reference_ids": foreign_refs, "case_id": case_id}
        result = analyze_answer(answer, list(playbook.get("required_questions") or []), playbook)
        synthesis_summary = _synthesis_summary(answer)
        cases.record_notebook_answer(case_id, question_type=f"PLAYBOOK:{playbook['case_type']}", answer=answer,
            notebook_id=notebook["notebook_id"], source_ids=sorted(known_ids),
            conversation_id=first.get("conversation_id"),
            submission_attempted=first.get("submission_attempted", False),
            submission_confirmed=first.get("submission_confirmed", False),
            response_reference=first.get("response_reference"))

        created_questions = []
        for disposition in result["open"]:
            question = str(disposition["question"])
            added = cases.add_question(case_id, question, why_it_matters=disposition["why_it_matters"],
                                       best_source_classes=disposition["best_source_classes"])
            if added.get("created"):
                created_questions.append(added["question"])

        followup = None
        # A real follow-up is required for unresolved required sections even
        # when equivalent question objects already existed locally.
        if ask_followup and result["open"]:
            fresh = cases.get_case(case_id) or case
            followup_rows = list(fresh.get("open_questions") or [])
            if not followup_rows:
                followup_rows = [{"question": row["question"]} for row in created_questions]
            followup_case = {**fresh, "open_questions": followup_rows[:3]}
            second_prompt = build_notebook_prompt(playbook, followup_case, followup=True)
            followup = adapter.ask_notebook(notebook["notebook_id"], second_prompt)
            foreign_refs = [str(row.get("source_id")) for row in (followup.get("references") or [])
                            if row.get("source_id") and str(row.get("source_id")) not in allowed_ids]
            if foreign_refs:
                return {"ok": False, "reason": "NOTEBOOK_PLAYBOOK_FOLLOWUP_SOURCE_CONTAMINATION",
                        "foreign_reference_ids": foreign_refs, "case_id": case_id}
            cases.record_notebook_answer(case_id, question_type=f"PLAYBOOK_FOLLOWUP:{playbook['case_type']}",
                answer=str(followup["answer"]), notebook_id=notebook["notebook_id"],
                source_ids=sorted(known_ids), conversation_id=followup.get("conversation_id"),
                submission_attempted=followup.get("submission_attempted", False),
                submission_confirmed=followup.get("submission_confirmed", False),
                response_reference=followup.get("response_reference"))

    receipt = {"receipt_id": "npr_" + uuid.uuid4().hex[:18], "case_id": case_id,
        "source_work_id": source_work_id,
        "playbook_id": playbook["playbook_id"], "case_type": playbook["case_type"],
        "playbook_version": playbook["version"], "notebook_id": notebook["notebook_id"],
        "questions_asked": len(playbook.get("required_questions") or []),
        "question_dispositions": result["question_dispositions"],
        "questions_answered": result["answered_count"], "questions_open": len(result["open"]),
        "followup_questions_created": len(created_questions),
        "followup_questions": created_questions,
        "synthesis_summary": synthesis_summary,
        "additional_sources_added": 0, "source_ids": sorted(known_ids),
        "references_first": first.get("references", []),
        "references_followup": (followup or {}).get("references", []),
        "initial_prompt_submission_confirmed": bool(first.get("submission_confirmed")),
        "initial_prompt": prompt,
        "initial_prompt_sha256": first.get("prompt_sha256"),
        "initial_response_reference": first.get("response_reference"),
        "initial_response_received_at": first.get("response_received_at"),
        "initial_verification_method": first.get("verification_method"),
        "followup_submissions_confirmed": bool(followup and followup.get("submission_confirmed")),
        "followup_prompt": second_prompt if followup else None,
        "followup_prompt_sha256": (followup or {}).get("prompt_sha256"),
        "followup_prompt_question_count": (len(followup_rows[:3]) if followup else 0),
        "followup_response_reference": (followup or {}).get("response_reference"),
        "followup_response_received_at": (followup or {}).get("response_received_at"),
        "followup_verification_method": (followup or {}).get("verification_method"),
        "source_count": len(notebook_sources), "first_conversation_id": first.get("conversation_id"),
        "followup_conversation_id": (followup or {}).get("conversation_id"),
        "first_answer": answer[:18000], "followup_answer": str((followup or {}).get("answer") or "")[:12000],
        "next_research_action": "EXPAND_SOURCES_FOR_OPEN_PLAYBOOK_QUESTIONS" if result["open"] else "SYNTHESIZE_CASE_RECOMMENDATION",
        "ready_for_handoff": False,
        "recorded_at": datetime.now(timezone.utc).isoformat()}
    _record(receipt)
    fresh = cases.get_case(case_id) or case
    cases._save(fresh, "NOTEBOOK_PLAYBOOK_RUN_COMPLETED", notebook_playbook_run_id=receipt["receipt_id"],
        notebook_playbook={"playbook_id":playbook["playbook_id"],"case_type":playbook["case_type"],
          "version":playbook["version"],"selection_reason":playbook.get("selection_reason", "BOUND_TO_EXISTING_CASE"),
          "last_run_at":receipt["recorded_at"], "notebook_id":notebook["notebook_id"],
          "last_source_count_at_run":len(fresh.get("sources") or []),
          "questions_asked":receipt["questions_asked"],"questions_answered":receipt["questions_answered"],
          "questions_open":receipt["questions_open"],"sources":receipt["source_ids"],
          "new_sources_added":0,"current_gaps":[q["question"] for q in (fresh.get("open_questions") or [])[:10]],
          "current_recommendation":synthesis_summary.get("recommendation_class"),
          "synthesis_summary":synthesis_summary,"ready_for_handoff":False},
        status="MORE_RESEARCH_REQUIRED" if created_questions else "SYNTHESIZING",
        continue_research=True, next_research_action=receipt["next_research_action"])
    return {"ok": True, **receipt, "open_questions": (cases.get_case(case_id) or {}).get("open_questions", [])}


def continue_from_playbook_answer(case_id: str, *, answer: str, notebook_id: str,
                                 adapter: NotebookLMResearchAdapter | None = None,
                                 max_followups: int = 3) -> dict[str, Any]:
    """Turn explicit partial/unknown answer sections into bounded case questions."""
    case = cases.get_case(case_id)
    if not case:
        return {"ok": False, "reason": "CASE_NOT_FOUND"}
    playbook = select_playbook(objective_family=case.get("objective_family", ""),
        owner_department=case.get("owner_department", ""), case_context=case.get("objective", ""))
    from notebook_playbooks import load_registry
    playbook = load_registry()[playbook["case_type"]]
    statuses = analyze_answer(answer, playbook["required_questions"], playbook)
    candidates = []
    existing_questions=[str(q.get("question") or "").casefold() for q in (case.get("open_questions") or [])]
    for index, disposition in enumerate(statuses["question_dispositions"],1):
        status_value=str(disposition.get("status") or "").upper()
        if status_value not in {"PARTIALLY_ANSWERED","UNANSWERED","CONTRADICTORY"}:
            continue
        section_match=re.search(rf"^\s*#{{1,6}}\s*(?:Question\s+)?{index}\s*[.:][^\n]*[\s\S]*?(?=^\s*#{{1,6}}\s*(?:Question\s+)?{index+1}\s*[.:]|\Z)",answer,re.IGNORECASE|re.MULTILINE)
        section=section_match.group(0) if section_match else ""
        unknown=re.search(r"\*\*(?:What Remains Unknowns?|Remaining Unknowns?)(?::)?\*\*\s*:?[ \t]*(.+?)(?:\n|$)",section,re.IGNORECASE)
        unknown_text=unknown.group(1).strip() if unknown else "Specific supporting evidence is incomplete; determine what is answerable from current sources and what requires an added source or test."
        base_q = playbook["required_questions"][index-1]
        if any(base_q.casefold()[:65] in q or (f"playbook question {index}" in q) for q in existing_questions):
            continue
        follow = (f"For playbook question {index}, {base_q} Resolve the documented gap: {unknown_text} "
                  "What does current case evidence establish, and what needs a new source or independent test?")
        candidates.append({"question": follow, "why_it_matters": f"NotebookLM marked playbook question {index} {status_value} and documented an unresolved evidence gap.",
                           "best_source_classes": gap_source_classes(base_q, playbook), "playbook_question": index})
    created = []
    for row in candidates:
        if len(created) >= max_followups:
            break
        result = cases.add_question(case_id, row["question"], why_it_matters=row["why_it_matters"],
                                    best_source_classes=row["best_source_classes"])
        if result.get("created"):
            created.append({**row, "question_id": result["question"]["question_id"]})
    followup = None
    if created:
        adapter = adapter or NotebookLMResearchAdapter(AdapterConfig(profile="default"))
        with adapter._job_slot():
            prompt = (f"Within case {case_id}, answer each numbered follow-up using only the sources already in this notebook. "
                      "For each, label ANSWERED/PARTIALLY_ANSWERED/UNANSWERED/CONTRADICTORY; cite the source; separate creator claims from verified facts; "
                      "if the notebook cannot answer, say so and identify the exact new source or independent Nexus test required.\n\n" +
                      "\n".join(f"{i+1}. {row['question']}" for i, row in enumerate(created)))
            followup = adapter.ask_notebook(notebook_id, prompt)
            known_ids = {str(row.get("id")) for row in adapter.sources(notebook_id) if row.get("id")}
            foreign = [str(row.get("source_id")) for row in followup.get("references", [])
                       if row.get("source_id") and str(row.get("source_id")) not in known_ids]
            if foreign:
                return {"ok": False, "reason": "NOTEBOOK_PLAYBOOK_FOLLOWUP_SOURCE_CONTAMINATION", "foreign_reference_ids": foreign}
            cases.record_notebook_answer(case_id, question_type=f"PLAYBOOK_FOLLOWUP:{playbook['case_type']}",
                answer=str(followup["answer"]), notebook_id=notebook_id, source_ids=sorted(known_ids),
                conversation_id=followup.get("conversation_id"),
                submission_attempted=followup.get("submission_attempted", False),
                submission_confirmed=followup.get("submission_confirmed", False),
                response_reference=followup.get("response_reference"))
    receipt = {"receipt_id":"npr_followup_"+uuid.uuid4().hex[:14],"case_id":case_id,
        "playbook_id":playbook["playbook_id"],"notebook_id":notebook_id,
        "questions_created":created,"questions_answered_by_notebook":bool(followup),
        "followup_answer":str((followup or {}).get("answer") or "")[:12000],
        "source_expansion_needed":True,"additional_sources_added":0,
        "next_research_action":"FETCH_GAP_MATCHED_SOURCES_INTO_SAME_CASE_NOTEBOOK" if created else "SYNTHESIZE_CASE",
        "recorded_at":datetime.now(timezone.utc).isoformat()}
    _record(receipt)
    fresh=cases.get_case(case_id) or case
    cases._save(fresh,"NOTEBOOK_PLAYBOOK_FOLLOWUPS_CREATED",notebook_playbook_run_id=receipt["receipt_id"],
        notebook_playbook={**(fresh.get("notebook_playbook") or {}),"last_followup_at":receipt["recorded_at"],
          "questions_open":len(fresh.get("open_questions") or []),"current_gaps":[q["question"] for q in created],
          "next_research_action":receipt["next_research_action"]},
        status="MORE_RESEARCH_REQUIRED" if created else fresh.get("status"),continue_research=True,
        next_research_action=receipt["next_research_action"])
    return {"ok":True,**receipt}


def expand_case_from_best_gap(case_id: str, *, adapter: NotebookLMResearchAdapter | None = None,
                              max_additions: int = 2, question_id: str | None = None,
                              question_text: str | None = None) -> dict[str, Any]:
    """Use the governed Hermes layer for an open case gap, then join results to its notebook."""
    case=cases.get_case(case_id)
    if not case:
        return {"ok":False,"reason":"CASE_NOT_FOUND"}
    workspace=case.get("notebook_workspace") or {}
    notebook_id=workspace.get("notebook_id") or next((r.get("notebook_id") for r in case.get("sources",[]) if r.get("notebook_id")),None)
    if not notebook_id:
        return {"ok":False,"reason":"CASE_NOTEBOOK_NOT_BOUND"}
    open_rows=list(case.get("open_questions") or [])
    if not open_rows and not (question_id and question_text):
        return {"ok":True,"reason":"NO_OPEN_CASE_GAP","added":[]}
    # Prefer a gap whose source classes are not already represented by the case.
    present={str(r.get("source_class") or "").upper() for r in case.get("sources",[])}
    chosen=(next((q for q in open_rows if str(q.get("question_id"))==str(question_id)),None) if question_id else None)
    chosen=chosen or (next((q for q in open_rows if set(str(v).upper() for v in q.get("best_source_classes",[])) - present),open_rows[0]) if open_rows else {})
    question=str(question_text or chosen.get("question") or "")
    try:
        from nexus_agent_platform.research_tool_layer import execute_research_question, plan_source_strategy
        strategy=plan_source_strategy(question,evidence_needed="Find current, direct evidence for this existing case gap; source snippets alone do not answer it.")
        # Preserve domain evidence classes from the playbook while allowing the governed planner to choose tools.
        strategy["source_classes_planned"]=list(dict.fromkeys(list(chosen.get("best_source_classes") or [])+list(strategy.get("source_classes_planned") or [])))
        result=execute_research_question(question,objective_family=str(case.get("objective_family") or "GENERAL_DISCOVERY"),
            source_strategy=strategy,research_case_id=case_id,originating_goal_id=case.get("originating_goal_id"),
            mode="autonomous",timeout_seconds=220,max_searches=3,max_pages=4)
    except Exception as exc:
        result={"execution_status":"PROVIDER_FAILURE","provider_error":type(exc).__name__+":"+str(exc)[:180],"records":[]}
    records=list(result.get("records") or []) if result.get("execution_status") not in {"PROVIDER_FAILURE","FAILED"} else []
    fallback_used=False
    fallback_reason=None
    if not records and result.get("execution_status")=="PROVIDER_FAILURE":
        # Reuse the established local HTML resilience path only after the
        # governed provider returns a classified failure. SERP rows remain
        # candidates; NotebookLM indexing/extraction is still required.
        try:
            from nexus_agent_platform.proactive_discovery import web_search
            found=web_search(question, min(5,max_additions*3))
            records=[{**row,"source_class":"UNKNOWN","extraction_status":"CANDIDATE_NOT_EXTRACTED",
                      "extracted_evidence":"","reported_evidence_role":"UNKNOWN"}
                     for row in found.get("results",[]) if row.get("url")]
            fallback_used=True
            fallback_reason=result.get("provider_error") or "GOVERNED_PROVIDER_FAILURE"
        except Exception as exc:
            fallback_reason=(result.get("provider_error") or "GOVERNED_PROVIDER_FAILURE")+";LOCAL_HTML:"+type(exc).__name__
    adapter=adapter or NotebookLMResearchAdapter(AdapterConfig(profile="default"))
    added=[]
    with adapter._job_slot():
        existing=adapter.sources(notebook_id)
        known_urls={str(x.get("url") or "").rstrip("/").lower() for x in existing}
        room=max(0,min(max_additions,5-len(existing)))
        for record in records:
            url=str(record.get("url") or "").strip()
            if not url or url.rstrip("/").lower() in known_urls or room<=0:
                continue
            source=adapter.add_source(notebook_id,url,video_title=str(record.get("title") or url))
            source_id=str(source.get("id"))
            indexed=adapter.wait_for_source(notebook_id,source_id)
            item={"source_id":source_id,"notebook_source_id":source_id,"notebook_id":notebook_id,
                "url":url,"title":record.get("title"),"source_class":record.get("source_class") or "UNKNOWN",
                "source_date":record.get("source_date"),"extraction_status":"NOTEBOOKLM_INDEXED_PENDING_PLAYBOOK_READ",
                "extracted_evidence":str(record.get("extracted_evidence") or "")[:1200],"evidence_role":record.get("reported_evidence_role"),
                "identity":url,"notebook_index_status":indexed.get("status")}
            cases.add_source(case_id,item)
            known_urls.add(url.rstrip("/").lower()); added.append(item); room-=1
        notebook_followup=None
        if added:
            prompt=(f"For case {case_id}, assess the new source(s) just added against this exact open question [{question_id or chosen.get('question_id') or 'UNTRACKED'}]: {question}\n"
                "Read source content, do not rely on search snippets. Report title, URL, source date if present, "
                "source type (firsthand/secondary/review/official/vendor/other), directly relevant evidence, "
                "limitations, and whether it resolves the question. Return evidence_status VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, or CONTRADICTED. If it does not, name the remaining gap. "
                "Do not infer local demand or economic viability from general claims.")
            notebook_followup=adapter.ask_notebook(notebook_id,prompt)
            current_sources=adapter.sources(notebook_id)
            allowed={str(x.get("id")) for x in current_sources if x.get("id")}
            foreign=[str(x.get("source_id")) for x in notebook_followup.get("references",[])
                     if x.get("source_id") and str(x.get("source_id")) not in allowed]
            if foreign:
                return {"ok":False,"reason":"NOTEBOOK_PLAYBOOK_SOURCE_EXPANSION_CONTAMINATION","foreign_reference_ids":foreign}
            cases.record_notebook_answer(case_id,question_type="PLAYBOOK_SOURCE_EXPANSION",answer=str(notebook_followup["answer"]),
                notebook_id=notebook_id,source_ids=sorted(allowed),conversation_id=notebook_followup.get("conversation_id"),
                submission_attempted=notebook_followup.get("submission_attempted", False),
                submission_confirmed=notebook_followup.get("submission_confirmed", False),
                response_reference=notebook_followup.get("response_reference"))
    receipt={"receipt_id":"npr_expand_"+uuid.uuid4().hex[:14],"case_id":case_id,"notebook_id":notebook_id,
        "question_id":chosen.get("question_id"),"question":question,"tools_selected":result.get("tools_selected") or result.get("tools_used"),
        "execution_status":result.get("execution_status"),"research_conclusion":result.get("research_conclusion"),
        "fallback_used":fallback_used,"fallback_reason":fallback_reason,
        "search_count":len(result.get("searches") or result.get("queries") or []),"sources_returned":len(records),
        "sources_added":len(added),"added_sources":[{"source_id":x["source_id"],"title":x["title"],"url":x["url"],"source_class":x["source_class"]} for x in added],
        "notebook_followup_answer":str((notebook_followup or {}).get("answer") or "")[:10000],
        "notebook_followup_prompt":prompt if added else None,
        "notebook_followup_submission_confirmed":bool((notebook_followup or {}).get("submission_confirmed")),
        "notebook_followup_response_history_reference":(notebook_followup or {}).get("response_reference"),
        "next_research_action":"ASK_NOTEBOOKLM_FOLLOWUP_IN_SAME_CASE" if added else "REFINE_SOURCE_STRATEGY_OR_USE_EXISTING_EVIDENCE",
        "recorded_at":datetime.now(timezone.utc).isoformat()}
    _record(receipt)
    fresh=cases.get_case(case_id) or case
    cases._save(fresh,"NOTEBOOK_PLAYBOOK_SOURCE_EXPANSION",notebook_playbook={**(fresh.get("notebook_playbook") or {}),
        "new_sources_added":len(added),"last_source_expansion_at":receipt["recorded_at"],
        "next_research_action":receipt["next_research_action"]},continue_research=True,
        next_research_action=receipt["next_research_action"])
    return {"ok":True,**receipt}
