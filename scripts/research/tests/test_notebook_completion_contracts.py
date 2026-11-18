import json
import sys
import types
from research import notebook_completion_contracts as contracts
import nexus_agent_platform


def _complete_state(purpose="MISSION_RESEARCH", domain="BUSINESS_OPPORTUNITY"):
    selected=contracts.select_contract(purpose,domain)
    state=contracts.new_contract_state(objective="Test objective",research_purpose=purpose,
        research_domain=domain,notebook_id="nb-existing",research_job_id="job-1",
        source_inventory=[{"source_id":"src-1","url":"https://example.org","title":"Source"}])
    prompt=contracts.build_required_question_prompt(state)
    assert all(q["question_text"] in prompt for q in state["required_questions"])
    statuses={q["question_id"]:"UNVERIFIED" for q in state["required_questions"]}
    contracts.register_notebook_submission(state,prompt=prompt,submission_confirmed=True,
        response=json.dumps({"question_results":[{"question_id":k,"evidence_status":v} for k,v in statuses.items()]}))
    ids=[q["question_id"] for q in state["required_questions"]]
    contracts.record_gap_review(state,question_ids=ids,supplementation_attempted=True,
        source_refs=["src-1"],unresolved_note="Not verified after bounded source review.",answer_updates=statuses)
    assert all(q["supplementation_attempted"] for q in state["required_questions"])
    contracts.set_synthesis(state,synthesis="Evidence synthesis with uncertainty preserved.",
        action_statement={f:"explicitly classified" for f in selected["action_fields"]},
        structured_extraction={"rules":[{"rule":"example","evidence_status":"UNVERIFIED"}]})
    state["handoff_package"] = contracts.compact_handoff(state, receipt_id="receipt-test")
    return state


def test_purpose_domain_select_four_contracts_deterministically():
    pairs=[("LIBRARY_INTELLIGENCE","BUSINESS_CREATION","BUSINESS_CREATION_NOTEBOOK_V1"),
      ("LIBRARY_INTELLIGENCE","BUSINESS_FUNDING","FUNDING_TECHNIQUE_INTELLIGENCE_NOTEBOOK_V1"),
      ("MISSION_RESEARCH","BUSINESS_OPPORTUNITY","BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1"),
      ("MISSION_RESEARCH","FOREX","FOREX_STRATEGY_MISSION_NOTEBOOK_V1")]
    for purpose,domain,expected in pairs:
        result=contracts.classify_research(objective="arbitrary",research_purpose=purpose,research_domain=domain)
        assert (result["status"],result["contract_id"],result["model_call_required"])==("RESOLVED",expected,False)
        assert contracts.select_contract(purpose,domain)["contract_id"]==expected


def test_ambiguous_intent_is_light_reasoning_extension_point_without_model_call():
    result=contracts.classify_research(objective="look into this")
    assert result["status"]=="AMBIGUOUS" and result["execution_class"]=="LIGHT_REASONING"
    assert result["model_call_required"] is True


def test_all_questions_have_stable_unique_ids():
    for cid,row in contracts.CONTRACTS.items():
        first=[contracts.question_row(cid,q) for q in row["questions"]]
        second=[contracts.question_row(cid,q) for q in row["questions"]]
        assert len({q["question_id"] for q in first})==len(first)
        assert [q["question_id"] for q in first]==[q["question_id"] for q in second]
        assert all(q["required"] and not q["asked"] for q in first)


def test_known_contract_questions_are_selected_without_ai():
    result=contracts.select_contract("MISSION_RESEARCH","FOREX")
    assert result["contract_id"]=="FOREX_STRATEGY_MISSION_NOTEBOOK_V1"
    assert len(result["question_rows"])==len(contracts.CONTRACTS[result["contract_id"]]["questions"])
    assert any("slippage" in q["question_text"].lower() for q in result["question_rows"])


def test_unasked_required_question_blocks_completion():
    state=_complete_state(); state["required_questions"][0]["asked"]=False
    result=contracts.verify_completion(state)
    assert not result["complete"] and result["unasked_question_ids"]==[state["required_questions"][0]["question_id"]]


def test_unverified_can_complete_after_bounded_investigation():
    state=_complete_state(); result=contracts.verify_completion(state)
    assert result["complete"] is True
    assert result["question_counts"]["question_count_unverified"]==len(state["required_questions"])


