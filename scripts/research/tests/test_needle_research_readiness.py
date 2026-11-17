import json
import types

import pytest

from research import needle_research_readiness as needle
from research import notebook_completion_contracts as contracts


def _state(domain="BUSINESS_OPPORTUNITY"):
    purpose="MISSION_RESEARCH" if domain in {"BUSINESS_OPPORTUNITY","FOREX"} else "LIBRARY_INTELLIGENCE"
    state=contracts.new_contract_state(objective="Research a concrete owner objective",
        research_purpose=purpose,research_domain=domain,notebook_id="nb-stable",research_job_id="job-research")
    for row in state["required_questions"]:
        row["asked"]=True
        row["evidence_status"]=row["answer_status"]="UNVERIFIED"
        row["supplementation_attempted"]=True
        row["source_refs"]=["src-1"]
    state["evidence_gaps"]=contracts._derive_gaps(state["required_questions"])
    contracts.record_gap_review(state,question_ids=[q["question_id"] for q in state["required_questions"]],
        supplementation_attempted=True,source_refs=["src-1"],unresolved_note="Unresolved after bounded research.")
    action={field:"evidence-qualified action" for field in contracts.CONTRACTS[state["contract_id"]]["action_fields"]}
    contracts.set_synthesis(state,synthesis="Objective-aligned synthesis with facts and unknowns separated.",
        action_statement=action,structured_extraction={"rules":[{"status":"UNVERIFIED"}]})
    state["handoff_package"]=contracts.compact_handoff(state,receipt_id="receipt-research")
    return state


def _complete():
    return {"complete":True,"criteria":{"all_required_questions_asked_at_least_once":True}}


def _router_for(answer, captured=None):
    captured=captured if captured is not None else {}
    def execute_reasoning(**kwargs):
        captured.update(kwargs)
        return {"result":{"choices":[{"message":{"content":json.dumps(answer)}}]},
            "provider":"openai-codex","model":"gpt-5.5","cost_class":"EXISTING_BUDGET",
            "latency_ms":12,"execution_metadata":{"resource_decision":"ALLOW_GOVERNED"}}
    return types.SimpleNamespace(execute_reasoning=execute_reasoning),captured


def _ready(state):
    downstream=contracts.CONTRACTS[state["contract_id"]]["handoff_department"]
    answer={"outcome":"READY_FOR_DEPARTMENT","reason_code":"READY","summary":"Usable with explicit external boundaries.",
        "affected_question_ids":[],"specific_gap":"","requested_research_action":"","evidence_needed":"",
        "unresolved_items_safe":True,"next_department":downstream}
    if state["contract_id"]=="BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1":
        ids=[str(g.get("question_id")) for g in state.get("evidence_gaps",[]) if g.get("question_id")]
        answer["source_exhaustion"]=True
        answer["external_boundaries"]=[{"question_ids":ids,"boundary":"A vendor-specific quote requires external supplier contact.",
            "required_actor":"supplier","sources_attempted":["official public pricing pages","public directories"]}]
    return answer


def _more(state, ids=None):
    downstream=contracts.CONTRACTS[state["contract_id"]]["handoff_department"]
    return {"outcome":"RESEARCH_MORE","reason_code":"UNSUPPORTED_CLAIM",
        "summary":"A material assertion is not supported.","affected_question_ids":ids or [state["required_questions"][0]["question_id"]],
        "specific_gap":"The asserted evidence status is stronger than the cited evidence.",
        "requested_research_action":"Check the official source for the claimed requirement and preserve absence of publication as unknown.",
        "evidence_needed":"Official product or regulator documentation.","unresolved_items_safe":False,
        "next_department":downstream}


def test_deterministic_incomplete_gate_never_calls_needle_router():
    router,captured=_router_for(_ready(_state()))
    state=_state(); state["required_questions"][0]["asked"]=False
    result=needle.verify_readiness(state,deterministic_result={"complete":False},router=router)
    assert result["status"]=="MECHANICAL_INCOMPLETE"
    assert not captured


def test_semantic_verification_uses_canonical_router_as_light_reasoning(tmp_path,monkeypatch):
    state=_state(); answer=_ready(state); router,captured=_router_for(answer)
    monkeypatch.setattr(needle,"ARTIFACT_ROOT",tmp_path / "artifacts")
    monkeypatch.setattr(needle,"RECEIPTS",tmp_path / "receipt.jsonl")
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    assert result["status"]=="READY_FOR_DEPARTMENT"
    assert captured["agent_key"]=="nexus_needle"
    assert captured["reasoning_class"]=="LIGHT_REASONING"
    assert captured["timeout_seconds"]==90
    assert captured["task_type"]=="research_readiness"
    assert captured["sensitivity"]=="internal_strategy"
    assert captured["payload"]["messages"]
    assert result["provider"]=="openai-codex"


def test_needles_prompt_checks_alignment_and_keeps_alpha_boundary():
    state=_state(); prompt=needle._build_prompt(state,deterministic_result=_complete(),repair_attempt=0)
    assert state["objective"] in prompt
    assert "objective alignment" in prompt.lower()
    assert "not Alpha" in prompt
    assert "must not invoke Alpha" in prompt
    assert "exactly 'BUSINESS_OPPORTUNITIES'" in prompt
    assert "Action Statement follows from the evidence" in prompt


def test_unsupported_verified_claim_returns_specific_research_more(tmp_path,monkeypatch):
    state=_state(); answer=_more(state); router,_=_router_for(answer)
    monkeypatch.setattr(needle,"ARTIFACT_ROOT",tmp_path / "artifacts")
    monkeypatch.setattr(needle,"RECEIPTS",tmp_path / "receipt.jsonl")
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    assert result["status"]=="RESEARCH_MORE"
    assert result["reason_code"]=="UNSUPPORTED_CLAIM"
    assert result["affected_question_ids"]==[state["required_questions"][0]["question_id"]]
    assert result["requested_research_action"] and result["evidence_needed"]


@pytest.mark.parametrize("domain",["BUSINESS_CREATION","BUSINESS_FUNDING","BUSINESS_OPPORTUNITY","FOREX"])
def test_explicit_unknowns_can_pass_and_domain_rubric_is_loaded(domain,tmp_path,monkeypatch):
    state=_state(domain); prompt=needle._build_prompt(state,deterministic_result=_complete(),repair_attempt=1)
    assert needle.RUBRICS[state["contract_id"]] in prompt
    router,_=_router_for(_ready(state))
    monkeypatch.setattr(needle,"ARTIFACT_ROOT",tmp_path / "artifacts")
    monkeypatch.setattr(needle,"RECEIPTS",tmp_path / "receipt.jsonl")
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=router,repair_attempt=1)
    assert result["status"]=="READY_FOR_DEPARTMENT" and result["unresolved_items_safe"]


def test_contradicted_status_is_preserved_in_semantic_input():
    state=_state(); state["required_questions"][0]["evidence_status"]="CONTRADICTED"
    package=needle._compact_input(state)
    assert package["required_questions"][0]["evidence_status"]=="CONTRADICTED"


def test_business_creation_folklore_rubric_rejects_universal_claims():
    text=needle.RUBRICS["BUSINESS_CREATION_NOTEBOOK_V1"].lower()
    assert "unsupported universal" in text and "truthful activity-based naics" in text
    assert "duns/tradeline" in text


def test_funding_rubric_separates_source_claim_from_verified_version():
    text=needle.RUBRICS["FUNDING_TECHNIQUE_INTELLIGENCE_NOTEBOOK_V1"]
    assert "SOURCE CLAIM" in text and "NEXUS VERIFIED VERSION" in text
    assert "unsupported claim labeled verified" in text


def test_opportunity_rubric_requires_comparable_candidates_without_ranking():
    text=needle.RUBRICS["BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1"]
    assert "every candidate" in text and "comparable dimensions" in text
    assert "Needle must not rank the final commercial winner" in text
    assert "25-output Research Deliverable Contract" in text
    assert "genuine external actor/action" in text


def test_opportunity_ready_is_demoted_when_unresolved_requirements_are_not_external_boundaries(tmp_path,monkeypatch):
    state=_state(); answer=_ready(state); answer["external_boundaries"]=[]
    router,_=_router_for(answer)
    monkeypatch.setattr(needle,"ARTIFACT_ROOT",tmp_path / "artifacts")
    monkeypatch.setattr(needle,"RECEIPTS",tmp_path / "receipt.jsonl")
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    assert result["status"]=="RESEARCH_MORE"
    assert result["reason_code"]=="BUSINESS_OPPORTUNITY_DELIVERABLES_UNRESOLVED"
    assert set(result["affected_question_ids"])=={q["question_id"] for q in state["required_questions"]}


def test_forex_vague_rules_need_more_but_explicit_rules_can_pass():
    rubric=needle.RUBRICS["FOREX_STRATEGY_MISSION_NOTEBOOK_V1"]
    assert "Vague rules" in rubric and "cannot be implemented" in rubric
    state=_state("FOREX")
    answer=_more(state,[state["required_questions"][-1]["question_id"]]); router,_=_router_for(answer)
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    assert result["status"]=="RESEARCH_MORE"
    router,_=_router_for(_ready(state)); result=needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    assert result["status"]=="READY_FOR_DEPARTMENT" and result["next_department"]=="TRADING"


def test_vague_research_more_is_rejected():
    state=_state(); answer=_more(state); answer["requested_research_action"]="Needs more research"
    router,_=_router_for(answer)
    with pytest.raises(ValueError,match="SPECIFIC_REPAIR"):
        needle.verify_readiness(state,deterministic_result=_complete(),router=router)