def test_partial_and_contradicted_evidence_states_are_preserved():
    state=_complete_state(); rows=state["required_questions"]
    rows[0]["evidence_status"]=rows[0]["answer_status"]="PARTIALLY_VERIFIED"
    rows[1]["evidence_status"]=rows[1]["answer_status"]="CONTRADICTED"
    refreshed=contracts._derive_gaps(rows,{g["question_id"]:g for g in state["evidence_gaps"]})
    assert refreshed[0]["evidence_status"]=="PARTIALLY_VERIFIED"
    assert refreshed[1]["evidence_status"]=="CONTRADICTED"


def test_unresolved_question_creates_gap():
    state=contracts.new_contract_state(objective="x",research_purpose="MISSION_RESEARCH",research_domain="FOREX")
    row=state["required_questions"][0]
    contracts.register_notebook_submission(state,prompt=contracts.build_required_question_prompt(state),
        submission_confirmed=True,response="no answer")
    assert state["evidence_gaps"][0]["question_id"]==row["question_id"]
    assert row["evidence_status"]=="UNVERIFIED"


def test_question_status_extraction_accepts_fenced_notebooklm_json():
    state=contracts.new_contract_state(objective="x",research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
    row=state["required_questions"][0]
    answer="```json\n"+json.dumps({"question_results":[{"question_id":row["question_id"],"evidence_status":"PARTIALLY_VERIFIED"}]})+"\n```"
    contracts.register_notebook_submission(state,prompt=f"[{row['question_id']}] {row['question_text']}",
        submission_confirmed=True,response=answer)
    assert row["asked"] and row["evidence_status"]=="PARTIALLY_VERIFIED"


def test_state_persists_notebook_identity_for_reuse(tmp_path,monkeypatch):
    monkeypatch.setattr(contracts,"CONTRACT_STATE_ROOT",tmp_path)
    state=contracts.new_contract_state(objective="x",research_purpose="MISSION_RESEARCH",research_domain="FOREX",notebook_id="same-notebook")
    assert contracts.persist_state(state,case_id="case-1").endswith("case-1.json")
    assert contracts.load_state(case_id="case-1")["notebook_id"]=="same-notebook"


def test_missing_action_statement_blocks_completion():
    state=_complete_state(); state["action_statement"]=None
    assert not contracts.verify_completion(state)["criteria"]["action_statement_present"]


def test_action_statement_requires_contract_fields():
    state=_complete_state(); del state["action_statement"]["NEXT_ACTION"]
    result=contracts.verify_completion(state)
    assert "NEXT_ACTION" in result["missing_action_fields"] and not result["complete"]


def test_business_opportunity_requires_all_25_nonempty_research_deliverables():
    assert len(contracts.BUSINESS_OPPORTUNITY_DELIVERABLES)==25
    state=_complete_state()
    assert set(contracts.BUSINESS_OPPORTUNITY_DELIVERABLES).issubset(state["action_statement"])
    state["action_statement"]["MARKET_DEMAND"]=""
    result=contracts.verify_completion(state)
    assert "MARKET_DEMAND" in result["missing_action_fields"] and not result["complete"]


def test_business_opportunity_compact_handoff_rejects_incomplete_deliverable():
    state=_complete_state()
    del state["action_statement"]["PARTNERS_AND_SUPPLIERS"]
    import pytest
    with pytest.raises(ValueError,match="RESEARCH_HANDOFF_CONTRACT_INCOMPLETE"):
        contracts.compact_handoff(state,receipt_id="receipt-incomplete")


def test_business_opportunity_handoff_records_deliverable_contract_validation():
    state=_complete_state()
    package=contracts.compact_handoff(state,receipt_id="receipt-complete")
    assert package["research_deliverable_contract"]=={
        "version":"nexus-research-deliverable-v1","required_output_count":25,
        "validated":True,"missing_action_fields":[]}


def test_structured_extraction_is_required():
    state=_complete_state(); state["structured_extraction"]=None
    assert not contracts.verify_completion(state)["criteria"]["structured_extraction_present"]


def test_library_distillation_uses_existing_department_knowledge(monkeypatch):
    calls=[]
    fake=types.SimpleNamespace(_write=lambda table,row:(calls.append((table,row)) or (201,[row])))
    monkeypatch.setitem(sys.modules,"nexus_agent_platform.supabase_knowledge",fake)
    # `from nexus_agent_platform import supabase_knowledge` can reuse an
    # already-loaded package attribute during collection-order runs.
    monkeypatch.setattr(nexus_agent_platform,"supabase_knowledge",fake,raising=False)
    state=_complete_state("LIBRARY_INTELLIGENCE","BUSINESS_FUNDING")
    result=contracts.persist_library_entry(state,state["structured_extraction"])
    assert result["status"]=="PERSISTED"
    assert {r["expert_id"] for _,r in calls}=={"CLYDE_CREDIT","GRANT_FUNDING"}
    assert all(t=="department_knowledge" for t,_ in calls)
    assert all("notebook answer" not in json.dumps(r).lower() for _,r in calls)


def test_business_opportunity_handoff_targets_opportunities():
    state=_complete_state(); package=contracts.compact_handoff(state,receipt_id="receipt-1")
    assert package["next_department"]=="BUSINESS_OPPORTUNITIES"
    assert package["contract_id"]=="BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1"
    assert package["question_count_required"]==len(state["required_questions"])


def test_forex_handoff_targets_trading_and_contains_extraction():
    state=_complete_state(domain="FOREX"); package=contracts.compact_handoff(state,receipt_id="r")
    assert package["next_department"]=="TRADING"
    assert package["handoff_payload"]["structured_extraction"]==state["structured_extraction"]


def test_transcript_fields_are_excluded_from_handoff():
    state=_complete_state(); state["action_statement"]["raw_transcript"]="private long answer"
    package=contracts.compact_handoff(state,receipt_id="r")
    assert "raw_transcript" not in json.dumps(package)
    assert package["provenance"]["notebook_id"]=="nb-existing"


def test_handoff_keeps_source_and_receipt_provenance():
    state=_complete_state(); package=contracts.compact_handoff(state,receipt_id="r")
    assert package["provenance"]["source_inventory"][0]["source_id"]=="src-1"
    assert package["provenance"]["receipt_id"]=="r"
    assert "answer" not in json.dumps(package).lower()


def test_deterministic_contract_checks_do_not_call_model_router(monkeypatch):
    fake=types.SimpleNamespace(execute_reasoning=lambda **kwargs: (_ for _ in ()).throw(AssertionError("model called")))
    monkeypatch.setitem(sys.modules,"model_router",fake)
    assert contracts.verify_completion(_complete_state())["complete"]
    assert contracts.select_contract("MISSION_RESEARCH","FOREX")["contract_id"]=="FOREX_STRATEGY_MISSION_NOTEBOOK_V1"


def test_global_supplementation_flag_cannot_hide_unreviewed_gap():
    state=_complete_state(); state["evidence_gaps"][0]["reviewed"]=False
    state["evidence_gaps"][0]["supplementation_attempted"]=False
    result=contracts.verify_completion(state)
    assert not result["criteria"]["all_evidence_gaps_reviewed"]
    assert not result["criteria"]["web_supplementation_attempted_where_appropriate"]


def test_explicit_canary_scope_preserves_unknown_and_marks_web_supplementation_not_applicable():
    state=contracts.new_contract_state(objective="Pricing page process canary",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
    question=state["required_questions"][0]
    contracts.register_notebook_submission(state,prompt=contracts.build_required_question_prompt(state),
        submission_confirmed=True,response="")
    contracts.record_gap_out_of_scope(state,question_id=question["question_id"],
        reason="Out of scope for bounded canary: only visible pricing was tested.")
    gap=next(row for row in state["evidence_gaps"] if row["question_id"]==question["question_id"])
    assert gap["reviewed"] and gap["web_supplementation_not_appropriate"]
    assert gap["evidence_status"]=="UNVERIFIED"
    assert "only visible pricing" in gap["unresolved_note"]


def test_synthesis_action_extraction_and_handoff_provenance_required():
    state=_complete_state(); result=contracts.verify_completion(state)
    assert result["criteria"]["synthesis_present"] and result["criteria"]["action_statement_present"]
    assert result["criteria"]["structured_extraction_present"]
    package=contracts.compact_handoff(state,receipt_id="receipt")
    for key in ("research_job_id","research_purpose","research_domain","contract_id","notebook_id","notebook_status","next_department"):
        assert key in package
    assert package["provenance"]["receipt_id"]=="receipt"


def test_library_completion_requires_successful_distillation():
    state=_complete_state("LIBRARY_INTELLIGENCE","BUSINESS_CREATION")
    assert not contracts.finalize_contract(state,receipt_id="r",library_entry_persisted=False)["ok"]
    assert contracts.finalize_contract(state,receipt_id="r",library_entry_persisted=True)["ok"]


def test_future_purposes_have_clean_unmapped_extension_points():
    assert "CLIENT_SPECIFIC_RESEARCH" in contracts.PURPOSES and "REFRESH_VERIFICATION" in contracts.PURPOSES
    result=contracts.classify_research(objective="research",research_purpose="CLIENT_SPECIFIC_RESEARCH",research_domain="BUSINESS_FUNDING")
    assert result["status"]=="UNMAPPED_PURPOSE_DOMAIN" and not result["model_call_required"]


def test_v6_is_not_resumed_by_contract_module():
    assert not hasattr(contracts,"resume_v6")


def test_business_opportunity_prompt_requires_comparable_per_candidate_answers():
    state=contracts.new_contract_state(objective="Compare online business candidates",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
    prompt=contracts.build_required_question_prompt(state)
    assert "separately for EACH candidate" in prompt
    assert "Do not collapse candidates" in prompt


def test_business_opportunity_question_groups_cover_stable_contract_ids_once():
    state=contracts.new_contract_state(objective="Custom AI agents for restaurant owners",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
    groups=contracts.question_groups(state)
    ids=[row["question_id"] for group in groups for row in group["questions"]]
    expected=[row["question_id"] for row in state["required_questions"]]
    assert [group["group_id"] for group in groups]==[
        "GROUP_A_DEFINITION","GROUP_B_DEMAND","GROUP_C_COMPETITION","GROUP_D_ECONOMICS",
        "GROUP_E_ACQUISITION","GROUP_F_OPERATIONS","GROUP_G_NEXUS_FIT",
        "GROUP_H_RISK_AND_CONTRADICTION","GROUP_I_SELECTION","GROUP_J_BUSINESS_MODELS",
        "GROUP_K_CUSTOMER_AND_DEMAND","GROUP_L_COMPETITION_AND_PRICING","GROUP_M_COSTS_AND_PARTNERS",
        "GROUP_N_COMPLIANCE_AND_CHANNELS","GROUP_O_TECHNOLOGY_AND_GAPS"]
    assert set(ids)==set(expected) and len(set(ids))==len(expected)


def test_group_prompt_contains_only_group_questions_and_stable_ids():
    state=contracts.new_contract_state(objective="Research one opportunity",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
    group=contracts.question_groups(state)[1]
    prompt=contracts.build_question_group_prompt(state,group["group_id"],group["questions"])
    assert "GROUP_B_DEMAND" in prompt
    assert all(row["question_id"] in prompt for row in group["questions"])
    assert all(row["question_id"] not in prompt for row in contracts.question_groups(state)[0]["questions"])
    assert "synthesis" not in prompt.casefold()


def test_synthesis_prompt_compacts_gap_details_without_losing_statuses():
    state=_complete_state()
    for gap in state["evidence_gaps"]:
        gap["unresolved_note"]="x"*1000
        gap["source_refs"]=[f"source-{i}" for i in range(20)]
    prompt=contracts.build_synthesis_prompt(state)
    assert len(prompt.encode()) < 12_000
    assert "VERIFIED" in prompt and "UNVERIFIED" in prompt
    assert "source-19" not in prompt
    assert "x"*500 not in prompt


def test_deliverables_parser_accepts_json_fenced_by_notebooklm():
    value={"synthesis":"preserve unknowns","action_statement":{"NEXT_ACTION":"verify"},
        "structured_extraction":{"evidence_status":"UNVERIFIED"}}
    answer="```json\n"+json.dumps(value)+"\n```"
    assert contracts.extract_deliverables(answer)==value


def test_notebook_transcript_is_local_and_case_state_is_compact(tmp_path,monkeypatch):
    from research import research_case_engine as cases
    monkeypatch.setattr(cases,"ROOT",tmp_path)
    saved={}
    monkeypatch.setattr(cases,"get_case",lambda case_id:{"case_id":case_id,"notebook_answers":[]})
    monkeypatch.setattr(cases,"_save",lambda case,event,**details:(saved.update(details) or {**case,**details}))
    result=cases.record_notebook_answer("case-x",question_type="CONTRACT:test",answer="long notebook answer",
        prompt="long notebook prompt",notebook_id="nb-x",response_id="resp-x")
    assert result["ok"]
    case_answers=saved["notebook_answers"]
    assert "answer" not in case_answers[-1] and "prompt" not in case_answers[-1]
    artifact=tmp_path / case_answers[-1]["local_artifact_ref"]
    body=json.loads(artifact.read_text())
    assert body["answer"]=="long notebook answer" and body["prompt"]=="long notebook prompt"


def test_runner_reconciles_saved_group_statuses_before_research_gap_routing(tmp_path, monkeypatch):
    from research import notebook_playbook_runner as runner

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    state=contracts.new_contract_state(objective="Assess one opportunity",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY",
        notebook_id="nb-dedicated",research_job_id="job-canary")
    rows=state["required_questions"]
    first,second=rows[:2]
    for row in (first,second):
        row["asked"]=True
        row["evidence_status"]=row["answer_status"]="UNVERIFIED"
    state["evidence_gaps"]=contracts._derive_gaps(rows)
    directory=tmp_path/"data/runtime/notebook_answer_artifacts/case"
    directory.mkdir(parents=True)
    answer={"question_results":[
        {"question_id":first["question_id"],"evidence_status":"PARTIALLY_VERIFIED"},
        {"question_id":second["question_id"],"evidence_status":"CONTRADICTED"}]}
    (directory/"answer.json").write_text(json.dumps({"answer":"```json\n"+json.dumps(answer)+"\n```"}),encoding="utf-8")
    case={"notebook_answers":[{"question_type":"CONTRACT_GROUP:CONTRACT:GROUP_A",
        "local_artifact_ref":"data/runtime/notebook_answer_artifacts/case/answer.json",
        "source_ids":["src-1"]}]}
    monkeypatch.setattr(runner,"persist_completion_state",lambda value,case_id: "local:state")
    changed=runner._reconcile_contract_group_statuses("case",state,case)
    assert changed==2
    assert first["evidence_status"]=="PARTIALLY_VERIFIED"
    assert second["evidence_status"]=="CONTRADICTED"
    assert first["source_refs"]==["src-1"]
    assert state["status_reconciled_from_local_notebook_turns"]==2


def test_runner_persists_new_source_in_the_same_dedicated_notebook_manifest(tmp_path,monkeypatch):
    from research import notebook_playbook_runner as runner
    monkeypatch.setattr(runner,"ROOT",tmp_path)
    directory=tmp_path/"data/runtime/dedicated_research_notebooks"
    directory.mkdir(parents=True)
    path=directory/"subject.json"
    path.write_text(json.dumps({"notebook_id":"nb-subject","notebook_role":"DEDICATED_RESEARCH",
        "source_refs":[{"id":"youtube","url":"https://youtube.test/video"}]}),encoding="utf-8")
    assert runner._record_dedicated_notebook_source("case-subject","nb-subject",
        {"source_id":"web-1","notebook_source_id":"web-1","url":"https://official.test/pricing",
         "title":"Official pricing","source_class":"OFFICIAL_PRIMARY_SOURCE"})
    saved=json.loads(path.read_text())
    assert saved["source_refs"][-1]["id"]=="web-1"
    assert saved["source_refs"][-1]["promoted_by_case_id"]=="case-subject"
    assert saved["linked_case_ids"]==["case-subject"]


def test_adaptive_questions_do_not_shift_contract_group_membership():
    from research import notebook_completion_contracts as contracts
    state=contracts.new_contract_state(objective="An online opportunity",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY")
    baseline={row["question_id"] for row in state["required_questions"]}
    original={group["group_id"]:[row["question_id"] for row in group["questions"]]
        for group in contracts.question_groups(state)}
    adaptive=contracts.question_row(state["contract_id"],"Can a lower-cost affiliate route validate customer demand?")
    adaptive["discovery_question"]=True
    state["required_questions"].append(adaptive)
    updated={group["group_id"]:[row["question_id"] for row in group["questions"]]
        for group in contracts.question_groups(state)}
    assert {qid for rows in original.values() for qid in rows}==baseline
    assert all(updated[group]==rows for group,rows in original.items())
    assert updated["GROUP_UNMAPPED_REMAINDER"]==[adaptive["question_id"]]