def test_unavailable_router_blocks_without_fallback():
    state=_state()
    class BrokenRouter:
        def execute_reasoning(self,**kwargs): raise RuntimeError("DURABLE_MODEL_CALL_CONTEXT_REQUIRED")
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=BrokenRouter())
    assert result["status"]=="BLOCKED"
    assert result["reason_code"]=="CANONICAL_MODEL_ROUTE_UNAVAILABLE"
    assert result["error"]=="DURABLE_MODEL_CALL_CONTEXT_REQUIRED"


def test_research_more_repair_reuses_same_notebook_and_creates_no_objective(monkeypatch,tmp_path):
    from research import notebook_playbook_runner as runner
    state=_state(); question=state["required_questions"][0]
    answer=json.dumps({"question_results":[{"question_id":question["question_id"],"evidence_status":"UNVERIFIED"}]})
    synthesis=json.dumps({"synthesis":"Updated evidence remains unresolved.",
        "action_statement":{key:"explicit" for key in contracts.CONTRACTS[state["contract_id"]]["action_fields"]},
        "structured_extraction":{"unresolved":"explicit"}})
    class Adapter:
        def __init__(self): self.notebook_ids=[]
        def _job_slot(self):
            from contextlib import nullcontext
            return nullcontext()
        def ask_notebook(self,notebook_id,prompt):
            self.notebook_ids.append(notebook_id)
            return {"answer":answer if "Synthesize" not in prompt else synthesis,
                "submission_confirmed":True,"submission_attempted":True,
                "references":[{"source_id":"src-1"}]}
        def sources(self,notebook_id): return [{"id":"src-1"}]
    adapter=Adapter(); called={}
    monkeypatch.setattr(runner.cases,"get_case",lambda case_id:{"case_id":case_id,"notebook_workspace":{"notebook_id":"nb-stable"}})
    monkeypatch.setattr(runner.cases,"record_notebook_answer",lambda *a,**k:{"ok":True})
    monkeypatch.setattr(runner,"expand_case_from_best_gap",lambda case_id,**kwargs:
        (called.update(case_id=case_id,notebook=kwargs["adapter"].notebook_id if hasattr(kwargs["adapter"],"notebook_id") else "nb-stable") or
         {"ok":True,"added_sources":[],"receipt_id":"source-repair-1"}))
    monkeypatch.setattr(runner,"persist_completion_state",lambda s,case_id=None:"local-checkpoint")
    result=runner._run_one_needle_repair("case-existing",state=state,adapter=adapter,
        needle=_more(state),max_added_sources=1)
    assert result["ok"] and result["notebook_id"]=="nb-stable"
    assert adapter.notebook_ids==["nb-stable","nb-stable"]
    assert called["case_id"]=="case-existing"
    assert result["return_to_needle_verification"] is True
    assert "owner_objective" not in called


def test_invalid_question_ids_and_wrong_department_are_rejected():
    state=_state(); answer=_more(state,["UNKNOWN_Q"]); router,_=_router_for(answer)
    with pytest.raises(ValueError,match="UNKNOWN_QUESTION"):
        needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    answer=_ready(state); answer["next_department"]="ALPHA"; router,_=_router_for(answer)
    with pytest.raises(ValueError,match="DEPARTMENT_MISMATCH"):
        needle.verify_readiness(state,deterministic_result=_complete(),router=router)


def test_semantic_result_persistence_is_compact_and_transcript_free(tmp_path,monkeypatch):
    state=_state(); router,_=_router_for(_ready(state))
    state["structured_extraction"]={"raw_transcript":"should not reach Needle"}
    state["handoff_package"]=contracts.compact_handoff(state,receipt_id="r")
    assert "should not reach Needle" not in json.dumps(needle._compact_input(state))
    monkeypatch.setattr(needle,"ARTIFACT_ROOT",tmp_path / "artifacts")
    monkeypatch.setattr(needle,"RECEIPTS",tmp_path / "receipt.jsonl")
    result=needle.verify_readiness(state,deterministic_result=_complete(),router=router)
    serialized=json.dumps({k:v for k,v in result.items() if k!="raw_answer"})
    receipt=(tmp_path / "receipt.jsonl").read_text()
    assert "PACKAGE=" not in serialized and "raw_answer" not in serialized and "prompt" not in receipt
    artifact=json.loads((tmp_path / result["artifact_ref"]).read_text())
    assert artifact["prompt"] and artifact["response"]


def test_mechanical_and_semantic_separation_and_v6_stays_stopped():
    assert not hasattr(needle,"alpha_review")
    assert not hasattr(needle,"execute_backtest")
    assert not hasattr(needle,"build_business_plan")
    assert "V6" not in needle.__doc__
